import asyncio
from pathlib import Path
from typing import Protocol


class ThemeAssetStore(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> str: ...


class LocalThemeAssetStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        del content_type
        safe_name = Path(key).name
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / safe_name
        await asyncio.to_thread(target.write_bytes, content)
        return f"/api/v1/aigc/assets/{safe_name}"


class S3ThemeAssetStore:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        public_base_url: str,
        prefix: str,
    ) -> None:
        import boto3

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")
        self._prefix = prefix.strip("/")

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        object_key = f"{self._prefix}/{Path(key).name}"
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )
        return f"{self._public_base_url}/{object_key}"
