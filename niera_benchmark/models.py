from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class GenerationConfig:
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 2048
    seed: Optional[int] = 42

@dataclass
class ModelResponse:
    model: str
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
