import ipaddress
import json

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from common.choices import RunStatus, ResultStatus
from projects.models import Project
from regressions.models import Regression, RegressionRun
from regressions.services import get_next_run_number
from results.models import Result
from results.services import get_or_create_signature, recalculate_run_counters


# Whitelisted CIDRs for secure ingestion
WHITELISTED_CIDRS = [
    "127.0.0.0/8",      # Localhost
    "10.0.0.0/8",       # Secure compute grid A
    "192.168.0.0/16",   # Secure compute grid B
    "172.16.0.0/12",    # Docker / container ranges
]


@method_decorator(csrf_exempt, name="dispatch")
class ImportRunView(View):
    def post(self, request, *args, **kwargs):
        # Dual-Layer Security Shield: Layer 1 - CIDR Network Whitelisting
        client_ip = self._get_client_ip(request)
        if not self._is_ip_whitelisted(client_ip):
            return JsonResponse({"error": f"Forbidden: IP {client_ip} is not in the secure subnet whitelist."}, status=403)

        # Dual-Layer Security Shield: Layer 2 - Token Authentication
        api_token = request.headers.get("X-Aura-API-Token")
        expected_token = getattr(settings, "SPECTRA_DV_API_TOKEN", "AURA-SECURE-TOKEN-12345")
        if api_token != expected_token:
            return JsonResponse({"error": "Unauthorized: Invalid or missing API Token."}, status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        project_name = payload.get("project_name")
        regression_name = payload.get("regression_name")

        if not project_name or not regression_name:
            return JsonResponse({"error": "Missing project_name or regression_name."}, status=400)

        # Build run safely
        try:
            with transaction.atomic():
                # Dynamic Project Resolution
                project, _ = Project.objects.get_or_create(
                    name=project_name,
                    defaults={"description": f"Automatically registered project for {project_name}"}
                )

                # Dynamic Regression Suite Resolution
                regression, _ = Regression.objects.get_or_create(
                    project=project,
                    name=regression_name,
                    defaults={"description": f"Automated regression suite for {regression_name}"}
                )

                run_number = get_next_run_number(regression)
                
                run = RegressionRun.objects.create(
                    regression=regression,
                    run_number=run_number,
                    run_name=payload.get("run_name", ""),
                    branch_name=payload.get("branch_name", ""),
                    suite_name=payload.get("suite_name", ""),
                    config_name=payload.get("config_name", ""),
                    build_id=payload.get("build_id", ""),
                    git_commit=payload.get("git_commit", ""),
                    status=payload.get("status", RunStatus.COMPLETED)
                )

                results_data = payload.get("results", [])
                result_objects = []
                
                # Pre-caching signatures to avoid DB queries inside the loop
                signature_cache = {}

                for res in results_data:
                    sig_title = res.get("signature_title")
                    signature_instance = None

                    if sig_title and res.get("status") == "fail":
                        if sig_title not in signature_cache:
                            sig_inst, _ = get_or_create_signature(
                                regression_run=run,
                                title=sig_title,
                                description=res.get("error_message", "")
                            )
                            signature_cache[sig_title] = sig_inst
                        signature_instance = signature_cache[sig_title]

                    result_objects.append(Result(
                        regression_run=run,
                        test_name=res.get("test_name", "Unknown Test"),
                        status=res.get("status", ResultStatus.UNKNOWN),
                        seed=res.get("seed", ""),
                        duration_seconds=res.get("duration_seconds"),
                        machine_name=res.get("machine_name", ""),
                        error_message=res.get("error_message", ""),
                        failure_signature=signature_instance
                    ))

                # Scalability: Use bulk_create for thousands of results
                Result.objects.bulk_create(result_objects, batch_size=1000)

                # Recompute overall run counters and signature counts
                recalculate_run_counters(run)
                
                from results.services import update_signature_counts
                for sig in signature_cache.values():
                    update_signature_counts(sig)

            return JsonResponse({
                "message": "Successfully imported regression run.",
                "run_id": run.pk,
                "run_number": run.run_number
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _is_ip_whitelisted(self, client_ip):
        if not client_ip:
            return False
        try:
            ip = ipaddress.ip_address(client_ip)
            for cidr in WHITELISTED_CIDRS:
                if ip in ipaddress.ip_network(cidr):
                    return True
        except ValueError:
            return False
        return False
