"""Supabase-powered object storage service."""

from typing import Optional
from loguru import logger
from supabase import create_client, Client

from config.settings import settings


class StorageService:
    def __init__(self) -> None:
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key or settings.supabase_key
            )
        return self._client

    def ensure_buckets(self) -> None:
        """Supabase buckets are typically managed via the dashboard, 
        but we can try to ensure they exist via API if using Service Role Key."""
        for bucket in (settings.s3_bucket_recordings, settings.s3_bucket_attachments):
            try:
                # Try to get bucket info
                self.client.storage.get_bucket(bucket)
            except Exception:
                try:
                    # Create if not exists (requires Service Role Key)
                    self.client.storage.create_bucket(bucket, options={"public": False})
                    logger.success(f"Supabase storage bucket created: {bucket}")
                except Exception as e:
                    logger.warning(f"Failed to ensure bucket {bucket}: {e}")

    def upload_recording(self, session_id: str, audio_bytes: bytes,
                          content_type: str = "audio/mpeg") -> Optional[str]:
        path = f"calls/{session_id}.mp3"
        try:
            self.client.storage.from_(settings.s3_bucket_recordings).upload(
                path=path,
                file=audio_bytes,
                file_options={"content-type": content_type, "x-upsert": "true"}
            )
            return path
        except Exception as e:
            logger.warning(f"Recording upload failed: {e}")
            return None

    def upload_attachment(self, ticket_id: str, filename: str,
                           file_bytes: bytes, content_type: str) -> Optional[str]:
        path = f"tickets/{ticket_id}/{filename}"
        try:
            self.client.storage.from_(settings.s3_bucket_attachments).upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": content_type, "x-upsert": "true"}
            )
            return path
        except Exception as e:
            logger.warning(f"Attachment upload failed: {e}")
            return None

    def get_presigned_url(self, bucket: str, key: str,
                           expires_in: int = 3600) -> Optional[str]:
        try:
            res = self.client.storage.from_(bucket).create_signed_url(key, expires_in)
            return res.get("signedURL")
        except Exception as e:
            logger.warning(f"Presign URL failed: {e}")
            return None


storage_service = StorageService()
