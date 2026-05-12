"""Settings package for Spectra-DV.

Import development settings for compatibility with older local run
configurations that still use DJANGO_SETTINGS_MODULE=spectra_dv.settings.
Production deployments should use spectra_dv.settings.prod explicitly.
"""

from .dev import *  # noqa: F403
