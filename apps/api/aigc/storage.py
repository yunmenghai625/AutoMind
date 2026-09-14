import asyncio
from pathlib import Path
from typing import Protocol


class ThemeAssetNotFoundError(FileNotFoundError):
    pass


class ThemeAssetStoreError(RuntimeError):
    pass


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
        public_base_url: str | None,
        prefix: str,
        proxy_base_url: str = "/api/v1/aigc/assets",
    ) -> None:
        import boto3
        from botocore.config import Config

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(
                connect_timeout=10,
                read_timeout=30,
                retries={"max_attempts": 1, "mode": "standard"},
            ),
        )
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self._proxy_base_url = proxy_base_url.rstrip("/")
        self._prefix = prefix.strip("/")

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        safe_name = Path(key).name
        object_key = f"{self._prefix}/{safe_name}"
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )
        if self._public_base_url:
            return f"{self._public_base_url}/{object_key}"
        return f"{self._proxy_base_url}/{safe_name}"

    async def get(self, key: str) -> tuple[bytes, str]:
        from botocore.exceptions import ClientError

        object_key = f"{self._prefix}/{Path(key).name}"
        body = None
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._bucket,
                Key=object_key,
            )
            body = response["Body"]
            content = await asyncio.to_thread(body.read)
            content_type = str(response.get("ContentType") or "application/octet-stream")
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise ThemeAssetNotFoundError(key) from exc
            raise ThemeAssetStoreError("Unable to read generated asset") from exc
        except (KeyError, OSError) as exc:
            raise ThemeAssetStoreError("Unable to read generated asset") from exc
        finally:
            if body is not None:
                body.close()
        return content, content_type
