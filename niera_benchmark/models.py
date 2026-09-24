from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class GenerationConfig:
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 2048
    seed: Optional[int] = 42
    # Unset by default, so runs made before these fields existed are unchanged.
    # num_ctx must hold the ~3.3k-token system prompt plus max_tokens; a
    # reasoning model's think block can outgrow Ollama's default window.
    num_ctx: Optional[int] = None
    request_timeout_s: int = 1800

@dataclass
class ModelResponse:
    model: str
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
