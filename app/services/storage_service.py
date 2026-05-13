"""MinIO/S3-compatible object storage service."""

from typing import Optional
from datetime import timedelta
import io

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from config.settings import settings


class StorageService:
    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
        return self._client

    def ensure_buckets(self) -> None:
        for bucket in (settings.s3_bucket_recordings, settings.s3_bucket_attachments):
            try:
                self.client.head_bucket(Bucket=bucket)
            except ClientError:
                try:
                    self.client.create_bucket(Bucket=bucket)
                    logger.success(f"S3 bucket created: {bucket}")
                except Exception as e:
                    logger.warning(f"Failed to create bucket {bucket}: {e}")

    def upload_recording(self, session_id: str, audio_bytes: bytes,
                          content_type: str = "audio/mpeg") -> Optional[str]:
        key = f"calls/{session_id}.mp3"
        try:
            self.client.put_object(
                Bucket=settings.s3_bucket_recordings,
                Key=key,
                Body=audio_bytes,
                ContentType=content_type,
                ACL="private",
            )
            return key
        except Exception as e:
            logger.warning(f"Recording upload failed: {e}")
            return None

    def upload_attachment(self, ticket_id: str, filename: str,
                           file_bytes: bytes, content_type: str) -> Optional[str]:
        key = f"tickets/{ticket_id}/{filename}"
        try:
            self.client.put_object(
                Bucket=settings.s3_bucket_attachments,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
                ACL="private",
            )
            return key
        except Exception as e:
            logger.warning(f"Attachment upload failed: {e}")
            return None

    def get_presigned_url(self, bucket: str, key: str,
                           expires_in: Optional[int] = None) -> Optional[str]:
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in or settings.s3_presigned_expiry,
            )
        except Exception as e:
            logger.warning(f"Presign URL failed: {e}")
            return None


storage_service = StorageService()
