"""
Global configuration for the COHA (CQ-Driven Ontology Harness for Agents) experiment framework.
"""

import os

# Anthropic API configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL_NAME = "LGAI-EXAONE/EXAONE-4.0-1.2B-Instruct"

# Ontology builder parameters
MAX_CQ_COUNT = 10
MAX_RETRY = 3
GATE_TIMEOUT = 30.0  # seconds

# Domain configurations
DOMAINS_CONFIG = {
    "smart_building": {
        "name": "Smart Building Management",
        "description": "Intelligent building management system with HVAC, sensors, actuators, and energy monitoring",
        "n_cqs": 10,
        "n_benchmark_qa": 30,
        "task_types": ["anomaly_detection", "control_command", "energy_optimization"],
    },
    "military_tactical": {
        "name": "Military Tactical QA",
        "description": "Military tactical decision support with units, missions, ROE, threats, and terrain",
        "n_cqs": 10,
        "n_benchmark_qa": 30,
        "task_types": ["roe_verification", "situation_assessment", "command_recommendation"],
    },
}

# Evaluation configuration
EVAL_CONFIG = {
    "llm_judge_model": MODEL_NAME,
    "retrieval_k": 5,
    "max_regeneration_attempts": 3,
    "embedding_model": "all-MiniLM-L6-v2",
}

# Results directory
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# Cache directory for ontologies
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
