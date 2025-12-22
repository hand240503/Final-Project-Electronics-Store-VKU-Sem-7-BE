from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.products.models import Product
from api.rating.models import Rating
import random
from typing import Dict

class Command(BaseCommand):
    help = 'Generate synthetic explicit ratings for recommendation system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=None,
            help='Number of users to generate ratings for (default: all users)'
        )
        parser.add_argument(
            '--coverage',
            type=float,
            default=0.7,
            help='Percentage of products each user rates (0.0-1.0, default: 0.7 = 70%%)'
        )
        parser.add_argument(
            '--min-ratings',
            type=int,
            default=5,
            dest='min_ratings',
            help='Minimum ratings per user (default: 5)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all explicit ratings before generating'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('Django Rating Data Generator'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        if options['clear']:
            self.clear_ratings()
        
        coverage = options['coverage']
        min_ratings = options['min_ratings']
        user_limit = options['users']
        
        self.generate_ratings(coverage, min_ratings, user_limit)
        self.validate_ratings()

    def clear_ratings(self):
        """Clear all explicit ratings"""
        count = Rating.objects.filter(rating_type=Rating.EXPLICIT).count()
        Rating.objects.filter(rating_type=Rating.EXPLICIT).delete()
        self.stdout.write(self.style.WARNING(f'✓ Deleted {count:,} explicit ratings'))

    # =========================
    # CONSTANTS
    # =========================
    GROUP_SELECTION_RATES = {
        1: {"apple_primary": 0.9, "random": 0.1},
        2: {"smartphone": 0.6, "watch_audio": 0.8, "tv_storage": 0.95},
        3: {"smartphone": 0.5, "wear_audio": 0.8, "tv_tablet": 0.95},
        4: {"laptop": 0.6, "minipc": 0.8, "others": 0.95},
        5: {"dell": 0.38, "hp": 0.665, "lenovo": 0.95},
        6: {"sony_camera": 0.5, "canon_camera": 0.8, "audio": 0.95},
        7: {"ps5": 0.4, "gaming_main": 0.8, "gaming_audio": 0.95},
        8: {"smart_home": 0.4, "monitors": 0.7, "xiaomi_devices": 0.9},
        9: {"xiaomi": 0.4, "oppo": 0.7, "vivo": 0.9},
        10: {"hp_laptop": 0.3, "dell_laptop": 0.55, "lenovo_laptop": 0.75, "printers": 0.9}
    }

    # Rating ranges (scale 1-5, integers only)
    # Distribution: 20% low (1-2) | 30% mid (3) | 50% high (4-5)
    RATING_WEIGHTS = {
        'low': 0.20,    # 1-2 stars: 20%
        'mid': 0.30,    # 3 stars: 30%
        'high': 0.50    # 4-5 stars: 50%
    }

    # =========================
    # RATING FUNCTIONS
    # =========================
    def rate_high(self):
        """Return 4 or 5 stars for high ratings"""
        return random.choice([4, 5])

    def rate_mid(self):
        """Return 3 stars for mid ratings"""
        return 3

    def rate_low(self):
        """Return 1 or 2 stars for low ratings"""
        return random.choice([1, 2])

    def rate_good(self):
        """Return 3 or 4 stars for good ratings"""
        return random.choice([3, 4])

    def rate_very_high(self):
        """Return 5 stars for very high ratings"""
        return 5

    # =========================
    # PRODUCT MAPPING
    # =========================
    def get_product_mapping(self):
        """Map all products by ID"""
        products = Product.objects.select_related('brand', 'category').all()
        return {product.id: product for product in products}

    def get_product_groups(self, product_map):
        """Create product groups from product mapping"""
        
        def filter_by_brand_category(brand=None, category=None, exclude_category=None):
            pids = []
            for pid, product in product_map.items():
                if brand and product.brand.name != brand:
                    continue
                if category:
                    if isinstance(category, list):
                        if product.category.name not in category:
                            continue
                    else:
                        if product.category.name != category:
                            continue
                if exclude_category and product.category.name == exclude_category:
                    continue
                pids.append(pid)
            return pids
        
        groups = {
            'APPLE_ALL': filter_by_brand_category(brand='Apple'),
            'SAMSUNG_SMARTPHONE': filter_by_brand_category(brand='Samsung', category='Smartphone'),
            'SAMSUNG_WATCH_AUDIO': filter_by_brand_category(brand='Samsung', category=['Audio', 'Smartwatch/Wearable']),
            'SAMSUNG_TV_STORAGE': filter_by_brand_category(brand='Samsung', category=['Display/TV', 'Storage', 'Tablet']),
            'XIAOMI_SMARTPHONE': filter_by_brand_category(brand='Xiaomi', category='Smartphone'),
            'XIAOMI_WEAR_AUDIO': filter_by_brand_category(brand='Xiaomi', category=['Audio', 'Smartwatch/Wearable']),
            'XIAOMI_TV_TABLET': filter_by_brand_category(brand='Xiaomi', category=['Display/TV', 'Tablet']),
            'ASUS_LAPTOP': filter_by_brand_category(brand='Asus', category='Laptop/PC'),
            'ASUS_MINIPC': filter_by_brand_category(brand='Asus', category='Mini PC'),
            'ASUS_OTHERS': filter_by_brand_category(brand='Asus', exclude_category='Laptop/PC'),
            'LENOVO_LAPTOP': filter_by_brand_category(brand='Lenovo', category='Laptop/PC'),
            'DELL_LAPTOP': filter_by_brand_category(brand='Dell', category='Laptop/PC'),
            'HP_LAPTOP': filter_by_brand_category(brand='HP', category='Laptop/PC'),
            'CANON_CAMERA': filter_by_brand_category(brand='Canon', category='Camera'),
            'SONY_CAMERA': filter_by_brand_category(brand='Sony', category='Camera'),
            'SONY_AUDIO': filter_by_brand_category(brand='Sony', category='Audio'),
            'LOGITECH_AUDIO': filter_by_brand_category(brand='Logitech', category='Audio'),
            'LOGITECH_PERIPHERALS': filter_by_brand_category(brand='Logitech', category='Input Devices/Peripherals'),
            'GOOGLE_SMARTHOME': filter_by_brand_category(brand='Google', category=['Smart Home/Appliance', 'Tablet', 'Audio']),
            'PS5': filter_by_brand_category(brand='Sony', category='Gaming Console'),
            'GAMING_CONSOLES': filter_by_brand_category(category='Gaming Console'),
            'PRINTERS': filter_by_brand_category(category='Printer'),
            'MONITORS': filter_by_brand_category(category='Display/TV'),
            'BUDGET_XIAOMI': filter_by_brand_category(brand='Xiaomi', category='Smartphone'),
            'BUDGET_OPPO': filter_by_brand_category(brand='Oppo', category='Smartphone'),
            'BUDGET_VIVO': filter_by_brand_category(brand='Vivo', category='Smartphone'),
            'ALL_PRODUCT_IDS': list(product_map.keys())
        }
        
        # Gaming products
        gaming_laptop_brands = ['Asus', 'Lenovo', 'Dell', 'HP']
        gaming_laptops = []
        for pid, product in product_map.items():
            if product.brand.name in gaming_laptop_brands and product.category.name == 'Laptop/PC':
                gaming_laptops.append(pid)
        
        gaming_audio = []
        for pid, product in product_map.items():
            if product.category.name in ['Audio', 'Input Devices/Peripherals']:
                gaming_audio.append(pid)
        
        groups['GAMING_MAIN'] = list(set(groups['GAMING_CONSOLES'] + gaming_laptops))
        groups['GAMING_AUDIO'] = gaming_audio
        
        return groups

    def sample_product_for_group(self, group_id: int, product_groups: dict) -> int:
        """Select product based on user group"""
        r = random.random()
        rates = self.GROUP_SELECTION_RATES.get(group_id, {})
        
        if group_id == 1:
            if r < rates["apple_primary"]:
                return random.choice(product_groups['APPLE_ALL']) if product_groups['APPLE_ALL'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 2:
            if r < rates["smartphone"]:
                return random.choice(product_groups['SAMSUNG_SMARTPHONE']) if product_groups['SAMSUNG_SMARTPHONE'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["watch_audio"]:
                return random.choice(product_groups['SAMSUNG_WATCH_AUDIO']) if product_groups['SAMSUNG_WATCH_AUDIO'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["tv_storage"]:
                return random.choice(product_groups['SAMSUNG_TV_STORAGE']) if product_groups['SAMSUNG_TV_STORAGE'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 3:
            if r < rates["smartphone"]:
                return random.choice(product_groups['XIAOMI_SMARTPHONE']) if product_groups['XIAOMI_SMARTPHONE'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["wear_audio"]:
                return random.choice(product_groups['XIAOMI_WEAR_AUDIO']) if product_groups['XIAOMI_WEAR_AUDIO'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["tv_tablet"]:
                return random.choice(product_groups['XIAOMI_TV_TABLET']) if product_groups['XIAOMI_TV_TABLET'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 4:
            if r < rates["laptop"]:
                return random.choice(product_groups['ASUS_LAPTOP']) if product_groups['ASUS_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["minipc"]:
                return random.choice(product_groups['ASUS_MINIPC']) if product_groups['ASUS_MINIPC'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["others"]:
                return random.choice(product_groups['ASUS_OTHERS']) if product_groups['ASUS_OTHERS'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 5:
            if r < rates["dell"]:
                return random.choice(product_groups['DELL_LAPTOP']) if product_groups['DELL_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["hp"]:
                return random.choice(product_groups['HP_LAPTOP']) if product_groups['HP_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["lenovo"]:
                return random.choice(product_groups['LENOVO_LAPTOP']) if product_groups['LENOVO_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 6:
            if r < rates["sony_camera"]:
                return random.choice(product_groups['SONY_CAMERA']) if product_groups['SONY_CAMERA'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["canon_camera"]:
                return random.choice(product_groups['CANON_CAMERA']) if product_groups['CANON_CAMERA'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["audio"]:
                audio_products = (product_groups.get('SONY_AUDIO', []) + product_groups.get('LOGITECH_AUDIO', []))
                return random.choice(audio_products) if audio_products else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 7:
            if r < rates["ps5"]:
                return random.choice(product_groups['PS5']) if product_groups['PS5'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["gaming_main"]:
                return random.choice(product_groups['GAMING_MAIN']) if product_groups['GAMING_MAIN'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["gaming_audio"]:
                return random.choice(product_groups['GAMING_AUDIO']) if product_groups['GAMING_AUDIO'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 8:
            if r < rates["smart_home"]:
                return random.choice(product_groups['GOOGLE_SMARTHOME']) if product_groups['GOOGLE_SMARTHOME'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["monitors"]:
                return random.choice(product_groups['MONITORS']) if product_groups['MONITORS'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["xiaomi_devices"]:
                xiaomi_devices = (product_groups.get('XIAOMI_TV_TABLET', []) + product_groups.get('XIAOMI_WEAR_AUDIO', []))
                return random.choice(xiaomi_devices) if xiaomi_devices else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 9:
            if r < rates["xiaomi"]:
                return random.choice(product_groups['BUDGET_XIAOMI']) if product_groups['BUDGET_XIAOMI'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["oppo"]:
                return random.choice(product_groups['BUDGET_OPPO']) if product_groups['BUDGET_OPPO'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["vivo"]:
                return random.choice(product_groups['BUDGET_VIVO']) if product_groups['BUDGET_VIVO'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            samsung_phones = product_groups.get('SAMSUNG_SMARTPHONE', [])
            return random.choice(samsung_phones) if samsung_phones else random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        elif group_id == 10:
            if r < rates["hp_laptop"]:
                return random.choice(product_groups['HP_LAPTOP']) if product_groups['HP_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["dell_laptop"]:
                return random.choice(product_groups['DELL_LAPTOP']) if product_groups['DELL_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["lenovo_laptop"]:
                return random.choice(product_groups['LENOVO_LAPTOP']) if product_groups['LENOVO_LAPTOP'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            elif r < rates["printers"]:
                return random.choice(product_groups['PRINTERS']) if product_groups['PRINTERS'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
            return random.choice(product_groups['MONITORS']) if product_groups['MONITORS'] else random.choice(product_groups['ALL_PRODUCT_IDS'])
        
        return random.choice(product_groups['ALL_PRODUCT_IDS'])

    def sample_rating(self, group_id: int, product_id: int, product_map: dict) -> int:
        """
        Generate rating based on user group and product
        Returns integer 1-5 (star rating)
        Distribution: 20% low (1-2) | 30% mid (3) | 50% high (4-5)
        """
        product = product_map[product_id]
        brand = product.brand.name
        category = product.category.name
        
        # Determine rating level based on group preferences
        rating_level = None
        
        if group_id == 1:  # Apple Loyalist
            if brand == "Apple" and category in ["Smartphone", "Laptop/PC", "Tablet", "Audio", "Smartwatch/Wearable"]:
                rating_level = 'high'
            elif brand == "Apple":
                rating_level = 'good'
            else:
                rating_level = 'low'
        
        elif group_id == 2:  # Samsung Heavy Users
            if brand == "Samsung":
                rating_level = 'high'
            elif brand == "Apple":
                rating_level = 'low'
            else:
                rating_level = 'mid'
        
        elif group_id == 3:  # Xiaomi + Smart Devices
            if brand == "Xiaomi":
                rating_level = 'high'
            elif brand in ["Google", "Samsung"] and category in ["Smart Home/Appliance", "Display/TV"]:
                rating_level = 'good'
            else:
                rating_level = 'mid'
        
        elif group_id == 4:  # Asus Laptop Enthusiast
            if brand == "Asus" and category in ["Laptop/PC", "Mini PC", "Display/TV"]:
                rating_level = 'high'
            elif category == "Laptop/PC" and brand in ["Dell", "HP", "Lenovo"]:
                rating_level = 'good'
            elif category == "Smartphone":
                rating_level = 'low'
            else:
                rating_level = 'mid'
        
        elif group_id == 5:  # Laptop Mixed Brand
            if category == "Laptop/PC" and brand in ["Dell", "HP", "Lenovo"]:
                rating_level = 'high'
            else:
                rating_level = 'mid'
        
        elif group_id == 6:  # Camera & Audio Creator
            if brand in ["Canon", "Sony"] and category == "Camera":
                rating_level = 'high'
            elif category == "Audio":
                rating_level = 'good'
            else:
                rating_level = 'low'
        
        elif group_id == 7:  # Gaming Hardcore
            if category == "Gaming Console":
                rating_level = 'high'
            elif category == "Laptop/PC" and brand in ["Asus", "Lenovo", "Dell", "HP"]:
                rating_level = 'high'
            elif category in ["Audio", "Input Devices/Peripherals"]:
                rating_level = 'good'
            elif category == "Smartphone":
                rating_level = 'low'
            else:
                rating_level = 'mid'
        
        elif group_id == 8:  # Smart Home Family
            if brand == "Google" and category in ["Smart Home/Appliance", "Tablet", "Audio"]:
                rating_level = 'high'
            elif category == "Display/TV":
                rating_level = 'high'
            elif brand in ["Samsung", "Xiaomi"] and category in ["Display/TV", "Smart Home/Appliance", "Tablet"]:
                rating_level = 'good'
            else:
                rating_level = 'mid'
        
        elif group_id == 9:  # Budget Android Mixed
            if brand in ["Xiaomi", "Oppo", "Vivo"] and category == "Smartphone":
                rating_level = 'high'
            elif brand == "Samsung" and category == "Smartphone":
                rating_level = 'mid'
            elif brand == "Apple" and category == "Smartphone":
                rating_level = 'low'
            else:
                rating_level = 'mid'
        
        elif group_id == 10:  # Office Workers
            if category == "Laptop/PC" and brand in ["HP", "Dell", "Lenovo"]:
                rating_level = 'high'
            elif category == "Printer":
                rating_level = 'good'
            elif category == "Display/TV":
                rating_level = 'mid'
            elif category == "Smartphone":
                rating_level = 'low'
            else:
                rating_level = 'mid'
        
        # Generate actual rating based on level with controlled distribution
        if rating_level == 'high':
            # 80% get high rating, 15% mid, 5% low
            r = random.random()
            if r < 0.80:
                return self.rate_high()  # 4-5 stars
            elif r < 0.95:
                return self.rate_mid()   # 3 stars
            else:
                return self.rate_low()   # 1-2 stars
        
        elif rating_level == 'good':
            # 60% get high, 30% mid, 10% low
            r = random.random()
            if r < 0.60:
                return self.rate_good()  # 3-4 stars
            elif r < 0.90:
                return self.rate_mid()   # 3 stars
            else:
                return self.rate_low()   # 1-2 stars
        
        elif rating_level == 'low':
            # 80% get low rating, 15% mid, 5% high
            r = random.random()
            if r < 0.80:
                return self.rate_low()   # 1-2 stars
            elif r < 0.95:
                return self.rate_mid()   # 3 stars
            else:
                return self.rate_high()  # 4-5 stars
        
        else:  # mid or default
            # 20% low, 30% mid, 50% high (target distribution)
            r = random.random()
            if r < 0.20:
                return self.rate_low()   # 1-2 stars
            elif r < 0.50:
                return self.rate_mid()   # 3 stars
            else:
                return self.rate_high()  # 4-5 stars

    def assign_user_groups(self, users):
        """Assign groups to users"""
        group_ids = list(range(1, 11))
        group_weights = [0.12, 0.12, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.06]
        
        user_groups = {}
        assigned = random.choices(group_ids, weights=group_weights, k=len(users))
        
        for idx, user in enumerate(users):
            user_groups[user.id] = assigned[idx]
        
        return user_groups

    def generate_ratings(self, coverage, min_ratings, user_limit=None):
        """Generate ratings to database with automatic calculation based on product count"""
        
        users = list(User.objects.all())
        if user_limit:
            users = users[:user_limit]
        
        if not users:
            self.stdout.write(self.style.ERROR('❌ No users found. Please create users first.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ Found {len(users)} users'))
        
        product_map = self.get_product_mapping()
        if not product_map:
            self.stdout.write(self.style.ERROR('❌ No products found. Please create products first.'))
            return
        
        total_products = len(product_map)
        self.stdout.write(self.style.SUCCESS(f'✓ Found {total_products} products'))
        
        # Tính toán số ratings dựa trên số sản phẩm và coverage
        # Ví dụ: 30 products × 0.7 coverage = ~21 ratings/user
        base_ratings = int(total_products * coverage)
        max_ratings = total_products  # Không thể vượt quá tổng số products
        
        # Đảm bảo có ít nhất min_ratings
        base_ratings = max(min_ratings, base_ratings)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Target ratings per user: {base_ratings} (~{coverage*100:.0f}% of {total_products} products)'))
        self.stdout.write(self.style.SUCCESS(f'✓ Min ratings per user: {min_ratings}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Max ratings per user: {max_ratings}'))
        
        product_groups = self.get_product_groups(product_map)
        user_groups = self.assign_user_groups(users)
        
        self.stdout.write(self.style.SUCCESS('✓ Assigned user groups'))
        self.stdout.write('')
        
        total_ratings = 0
        batch_size = 500
        ratings_batch = []
        
        for idx, user in enumerate(users, 1):
            group_id = user_groups[user.id]
            
            # Tính số ratings cho user này với một chút randomness
            # Gaussian distribution với mean=base_ratings, stddev=20% của base_ratings
            stddev = max(2, int(base_ratings * 0.2))
            num_ratings = int(random.gauss(base_ratings, stddev))
            
            # Đảm bảo trong khoảng hợp lệ
            num_ratings = max(min_ratings, min(num_ratings, max_ratings))
            
            rated_products = set()
            attempts = 0
            max_attempts = num_ratings * 3
            
            while len(rated_products) < num_ratings and attempts < max_attempts:
                attempts += 1
                product_id = self.sample_product_for_group(group_id, product_groups)
                
                if product_id not in rated_products:
                    rated_products.add(product_id)
                    product = product_map[product_id]
                    score = self.sample_rating(group_id, product_id, product_map)
                    
                    rating = Rating(
                        user=user,
                        product=product,
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
                            f'  → Processing: {idx}/{len(users)} users | Created {total_ratings:,} ratings...', 
                            ending='\r'
                        )
                        self.stdout.flush()
                        ratings_batch = []
        
        if ratings_batch:
            Rating.objects.bulk_create(ratings_batch, ignore_conflicts=True)
        
        self.stdout.write('')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Created {total_ratings:,} explicit ratings'))
        self.stdout.write(self.style.SUCCESS(f'✓ Average ratings per user: {total_ratings / len(users):.1f}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Coverage: {(total_ratings / len(users)) / total_products * 100:.1f}% of products per user'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- User Group Distribution ---'))
        group_counts = {}
        for gid in range(1, 11):
            count = sum(1 for g in user_groups.values() if g == gid)
            group_counts[gid] = count
            self.stdout.write(f'Group {gid}: {count} users ({count/len(users)*100:.1f}%)')

    def validate_ratings(self):
        """Validate ratings in database"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Rating Validation ==='))
        
        total_ratings = Rating.objects.filter(rating_type=Rating.EXPLICIT).count()
        total_users = Rating.objects.filter(rating_type=Rating.EXPLICIT).values('user').distinct().count()
        total_products = Rating.objects.filter(rating_type=Rating.EXPLICIT).values('product').distinct().count()
        
        self.stdout.write(f'Total explicit ratings: {total_ratings:,}')
        self.stdout.write(f'Users with ratings: {total_users:,}')
        self.stdout.write(f'Products rated: {total_products:,}')
        
        if total_users > 0:
            avg_per_user = total_ratings / total_users
            self.stdout.write(f'Average ratings per user: {avg_per_user:.1f}')
        
        from django.db.models import Count
        rating_dist = Rating.objects.filter(
            rating_type=Rating.EXPLICIT
        ).values('score').annotate(count=Count('id')).order_by('score')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- Rating Distribution ---'))
        for item in rating_dist:
            self.stdout.write(f'Score {item["score"]}: {item["count"]:,} ratings')