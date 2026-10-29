"""
Forensic Evidence Analysis System (FEAS) - Cloudflare R2 Cloud Storage Service
=============================================================================
Provides zero-egress, S3-compatible cloud object storage for CCTV video evidence,
incident keyframes, and forensic reports via Cloudflare R2 (10 GB Free Tier).

Offloads large multi-megabyte video files from Render's ephemeral disk to 
permanent cloud storage, preventing container disk bloat and memory leaks.
"""

import logging
import mimetypes
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("feas.r2")


class CloudflareR2Service:
    """Manages S3-compatible storage operations on Cloudflare R2."""

    def __init__(self):
        self.account_id = os.environ.get("R2_ACCOUNT_ID", "").strip()
        self.access_key_id = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
        self.secret_access_key = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
        self.bucket_name = os.environ.get("R2_BUCKET_NAME", "feas-evidence").strip()
        self.public_url = os.environ.get("R2_PUBLIC_URL", "").strip().rstrip("/")
        # In cloud environments, auto-cleaning local videos after upload frees ephemeral disk
        self.auto_clean_local = os.environ.get("R2_AUTO_CLEAN_LOCAL", "true").lower() in ("true", "1", "yes")

        self._s3_client = None
        self._init_client()

    def _init_client(self):
        """Initialize boto3 S3 client if Cloudflare credentials are configured."""
        if not self.is_configured():
            logger.info("Cloudflare R2 is not configured. Falling back to local storage.")
            return

        try:
            import boto3
            from botocore.config import Config

            endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
            self._s3_client = boto3.client(
                service_name="s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name="auto",
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            )
            logger.info(f"Cloudflare R2 client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Cloudflare R2 client: {e}")
            self._s3_client = None

    def is_configured(self) -> bool:
        """Check if all required Cloudflare R2 environment variables are present."""
        return bool(self.account_id and self.access_key_id and self.secret_access_key and self.bucket_name)

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of Cloudflare R2 storage."""
        masked_key = f"{self.access_key_id[:4]}...{self.access_key_id[-4:]}" if len(self.access_key_id) > 8 else "NOT_SET"
        return {
            "service": "Cloudflare R2 Object Storage",
            "is_configured": self.is_configured(),
            "active": self._s3_client is not None,
            "bucket_name": self.bucket_name if self.is_configured() else None,
            "account_id_masked": f"{self.account_id[:6]}..." if len(self.account_id) > 6 else "NOT_SET",
            "access_key_masked": masked_key,
            "has_public_url": bool(self.public_url),
            "auto_clean_local": self.auto_clean_local,
            "free_tier": {
                "storage_capacity": "10 GB Free Forever",
                "egress_fee": "$0.00 / GB (Zero Bandwidth Fees)",
                "class_a_operations": "1,000,000 requests / month free",
                "class_b_operations": "10,000,000 requests / month free",
            },
        }

    def upload_file(
        self,
        local_path: Union[str, Path],
        object_key: str,
        content_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload a file to Cloudflare R2.
        
        Returns result dict with object URL and metadata, or None if R2 is not active.
        """
        p = Path(local_path)
        if not p.exists() or not p.is_file():
            logger.warning(f"R2 upload skipped: file not found at {local_path}")
            return None

        if not self._s3_client:
            return None

        clean_key = object_key.lstrip("/")
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(p))
            content_type = content_type or "application/octet-stream"

        file_size = p.stat().st_size
        logger.info(f"Uploading {p.name} ({file_size / (1024*1024):.2f} MB) to R2 key '{clean_key}'...")

        try:
            self._s3_client.upload_file(
                Filename=str(p),
                Bucket=self.bucket_name,
                Key=clean_key,
                ExtraArgs={"ContentType": content_type},
            )

            url = self.get_file_url(clean_key)
            return {
                "key": clean_key,
                "url": url,
                "size_bytes": file_size,
                "content_type": content_type,
                "storage": "CLOUDFLARE_R2",
                "bucket": self.bucket_name,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Cloudflare R2 upload error for '{clean_key}': {e}")
            return None

    def get_file_url(self, object_key: str, expires_in_seconds: int = 604800) -> str:
        """Resolve a public or presigned download URL for an object in R2.
        
        Defaults to a 7-day presigned URL if no public custom domain is configured.
        """
        clean_key = object_key.lstrip("/")
        if self.public_url:
            return f"{self.public_url}/{clean_key}"

        if not self._s3_client:
            return f"/storage/{clean_key}"

        try:
            return self._s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": clean_key},
                ExpiresIn=expires_in_seconds,
            )
        except Exception as e:
            logger.warning(f"Presigned URL generation failed: {e}")
            return f"https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}/{clean_key}"

    def process_and_archive_cctv_run(
        self,
        case_id: str,
        evidence_id: str,
        annotated_video_path: Optional[Union[str, Path]] = None,
        raw_video_path: Optional[Union[str, Path]] = None,
        keyframe_paths: Optional[List[Union[str, Path]]] = None,
    ) -> Dict[str, Any]:
        """Upload CCTV evidence artifacts to Cloudflare R2 and clean local storage."""
        if not self.is_configured() or not self._s3_client:
            return {"cloud_active": False, "storage": "LOCAL"}

        uploaded_artifacts = {}

        # 1. Upload Annotated Video
        if annotated_video_path:
            p_annotated = Path(annotated_video_path)
            if p_annotated.exists():
                key = f"cases/{case_id}/videos/{evidence_id}_annotated.mp4"
                up_res = self.upload_file(p_annotated, key, content_type="video/mp4")
                if up_res:
                    uploaded_artifacts["annotated_video"] = up_res
                    if self.auto_clean_local:
                        try:
                            p_annotated.unlink(missing_ok=True)
                            logger.info(f"Local annotated video cleaned: {p_annotated}")
                        except Exception as e:
                            logger.warning(f"Could not remove local annotated file: {e}")

        # 2. Upload Keyframes (entry, exit, best confidence)
        kf_uploaded = []
        for kf in keyframe_paths or []:
            p_kf = Path(kf)
            if p_kf.exists():
                kf_key = f"cases/{case_id}/keyframes/{evidence_id}_{p_kf.name}"
                up_kf = self.upload_file(p_kf, kf_key, content_type="image/jpeg")
                if up_kf:
                    kf_uploaded.append(up_kf)
        if kf_uploaded:
            uploaded_artifacts["keyframes"] = kf_uploaded

        # 3. Clean raw input video from local disk to guarantee 0 MB local storage bloat
        if raw_video_path and self.auto_clean_local:
            p_raw = Path(raw_video_path)
            if p_raw.exists():
                try:
                    p_raw.unlink(missing_ok=True)
                    logger.info(f"Local raw input video cleaned: {p_raw}")
                except Exception as e:
                    logger.warning(f"Could not remove local raw file: {e}")

        return {
            "cloud_active": True,
            "storage": "CLOUDFLARE_R2",
            "bucket": self.bucket_name,
            "artifacts": uploaded_artifacts,
        }


# Singleton service instance
r2_service = CloudflareR2Service()
