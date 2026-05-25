from typing import Any, Dict
from ..models.provider import Provider


class DeepSeekProvider(Provider):
    @property
    def provider_name(self) -> str:
        return "deepseek"

    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def get_base_url(self) -> str:
        return "https://api.deepseek.com"

    def get_model_id(self, model_key: str) -> str:
        return "deepseek-chat"

    def transform_request(self, request: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        return {
            "model": self.get_model_id(model_key),
            "messages": request.get("messages", []),
            "max_tokens": request.get("max_tokens", 1024),
            "stream": request.get("stream", False),
            "temperature": request.get("temperature", 1.0)
        }

    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": response.get("id", ""),
            "model": response.get("model", ""),
            "role": "assistant",
            "content": response.get("choices", [{}])[0].get("message", {}).get("content", ""),
            "stop_reason": response.get("choices", [{}])[0].get("finish_reason", "stop"),
            "usage": response.get("usage", {})
        }
