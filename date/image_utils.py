
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PHOTOS = 6
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  
MAX_DIMENSION = 1600  
MAX_PIXELS = 40_000_000  
MIN_DIMENSION = 200 
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
JPEG_QUALITY = 85

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def process_upload(uploaded):
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"This file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    try:
        uploaded.seek(0)
        probe = Image.open(uploaded)
        probe.verify() 
        uploaded.seek(0)
        image = Image.open(uploaded)
        if image.format not in ALLOWED_FORMATS:
            raise ValidationError("Please upload a JPG, PNG or WebP image.")
        width, height = image.size
        if width * height > MAX_PIXELS:
            raise ValidationError("This image is too large.")
        if min(width, height) < MIN_DIMENSION:
            raise ValidationError(
                f"This image is too small (at least {MIN_DIMENSION}px on each side)."
            )
        image.load()  
    except ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise ValidationError("This file isn't a valid image.") from None


    image = ImageOps.exif_transpose(image)
    image = _flatten_to_rgb(image)
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return ContentFile(buffer.getvalue(), name="photo.jpg")


def _flatten_to_rgb(image):
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")
