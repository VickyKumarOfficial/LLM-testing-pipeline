import json
import re
from pathlib import Path
from typing import Any, Dict

PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

# Keys that describe the profile itself rather than the student.
_NON_PLACEHOLDER_KEYS = {"profile_id", "profile_note"}


def load_profile(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_value(value: Any) -> str:
    """Flatten a profile value into prompt-ready text.

    Scalars pass through. Lists of strings become bullets. Lists of dicts
    (the knowledge-graph style entries) become one bullet per concept with
    its mastery metadata inline.
    """
    if value is None:
        return "not available"
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                concept = item.get("concept", "")
                parts = []
                if "mastery" in item:
                    parts.append(f"mastery {item['mastery']}")
                if "status" in item:
                    parts.append(str(item["status"]))
                head = f"  - {concept}"
                if parts:
                    head += f" ({', '.join(parts)})"
                lines.append(head)
                for extra_key in ("error_pattern", "evidence"):
                    if item.get(extra_key):
                        label = extra_key.replace("_", " ")
                        lines.append(f"      {label}: {item[extra_key]}")
            else:
                lines.append(f"  - {item}")
        return "\n".join(lines)
    return json.dumps(value, ensure_ascii=False)


def render_system_prompt(template: str, profile: Dict[str, Any]) -> str:
    """Substitute {{placeholders}} in the system prompt from the profile.

    Raises if the template asks for a field the profile does not supply, so a
    run never silently ships literal braces to the model.
    """
    rendered_fields = {
        key: _render_value(value)
        for key, value in profile.items()
        if key not in _NON_PLACEHOLDER_KEYS
    }

    required = set(PLACEHOLDER_RE.findall(template))
    missing = sorted(required - set(rendered_fields))
    if missing:
        raise KeyError(
            "Student profile is missing fields required by the system prompt: "
            + ", ".join(missing)
        )

    def _replace(match: "re.Match[str]") -> str:
        return rendered_fields[match.group(1)]

    return PLACEHOLDER_RE.sub(_replace, template)
