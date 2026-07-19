"""Alibaba Cloud Object Storage Service (OSS) helper client with local fallback support."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional
from app.core.logger import get_logger

try:
    import oss2
except ImportError:
    oss2 = None

logger = get_logger("agentsphere.storage.oss")


class OSSClient:
    """Manages file uploads to Alibaba OSS and falls back to local hosting for sandbox environments."""

    def __init__(self) -> None:
        self.access_key_id = os.getenv("ALIBABA_OSS_ACCESS_KEY_ID")
        self.access_key_secret = os.getenv("ALIBABA_OSS_ACCESS_KEY_SECRET")
        self.endpoint = os.getenv("ALIBABA_OSS_ENDPOINT", "https://oss-cn-hangzhou.aliyuncs.com")
        self.bucket_name = os.getenv("ALIBABA_OSS_BUCKET")
        self.local_assets_dir = Path("app/static/assets")
        self.local_assets_dir.mkdir(parents=True, exist_ok=True)

        self._auth = None
        self._bucket = None

        if oss2 is not None and self.access_key_id and self.access_key_secret and self.bucket_name:
            try:
                self._auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                self._bucket = oss2.Bucket(self._auth, self.endpoint, self.bucket_name)
                logger.info("Alibaba OSS Client initialized successfully for bucket: %s", self.bucket_name)
            except Exception as e:
                logger.warning("Failed to initialize Alibaba OSS: %s. Using local fallback.", e)
        else:
            logger.info("Alibaba OSS credentials missing or SDK uninstalled. Falling back to local static hosting.")

    def upload_file(self, source_path: str, object_name: Optional[str] = None) -> str:
        """Upload a file to Alibaba OSS bucket or save locally inside static directories."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        name = object_name or source.name

        if self._bucket is not None:
            try:
                with open(source, "rb") as f:
                    self._bucket.put_object(name, f)
                # Formulate the public OSS URL
                clean_endpoint = self.endpoint.replace("https://", "").replace("http://", "")
                url = f"https://{self.bucket_name}.{clean_endpoint}/{name}"
                logger.info("File uploaded successfully to Alibaba OSS: %s", url)
                return url
            except Exception as e:
                logger.error("Alibaba OSS upload failed for %s: %s. Using local static path.", source_path, e)

        # Local Static File Fallback
        dest = self.local_assets_dir / name
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            logger.info("Saved file locally for static delivery: %s", dest)
            return f"/static/assets/{name}"
        except Exception as e:
            logger.exception("Failed to write static asset locally")
            raise RuntimeError(f"Failed to persist asset: {e}") from e
