"""
Image processing service.

Handles image compression, resizing, and format optimization
before upload to S3 or local storage.
"""
from __future__ import annotations

import logging
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)

# Maximum dimension (width or height) for uploaded images
MAX_IMAGE_DIMENSION = 1200
THUMBNAIL_DIMENSION = 400
COMPRESSION_QUALITY = 85


class ImageProcessor:
    """
    Processes images before upload: resize, compress, convert to WebP.

    Usage:
        processor = ImageProcessor()
        optimized_file = processor.optimize(uploaded_file)
    """

    @staticmethod
    def optimize(file, max_dimension: int = MAX_IMAGE_DIMENSION) -> InMemoryUploadedFile:
        """
        Optimize an uploaded image file.

        - Resizes if larger than max_dimension
        - Converts to WebP for smaller file size
        - Compresses with quality setting

        Args:
            file: Django UploadedFile
            max_dimension: Maximum width or height in pixels

        Returns:
            Optimized InMemoryUploadedFile
        """
        try:
            from PIL import Image

            img = Image.open(file)

            # Convert RGBA to RGB (WebP supports both, but JPEG doesn't)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                img = background

            # Resize if too large
            if max(img.size) > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

            # Auto-rotate based on EXIF
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            # Save as WebP
            buffer = BytesIO()
            img.save(buffer, format='WEBP', quality=COMPRESSION_QUALITY, optimize=True)
            buffer.seek(0)

            # Create new InMemoryUploadedFile
            original_name = getattr(file, 'name', 'image.webp')
            name_without_ext = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
            new_name = f"{name_without_ext}.webp"

            optimized = InMemoryUploadedFile(
                file=buffer,
                field_name=None,
                name=new_name,
                content_type='image/webp',
                size=buffer.getbuffer().nbytes,
                charset=None,
            )

            original_size = getattr(file, 'size', 0)
            new_size = buffer.getbuffer().nbytes
            if original_size:
                reduction = ((original_size - new_size) / original_size) * 100
                logger.info(
                    "Image optimized: %s → %s (%.0f%% reduction)",
                    _format_size(original_size),
                    _format_size(new_size),
                    reduction,
                )

            return optimized

        except ImportError:
            logger.warning("Pillow not installed — skipping image optimization")
            return file
        except Exception as e:
            logger.warning("Image optimization failed: %s — using original", e)
            # Reset file position and return original
            if hasattr(file, 'seek'):
                file.seek(0)
            return file


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    return f"{size_bytes / (1024 * 1024):.1f}MB"
