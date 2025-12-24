"""
Django Management Command: Generate Ratings with User Groups
Location: api/rating/management/commands/generate_ratings.py

Usage:
    python manage.py generate_ratings --clear
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.products.models import Product
from api.rating.models import Rating
import random

class Command(BaseCommand):
    help = 'Generate synthetic ratings with realistic user behavior patterns'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=None)
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('SMART RATING GENERATOR WITH USER GROUPS'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        if options['clear']:
            self.clear_ratings()
        
        self.generate_ratings(options['users'])

    def clear_ratings(self):
        count = Rating.objects.filter(rating_type=Rating.EXPLICIT).count()
        Rating.objects.filter(rating_type=Rating.EXPLICIT).delete()
        self.stdout.write(self.style.WARNING(f'✓ Deleted {count:,} ratings\n'))

    # =========================================================================
    # PRODUCT GROUPS - Nhóm sản phẩm theo brand/category
    # =========================================================================
    PRODUCT_GROUPS = {
        # Apple Ecosystem
        'APPLE_PHONES': ['iPhone 15 Pro'],
        'APPLE_LAPTOPS': ['MacBook Pro 16'],
        'APPLE_TABLETS': ['iPad Pro 12.9'],
        'APPLE_WATCHES': ['Apple Watch Series 9'],
        'APPLE_AUDIO': ['Apple AirPods Pro 2'],
        'APPLE_ACCESSORIES': [
            'Apple Magic Keyboard',
            'Apple MagSafe Charger',
            'Apple Silicone Case',
            'Apple Pencil 2',
            'Apple USB-C to 3.5mm Audio Adapter'
        ],
        
        # Samsung Ecosystem
        'SAMSUNG_PHONES': ['Galaxy S23 Ultra'],
        'SAMSUNG_TABLETS': ['Samsung Galaxy Tab S9'],
        'SAMSUNG_WATCHES': ['Samsung Galaxy Watch 6'],
        'SAMSUNG_MONITORS': ['Samsung Odyssey G7'],
        'SAMSUNG_ACCESSORIES': [
            'Samsung S Pen',
            'Samsung Clear View Case',
            'Samsung Wireless Charging Pad'
        ],
        
        # Premium Audio
        'PREMIUM_AUDIO': [
            'Sony WH-1000XM5',
            'Bose QuietComfort 45'
        ],
        
        # Professional Laptops
        'BUSINESS_LAPTOPS': [
            'Dell XPS 13',
            'Lenovo ThinkPad X1 Carbon',
            'Microsoft Surface Laptop 5'
        ],
        
        # Gaming Laptops
        'GAMING_LAPTOPS': [
            'Asus ROG Strix G15',
            'Acer Predator Helios 300',
            'Asus TUF Gaming F15',
            'Acer Nitro 5'
        ],
        
        # Gaming Peripherals
        'GAMING_PERIPHERALS': [
            'Razer DeathAdder V2',
            'Logitech G502 Mouse',
            'Samsung Odyssey G7'
        ],
        
        # Professional Cameras
        'CAMERAS': [
            'Sony A7 IV Camera',
            'Canon EOS R6'
        ],
        'CAMERA_ACCESSORIES': [
            'Sony SD Card 128GB',
            'Sony NP-FZ100 Battery',
            'Sony Camera Carrying Case'
        ],
        
        # Office Equipment
        'MICE_KEYBOARDS': ['Logitech MX Master 3'],
        'MONITORS': [
            'LG 27UK850 Monitor',
            'Dell UltraSharp U2723QE'
        ],
        'PRINTERS': [
            'HP LaserJet Pro M404',
            'HP Envy 6055 Printer'
        ],
        'PRINTER_SUPPLIES': [
            'HP 80A Toner Cartridge',
            'HP Premium Printing Paper'
        ],
        
        # Dell Accessories
        'DELL_ACCESSORIES': [
            'Dell USB-C Dock',
            'Dell Wireless Mouse',
            'Dell Laptop Stand'
        ],
        
        # Microsoft Products
        'MICROSOFT_DEVICES': [
            'Microsoft Surface Pro 9',
            'Microsoft Surface Laptop 5'
        ],
        
        # Sony Products
        'SONY_PHONES': ['Sony Xperia 1 V']
    }

    # =========================================================================
    # USER GROUPS - 8 nhóm người dùng với behavior khác nhau
    # =========================================================================
    USER_GROUPS = {
        1: {
            'name': 'Apple Ecosystem Lovers',
            'description': 'Người dùng trung thành với Apple, mua cả hệ sinh thái',
            'weight': 0.15,  # 15% users
            'preferences': {
                'APPLE_PHONES': 0.95,
                'APPLE_LAPTOPS': 0.85,
                'APPLE_TABLETS': 0.75,
                'APPLE_WATCHES': 0.80,
                'APPLE_AUDIO': 0.90,
                'APPLE_ACCESSORIES': 0.70,
                'PREMIUM_AUDIO': 0.40,
                'MONITORS': 0.30
            },
            'ratings': {
                'APPLE_PHONES': 'very_high',
                'APPLE_LAPTOPS': 'very_high',
                'APPLE_TABLETS': 'high',
                'APPLE_WATCHES': 'high',
                'APPLE_AUDIO': 'very_high',
                'APPLE_ACCESSORIES': 'high',
                'SAMSUNG_PHONES': 'low',
                'SAMSUNG_TABLETS': 'low',
                'default': 'mid'
            }
        },
        
        2: {
            'name': 'Samsung Enthusiasts',
            'description': 'Người dùng thích Samsung và Android',
            'weight': 0.12,  # 12% users
            'preferences': {
                'SAMSUNG_PHONES': 0.95,
                'SAMSUNG_TABLETS': 0.70,
                'SAMSUNG_WATCHES': 0.75,
                'SAMSUNG_MONITORS': 0.60,
                'SAMSUNG_ACCESSORIES': 0.65,
                'PREMIUM_AUDIO': 0.50,
                'BUSINESS_LAPTOPS': 0.40
            },
            'ratings': {
                'SAMSUNG_PHONES': 'very_high',
                'SAMSUNG_TABLETS': 'high',
                'SAMSUNG_WATCHES': 'high',
                'SAMSUNG_ACCESSORIES': 'high',
                'APPLE_PHONES': 'low',
                'APPLE_LAPTOPS': 'low',
                'default': 'mid'
            }
        },
        
        3: {
            'name': 'Professional Creatives',
            'description': 'Photographer, videographer, content creator',
            'weight': 0.10,  # 10% users
            'preferences': {
                'CAMERAS': 0.95,
                'CAMERA_ACCESSORIES': 0.90,
                'APPLE_LAPTOPS': 0.70,
                'BUSINESS_LAPTOPS': 0.60,
                'PREMIUM_AUDIO': 0.65,
                'MONITORS': 0.75,
                'APPLE_TABLETS': 0.50
            },
            'ratings': {
                'CAMERAS': 'very_high',
                'CAMERA_ACCESSORIES': 'high',
                'APPLE_LAPTOPS': 'high',
                'MONITORS': 'high',
                'PREMIUM_AUDIO': 'high',
                'GAMING_LAPTOPS': 'low',
                'GAMING_PERIPHERALS': 'low',
                'default': 'mid'
            }
        },
        
        4: {
            'name': 'Hardcore Gamers',
            'description': 'Chơi game chuyên nghiệp',
            'weight': 0.12,  # 12% users
            'preferences': {
                'GAMING_LAPTOPS': 0.90,
                'GAMING_PERIPHERALS': 0.95,
                'MONITORS': 0.70,
                'PREMIUM_AUDIO': 0.60,
                'SAMSUNG_MONITORS': 0.75
            },
            'ratings': {
                'GAMING_LAPTOPS': 'very_high',
                'GAMING_PERIPHERALS': 'very_high',
                'SAMSUNG_MONITORS': 'high',
                'MONITORS': 'high',
                'PREMIUM_AUDIO': 'high',
                'BUSINESS_LAPTOPS': 'low',
                'APPLE_PHONES': 'low',
                'default': 'mid'
            }
        },
        
        5: {
            'name': 'Business Professionals',
            'description': 'Dân văn phòng, làm việc remote',
            'weight': 0.18,  # 18% users (nhóm lớn nhất)
            'preferences': {
                'BUSINESS_LAPTOPS': 0.90,
                'MONITORS': 0.75,
                'MICE_KEYBOARDS': 0.85,
                'PRINTERS': 0.60,
                'PRINTER_SUPPLIES': 0.55,
                'DELL_ACCESSORIES': 0.65,
                'MICROSOFT_DEVICES': 0.50,
                'PREMIUM_AUDIO': 0.45
            },
            'ratings': {
                'BUSINESS_LAPTOPS': 'very_high',
                'MONITORS': 'high',
                'MICE_KEYBOARDS': 'high',
                'DELL_ACCESSORIES': 'high',
                'PRINTERS': 'high',
                'GAMING_LAPTOPS': 'low',
                'GAMING_PERIPHERALS': 'low',
                'default': 'mid'
            }
        },
        
        6: {
            'name': 'Tech Enthusiasts',
            'description': 'Thích thử công nghệ mới, đa dạng brands',
            'weight': 0.13,  # 13% users
            'preferences': {
                'APPLE_PHONES': 0.60,
                'SAMSUNG_PHONES': 0.55,
                'SONY_PHONES': 0.70,
                'PREMIUM_AUDIO': 0.80,
                'MICROSOFT_DEVICES': 0.65,
                'CAMERAS': 0.50,
                'GAMING_LAPTOPS': 0.45,
                'BUSINESS_LAPTOPS': 0.50
            },
            'ratings': {
                'SONY_PHONES': 'high',
                'PREMIUM_AUDIO': 'high',
                'MICROSOFT_DEVICES': 'high',
                'default': 'good'
            }
        },
        
        7: {
            'name': 'Audio Lovers',
            'description': 'Đam mê âm thanh, nghe nhạc chuyên nghiệp',
            'weight': 0.08,  # 8% users
            'preferences': {
                'PREMIUM_AUDIO': 0.95,
                'APPLE_AUDIO': 0.75,
                'APPLE_PHONES': 0.60,
                'SAMSUNG_PHONES': 0.50,
                'APPLE_TABLETS': 0.45
            },
            'ratings': {
                'PREMIUM_AUDIO': 'very_high',
                'APPLE_AUDIO': 'high',
                'APPLE_PHONES': 'high',
                'GAMING_PERIPHERALS': 'low',
                'default': 'mid'
            }
        },
        
        8: {
            'name': 'Budget Conscious Users',
            'description': 'Người dùng tiết kiệm, ưu tiên giá trị',
            'weight': 0.12,  # 12% users
            'preferences': {
                'BUSINESS_LAPTOPS': 0.60,
                'MICE_KEYBOARDS': 0.70,
                'SAMSUNG_PHONES': 0.65,
                'MONITORS': 0.55,
                'PRINTERS': 0.50
            },
            'ratings': {
                'BUSINESS_LAPTOPS': 'good',
                'SAMSUNG_PHONES': 'good',
                'MICE_KEYBOARDS': 'high',
                'APPLE_PHONES': 'low',
                'APPLE_LAPTOPS': 'very_low',
                'CAMERAS': 'low',
                'default': 'mid'
            }
        }
    }

    # =========================================================================
    # RATING LEVELS
    # =========================================================================
    def get_rating_score(self, level):
        """Trả về rating score theo level"""
        if level == 'very_high':
            return 5  # Always 5 stars
        elif level == 'high':
            # 70% → 5 stars, 30% → 4 stars
            return 5 if random.random() < 0.7 else 4
        elif level == 'good':
            # 50% → 4 stars, 50% → 3 stars
            return random.choice([3, 4])
        elif level == 'mid':
            # 20% → 4-5, 40% → 3, 40% → 1-2
            r = random.random()
            if r < 0.2:
                return random.choice([4, 5])
            elif r < 0.6:
                return 3
            else:
                return random.choice([1, 2])
        elif level == 'low':
            # 80% → 1-2 stars, 20% → 3 stars
            return random.choice([1, 2]) if random.random() < 0.8 else 3
        elif level == 'very_low':
            return random.choice([1, 2])  # Always low
        else:
            return 3  # Default

    # =========================================================================
    # MAIN LOGIC
    # =========================================================================
    def get_products_by_names(self):
        """Lấy products và map theo groups"""
        all_products = []
        for products in self.PRODUCT_GROUPS.values():
            all_products.extend(products)
        
        products = Product.objects.filter(name__in=all_products)
        
        # Map products to groups
        product_to_group = {}
        for group_name, product_names in self.PRODUCT_GROUPS.items():
            for name in product_names:
                product_to_group[name] = group_name
        
        # Create product map with group info
        product_map = {}
        for p in products:
            product_map[p.id] = {
                'product': p,
                'group': product_to_group.get(p.name, 'OTHER')
            }
        
        self.stdout.write(f'✓ Found {len(product_map)}/45 products')
        
        # Check missing
        found_names = {p.name for p in products}
        missing = set(all_products) - found_names
        if missing:
            self.stdout.write(self.style.WARNING(f'⚠ Missing {len(missing)} products'))
        
        return product_map

    def assign_user_groups(self, users):
        """Gán users vào groups theo weights"""
        group_ids = list(self.USER_GROUPS.keys())
        weights = [self.USER_GROUPS[gid]['weight'] for gid in group_ids]
        
        user_groups = {}
        assigned = random.choices(group_ids, weights=weights, k=len(users))
        
        for idx, user in enumerate(users):
            user_groups[user.id] = assigned[idx]
        
        return user_groups

    def select_products_for_user(self, group_id, product_map):
        """Chọn products mà user sẽ rate dựa trên preferences"""
        group_config = self.USER_GROUPS[group_id]
        preferences = group_config['preferences']
        
        selected = []
        
        for product_id, info in product_map.items():
            product_group = info['group']
            
            # Lấy probability từ preferences
            prob = preferences.get(product_group, 0.15)  # Default 15% for other groups
            
            # Random để quyết định có rate hay không
            if random.random() < prob:
                selected.append(product_id)
        
        return selected

    def generate_rating_for_product(self, group_id, product_info):
        """Generate rating dựa trên group preferences"""
        group_config = self.USER_GROUPS[group_id]
        ratings = group_config['ratings']
        
        product_group = product_info['group']
        
        # Lấy rating level cho product group này
        level = ratings.get(product_group, ratings.get('default', 'mid'))
        
        return self.get_rating_score(level)

    def generate_ratings(self, user_limit=None):
        """Main generation function"""
        # Load users
        users = list(User.objects.all())
        if user_limit:
            users = users[:user_limit]
        
        if not users:
            self.stdout.write(self.style.ERROR('❌ No users found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ Found {len(users)} users'))
        
        # Load products
        product_map = self.get_products_by_names()
        if not product_map:
            self.stdout.write(self.style.ERROR('❌ No products found'))
            return
        
        # Assign user groups
        user_groups = self.assign_user_groups(users)
        
        # Display group distribution
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- User Group Distribution ---'))
        for gid in sorted(self.USER_GROUPS.keys()):
            count = sum(1 for g in user_groups.values() if g == gid)
            pct = count / len(users) * 100
            name = self.USER_GROUPS[gid]['name']
            self.stdout.write(f'Group {gid} ({name}): {count} users ({pct:.1f}%)')
        
        # Generate ratings
        self.stdout.write('')
        self.stdout.write('Generating ratings...')
        
        ratings_batch = []
        total_ratings = 0
        batch_size = 500
        
        for idx, user in enumerate(users, 1):
            group_id = user_groups[user.id]
            
            # Select products based on preferences
            products_to_rate = self.select_products_for_user(group_id, product_map)
            
            for product_id in products_to_rate:
                product_info = product_map[product_id]
                score = self.generate_rating_for_product(group_id, product_info)
                
                rating = Rating(
                    user=user,
                    product=product_info['product'],
                    score=score,
                    rating_type=Rating.EXPLICIT,
                    confidence=1.0,
                    source='synthetic_data'
                )
                
                ratings_batch.append(rating)
                total_ratings += 1
                
                if len(ratings_batch) >= batch_size:
                    Rating.objects.bulk_create(ratings_batch, ignore_conflicts=True)
                    self.stdout.write(
                        f'  → {idx}/{len(users)} users | {total_ratings:,} ratings...', 
                        ending='\r'
                    )
                    self.stdout.flush()
                    ratings_batch = []
        
        if ratings_batch:
            Rating.objects.bulk_create(ratings_batch, ignore_conflicts=True)
        
        # Summary
        self.stdout.write('')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('✓ COMPLETED'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'Total products: {len(product_map)}')
        self.stdout.write(f'Total ratings: {total_ratings:,}')
        self.stdout.write(f'Average per user: {total_ratings / len(users):.1f}')
        
        self.validate_ratings()

    def validate_ratings(self):
        """Validation và statistics"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- Rating Statistics ---'))
        
        from django.db.models import Count
        
        total = Rating.objects.filter(rating_type=Rating.EXPLICIT).count()
        distribution = Rating.objects.filter(
            rating_type=Rating.EXPLICIT
        ).values('score').annotate(count=Count('id')).order_by('score')
        
        for item in distribution:
            count = item['count']
            score = item['score']
            pct = (count / total * 100) if total > 0 else 0
            self.stdout.write(f'{score} stars: {count:>6,} ({pct:>5.1f}%)')
        
        self.stdout.write(self.style.SUCCESS('='*70))