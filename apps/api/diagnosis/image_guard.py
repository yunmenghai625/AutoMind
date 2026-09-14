import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError


class ImageGuardError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class GuardedImage:
    content: bytes
    content_type: str
    sha256: str
    original_width: int
    original_height: int
    width: int
    height: int


class ImageGuard:
    _accepted_mime = {"image/jpeg", "image/png", "image/webp"}
    _accepted_format = {"JPEG", "PNG", "WEBP"}
    _format_mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

    def __init__(
        self,
        *,
        max_bytes: int,
        max_dimension: int,
        max_pixels: int,
        jpeg_quality: int,
    ) -> None:
        self._max_bytes = max_bytes
        self._max_dimension = max_dimension
        self._max_pixels = max_pixels
        self._jpeg_quality = jpeg_quality

    def process(self, content: bytes, declared_mime: str | None) -> GuardedImage:
        if not content:
            raise ImageGuardError("EMPTY_IMAGE", "上传图片为空")
        if len(content) > self._max_bytes:
            raise ImageGuardError("IMAGE_TOO_LARGE", "图片超过允许的文件大小")
        if declared_mime not in self._accepted_mime:
            raise ImageGuardError("UNSUPPORTED_IMAGE_MIME", "仅支持 JPEG、PNG 或 WebP 图片")

        try:
            with Image.open(io.BytesIO(content)) as source:
                detected_format = source.format
                original_width, original_height = source.size
                if detected_format not in self._accepted_format:
                    raise ImageGuardError(
                        "UNSUPPORTED_IMAGE_FORMAT", "图片实际格式不是 JPEG、PNG 或 WebP"
                    )
                if self._format_mime[detected_format] != declared_mime:
                    raise ImageGuardError("IMAGE_MIME_MISMATCH", "图片声明类型与实际格式不一致")
                if original_width * original_height > self._max_pixels:
                    raise ImageGuardError("IMAGE_DIMENSIONS_TOO_LARGE", "图片像素尺寸超过限制")
                source.load()
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail(
                    (self._max_dimension, self._max_dimension), Image.Resampling.LANCZOS
                )
                output = io.BytesIO()
                normalized.save(
                    output,
                    format="JPEG",
                    quality=self._jpeg_quality,
                    optimize=True,
                    progressive=True,
                )
        except ImageGuardError:
            raise
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageGuardError("INVALID_IMAGE", "图片内容不是有效图片") from exc

        compressed = output.getvalue()
        return GuardedImage(
            content=compressed,
            content_type="image/jpeg",
            sha256=hashlib.sha256(compressed).hexdigest(),
            original_width=original_width,
            original_height=original_height,
            width=normalized.width,
            height=normalized.height,
        )
