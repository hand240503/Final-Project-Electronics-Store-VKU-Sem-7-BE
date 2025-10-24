# api/products/management/commands/fake_categories.py
from django.core.management.base import BaseCommand
from api.products.models import Category

class Command(BaseCommand):
    help = 'Tạo fake categories cho shop điện tử'

    def handle(self, *args, **kwargs):
        # Xóa dữ liệu cũ (tùy chọn)
        Category.objects.all().delete()

        # # Categories gốc
        # laptops = Category.objects.create(name="Laptops")
        # smartphones = Category.objects.create(name="Smartphones")
        # tv_audio = Category.objects.create(name="TV & Audio")
        # accessories = Category.objects.create(name="Accessories")

        # # Subcategories
        # Category.objects.create(name="Gaming Laptops", parent=laptops)
        # Category.objects.create(name="Ultrabooks", parent=laptops)
        # Category.objects.create(name="MacBooks", parent=laptops)
        # Category.objects.create(name="2-in-1 Laptops", parent=laptops)

        # Category.objects.create(name="Android Phones", parent=smartphones)
        # Category.objects.create(name="iPhones", parent=smartphones)
        # Category.objects.create(name="Refurbished Phones", parent=smartphones)
        # Category.objects.create(name="Phone Accessories", parent=smartphones)

        # Category.objects.create(name="LED & OLED TVs", parent=tv_audio)
        # Category.objects.create(name="Soundbars", parent=tv_audio)
        # Category.objects.create(name="Home Theaters", parent=tv_audio)
        # Category.objects.create(name="Projectors", parent=tv_audio)

        # Category.objects.create(name="Chargers & Cables", parent=accessories)
        # Category.objects.create(name="Headphones", parent=accessories)
        # Category.objects.create(name="Keyboards & Mice", parent=accessories)
        # Category.objects.create(name="Smartwatches", parent=accessories)

        self.stdout.write(self.style.SUCCESS('Fake categories created successfully!'))
