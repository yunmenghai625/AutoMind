import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    url: str


class StorageProvider(Protocol):
    async def put(self, *, key: str, content: bytes, content_type: str) -> StoredObject: ...

    async def delete(self, key: str) -> None: ...


class LocalStorageProvider:
    def __init__(self, *, root: str, public_prefix: str) -> None:
        self.root = Path(root).resolve()
        self._public_prefix = public_prefix.rstrip("/")

    async def put(self, *, key: str, content: bytes, content_type: str) -> StoredObject:
        del content_type
        safe_key = Path(key).name
        self.root.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread((self.root / safe_key).write_bytes, content)
        return StoredObject(key=safe_key, url=f"{self._public_prefix}/{safe_key}")

    async def delete(self, key: str) -> None:
        target = (self.root / Path(key).name).resolve()
        if target.parent == self.root and target.is_file():
            await asyncio.to_thread(target.unlink)


class S3CompatibleStorageProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        public_base_url: str | None,
        prefix: str,
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
                s3={"addressing_style": "virtual"},
            ),
        )
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self._prefix = prefix.strip("/")

    async def put(self, *, key: str, content: bytes, content_type: str) -> StoredObject:
        object_key = f"{self._prefix}/{Path(key).name}"
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )
        url = (
            f"{self._public_base_url}/{object_key}"
            if self._public_base_url
            else f"s3://{self._bucket}/{object_key}"
        )
        return StoredObject(key=object_key, url=url)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
