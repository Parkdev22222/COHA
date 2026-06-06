"""
Baseline: Paper 2604 Agent (arXiv:2604.00555 style).

Implements a three-layer ontology-constrained agent inspired by arXiv:2604.00555.
Uses Role/Domain/Interaction layers from a manual ontology, with input gate only.
No automated ontology generation; manual ontology is required.
"""

import re
import time
import logging

from llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


class Paper2604Agent:
    """
    Baseline agent inspired by arXiv:2604.00555 — three-layer manual ontology approach.

    Uses a structured three-layer ontology framework:
    - Role Layer: Agent roles and their capabilities
    - Domain Layer: Domain entities, relationships, and constraints
    - Interaction Layer: Rules governing agent-environment interactions

    Input gate validates entity types using the manual ontology.
    No automated ontology construction or output gate.
    """

    def __init__(self, llm_client: UnifiedLLMClient, ontology_ttl: str):
        """
        Initialize the Paper 2604 agent.

        Args:
            llm_client: UnifiedLLMClient instance.
            ontology_ttl: Manual OWL ontology in Turtle format (required).
        """
        self.llm_client = llm_client
        self.ontology_ttl = ontology_ttl

        # Build three-layer representation from ontology
        self._role_layer = self._extract_role_layer(ontology_ttl)
        self._domain_layer = self._extract_domain_layer(ontology_ttl)
        self._interaction_layer = self._extract_interaction_layer(ontology_ttl)

        # Compile system prompt from three layers
        self._system_prompt = self._build_system_prompt()

    def _extract_role_layer(self, ttl: str) -> dict:
        """
        Extract Role Layer from ontology: agent roles and capabilities.

        Args:
            ttl: OWL ontology in Turtle format.

        Returns:
            Dict mapping role names to their inferred capabilities.
        """
        roles = {}

        # Find agent-like classes
        agent_patterns = ["Agent", "Controller", "Manager", "System", "Unit", "Commander"]
        class_pattern = re.compile(r":([A-Z][a-zA-Z0-9]+)\s+a\s+owl:Class", re.MULTILINE)

        for m in class_pattern.finditer(ttl):
            cls_name = m.group(1)
            if any(kw in cls_name for kw in agent_patterns):
                # Infer capabilities from class name
                if any(kw in cls_name.lower() for kw in ["sensor", "monitor"]):
                    capabilities = ["observe", "report", "detect_anomaly"]
                elif any(kw in cls_name.lower() for kw in ["actuator", "control"]):
                    capabilities = ["command", "activate", "deactivate", "set_parameter"]
                elif any(kw in cls_name.lower() for kw in ["unit", "commander"]):
                    capabilities = ["assess", "issue_order", "request_support"]
                elif any(kw in cls_name.lower() for kw in ["manager", "system"]):
                    capabilities = ["monitor", "command", "report", "optimize"]
                else:
                    capabilities = ["observe", "respond"]
                roles[cls_name] = capabilities

        # Default role if none found
        if not roles:
            roles["DefaultAgent"] = ["observe", "respond", "report"]

        return roles

    def _extract_domain_layer(self, ttl: str) -> dict:
        """
        Extract Domain Layer: entities, properties, and constraints.

        Args:
            ttl: OWL ontology in Turtle format.

        Returns:
            Dict with 'entities', 'properties', and 'constraints'.
        """
        entities = []
        properties = []
        constraints = []

        # Extract classes
        class_pattern = re.compile(r":([A-Z][a-zA-Z0-9]+)\s+a\s+owl:Class", re.MULTILINE)
        for m in class_pattern.finditer(ttl):
            entities.append(m.group(1))

        # Extract object properties
        prop_pattern = re.compile(
            r":([a-z][a-zA-Z0-9]+)\s+a\s+owl:ObjectProperty", re.MULTILINE
        )
        for m in prop_pattern.finditer(ttl):
            properties.append(m.group(1))

        # Extract data properties
        dprop_pattern = re.compile(
            r":([a-z][a-zA-Z0-9]+)\s+a\s+owl:DatatypeProperty", re.MULTILINE
        )
        for m in dprop_pattern.finditer(ttl):
            properties.append(m.group(1))

        # Extract subclass axioms as constraints
        subclass_pattern = re.compile(
            r":([A-Z][a-zA-Z0-9]+)\s+rdfs:subClassOf\s+:([A-Z][a-zA-Z0-9]+)",
            re.MULTILINE,
        )
        for m in subclass_pattern.finditer(ttl):
            constraints.append(f"{m.group(1)} is a subtype of {m.group(2)}")

        # Extract rdfs:comment constraints
        comment_pattern = re.compile(r'rdfs:comment\s+"([^"]+)"', re.MULTILINE)
        for m in comment_pattern.finditer(ttl):
            comment = m.group(1)
            if any(kw in comment.lower() for kw in ["must", "require", "only", "valid", "cannot", "min", "max"]):
                constraints.append(comment)

        return {
            "entities": entities,
            "properties": properties,
            "constraints": constraints[:20],  # Cap at 20 for prompt length
        }

    def _extract_interaction_layer(self, ttl: str) -> list:
        """
        Extract Interaction Layer: rules governing agent-environment interaction.

        Args:
            ttl: OWL ontology in Turtle format.

        Returns:
            List of interaction rule strings.
        """
        rules = []

        # Extract domain/range pairs as interaction rules
        domain_pattern = re.compile(
            r":([a-z][a-zA-Z0-9]+).*?rdfs:domain\s+:([A-Z][a-zA-Z0-9]+).*?rdfs:range\s+:([A-Z][a-zA-Z0-9]+)",
            re.DOTALL,
        )
        for m in domain_pattern.finditer(ttl):
            prop, dom, rng = m.group(1), m.group(2), m.group(3)
            rules.append(f"Property '{prop}' links {dom} entities to {rng} entities")

        # Extract cardinality rules
        max_card_pattern = re.compile(r"owl:maxCardinality\s+(\d+)", re.MULTILINE)
        for m in max_card_pattern.finditer(ttl):
            rules.append(f"Cardinality constraint: maximum {m.group(1)} value(s) allowed")

        # Domain-specific operational rules from comments
        comment_pattern = re.compile(r'rdfs:comment\s+"([^"]+)"', re.MULTILINE)
        for m in comment_pattern.finditer(ttl):
            c = m.group(1)
            if len(c) > 30 and any(kw in c.lower() for kw in ["if", "when", "must", "requires"]):
                rules.append(c)

        return rules[:15]

    def _build_system_prompt(self) -> str:
        """
        Build the three-layer system prompt for the LLM.

        Returns:
            System prompt string encoding all three layers.
        """
        # Role Layer
        roles_text = "\n".join(
            f"  - {role}: {', '.join(caps)}"
            for role, caps in self._role_layer.items()
        )

        # Domain Layer
        entities_text = ", ".join(self._domain_layer["entities"][:15])
        constraints_text = "\n".join(
            f"  - {c}" for c in self._domain_layer["constraints"][:10]
        )

        # Interaction Layer
        interactions_text = "\n".join(
            f"  - {rule}" for rule in self._interaction_layer[:10]
        )

        system_prompt = f"""You are an ontology-constrained AI agent operating under a three-layer framework.

## ROLE LAYER
Available agent roles and capabilities:
{roles_text if roles_text else "  - Agent: observe, respond, report"}

## DOMAIN LAYER
Domain entity types: {entities_text if entities_text else "as defined in the ontology"}

Domain constraints:
{constraints_text if constraints_text else "  - Follow domain-specific operational rules"}

## INTERACTION LAYER
Interaction rules governing your responses:
{interactions_text if interactions_text else "  - Reference only ontology-defined entities"}

## INSTRUCTIONS
- Respond only about entities defined in the Domain Layer
- Apply all constraints from the Domain Layer
- Follow interaction rules from the Interaction Layer
- Do not introduce entities or relationships not present in the ontology
- Validate all numerical values against domain constraints before reporting"""

        return system_prompt

    def _validate_input(self, query: str) -> bool:
        """
        Validate query against the Role and Domain layers.

        Checks that entity types mentioned in the query are present
        in the ontology's domain layer.

        Args:
            query: User query string.

        Returns:
            True if query appears to reference valid domain entities.
        """
        query_lower = query.lower()
        entities = self._domain_layer["entities"]

        # Check for entity type mentions
        for entity in entities:
            if entity.lower() in query_lower:
                return True
            # Check word fragments
            words = re.findall(r"[A-Z][a-z]+|[a-z]+", entity)
            if any(w.lower() in query_lower for w in words if len(w) > 3):
                return True

        # Allow if query contains domain-generic terms
        generic_terms = [
            "zone", "sensor", "temperature", "unit", "mission", "command",
            "energy", "meter", "hvac", "threat", "roe", "terrain", "actuator",
        ]
        return any(term in query_lower for term in generic_terms)

    def run(self, query: str) -> dict:
        """
        Generate a response using the three-layer ontology framework.

        Validates input via the Role/Domain layers, then generates
        a response with the ontology-encoded system prompt.

        Args:
            query: User query string.

        Returns:
            dict with keys:
                - response: str — LLM-generated response
                - latency_ms: float — total wall-clock time in milliseconds
        """
        t_start = time.time()

        # Input gate using three-layer validation
        input_valid = self._validate_input(query)

        if not input_valid:
            response = (
                "Query rejected: the entities referenced in your query are not "
                "recognized in the domain ontology. Please rephrase using valid "
                "domain entity types."
            )
        else:
            response = self._call_llm(query)

        latency_ms = (time.time() - t_start) * 1000

        return {
            "response": response,
            "latency_ms": latency_ms,
        }

    def _call_llm(self, query: str) -> str:
        """Call the LLM with the three-layer system prompt."""
        try:
            return self.llm_client.generate(
                system=self._system_prompt, user=query, max_tokens=1024
            )
        except RuntimeError as e:
            logger.error(f"Paper2604Agent LLM call failed: {e}")
            return f"[Error: LLM call failed: {e}]"


if __name__ == "__main__":
    from llm_client import get_client
    from domains.smart_building import MANUAL_ONTOLOGY_TTL

    client = get_client()
    agent = Paper2604Agent(client, MANUAL_ONTOLOGY_TTL)

    result = agent.run("Zone B-103 reads 28.5°C with setpoint 22°C. What HVAC command?")
    print(f"Response: {result['response'][:300]}")
    print(f"Latency: {result['latency_ms']:.0f} ms")
