"""Global configuration for COHA v2."""
import os

MODEL_NAME = "LGAI-EXAONE/EXAONE-4.0-1.2B"
MAX_RETRIES = 3
GATE_TIMEOUT = 60.0
N_CQS_PER_SUBDOMAIN = 20  # 20 * 3 subdomains = 60 total

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
