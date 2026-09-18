from abc import ABC, abstractmethod
from niera_benchmark.models import GenerationConfig, ModelResponse

class ModelBackend(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str,
                 config: GenerationConfig) -> ModelResponse:
        raise NotImplementedError
