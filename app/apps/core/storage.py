"""
S3/Cloudinary upload service for image storage.

Validates MIME type and file size before uploading.
Generates unique filenames (UUID) to prevent collisions.
"""
import mimetypes
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from apps.core.exceptions import InvalidFileTypeError, FileTooLargeError
from apps.core.utils import generate_unique_filename


class S3UploadService:
    """
    Service for uploading images to AWS S3.

    Usage:
        service = S3UploadService()
        url = service.upload(file, folder='restaurants')
    """

    def __init__(self):
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.region = settings.AWS_S3_REGION_NAME
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    def upload(self, file, folder: str = 'images') -> str:
        """
        Upload a file to S3 after validating MIME type and size.

        Args:
            file: Django UploadedFile or file-like object
            folder: S3 folder/prefix (e.g., 'restaurants', 'products')

        Returns:
            Public URL of the uploaded file

        Raises:
            InvalidFileTypeError: If MIME type is not allowed
            FileTooLargeError: If file exceeds size limit
        """
        self._validate_mime(file)
        self._validate_size(file)

        filename = generate_unique_filename(file.name)
        key = f"{folder}/{filename}"

        content_type = getattr(file, 'content_type', 'image/jpeg')

        try:
            self.client.upload_fileobj(
                file,
                self.bucket_name,
                key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read',
                },
            )
        except ClientError as e:
            raise Exception(f"Erro ao fazer upload da imagem: {str(e)}")

        return self._generate_url(key)

    def delete(self, url: str) -> bool:
        """
        Delete a file from S3 by its URL.

        Args:
            url: Public URL of the file

        Returns:
            True if deleted successfully
        """
        key = self._extract_key_from_url(url)
        if not key:
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def _validate_mime(self, file) -> None:
        """Validate file MIME type against allowed types."""
        content_type = getattr(file, 'content_type', None)

        if not content_type:
            # Try to guess from filename
            content_type, _ = mimetypes.guess_type(file.name)

        if content_type not in settings.ALLOWED_IMAGE_TYPES:
            allowed = ', '.join(settings.ALLOWED_IMAGE_TYPES)
            raise InvalidFileTypeError(
                f"Tipo de arquivo não permitido: {content_type}. "
                f"Tipos aceitos: {allowed}"
            )

    def _validate_size(self, file) -> None:
        """Validate file size against MAX_UPLOAD_SIZE_MB."""
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        size = getattr(file, 'size', None)
        if size and size > max_bytes:
            raise FileTooLargeError(
                f"Arquivo excede o tamanho máximo de {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

    def _generate_url(self, key: str) -> str:
        """Generate the public URL for an S3 object."""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"

    def _extract_key_from_url(self, url: str) -> str | None:
        """Extract S3 key from a public URL."""
        prefix = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/"
        if url.startswith(prefix):
            return url[len(prefix):]
        return None


class LocalUploadService:
    """
    Fallback upload service for local development (saves to MEDIA_ROOT).

    Usage:
        service = LocalUploadService()
        url = service.upload(file, folder='restaurants')
    """

    def _validate_mime(self, file) -> None:
        """Validate file MIME type against allowed types."""
        content_type = getattr(file, 'content_type', None)
        if not content_type:
            content_type, _ = mimetypes.guess_type(file.name)
        if content_type and content_type not in settings.ALLOWED_IMAGE_TYPES:
            allowed = ', '.join(settings.ALLOWED_IMAGE_TYPES)
            raise InvalidFileTypeError(
                f"Tipo de arquivo não permitido: {content_type}. "
                f"Tipos aceitos: {allowed}"
            )

    def _validate_size(self, file) -> None:
        """Validate file size against MAX_UPLOAD_SIZE_MB."""
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        size = getattr(file, 'size', None)
        if size and size > max_bytes:
            raise FileTooLargeError(
                f"Arquivo excede o tamanho máximo de {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

    def upload(self, file, folder: str = 'images') -> str:
        """Save file locally and return its URL."""
        import os

        self._validate_mime(file)
        self._validate_size(file)

        filename = generate_unique_filename(file.name)
        rel_path = f"{folder}/{filename}"

        # Ensure the directory exists
        full_dir = os.path.join(settings.MEDIA_ROOT, folder)
        os.makedirs(full_dir, exist_ok=True)

        full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        with open(full_path, 'wb') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        return f"{settings.MEDIA_URL}{rel_path}"

    def delete(self, url: str) -> bool:
        """Delete a locally stored file."""
        import os

        if not url or not url.startswith(settings.MEDIA_URL):
            return False

        rel_path = url.replace(settings.MEDIA_URL, '')
        full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False


def get_upload_service():
    """
    Factory function that returns the appropriate upload service
    based on configuration.

    In DEBUG mode, always uses LocalUploadService for reliability.
    In production, uses S3UploadService if AWS credentials are configured.
    """
    if not settings.DEBUG and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        return S3UploadService()
    return LocalUploadService()
