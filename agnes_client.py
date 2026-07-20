"""
智造AI创意工坊 - Agnes AI API 客户端
支持多 API Key 轮换，突破 RPM 限制
"""
import random
import httpx
from config import (
    AGNES_API_KEYS,
    AGNES_BASE_URL,
    IMAGE_MODEL,
    VIDEO_MODEL,
    IMAGE_TIMEOUT,
    VIDEO_TIMEOUT,
    VIDEO_NUM_FRAMES_MAP,
    VIDEO_FRAME_RATE,
)


class AgnesClient:
    """Agnes AI API 客户端，支持多 Key 轮换"""

    def __init__(self):
        self.base_url = AGNES_BASE_URL
        self.api_keys = AGNES_API_KEYS
        self.client = httpx.AsyncClient(
            timeout=IMAGE_TIMEOUT,
            limits=httpx.Limits(max_connections=100),
            verify=False,
        )

    def _get_headers(self):
        """随机选择一个 API Key"""
        key = random.choice(self.api_keys)
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def _request_with_retry(self, method, url, json_data=None, params=None, max_retries=3):
        """
        带重试的请求
        - 401: 换一个 Key 重试
        - 503: 等 2 秒后重试
        - 其他: 直接返回错误
        """
        for attempt in range(max_retries):
            headers = self._get_headers()
            kwargs = {"headers": headers}
            if json_data:  # 非空字典才传 json 参数
                kwargs["json"] = json_data
            if params is not None:
                kwargs["params"] = params
            try:
                if method == "POST":
                    response = await self.client.post(url, **kwargs)
                elif method == "GET":
                    response = await self.client.get(url, **kwargs)
                else:
                    response = await self.client.request(method, url, **kwargs)

                # 成功
                if response.status_code == 200:
                    return response.json()

                # 401: 认证失败，换 Key 重试
                if response.status_code == 401:
                    continue

                # 503: 服务繁忙，等 2 秒重试
                if response.status_code == 503:
                    import asyncio
                    await asyncio.sleep(2)
                    continue

                # 其他错误直接返回
                response.raise_for_status()

            except httpx.ReadTimeout:
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
                return {"error": f"请求超时 (尝试 {attempt + 1}/{max_retries})"}
            except Exception as e:
                return {"error": f"请求失败: {str(e)}"}

        return {"error": "所有 API Key 均认证失败或服务繁忙"}

    async def text_to_image(self, prompt, size="1024x1024", ratio="1:1"):
        """文生图"""
        try:
            payload = {
                "model": IMAGE_MODEL,
                "prompt": prompt,
                "size": size,
                "extra_body": {"response_format": "url"},
            }
            if size in ["1K", "2K", "3K", "4K"]:
                payload["ratio"] = ratio

            data = await self._request_with_retry(
                "POST",
                f"{self.base_url}/images/generations",
                payload,
            )

            if isinstance(data, dict) and data.get("error"):
                return data
            if data.get("data") and len(data["data"]) > 0:
                return {"url": data["data"][0].get("url")}
            return {"error": "API返回数据为空"}

        except Exception as e:
            return {"error": f"生成失败: {str(e)}"}

    async def image_to_image(self, prompt, image_url, size="1024x1024", ratio="1:1"):
        """图生图"""
        try:
            payload = {
                "model": IMAGE_MODEL,
                "prompt": prompt,
                "size": size,
                "extra_body": {
                    "image": [image_url],
                    "response_format": "url",
                },
            }
            if size in ["1K", "2K", "3K", "4K"]:
                payload["ratio"] = ratio

            data = await self._request_with_retry(
                "POST",
                f"{self.base_url}/images/generations",
                payload,
            )

            if isinstance(data, dict) and data.get("error"):
                return data
            if data.get("data") and len(data["data"]) > 0:
                return {"url": data["data"][0].get("url")}
            return {"error": "API返回数据为空"}

        except Exception as e:
            return {"error": f"编辑失败: {str(e)}"}

    async def create_video_task(self, prompt, image_url=None, ratio="4:3", duration=5):
        """创建视频生成任务"""
        try:
            num_frames = VIDEO_NUM_FRAMES_MAP.get(duration, 121)

            # 根据比例映射宽高
            ratio_map = {
                "1:1": (768, 768),
                "3:4": (768, 1024),
                "4:3": (1024, 768),
                "16:9": (1280, 720),
                "9:16": (720, 1280),
                "2:3": (768, 1152),
                "3:2": (1152, 768),
                "21:9": (1280, 544),
            }
            width, height = ratio_map.get(ratio, (1152, 768))

            payload = {
                "model": VIDEO_MODEL,
                "prompt": prompt,
                "height": height,
                "width": width,
                "num_frames": num_frames,
                "frame_rate": VIDEO_FRAME_RATE,
            }

            if image_url:
                payload["image"] = image_url

            data = await self._request_with_retry(
                "POST",
                f"{self.base_url}/videos",
                payload,
            )

            if isinstance(data, dict) and data.get("error"):
                return data

            # 检查队列已满
            if data.get("code") == "video_queue_full":
                return {"error": "视频队列已满，请稍后重试"}

            return {
                "task_id": data.get("task_id"),
                "video_id": data.get("video_id"),
                "status": data.get("status", "queued"),
                "seconds": data.get("seconds", duration),
                "size": data.get("size"),
            }

        except Exception as e:
            return {"error": f"创建任务失败: {str(e)}"}

    async def poll_video_result(self, video_id):
        """轮询视频结果"""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.base_url}/agnesapi",
                {},
                params={"video_id": video_id},
            )

            if isinstance(data, dict) and data.get("error"):
                return data

            return {
                "status": data.get("status"),
                "progress": data.get("progress", 0),
                "url": data.get("url"),
                "error": data.get("error"),
                "seconds": data.get("seconds"),
                "size": data.get("size"),
            }

        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}

    async def close(self):
        await self.client.aclose()


# 全局单例
agnes_client = AgnesClient()
