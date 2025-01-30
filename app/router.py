from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
from .services.openai_service import OpenAIService
from loguru import logger

router = APIRouter()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def openai_proxy(
    request: Request, 
    path: str,
    authorization: Optional[str] = Header(None)
):

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    
    # path 是否以 /v1 开头，完全由用户配置决定，因此要删除 path 开头的 /v1
    path = path.lstrip('/v1')
    logger.info(f"Forwarding request to path: {path}")
    # 验证 Bearer token
    token = authorization.replace("Bearer ", "")
    if token != request.app.state.settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    json_data = await request.json() if request.method in ["POST", "PUT"] else {}
    
    # 确保输入模型名称为 deepseek-chat
    if "model" in json_data and json_data["model"] != "deepseek-chat":
        raise HTTPException(status_code=400, detail="Only deepseek-chat model is supported")

    service = request.app.state.openai_service
    
    # 如果是流式请求，直接返回 StreamingResponse
    if json_data.get('stream', False):
        return StreamingResponse(
            service.forward_stream_request(
                f"/{path}",
                request.method,
                dict(request.headers),
                json_data
            ),
            media_type='text/event-stream'
        )
    
    # 非流式请求
    response = await service.forward_normal_request(
        f"/{path}",
        request.method,
        dict(request.headers),
        json_data
    )
    
    return JSONResponse(content=response) 