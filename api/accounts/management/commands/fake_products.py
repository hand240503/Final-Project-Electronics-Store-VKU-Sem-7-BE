# api/products/management/commands/fake_products_real.py
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from api.products.models import (
    Brand, Category, Product, ProductVariant, Document, ProductDocument,
    Review, ShippingInfo, ReturnPolicy, Notification
)

BRANDS = [
    "Apple", "Samsung", "Sony", "LG", "Dell", "HP", "Lenovo", "Asus", "Acer", "Microsoft"
]

CATEGORIES = [
    "Smartphones", "Laptops", "Tablets", "Monitors", "Headphones",
    "Keyboards", "Mice", "Printers", "Smartwatches", "Cameras"
]

PRODUCTS = [
    "iPhone 15 Pro", "Galaxy S23 Ultra", "Sony WH-1000XM5", "MacBook Pro 16",
    "Dell XPS 13", "iPad Pro 12.9", "Samsung Galaxy Tab S9", "LG 27UK850 Monitor",
    "Logitech MX Master 3", "HP LaserJet Pro M404", "Lenovo ThinkPad X1 Carbon",
    "Asus ROG Strix G15", "Acer Predator Helios 300", "Microsoft Surface Pro 9",
    "Sony A7 IV Camera", "Canon EOS R6", "Bose QuietComfort 45", "Apple Watch Series 9",
    "Samsung Galaxy Watch 6", "Razer DeathAdder V2", "Apple Magic Keyboard",
    "Dell UltraSharp U2723QE", "HP Envy 6055 Printer", "Logitech G502 Mouse",
    "Asus TUF Gaming F15", "Acer Nitro 5", "Samsung Odyssey G7", "Apple AirPods Pro 2",
    "Sony Xperia 1 V", "Microsoft Surface Laptop 5"
]

class Command(BaseCommand):
    help = "Create 30 real fake products with real brands/categories"

    def truncate_tables(self):
        self.stdout.write("Truncating related tables...")
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            tables = [
                "product_documents", "documents", "product_variants", "reviews",
                "shipping_info", "return_policy", "notifications", "products",
                "brands", "categories"
            ]
            for table in tables:
                cursor.execute(f"TRUNCATE TABLE {table};")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        self.stdout.write("Tables truncated.")

    def handle(self, *args, **kwargs):
        self.truncate_tables()

        self.stdout.write("Seeding real fake data...")

        # --- Brands ---
        brands = []
        for name in BRANDS:
            brand = Brand.objects.create(name=name, description=f"{name} official products")
            brands.append(brand)

        # --- Categories ---
        categories = []
        for name in CATEGORIES:
            category = Category.objects.create(name=name)
            categories.append(category)

        # --- Users for reviews ---
        users = []
        for i in range(5):
            user, _ = User.objects.get_or_create(
                username=f"user{i+1}",
                defaults={"email": f"user{i+1}@example.com", "password": "testpass"}
            )
            users.append(user)

        # --- Products ---
        for i, product_name in enumerate(PRODUCTS[:30]):
            product = Product.objects.create(
                name=product_name,
                description=f"Description for {product_name}",
                price=random.uniform(100, 2000),
                discount_price=random.choice([None, random.uniform(50, 1500)]),
                brand=random.choice(brands),
                category=random.choice(categories),
                rating=random.uniform(1, 5),
                num_reviews=random.randint(0, 50),
                is_available=random.choice([True, True, False])
            )

            # --- Product Variants ---
            colors = ["Red", "Blue", "Black", "White", "Silver"]
            sizes = ["S", "M", "L", "XL"]
            for _ in range(random.randint(1, 3)):
                ProductVariant.objects.create(
                    product=product,
                    name=f"{random.choice(colors)} - {random.choice(sizes)}",
                    color=random.choice(colors),
                    size=random.choice(sizes),
                    stock=random.randint(0, 100),
                    price=product.price,
                    discount_price=product.discount_price
                )

            # --- Documents ---
            for j in range(random.randint(1, 2)):
                doc = Document.objects.create(
                    title=f"{product_name} Image {j+1}",
                    type=Document.IMAGE,
                    file=f"documents/{product_name.replace(' ', '_').lower()}_{j+1}.jpg"
                )
                ProductDocument.objects.create(
                    product=product,
                    document=doc,
                    is_main=(j==0)
                )

            # --- Reviews ---
            for _ in range(random.randint(1, 5)):
                Review.objects.create(
                    product=product,
                    user=random.choice(users),
                    rating=random.randint(1, 5),
                    comment=f"Review for {product_name}"
                )

            # --- Shipping Info ---
            ShippingInfo.objects.create(
                product=product,
                info="Ships in 3-5 business days. Free shipping over $50."
            )

            # --- Return Policy ---
            ReturnPolicy.objects.create(
                product=product,
                policy_text="30-day return policy. Product must be in original condition."
            )

            # --- Notifications ---
            Notification.objects.create(
                product=product,
                email=f"notify{i+1}@example.com",
                notified=False
            )

        self.stdout.write(self.style.SUCCESS("Real fake data created successfully!"))
