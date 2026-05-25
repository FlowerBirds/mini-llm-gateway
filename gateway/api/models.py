from fastapi import APIRouter
from ..models.manager import get_model_manager

router = APIRouter()


@router.get("/anthropic/v1/models")
async def list_models_v1():
    return await _list_models()


@router.get("/anthropic/models")
async def list_models():
    return await _list_models()


async def _list_models():
    model_manager = get_model_manager()
    models = model_manager.get_models()

    result = []
    for model in models:
        if not model.get("enabled", True):
            continue
        result.append({
            "id": model.get("id"),
            "object": "model",
            "type": "chat",
            "created": 1700000000,
            "name": model.get("name"),
            "display_name": model.get("name"),
            "provider": model.get("provider"),
            "enabled": model.get("enabled", True)
        })

    return {"object": "list", "data": result}
