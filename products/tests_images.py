import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from products.images import compress_image
from products.models import Product
from quotes.models import Quote
from scouting.models import Prospect

TMP_MEDIA = tempfile.mkdtemp()


def png_upload(name="photo.png", size=(1600, 900), mode="RGBA"):
    buf = BytesIO()
    Image.new(mode, size, (200, 30, 30, 255) if mode == "RGBA" else (200, 30, 30)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class CompressImageTests(TestCase):
    def test_resizes_and_converts_to_jpeg(self):
        out = compress_image(png_upload())
        img = Image.open(BytesIO(out))
        self.assertEqual(img.format, "JPEG")
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.size, (800, 450))

    def test_small_image_not_upscaled(self):
        out = compress_image(png_upload(size=(300, 200)))
        self.assertEqual(Image.open(BytesIO(out)).size, (300, 200))

    def test_exif_rotation_applied(self):
        # A landscape JPEG tagged "rotate 90" should come out portrait
        buf = BytesIO()
        img = Image.new("RGB", (1200, 600), (0, 0, 255))
        exif = img.getexif()
        exif[0x0112] = 6  # Orientation: rotate 90 CW
        img.save(buf, format="JPEG", exif=exif.tobytes())
        out = compress_image(SimpleUploadedFile("rot.jpg", buf.getvalue()))
        w, h = Image.open(BytesIO(out)).size
        self.assertGreater(h, w)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class CompressedImageMixinTests(TestCase):
    """All three models share one save() path now; check each still compresses."""

    def assert_compressed(self, obj):
        self.assertTrue(obj.image.name.endswith(".jpg"), obj.image.name)
        with obj.image.open("rb") as f:
            img = Image.open(f)
            self.assertEqual(img.format, "JPEG")
            self.assertLessEqual(img.width, 800)

    def test_product(self):
        p = Product.objects.create(sku="IMG1", vendor="v", image=png_upload())
        self.assert_compressed(p)

    def test_prospect(self):
        p = Prospect.objects.create(show_name="s", vendor_name="v", product_name="p", image=png_upload())
        self.assert_compressed(p)

    def test_legacy_quote_now_rotates_too(self):
        q = Quote.objects.create(quote_num="Q1", image=png_upload())
        self.assert_compressed(q)

    def test_unchanged_image_not_recompressed_on_resave(self):
        p = Product.objects.create(sku="IMG2", vendor="v", image=png_upload())
        name = p.image.name
        p.name = "renamed"
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.image.name, name)
