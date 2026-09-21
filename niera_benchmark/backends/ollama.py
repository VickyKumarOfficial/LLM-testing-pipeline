import time
import requests

from niera_benchmark.models import GenerationConfig, ModelResponse
from niera_benchmark.backends.base import ModelBackend

class OllamaBackend(ModelBackend):
    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")

    def generate(self, system_prompt: str, user_prompt: str,
                 config: GenerationConfig) -> ModelResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
            },
        }
        if config.seed is not None:
            payload["options"]["seed"] = config.seed

        started = time.perf_counter()
        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=1800,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        return ModelResponse(
            model=self.model,
            text=message.get("content", ""),
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            latency_ms=latency_ms,
            metadata={
                "backend": "ollama",
                "total_duration_ns": data.get("total_duration"),
                "load_duration_ns": data.get("load_duration"),
                "prompt_eval_duration_ns": data.get("prompt_eval_duration"),
                "eval_duration_ns": data.get("eval_duration"),
                "done_reason": data.get("done_reason"),
            },
        )
