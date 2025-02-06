import httpx
import asyncio
import json
import brotli
from typing import Dict, Any, AsyncGenerator
from ..models import UpstreamConfig
from loguru import logger

class OpenAIService:
    def __init__(self, upstream_configs: list[UpstreamConfig]):
        self.upstream_configs = sorted(upstream_configs, key=lambda x: x.priority)
        self.current_upstream_index = 0
        self.tried_upstreams = 0
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"OpenAIService initialized with {len(upstream_configs)} upstream configs")

    async def forward_normal_request(self, path: str, method: str, headers: Dict, json_data: Dict) -> Any:
        # 重置计数器
        self.current_upstream_index = 0
        self.tried_upstreams = 0
        
        while True:
            try:
                current_upstream = self.upstream_configs[self.current_upstream_index]
                logger.info(f"Using upstream config #{self.current_upstream_index + 1} with base URL: {current_upstream.base_url}")
                
                # 替换模型名称
                if "model" in json_data:
                    original_model = json_data["model"]
                    mapped_model = current_upstream.model_mapping.get(original_model, original_model)
                    json_data["model"] = mapped_model
                    logger.info(f"Model mapping: {original_model} -> {mapped_model}")

                # 修复 URL 格式
                base_url = current_upstream.base_url.rstrip('/')
                path = path.lstrip('/')
                url = f"{base_url}/{path}"
                logger.debug(f"Full request URL: {url}")
                
                # 创建新的headers，避免修改原始headers
                request_headers = headers.copy()
                # 移除可能导致问题的headers
                request_headers.pop('host', None)
                request_headers.pop('content-length', None)
                request_headers.pop('authorization', None)
                request_headers['Authorization'] = f"Bearer {current_upstream.api_key}"
                
                logger.debug("Sending request with modified headers")
                try:
                    response = await self.client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        json=json_data,
                        timeout=current_upstream.timeout
                    )
                except httpx.TimeoutException as te:
                    logger.error(f"Request timeout for {url}: {str(te)}")
                    raise
                except httpx.RequestError as re:
                    logger.error(f"Request failed for {url}: {str(re)}")
                    raise
                
                logger.info(f"Response received - Status code: {response.status_code}")
                logger.debug(f"Response headers: {response.headers}")
                
                if response.status_code >= 500:
                    logger.error(f"Upstream server error: {response.status_code}")
                    logger.error(f"Error response body: {response.text}")
                    raise Exception(f"Upstream server error: {response.status_code}")

                try:
                    # 检查响应是否使用了 Brotli 压缩
                    content_encoding = response.headers.get('content-encoding', '').lower()
                    if content_encoding == 'br':
                        try:
                            # 尝试 Brotli 解压缩
                            response_text = brotli.decompress(response.content).decode('utf-8')
                        except Exception as be:
                            # 如果 Brotli 解压缩失败，尝试直接解码内容
                            logger.warning(f"Brotli decompression failed: {str(be)}, trying direct decode")
                            response_text = response.content.decode('utf-8')
                    else:
                        # 使用普通的文本解码
                        response_text = response.text
                    
                    try:
                        response_json = json.loads(response_text)
                    except json.JSONDecodeError as je:
                        logger.error(f"Invalid JSON response: {response_text}")
                        raise Exception("Invalid JSON response from upstream") from je
                        
                    logger.debug(f"Response body: {response_json}")
                    return response_json
                    
                except Exception as e:
                    logger.error(f"Error processing response: {str(e)}")
                    logger.error(f"Response headers: {response.headers}")
                    logger.error(f"Raw response content: {response.content}")
                    raise Exception("Failed to process upstream response") from e

            except Exception as e:
                logger.error(f"Error occurred while forwarding request: {str(e)}", exc_info=True)
                self.tried_upstreams += 1
                logger.warning(f"Switching to next upstream config (tried {self.tried_upstreams}/{len(self.upstream_configs)})")
                self.current_upstream_index = (self.current_upstream_index + 1) % len(self.upstream_configs)
                if self.tried_upstreams >= len(self.upstream_configs):
                    logger.critical("All upstream services failed")
                    raise Exception("All upstream services failed") from e

    async def forward_stream_request(self, path: str, method: str, headers: Dict, json_data: Dict) -> AsyncGenerator[bytes, None]:
        # 重置计数器
        self.current_upstream_index = 0
        self.tried_upstreams = 0
        
        while True:
            try:
                current_upstream = self.upstream_configs[self.current_upstream_index]
                logger.info(f"Using upstream config #{self.current_upstream_index + 1} for stream request")
                
                # 替换模型名称
                if "model" in json_data:
                    original_model = json_data["model"]
                    mapped_model = current_upstream.model_mapping.get(original_model, original_model)
                    json_data["model"] = mapped_model
                    logger.info(f"Stream request model mapping: {original_model} -> {mapped_model}")

                url = f"{current_upstream.base_url}{path}"
                logger.debug(f"Stream request URL: {url}")
                
                # 创建新的headers，避免修改原始headers
                request_headers = headers.copy()
                # 移除可能导致问题的headers
                request_headers.pop('host', None)
                request_headers.pop('content-length', None)
                request_headers.pop('authorization', None)
                request_headers['Authorization'] = f"Bearer {current_upstream.api_key}"
                request_headers['Accept'] = 'text/event-stream'
                request_headers['Cache-Control'] = 'no-cache'
                request_headers['Connection'] = 'keep-alive'
                
                logger.debug("Initiating stream connection")
                async with self.client.stream(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    timeout=current_upstream.timeout
                ) as response:
                    if response.status_code >= 500:
                        logger.error(f"Stream request upstream server error: {response.status_code}")
                        raise Exception(f"Upstream server error: {response.status_code}")
                    
                    logger.info("Stream connection established successfully")
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            logger.debug(f"Received stream data: {line}")
                            yield f"{line}\n\n".encode('utf-8')
                    
                    logger.info("Stream request completed successfully")
                return

            except Exception as e:
                # print stack trace
                import traceback
                traceback.print_exc()
                logger.error(f"Error occurred while forwarding stream request: {str(e)}", exc_info=True)
                self.tried_upstreams += 1
                logger.warning(f"Switching to next upstream config for stream request (tried {self.tried_upstreams}/{len(self.upstream_configs)})")
                self.current_upstream_index = (self.current_upstream_index + 1) % len(self.upstream_configs)
                if self.tried_upstreams >= len(self.upstream_configs):
                    logger.critical("All upstream services failed for stream request")
                    raise Exception("All upstream services failed") from e
    
    async def __del__(self):
        await self.client.aclose()
        logger.info("OpenAIService client closed")