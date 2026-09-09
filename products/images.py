"""
Shared image handling for models with an `image` ImageField.

`compress_image()` used to be copied into products, quotes and scouting — and the
quotes copy had drifted (no EXIF rotation, so phone photos came out sideways).
One implementation now lives here, plus a mixin that does the "compress on first
upload / on change" dance in save().
"""

import os
from io import BytesIO

from django.core.files.base import ContentFile


def compress_image(image_field, max_width=800, quality=72):
    """Return JPEG bytes: EXIF-rotated, RGB, resized to at most `max_width` wide."""
    from PIL import Image, ImageOps

    img = Image.open(image_field)

    # Honour EXIF rotation tag (fixes phone photos appearing sideways/upside-down)
    img = ImageOps.exif_transpose(img)

    # JPEG can't hold alpha / palette modes
    if img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    output = BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()


class CompressedImageMixin:
    """
    For models with an `image = ImageField(...)`. On save, if the image is new or
    changed, replaces it with a compressed JPEG of the same base name.
    Put the mixin BEFORE models.Model in the class bases.
    """

    image_field_name = "image"

    def _image_unchanged(self):
        if not self.pk:
            return False
        try:
            old = type(self).objects.get(pk=self.pk)
        except type(self).DoesNotExist:
            return False
        return getattr(old, self.image_field_name) == getattr(self, self.image_field_name)

    def save(self, *args, **kwargs):
        image = getattr(self, self.image_field_name)
        if image and not self._image_unchanged():
            base = os.path.splitext(os.path.basename(image.name))[0]
            image.save(f"{base}.jpg", ContentFile(compress_image(image)), save=False)
        super().save(*args, **kwargs)
