import json
import random
import re
import time
import urllib.request
import urllib.error
import sys
import os

API_URL = "http://127.0.0.1:8000/api/v1/import/run/"
API_TOKEN = "AURA-SECURE-TOKEN-12345"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "parser_config.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def generate_mock_log(test_id):
    """Generate a messy, simulated EDA log file in memory."""
    lines = [
        f"Starting Simulation...",
        f"TEST_NAME=test_alu_random_{test_id}",
        f"Some random build output...",
        f"SVSEED={random.randint(1000, 9999)}"
    ]
    
    is_pass = random.random() < 0.90
    if is_pass:
        lines.append("UVM_INFO @ 120ns : reporter [TEST_DONE] TEST PASSED")
    else:
        error_types = ["ALU_MISMATCH", "TIMEOUT", "MEM_CORRUPTION"]
        err = random.choice(error_types)
        lines.append(f"UVM_ERROR @ 500ns : reporter [{err}] Expected value did not match actual.")
    
    return "\n".join(lines)

def parse_single_log_content(log_content, config):
    """Parses a single log's content and returns a result dict."""
    vcs_rules = config["parsers"]["vcs_uvm"]
    
    re_project_name = re.compile(vcs_rules.get("project_name", "(?:#\\s*)?PROJECT_NAME=(.*)"))
    re_regression_name = re.compile(vcs_rules.get("regression_name", "(?:#\\s*)?REGRESSION_NAME=(.*)"))
    re_test_name = re.compile(vcs_rules["test_name"])
    re_seed = re.compile(vcs_rules["seed"])
    re_pass = re.compile(vcs_rules["pass"])
    re_fail = re.compile(vcs_rules["fail"])

    project_name = "4-Bit Binary Counter"
    regression_name = "Counter_Random_Seed_Regression"
    test_name = "unknown_test"
    seed = ""
    status = "unknown"
    error_msg = ""
    sig_title = ""
    
    for line in log_content.split("\n"):
        line = line.strip()
        m_proj = re_project_name.search(line)
        if m_proj:
            project_name = m_proj.group(1).strip()
            
        m_reg = re_regression_name.search(line)
        if m_reg:
            regression_name = m_reg.group(1).strip()
            
        m_name = re_test_name.search(line)
        if m_name:
            test_name = m_name.group(1).strip()
        
        m_seed = re_seed.search(line)
        if m_seed:
            seed = m_seed.group(1).strip()
            
        if re_pass.search(line):
            status = "pass"
            
        m_fail = re_fail.search(line)
        if m_fail:
            status = "fail"
            sig_title = m_fail.group(1).strip()
            error_msg = line

    return {
        "project_name": project_name,
        "regression_name": regression_name,
        "test_name": test_name,
        "seed": seed,
        "status": status,
        "error_message": error_msg,
        "signature_title": sig_title,
        "duration_seconds": round(random.uniform(1.0, 50.0), 2),
        "machine_name": f"node-{random.randint(1,10)}"
    }

def parse_mock_logs(num_logs, config):
    results = []
    for i in range(num_logs):
        log_content = generate_mock_log(i)
        res = parse_single_log_content(log_content, config)
        if res["test_name"] == "unknown_test":
            res["test_name"] = f"unknown_test_{i}"
        results.append(res)
    return results

def parse_real_logs(directory, config):
    """Scans a directory for log files and parses them."""
    results = []
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return results

    for filename in os.listdir(directory):
        if filename.endswith(".log"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            res = parse_single_log_content(content, config)
            if res["test_name"] == "unknown_test":
                res["test_name"] = filename
            results.append(res)
            
    return results

def main():
    print("Loading parser config...")
    config = load_config()
    
    start_parse = time.time()
    
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
        print(f"Scanning directory '{log_dir}' for real log files...")
        results = parse_real_logs(log_dir, config)
    else:
        num_logs = 1000
        print(f"Simulating streaming and parsing {num_logs} mock log files...")
        results = parse_mock_logs(num_logs, config)
        
    parse_time = time.time() - start_parse
    print(f"Parsing complete in {parse_time:.3f} seconds. Parsed {len(results)} files.")
    
    if not results:
        print("No logs parsed, exiting.")
        return
    
    project_name = results[0]["project_name"] if results else "4-Bit Binary Counter"
    regression_name = results[0]["regression_name"] if results else "Counter_Random_Seed_Regression"
    
    payload = {
        "project_name": project_name,
        "regression_name": regression_name,
        "run_name": "Nightly CI Pipeline",
        "branch_name": "main",
        "suite_name": "full_chip_suite",
        "config_name": "default",
        "build_id": f"build-{int(time.time())}",
        "git_commit": "abc1234",
        "status": "completed",
        "results": results
    }
    
    print("Transmitting JSON payload securely to Spectra-DV...")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Aura-API-Token", API_TOKEN)
    
    start_tx = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode())
            tx_time = time.time() - start_tx
            print(f"Server response: {resp_data}")
            print(f"Transmission and DB ingestion complete in {tx_time:.3f} seconds.")
            print(f"Total end-to-end time: {parse_time + tx_time:.3f} seconds.")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()
