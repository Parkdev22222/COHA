"""Diagnose why B2-Vanilla produced 0 classes."""
import re
import sys
sys.path.insert(0, ".")
from coha.owl_utils import merge_ontologies, extract_class_names, extract_property_names
from coha.axiom_generator import AxiomGenerator

def clean_turtle(text):
    for marker in ["```turtle", "```ttl"]:
        if marker in text:
            start = text.find(marker) + len(marker)
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text[start:].strip()
    if "```" in text:
        start = text.find("```") + 3
        nl = text.find("\n", start)
        if nl != -1:
            start = nl + 1
        end = text.find("```", start)
        return text[start:end].strip() if end != -1 else text[start:].strip()
    return text.strip()

print("=" * 60)
print("SCENARIO 1: Model returns raw Turtle (no code block)")
print("=" * 60)
raw_turtle = """@prefix : <http://coha.org/military#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
:Unit a owl:Class ; rdfs:label "Unit" .
:InfantryUnit a owl:Class ; rdfs:subClassOf :Unit ."""

result = clean_turtle(raw_turtle)
print(f"cleaned length: {len(result)}")
print(f"classes found: {extract_class_names(result)}")

print()
print("=" * 60)
print("SCENARIO 2: Model returns explanation + Turtle without code block")
print("=" * 60)
explanation_turtle = """Based on the user story, here are the new OWL axioms:

:Mission a owl:Class ; rdfs:label "Mission" .
:OffensiveMission a owl:Class ; rdfs:subClassOf :Mission ."""

result2 = clean_turtle(explanation_turtle)
print(f"cleaned length: {len(result2)}")
print(f"classes found: {extract_class_names(result2)}")

print()
print("=" * 60)
print("SCENARIO 3: Model echoes back existing ontology + adds tiny delta")
print("=" * 60)
# This is the key scenario: model repeats existing ontology
existing = "@prefix : <http://coha.org/military#> .\n:Unit a owl:Class ."
echoed_response = existing + "\n# New additions:\n:Mission a owl:Class ."
result3 = clean_turtle(echoed_response)
print(f"cleaned length: {len(result3)}")
print(f"classes found: {extract_class_names(result3)}")

print()
print("=" * 60)
print("SCENARIO 4: Model says 'no new axioms needed'")
print("=" * 60)
no_new = "The existing ontology already covers this competency question. No new axioms are needed."
result4 = clean_turtle(no_new)
print(f"cleaned: {repr(result4[:80])}")
acc = merge_ontologies("", result4)
print(f"after merge, classes: {extract_class_names(acc)}")

print()
print("=" * 60)
print("SCENARIO 5: Model generates empty code block")
print("=" * 60)
empty_block = "```turtle\n```"
result5 = clean_turtle(empty_block)
print(f"cleaned: {repr(result5)}")
print(f"truthy: {bool(result5)}")  # if falsy, Vanilla skips merge

print()
print("=" * 60)
print("SCENARIO 6: Model generates valid turtle in code block")
print("=" * 60)
valid_block = "```turtle\n:Platoon a owl:Class ; rdfs:subClassOf :Unit .\n```"
result6 = clean_turtle(valid_block)
print(f"cleaned: {repr(result6)}")
print(f"classes: {extract_class_names(result6)}")

print()
print("=" * 60)
print("ACCUMULATION TEST: what happens after 3 CQs with 'no new axioms' response")
print("=" * 60)
acc = ""
for i in range(3):
    delta = clean_turtle("No new axioms needed for this CQ.")
    print(f"  CQ {i+1}: delta={repr(delta[:30])}, truthy={bool(delta)}")
    if delta:
        acc = merge_ontologies(acc, delta)
print(f"Final classes: {extract_class_names(acc)}")
print(f"Final acc length: {len(acc)}")
