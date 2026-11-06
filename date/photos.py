from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_PHOTOS = 6
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000  # Pillow refuses anything over twice this


def process_upload(uploaded):
    """Re-encode an upload as a resized JPEG. Saving a fresh file drops EXIF,
    which can contain the photo's GPS location."""
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValidationError("That file is too large (8 MB max).")
    try:
        image = ImageOps.exif_transpose(Image.open(uploaded)).convert("RGB")
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ValidationError("We couldn't read that image. Please upload a JPEG or PNG photo.")
    image.thumbnail((1600, 1600))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue(), name="photo.jpg")
