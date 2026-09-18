from typing import Dict, Any

def basic_evaluation(test: Dict[str, Any], response_text: str) -> Dict[str, Any]:
    # Intentionally conservative for v0.1:
    # semantic scoring is not claimed until the frozen question set and
    # subject-aware evaluators are implemented.
    return {
        "non_empty": bool(response_text.strip()),
        "expected_behavior_reference": test.get("expected_behavior", ""),
        "semantic_evaluation": "PENDING",
    }
