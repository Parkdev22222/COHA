# COHA: CQ-Driven Ontology Harness for Agents

COHA is a three-phase framework that enforces domain-specific ontological constraints on LLM agents using automatically generated competency questions (CQs) and OWL axioms. It targets two application domains: **Smart Building Management** and **Military Tactical Decision Support**.

---

## Table of Contents

1. [Framework Overview](#framework-overview)
2. [Directory Structure](#directory-structure)
3. [Module Descriptions](#module-descriptions)
4. [Installation](#installation)
5. [Running Experiments](#running-experiments)
6. [Output Files](#output-files)
7. [Military Doctrine Sources](#military-doctrine-sources)
8. [Evaluation Metrics](#evaluation-metrics)

---

## Framework Overview

```
Domain Docs + User Stories
         │
         ▼
┌──────────────────────────────────────────────┐
│  Phase 1 — Ontology Builder                  │
│  (select one method)                         │
│                                              │
│  ① CQbyCQ   : CQ generation → OWL axioms    │
│               per CQ → consistency check     │
│  ② Text2Onto: concept/taxonomy/relation      │
│               extraction → OWL synthesis     │
│  ③ OntoGPT  : single-pass YAML schema        │
│               extraction → OWL synthesis     │
│                                              │
│  Output: ontology.ttl (OWL/Turtle)           │
└────────────────────┬─────────────────────────┘
          │ ontology_ttl
          ▼
┌─────────────────────┐
│  Phase 2            │  Harness Compiler
│  Rule Compiler      │  OWL axioms → 4 rule types:
│                     │    INPUT_VALIDATION, OUTPUT_CONSTRAINT,
│                     │    PHASE_GATE, TOOL_SCOPE
└─────────┬───────────┘
          │ HarnessRuleSet
          ▼
┌─────────────────────┐
│  Phase 3            │  Closed-Loop Agent Runtime
│  Agent Runtime      │  InputGate → Context Assembly (FAISS) →
│                     │  LLM → OutputGate (LLM judge) → PhaseGate
└─────────────────────┘
```

### LLM Backend Selection

`UnifiedLLMClient` auto-selects the inference backend from the model name:

| Model name prefix | Backend |
|---|---|
| `claude-*` | Anthropic Messages API |
| anything else | HuggingFace `transformers` pipeline |

Default model: `LGAI-EXAONE/EXAONE-4.0-1.2B`  
To use the Anthropic backend, set `ANTHROPIC_API_KEY` and pass e.g. `--model claude-sonnet-4-6`.

---

## Directory Structure

```
COHA/
├── config.py                   # Global config (model, paths, domain params)
├── llm_client.py               # UnifiedLLMClient — Anthropic + HuggingFace backends
├── run_experiments.py          # CLI entry point
├── requirements.txt
│
├── phase1/                     # Ontology construction pipeline
│   ├── cq_generator.py         # LLM-based competency question generation
│   ├── cqbycq_loop.py          # Iterative CQ→axiom expansion loop (CQbyCQ method)
│   ├── text2onto.py            # Multi-pass concept/relation extraction (Text2Onto method)
│   ├── ontogpt.py              # Single-pass structured schema extraction (OntoGPT method)
│   ├── ontology_builder.py     # Phase 1 orchestrator — dispatches to selected method
│   └── consistency_validator.py# OWL consistency check via owlready2 / HermiT
│
├── phase2/                     # Harness compilation
│   ├── axiom_extractor.py      # Parse Turtle TTL → axiom dicts
│   ├── rule_types.py           # HarnessRule / HarnessRuleSet dataclasses
│   └── harness_compiler.py     # Axiom → rule translation (4 rule types)
│
├── phase3/                     # Agent runtime
│   ├── context_assembly.py     # FAISS index + ontology-guided retrieval
│   ├── gates.py                # InputGate, OutputGate, PhaseGate
│   └── agent_runtime.py        # Full closed-loop query execution
│
├── baselines/                  # Comparison baselines
│   ├── vanilla_agent.py        # Plain LLM, no retrieval
│   ├── rag_agent.py            # Dense retrieval (sentence-transformers + cosine)
│   ├── graphrag_agent.py       # Graph-based community summaries
│   ├── ograg_agent.py          # Ontology-guided RAG (OG-RAG)
│   └── paper_2604_agent.py     # arXiv:2604.00555 replication
│
├── domains/                    # Domain data modules
│   ├── smart_building.py       # HVAC / sensor / energy management domain
│   └── military_tactical.py    # US Army doctrine domain (see §Military Doctrine)
│
├── evaluation/                 # Metrics + evaluator
│   ├── metrics.py              # CVR, TSR, HR, RF, RCT, GO, MSC
│   └── evaluator.py            # Per-agent + comparison table generation
│
├── experiments/                # Experiment runners
│   ├── main_experiment.py      # COHA vs all baselines
│   ├── ablation_study.py       # Gate / ontology ablation variants
│   └── efficiency_benchmark.py # RCT / GO / MSC throughput benchmarks
│
├── cache/                      # Auto-generated (created at runtime)
│   ├── smart_building_ontology.ttl              # CQbyCQ
│   ├── smart_building_text2onto_ontology.ttl    # Text2Onto
│   ├── smart_building_ontogpt_ontology.ttl      # OntoGPT
│   ├── smart_building_manual_ontology.ttl       # hand-crafted reference
│   ├── military_tactical_ontology.ttl
│   ├── military_tactical_text2onto_ontology.ttl
│   ├── military_tactical_ontogpt_ontology.ttl
│   └── military_tactical_manual_ontology.ttl
│
└── results/                    # Auto-generated JSON result files
    ├── smart_building_main_results.json
    ├── military_tactical_main_results.json
    ├── smart_building_ablation_results.json
    └── ...
```

---

## Module Descriptions

### `config.py`
Global settings: `MODEL_NAME`, `ONTOLOGY_METHOD`, `ANTHROPIC_API_KEY`, `DOMAINS_CONFIG`, `EVAL_CONFIG`, `RESULTS_DIR`, `CACHE_DIR`.

### `llm_client.py`
`UnifiedLLMClient` wraps both backends behind a single `generate(system, user, max_tokens)` interface. All heavy imports (`anthropic`, `transformers`, `torch`) are deferred to first use. Includes 3-attempt exponential-backoff retry for both backends.

### Phase 1 — `phase1/`

Three interchangeable ontology construction methods are available, all producing the same output format (`ontology_ttl`, `cqs`, `cq_coverage_rate`, `is_consistent`, `n_iterations`).

#### Method ① CQbyCQ (default)

| File | Role |
|---|---|
| `cq_generator.py` | Prompts the LLM to generate `n` competency questions from domain docs and user stories |
| `cqbycq_loop.py` | Iterates over each CQ: feeds doc + current ontology to LLM, extracts OWL axioms, accumulates incrementally |
| `consistency_validator.py` | Validates OWL consistency after each CQ via owlready2 / HermiT; triggers regeneration on violation |

Pipeline: `generate CQs → for each CQ: generate axioms → validate → accumulate`

#### Method ② Text2Onto

| File | Role |
|---|---|
| `text2onto.py` | `Text2OntoLearner` — 4-step multi-pass extraction pipeline |

Steps:
1. **Concept extraction** — LLM identifies domain entity types (OWL Classes) from raw text
2. **Taxonomy construction** — LLM organises concepts into an is-a (rdfs:subClassOf) hierarchy
3. **Relation extraction** — LLM extracts ObjectProperties (`Domain --prop--> Range`) and DatatypeProperties (`Class .attr: xsd:type`)
4. **OWL synthesis** — assembles extracted elements into valid Turtle

Reference: Cimiano & Völker (2005), *text2onto — A framework for ontology learning and data-driven change discovery*

#### Method ③ OntoGPT

| File | Role |
|---|---|
| `ontogpt.py` | `OntoGPTExtractor` — single-pass structured schema extraction |

Steps:
1. **Structured extraction** — LLM fills a predefined YAML schema (analogous to OntoGPT's LinkML templates) with five named slots: `classes`, `subclass_of`, `object_properties`, `datatype_properties`, `disjoint_classes`
2. **OWL synthesis** — converts the parsed schema into valid Turtle; falls back to manual line-by-line parsing if PyYAML fails

Reference: Caufield et al. (2024), *OntoGPT: A framework for ontology extraction using large language models* — https://github.com/monarch-initiative/ontogpt

#### Method selection and caching

`OntologyBuilder.build(method="cqbycq"|"text2onto"|"ontogpt")` dispatches to the chosen method. Each method writes its own cache file so multiple methods can coexist:

| Method | Cache JSON | Turtle export |
|---|---|---|
| `cqbycq` | `cache/{domain}_ontology.json` | `cache/{domain}_ontology.ttl` |
| `text2onto` | `cache/{domain}_text2onto_ontology.json` | `cache/{domain}_text2onto_ontology.ttl` |
| `ontogpt` | `cache/{domain}_ontogpt_ontology.json` | `cache/{domain}_ontogpt_ontology.ttl` |

### Phase 2 — `phase2/`

| File | Role |
|---|---|
| `axiom_extractor.py` | Regex/string parsing of Turtle TTL to extract classes, object properties, subclass axioms |
| `rule_types.py` | `HarnessRule` dataclass (rule_id, rule_type, trigger, constraint, entity_class, property_name, metadata) and `HarnessRuleSet` container |
| `harness_compiler.py` | Maps each OWL axiom type to a rule type: ObjectProperty domain/range → INPUT_VALIDATION; class definitions → OUTPUT_CONSTRAINT; ordering-sensitive properties → PHASE_GATE; class hierarchy → TOOL_SCOPE |

### Phase 3 — `phase3/`

| File | Role |
|---|---|
| `context_assembly.py` | Builds FAISS index over domain document chunks; ontology-guided retrieval boosts chunks whose entities match the query; falls back to keyword retrieval if FAISS unavailable |
| `gates.py` | **InputGate**: keyword-based entity-type validation; **OutputGate**: LLM-judge checks response assertions against OUTPUT_CONSTRAINT rules; **PhaseGate**: enforces read-before-write ordering via precondition flags |
| `agent_runtime.py` | Per-query pipeline: InputGate → retrieve context → LLM generate → OutputGate → PhaseGate → optional regeneration (up to `max_regeneration_attempts`) |

### Baselines — `baselines/`

| Agent | Description |
|---|---|
| `VanillaAgent` | Zero-context LLM call |
| `RAGAgent` | Top-k cosine retrieval with sentence-transformers |
| `GraphRAGAgent` | Entity graph construction + community summary generation |
| `OGRAGAgent` | Ontology-guided RAG: retrieval score reweighted by ontology relevance |
| `Paper2604Agent` | Replication of the arXiv:2604.00555 approach |

### Evaluation — `evaluation/`

`COHAEvaluator.evaluate_agent(agent, name)` runs the agent over the benchmark QA set and returns all metrics. `compare_all(results)` produces a pandas DataFrame comparison table.

---

## Installation

```bash
pip install -r requirements.txt
```

**For Anthropic backend:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**For HuggingFace backend (default):**  
No API key needed. On first run the model weights are downloaded automatically. GPU is used automatically if available (`device_map="auto"`).

> Note: `LGAI-EXAONE/EXAONE-4.0-1.2B` requires `trust_remote_code=True` (already set in `llm_client.py`).

---

## Running Experiments

### Full experiment suite (both domains, all experiment types):
```bash
python run_experiments.py
```

### Specific experiment and domain:
```bash
# Main comparison (COHA vs all baselines)
python run_experiments.py --experiment main --domain smart_building

# Ablation study
python run_experiments.py --experiment ablation --domain military_tactical

# Efficiency benchmark
python run_experiments.py --experiment efficiency --domain both --n-queries 50
```

### Override the LLM model:
```bash
# Use Anthropic Claude
python run_experiments.py --model claude-sonnet-4-6 --domain smart_building

# Use a different HuggingFace model
python run_experiments.py --model meta-llama/Llama-3.2-1B-Instruct --domain both
```

### Select ontology construction method:
```bash
# Default — CQbyCQ iterative loop (paper method)
python run_experiments.py --onto-method cqbycq

# Text2Onto — multi-pass concept/relation extraction
python run_experiments.py --onto-method text2onto --domain smart_building

# OntoGPT — single-pass structured schema extraction
python run_experiments.py --onto-method ontogpt --domain military_tactical
```

The default method can also be changed permanently in `config.py`:
```python
ONTOLOGY_METHOD = "text2onto"  # "cqbycq" | "text2onto" | "ontogpt"
```

### Skip saving results to disk:
```bash
python run_experiments.py --experiment main --domain smart_building --no-save
```

### Run a single domain directly:
```python
from experiments.main_experiment import run_main_experiment
results = run_main_experiment("military_tactical")
```

---

## Output Files

| Path | Description |
|---|---|
| `cache/{domain}_ontology.json` | Cached Phase 1 result — CQbyCQ (ontology + CQ coverage metrics) |
| `cache/{domain}_ontology.ttl` | Auto-generated OWL ontology — CQbyCQ (Protégé-compatible) |
| `cache/{domain}_text2onto_ontology.json` | Cached Phase 1 result — Text2Onto |
| `cache/{domain}_text2onto_ontology.ttl` | Auto-generated OWL ontology — Text2Onto |
| `cache/{domain}_ontogpt_ontology.json` | Cached Phase 1 result — OntoGPT |
| `cache/{domain}_ontogpt_ontology.ttl` | Auto-generated OWL ontology — OntoGPT |
| `cache/{domain}_manual_ontology.ttl` | Hand-crafted reference ontology for each domain |
| `results/{domain}_main_results.json` | Main experiment: CVR, TSR, HR, RF per agent |
| `results/{domain}_ablation_results.json` | Ablation: metrics per COHA variant |
| `results/{domain}_efficiency_results.json` | RCT, GO, MSC timing benchmarks |

The `.ttl` files are valid OWL 2 / Turtle and can be loaded directly in **Protégé**, **ROBOT**, or any SPARQL endpoint.

---

## Military Doctrine Sources

The `military_tactical` domain is built from publicly available, unclassified US Army doctrine publications. The content covers operational planning, unit capabilities, threat assessment, and rules of engagement.

### Primary Sources

| Document | Full Title | Publisher | URL |
|---|---|---|---|
| **ADP 3-0** (July 2019) | *Operations* | Headquarters, Department of the Army | https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN18010-ADP_3-0-000-WEB-1.pdf |
| **ADP 3-90** (July 2019) | *Offense and Defense* | Headquarters, Department of the Army | https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN18023-ADP_3-90-000-WEB-1.pdf |
| **FM 3-0** (October 2022) | *Operations* | Headquarters, Department of the Army | https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN36290-FM_3-0-000-WEB-1.pdf |

### ROE / Law of Armed Conflict Sources

| Reference | Title / Description |
|---|---|
| **CALL 96-6** | Center for Army Lessons Learned, *Rules of Engagement Handbook* (1996) — EOF/escalation-of-force procedures |
| **FM 27-100, Ch. 8** | *Legal Support to Operations* — ROE authority chains, self-defense categories (unit, individual, national) |
| **FM 100-23, App. D** | *Peace Operations* — weapons states (FREE/TIGHT/HOLD), graduated response, proportionality |

### Content Reflected in the Domain

**From ADP 3-0 (Operations):**
- Eight elements of combat power (Leadership, Information, C2, Movement & Maneuver, Intelligence, Fires, Sustainment, Protection)
- Operations process: plan → prepare → execute → assess
- METT-TC planning factors (Mission, Enemy, Terrain/Weather, Troops, Time, Civil)
- OAKOC terrain analysis (Observation, Avenues of approach, Key terrain, Obstacles, Cover/concealment)
- ASCOPE civil considerations (Areas, Structures, Capabilities, Organizations, People, Events)
- Tenets of Unified Land Operations: simultaneity, depth, synchronization, flexibility
- Competition continuum: competition below armed conflict → armed conflict → return to competition
- Multi-domain operations concept (land, air, maritime, space, cyberspace)

**From ADP 3-90 (Offense and Defense):**
- Offensive operation types: movement to contact, attack, exploitation, pursuit
- Forms of maneuver: envelopment, turning movement, infiltration, penetration, frontal attack
- Defensive operation types: area defense, mobile defense, retrograde
- Task organization: OPCON, TACON, support relationships
- 14 mission types with ADP 3-90 doctrinal subtype hierarchy

**From FM 3-0 (Operations, 2022):**
- 10 unit types with organic weapons systems: Infantry (M4/M249/M240B/Javelin), Armor (M1A2 SEPv3), Mechanized Infantry (M2A4 Bradley), Field Artillery (M109A7/HIMARS/M777), Aviation (AH-64E/UH-60/CH-47), Engineer, Air Defense (Patriot/Avenger/SHORAD), Military Intelligence, Signal, Logistics
- Command echelon hierarchy: Squad (9) → Team (4) → Platoon (35) → Company (140) → Battalion (800) → Brigade (3,500) → Division (15,000–20,000) → Corps (20,000–45,000)
- Combined arms integration principles
- Threat level assessment framework

**From Unclassified ROE / LOAC Materials:**
- Five threat levels with corresponding ROE states:
  - GREEN (no threat) — weapons HOLD, no engagement authority
  - YELLOW (potential) — weapons TIGHT, positive ID required
  - AMBER (probable) — weapons TIGHT, commander authorization required
  - RED (imminent) — weapons FREE, self-defense authorized
  - BLACK (active engagement) — weapons FREE, fire superiority
- Weapons states: FREE (engage without further order), TIGHT (positive ID required), HOLD (do not fire except self-defense)
- Escalation-of-Force (EOF) four-step SHOUT–SHOW–SHOVE–SHOOT sequence
- Hostile act / hostile intent distinction
- Proportionality and necessity requirements under LOAC
- ROE authority chain: National Command Authority → CCDR → JFC → ARFOR → Division → Brigade → Battalion → Company
- Self-defense categories: individual, unit, national

### Benchmark QA Dataset

The `BENCHMARK_QA` list in `domains/military_tactical.py` contains **30 questions** derived from doctrine:

| Category | Count | Example topics |
|---|---|---|
| `roe_verification` | 10 | EOF sequence, weapons state transitions, hostile act/intent, proportionality |
| `situation_assessment` | 10 | METT-TC analysis, threat level determination, terrain evaluation (OAKOC) |
| `command_recommendation` | 10 | Unit employment, combined arms tasks, defensive/offensive mission selection |

Each item includes a `ground_truth` string citing the applicable doctrine section (e.g., "IAW ADP 3-0, Ch. 3" or "Per FM 100-23 App. D").

---

## Evaluation Metrics

| Metric | Name | Description |
|---|---|---|
| **CVR** | Constraint Violation Rate | Fraction of responses that violate ontology constraints (lower is better) |
| **TSR** | Task Success Rate | Fraction of queries answered correctly per LLM judge (higher is better) |
| **HR** | Hallucination Rate | Fraction of responses containing factually unsupported claims |
| **RF** | Response Fidelity | Semantic similarity of response to ground truth |
| **RCT** | Rule Compilation Time | Milliseconds to compile HarnessRuleSet from ontology (Phase 2 efficiency) |
| **GO** | Gate Overhead | Mean additional latency per query introduced by all three gates |
| **MSC** | Multi-step Consistency | Consistency of answers across sequential multi-turn queries |
| **CQ Coverage Rate** | — | Fraction of CQs whose content is reflected in the final ontology |
