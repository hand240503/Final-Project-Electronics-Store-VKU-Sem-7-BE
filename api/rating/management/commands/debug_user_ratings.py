"""
Debug Command - Analyze User Interaction vs Ratings

Shows:
1. Which products user interacted with
2. Which products have explicit ratings
3. Which products should get implicit ratings
4. Why some products are skipped
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count
from api.rating.models import CollectorLog, Rating
from api.products.models import Product
from collections import defaultdict
from django.db.models import Q

class Command(BaseCommand):
    help = 'Debug user interactions and ratings'
    
    WEIGHTS = {
        'buy': 100,
        'addToCart': 50,
        'moreDetails': 35,
        'details': 15,
    }
    
    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='User ID to debug')
    
    def handle(self, *args, **options):
        user_id = options['user_id']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User {user_id} not found'))
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'🔍 DEBUG USER {user_id} ({user.username})'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        # 1. Get all interactions
        logs = CollectorLog.objects.filter(user_id=user_id).order_by('product_id', 'timestamp')
        total_interactions = logs.count()
        
        self.stdout.write(f'\n📊 TOTAL INTERACTIONS: {total_interactions}')
        
        if total_interactions == 0:
            self.stdout.write(self.style.WARNING('No interactions found'))
            return
        
        # 2. Aggregate by product
        product_interactions = defaultdict(lambda: defaultdict(int))
        product_details = {}
        
        for log in logs:
            product_id = log.product_id
            event = log.event
            
            if event in self.WEIGHTS:
                product_interactions[product_id][event] += 1
            
            if product_id not in product_details:
                try:
                    product = Product.objects.get(id=product_id)
                    product_details[product_id] = product.name
                except Product.DoesNotExist:
                    product_details[product_id] = f'Unknown (ID: {product_id})'
        
        # 3. Get explicit ratings
        explicit_ratings = Rating.objects.filter(
            user_id=user_id,
            rating_type=Rating.EXPLICIT
        )
        explicit_product_ids = set(explicit_ratings.values_list('product_id', flat=True))
        
        self.stdout.write(f'\n📝 EXPLICIT RATINGS: {explicit_ratings.count()}')
        if explicit_ratings.count() > 0:
            self.stdout.write('\nProducts with explicit ratings:')
            for rating in explicit_ratings[:10]:  # Show first 10
                product_name = product_details.get(rating.product_id, f'Product {rating.product_id}')
                self.stdout.write(f'  • Product {rating.product_id}: {product_name} - Score: {rating.score}')
            
            if explicit_ratings.count() > 10:
                self.stdout.write(f'  ... and {explicit_ratings.count() - 10} more')
        
        # 4. Get implicit ratings
        implicit_ratings = Rating.objects.filter(
            user_id=user_id,
            rating_type=Rating.IMPLICIT
        )
        
        self.stdout.write(f'\n💡 IMPLICIT RATINGS: {implicit_ratings.count()}')
        if implicit_ratings.count() > 0:
            for rating in implicit_ratings:
                product_name = product_details.get(rating.product_id, f'Product {rating.product_id}')
                self.stdout.write(f'  • Product {rating.product_id}: {product_name} - Score: {rating.score} (Confidence: {rating.confidence})')
        
        # 5. Analyze each interacted product
        self.stdout.write(f'\n📦 INTERACTED PRODUCTS: {len(product_interactions)}')
        self.stdout.write('=' * 80)
        
        for idx, (product_id, events) in enumerate(sorted(product_interactions.items()), 1):
            product_name = product_details.get(product_id, f'Unknown')
            
            # Calculate raw score
            raw_score = sum(self.WEIGHTS[event] * count for event, count in events.items())
            
            # Calculate normalized score (like in main command)
            max_score = max(sum(self.WEIGHTS[e] * c for e, c in evs.items()) 
                          for evs in product_interactions.values())
            normalized_score = (raw_score / max_score) * 4.0 + 1.0
            
            # Check status
            has_explicit = product_id in explicit_product_ids
            has_implicit = implicit_ratings.filter(product_id=product_id).exists()
            
            status = '✅ SAVED' if has_implicit else ('⚠️ SKIPPED (explicit)' if has_explicit else '❌ MISSING')
            
            self.stdout.write(f'\n[{idx}] Product {product_id}: {product_name}')
            self.stdout.write(f'    Status: {status}')
            self.stdout.write(f'    Interactions:')
            for event, count in sorted(events.items(), key=lambda x: self.WEIGHTS[x[0]], reverse=True):
                self.stdout.write(f'      • {event}: {count}x (weight: {self.WEIGHTS[event]})')
            self.stdout.write(f'    Raw Score: {raw_score}')
            self.stdout.write(f'    Normalized Score: {normalized_score:.2f} / 5.0')
            
            if has_explicit:
                explicit_rating = explicit_ratings.get(product_id=product_id)
                self.stdout.write(f'    Explicit Rating: {explicit_rating.score}')
        
        # 6. Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write('=' * 80)
        
        skipped_count = sum(1 for pid in product_interactions.keys() if pid in explicit_product_ids)
        saved_count = implicit_ratings.count()
        missing_count = len(product_interactions) - skipped_count - saved_count
        
        self.stdout.write(f'Total products interacted: {len(product_interactions)}')
        self.stdout.write(f'  ✅ Saved as implicit: {saved_count}')
        self.stdout.write(f'  ⚠️  Skipped (has explicit): {skipped_count}')
        self.stdout.write(f'  ❌ Missing (should be saved): {missing_count}')
        
        if missing_count > 0:
            self.stdout.write(self.style.ERROR(f'\n⚠️  WARNING: {missing_count} products should have implicit ratings but don\'t!'))
            self.stdout.write(self.style.ERROR('    Run: python manage.py calculate_implicit_ratings'))
        
        # 7. Check data integrity
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('🔍 DATA INTEGRITY CHECK'))
        self.stdout.write('=' * 80)
        
        conflicts = Rating.objects.filter(
            user_id=user_id
        ).values('product_id').annotate(
            explicit_count=Count('id', filter=Q(rating_type=Rating.EXPLICIT)),
            implicit_count=Count('id', filter=Q(rating_type=Rating.IMPLICIT))
        ).filter(explicit_count__gt=0, implicit_count__gt=0)
        
        if conflicts.exists():
            self.stdout.write(self.style.ERROR(f'❌ Found {conflicts.count()} products with BOTH explicit and implicit ratings:'))
            for conflict in conflicts:
                product_name = product_details.get(conflict['product_id'], f'Product {conflict["product_id"]}')
                self.stdout.write(f'  • Product {conflict["product_id"]}: {product_name}')
        else:
            self.stdout.write(self.style.SUCCESS('✅ No conflicts found'))
        
        # 8. Show interaction timeline
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📅 INTERACTION TIMELINE (Last 20)'))
        self.stdout.write('=' * 80)
        
        recent_logs = CollectorLog.objects.filter(user_id=user_id).order_by('-timestamp')[:20]
        
        for log in recent_logs:
            product_name = product_details.get(log.product_id, f'Product {log.product_id}')
            has_explicit = log.product_id in explicit_product_ids
            status_icon = '⚠️' if has_explicit else '✅'
            
            self.stdout.write(
                f'{status_icon} {log.timestamp.strftime("%Y-%m-%d %H:%M:%S")} | '
                f'{log.event:12} | Product {log.product_id}: {product_name[:40]}'
            )


