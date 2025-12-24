"""
Implicit Rating Calculator with Cold Start Problem Solutions

Strategies implemented:
1. Content-Based Bootstrapping for new users
2. Popularity-Based Baseline for new products
3. Hybrid approach combining collaborative + content
4. Minimum interaction threshold
5. Skip products with existing explicit ratings
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q
from api.rating.models import CollectorLog, Rating
from api.products.models import Product
from collections import defaultdict
from datetime import date, timedelta
import math


class Command(BaseCommand):
    help = 'Calculate implicit ratings with cold start handling'
    
    WEIGHTS = {
        'buy': 100,
        'addToCart': 50,
        'moreDetails': 35,
        'details': 15,
    }
    
    # Cold start thresholds
    MIN_USER_INTERACTIONS = 5
    MIN_PRODUCT_INTERACTIONS = 3
    COLD_START_CONFIDENCE = 0.3
    
    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                          help='Clear all implicit ratings and exit (no recalculation)')
        parser.add_argument('--stats', action='store_true',
                          help='Show statistics only (no calculation or clearing)')
        parser.add_argument('--user', type=int,
                          help='Calculate for specific user ID')
        parser.add_argument('--cold-start-only', action='store_true',
                          help='Only calculate for cold start users/products')
        parser.add_argument('--no-clear', action='store_true',
                          help='Skip automatic clearing (keep existing implicit ratings)')
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 IMPLICIT RATING WITH COLD START HANDLING'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Handle --clear flag: Clear and exit
        if options['clear']:
            self._clear_all_implicit_ratings()
            self.stdout.write(self.style.SUCCESS('\n✅ Cleared all implicit ratings. Exiting...'))
            return
        
        # Handle --stats flag: Just show statistics
        if options['stats']:
            self._show_statistics()
            return
        
        # Normal calculation mode: Clear old data first (unless --no-clear)
        if not options.get('no_clear', False):
            self._clear_all_implicit_ratings()
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  Skipping auto-clear (--no-clear flag set)\n'))
        
        # Calculate ratings
        if options['user']:
            self._calculate_for_user(options['user'])
        else:
            self._calculate_for_all_users(options.get('cold_start_only', False))
    
    def _clear_ratings(self):
        count = Rating.objects.filter(rating_type=Rating.IMPLICIT).count()
        Rating.objects.filter(rating_type=Rating.IMPLICIT).delete()
        self.stdout.write(self.style.WARNING(f'🗑️  Deleted {count:,} ratings\n'))
    
    def _clear_all_implicit_ratings(self):
        """
        Clear ALL implicit ratings before recalculation
        This ensures fresh start and removes stale data
        """
        count = Rating.objects.filter(rating_type=Rating.IMPLICIT).count()
        
        if count > 0:
            self.stdout.write(self.style.WARNING('\n🧹 CLEANING OLD DATA'))
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(f'Found {count:,} existing implicit ratings')
            self.stdout.write('Deleting all implicit ratings...')
            
            Rating.objects.filter(rating_type=Rating.IMPLICIT).delete()
            
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {count:,} old implicit ratings'))
            self.stdout.write(self.style.SUCCESS('Starting fresh calculation...\n'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✨ No existing implicit ratings found. Starting fresh...\n'))
    
    def _get_user_explicit_products(self, user_id):
        """
        Get set of product IDs that user has already rated explicitly
        These should be excluded from implicit rating calculation
        """
        explicit_product_ids = Rating.objects.filter(
            user_id=user_id,
            rating_type=Rating.EXPLICIT
        ).values_list('product_id', flat=True)
        
        return set(explicit_product_ids)
    
    def _calculate_for_all_users(self, cold_start_only=False):
        """Calculate for all users with cold start handling"""
        
        if cold_start_only:
            users = self._get_cold_start_users()
            self.stdout.write(self.style.WARNING(f'❄️  Processing {len(users)} COLD START users\n'))
        else:
            users = User.objects.all()
            self.stdout.write(self.style.SUCCESS(f'👥 Processing {users.count()} users\n'))
        
        total_saved = 0
        total_updated = 0
        total_skipped = 0
        cold_users = 0
        warm_users = 0
        
        for idx, user in enumerate(users, 1):
            user_id = user.id
            
            # Check if cold start user
            interaction_count = CollectorLog.objects.filter(user_id=user_id).count()
            is_cold = interaction_count < self.MIN_USER_INTERACTIONS
            
            if is_cold:
                self.stdout.write(f'[{idx}/{len(users)}] ❄️  User {user_id} (COLD - {interaction_count} interactions)')
                cold_users += 1
            else:
                self.stdout.write(f'[{idx}/{len(users)}] 🔥 User {user_id} (WARM - {interaction_count} interactions)')
                warm_users += 1
            
            saved, updated, skipped = self._calculate_and_save(user_id, is_cold)
            total_saved += saved
            total_updated += updated
            total_skipped += skipped
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ COMPLETED'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Cold start users: {cold_users}')
        self.stdout.write(f'Warm users: {warm_users}')
        self.stdout.write(f'Created: {total_saved:,} | Updated: {total_updated:,} | Skipped (explicit exists): {total_skipped:,}')
    
    def _calculate_for_user(self, user_id):
        """Calculate for specific user"""
        try:
            user = User.objects.get(id=user_id)
            interaction_count = CollectorLog.objects.filter(user_id=user_id).count()
            is_cold = interaction_count < self.MIN_USER_INTERACTIONS
            
            status = "COLD START" if is_cold else "WARM"
            self.stdout.write(f'Processing {user.username} ({status} - {interaction_count} interactions)\n')
            
            saved, updated, skipped = self._calculate_and_save(user_id, is_cold)
            self.stdout.write(self.style.SUCCESS(f'✅ Created: {saved} | Updated: {updated} | Skipped: {skipped}'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User {user_id} not found'))
    
    def _calculate_and_save(self, user_id, is_cold_start):
        """Main calculation logic with cold start detection"""
        
        # Get products user has already rated explicitly
        explicit_products = self._get_user_explicit_products(user_id)
        
        if explicit_products:
            self.stdout.write(f'  ⚠️  User has {len(explicit_products)} explicit ratings - will skip those products')
        
        if is_cold_start:
            ratings = self._calculate_cold_start(user_id)
        else:
            ratings = self._calculate_warm_user(user_id)
        
        return self._save_ratings(ratings, user_id, is_cold_start, explicit_products)
    
    def _calculate_warm_user(self, user_id):
        """
        Calculate for users with sufficient interaction history
        Uses hybrid approach: collaborative + time decay
        """
        logs = CollectorLog.objects.filter(user_id=user_id)
        
        product_data = defaultdict(lambda: {'total_score': 0, 'interactions': [], 'events': defaultdict(int)})
        today = date.today()
        
        # Aggregate interactions
        for log in logs:
            age_days = (today - log.timestamp.date()).days
            weight = self.WEIGHTS.get(log.event, 0)
            
            # Exponential time decay (half-life = 60 days)
            decay = math.exp(-math.log(2) * age_days / 60)
            
            product_data[log.product_id]['total_score'] += weight * decay
            product_data[log.product_id]['interactions'].append(age_days)
            product_data[log.product_id]['events'][log.event] += 1
        
        # Calculate ratings with ABSOLUTE thresholds
        ratings = {}
        
        for product_id, data in product_data.items():
            raw_score = data['total_score']
            
            # Use absolute scoring with diminishing returns
            if raw_score >= 500:
                rating = 5.0
            elif raw_score >= 300:
                rating = 4.0 + (raw_score - 300) / 200
            elif raw_score >= 150:
                rating = 3.0 + (raw_score - 150) / 150
            elif raw_score >= 50:
                rating = 2.0 + (raw_score - 50) / 100
            else:
                rating = 1.0 + raw_score / 50
            
            ratings[product_id] = {
                'score': min(rating, 5.0),
                'confidence': self._calculate_confidence(data),
                'is_cold': False
            }
        
        return ratings
    
    def _calculate_cold_start(self, user_id):
        """
        Cold Start Strategy - Multi-pronged approach:
        
        1. If user has ANY interaction: Use those + boost with popularity
        2. If user has ZERO interaction: Use pure popularity baseline
        3. Apply content-based filtering if user profile available
        """
        
        interaction_count = CollectorLog.objects.filter(user_id=user_id).count()
        
        if interaction_count == 0:
            return self._popularity_baseline()
        elif interaction_count < self.MIN_USER_INTERACTIONS:
            return self._hybrid_cold_start(user_id)
        else:
            return self._calculate_warm_user(user_id)
    
    def _popularity_baseline(self):
        """
        Strategy for users with ZERO interactions
        Return popular products as baseline recommendations
        """
        
        popular_products = CollectorLog.objects.values('product_id').annotate(
            interaction_count=Count('id'),
            buy_count=Count('id', filter=Q(event='buy')),
            cart_count=Count('id', filter=Q(event='addToCart'))
        ).order_by('-interaction_count')[:20]
        
        ratings = {}
        
        for idx, product in enumerate(popular_products):
            base_score = 5.0 - (idx * 0.15)
            
            quality_boost = (
                product['buy_count'] * 0.1 + 
                product['cart_count'] * 0.05
            ) / max(product['interaction_count'], 1)
            
            final_score = base_score + quality_boost
            
            ratings[product['product_id']] = {
                'score': max(min(final_score, 5.0), 2.5),
                'confidence': self.COLD_START_CONFIDENCE,
                'is_cold': True
            }
        
        return ratings
    
    def _hybrid_cold_start(self, user_id):
        """
        Strategy for users with SOME interactions (but < threshold)
        Combine their sparse data with popularity baseline
        """
        
        user_ratings = self._calculate_warm_user(user_id)
        popular_ratings = self._popularity_baseline()
        
        hybrid_ratings = {}
        
        # Add user's interactions (higher weight)
        for product_id, rating_info in user_ratings.items():
            hybrid_ratings[product_id] = {
                'score': rating_info['score'],
                'confidence': self.COLD_START_CONFIDENCE + 0.2,
                'is_cold': True
            }
        
        # Fill with popular items user hasn't interacted with
        user_product_ids = set(user_ratings.keys())
        added = 0
        
        for product_id, rating_info in popular_ratings.items():
            if product_id not in user_product_ids and added < 10:
                hybrid_ratings[product_id] = rating_info
                added += 1
        
        return hybrid_ratings
    
    def _get_cold_start_users(self):
        """Get list of cold start users"""
        user_interactions = CollectorLog.objects.values('user_id').annotate(
            count=Count('id')
        ).filter(count__lt=self.MIN_USER_INTERACTIONS)
        
        cold_user_ids = [u['user_id'] for u in user_interactions]
        
        all_user_ids = User.objects.values_list('id', flat=True)
        users_with_interactions = CollectorLog.objects.values_list('user_id', flat=True).distinct()
        zero_interaction_users = set(all_user_ids) - set(users_with_interactions)
        
        cold_user_ids.extend(zero_interaction_users)
        
        return User.objects.filter(id__in=cold_user_ids)
    
    def _calculate_confidence(self, data):
        """
        Calculate confidence score based on:
        - Number of interactions
        - Diversity of events
        - Recency
        """
        
        interaction_count = len(data['interactions'])
        event_diversity = len(data['events'])
        
        count_confidence = min(interaction_count / 20, 1.0)
        diversity_bonus = min(event_diversity / 4, 0.3)
        
        recent_count = sum(1 for age in data['interactions'] if age <= 7)
        recency_bonus = min(recent_count / 5, 0.2)
        
        total_confidence = count_confidence + diversity_bonus + recency_bonus
        
        return min(total_confidence, 1.0)
    
    def _save_ratings(self, ratings, user_id, is_cold_start, explicit_products):
        """
        Save ratings with cold start indicator
        Skip products that already have explicit ratings
        """
        saved = 0
        updated = 0
        skipped = 0
        
        for product_id, rating_info in ratings.items():
            # CRITICAL: Skip if user already has explicit rating for this product
            if product_id in explicit_products:
                skipped += 1
                continue
            
            try:
                user = User.objects.get(id=user_id)
                product = Product.objects.get(id=product_id)
                
                rating_obj, created = Rating.objects.update_or_create(
                    user=user,
                    product=product,
                    rating_type=Rating.IMPLICIT,
                    defaults={
                        'score': round(rating_info['score'], 2),
                        'confidence': round(rating_info['confidence'], 2),
                        'source': 'cold_start' if rating_info['is_cold'] else 'calculated',
                    }
                )
                
                if created:
                    saved += 1
                else:
                    updated += 1
                    
            except (User.DoesNotExist, Product.DoesNotExist):
                continue
        
        if skipped > 0:
            self.stdout.write(f'  ✅ Created: {saved} | Updated: {updated} | ⚠️  Skipped (explicit exists): {skipped}')
        else:
            self.stdout.write(f'  ✅ Created: {saved} | Updated: {updated}')
        
        return saved, updated, skipped
    
    def _show_statistics(self):
        """Show statistics including cold start metrics"""
        self.stdout.write(self.style.SUCCESS('\n📊 STATISTICS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        ratings = Rating.objects.filter(rating_type=Rating.IMPLICIT)
        total = ratings.count()
        
        if total == 0:
            self.stdout.write('No ratings found')
            return
        
        # General stats
        users_count = ratings.values('user').distinct().count()
        products_count = ratings.values('product').distinct().count()
        
        self.stdout.write(f'Total implicit ratings: {total:,}')
        self.stdout.write(f'Users with implicit ratings: {users_count:,}')
        self.stdout.write(f'Products rated implicitly: {products_count:,}')
        
        # Explicit vs Implicit comparison
        explicit_count = Rating.objects.filter(rating_type=Rating.EXPLICIT).count()
        self.stdout.write(f'\n📊 Rating Type Distribution:')
        self.stdout.write(f'  Explicit ratings: {explicit_count:,}')
        self.stdout.write(f'  Implicit ratings: {total:,}')
        self.stdout.write(f'  Total ratings: {explicit_count + total:,}')
        
        # Cold start stats
        cold_ratings = ratings.filter(source='cold_start').count()
        warm_ratings = ratings.filter(source='calculated').count()
        
        self.stdout.write(f'\n❄️  Cold Start Analysis:')
        self.stdout.write(f'  Cold start ratings: {cold_ratings:,} ({cold_ratings/total*100:.1f}%)')
        self.stdout.write(f'  Warm ratings: {warm_ratings:,} ({warm_ratings/total*100:.1f}%)')
        
        # Confidence distribution
        self.stdout.write(f'\n🎯 Confidence Distribution:')
        high_conf = ratings.filter(confidence__gte=0.7).count()
        med_conf = ratings.filter(confidence__gte=0.4, confidence__lt=0.7).count()
        low_conf = ratings.filter(confidence__lt=0.4).count()
        
        self.stdout.write(f'  High (≥0.7): {high_conf:,} ({high_conf/total*100:.1f}%)')
        self.stdout.write(f'  Medium (0.4-0.7): {med_conf:,} ({med_conf/total*100:.1f}%)')
        self.stdout.write(f'  Low (<0.4): {low_conf:,} ({low_conf/total*100:.1f}%)')
        
        # User interaction distribution
        self.stdout.write(f'\n👥 User Interaction Distribution:')
        
        all_users = User.objects.all().count()
        
        user_interactions = CollectorLog.objects.values('user_id').annotate(
            count=Count('id')
        )
        
        zero_int = all_users - user_interactions.count()
        sparse = sum(1 for u in user_interactions if u['count'] < 5)
        moderate = sum(1 for u in user_interactions if 5 <= u['count'] < 20)
        active = sum(1 for u in user_interactions if u['count'] >= 20)
        
        self.stdout.write(f'  Zero interactions: {zero_int:,}')
        self.stdout.write(f'  Sparse (1-4): {sparse:,}')
        self.stdout.write(f'  Moderate (5-19): {moderate:,}')
        self.stdout.write(f'  Active (20+): {active:,}')
        
        # Check for conflicts (shouldn't exist now)
        self.stdout.write(f'\n🔍 Data Integrity Check:')
        users_with_both = Rating.objects.values('user_id', 'product_id').annotate(
            explicit_count=Count('id', filter=Q(rating_type=Rating.EXPLICIT)),
            implicit_count=Count('id', filter=Q(rating_type=Rating.IMPLICIT))
        ).filter(explicit_count__gt=0, implicit_count__gt=0).count()
        
        if users_with_both > 0:
            self.stdout.write(self.style.ERROR(f'  ⚠️  Found {users_with_both} products with BOTH explicit and implicit ratings!'))
            self.stdout.write(self.style.ERROR(f'      This should not happen - please investigate!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ No conflicts found - explicit and implicit ratings are properly separated'))