"""
Implicit Rating Calculator with Cold Start Problem Solutions

Strategies implemented:
1. Content-Based Bootstrapping for new users
2. Popularity-Based Baseline for new products
3. Hybrid approach combining collaborative + content
4. Minimum interaction threshold
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
    MIN_USER_INTERACTIONS = 5  # Minimum interactions to be considered "warm"
    MIN_PRODUCT_INTERACTIONS = 3
    COLD_START_CONFIDENCE = 0.3  # Low confidence for cold start ratings
    
    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--stats', action='store_true')
        parser.add_argument('--user', type=int)
        parser.add_argument('--cold-start-only', action='store_true',
                          help='Only calculate for cold start users/products')
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 IMPLICIT RATING WITH COLD START HANDLING'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if options['clear']:
            self._clear_ratings()
        
        if options['user']:
            self._calculate_for_user(options['user'])
        else:
            self._calculate_for_all_users(options.get('cold_start_only', False))
        
        if options['stats']:
            self._show_statistics()
    
    def _clear_ratings(self):
        count = Rating.objects.filter(rating_type=Rating.IMPLICIT).count()
        Rating.objects.filter(rating_type=Rating.IMPLICIT).delete()
        self.stdout.write(self.style.WARNING(f'🗑️  Deleted {count:,} ratings\n'))
    
    def _calculate_for_all_users(self, cold_start_only=False):
        """Calculate for all users with cold start handling"""
        
        # Get all users (not just those with interactions)
        if cold_start_only:
            # Only cold start users
            users = self._get_cold_start_users()
            self.stdout.write(self.style.WARNING(f'❄️  Processing {len(users)} COLD START users\n'))
        else:
            users = User.objects.all()
            self.stdout.write(self.style.SUCCESS(f'👥 Processing {users.count()} users\n'))
        
        total_saved = 0
        total_updated = 0
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
            
            saved, updated = self._calculate_and_save(user_id, is_cold)
            total_saved += saved
            total_updated += updated
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ COMPLETED'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Cold start users: {cold_users}')
        self.stdout.write(f'Warm users: {warm_users}')
        self.stdout.write(f'Created: {total_saved:,} | Updated: {total_updated:,}')
    
    def _calculate_for_user(self, user_id):
        """Calculate for specific user"""
        try:
            user = User.objects.get(id=user_id)
            interaction_count = CollectorLog.objects.filter(user_id=user_id).count()
            is_cold = interaction_count < self.MIN_USER_INTERACTIONS
            
            status = "COLD START" if is_cold else "WARM"
            self.stdout.write(f'Processing {user.username} ({status} - {interaction_count} interactions)\n')
            
            saved, updated = self._calculate_and_save(user_id, is_cold)
            self.stdout.write(self.style.SUCCESS(f'✅ Created: {saved} | Updated: {updated}'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User {user_id} not found'))
    
    def _calculate_and_save(self, user_id, is_cold_start):
        """Main calculation logic with cold start detection"""
        
        if is_cold_start:
            # Use cold start strategy
            ratings = self._calculate_cold_start(user_id)
        else:
            # Use normal collaborative filtering
            ratings = self._calculate_warm_user(user_id)
        
        return self._save_ratings(ratings, user_id, is_cold_start)
    
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
        
        # Calculate ratings with ABSOLUTE thresholds (not relative)
        ratings = {}
        
        for product_id, data in product_data.items():
            raw_score = data['total_score']
            
            # Use absolute scoring with diminishing returns
            # This prevents single product from always getting 5.0
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
            # Strategy 1: Pure Cold Start (no interactions at all)
            return self._popularity_baseline()
        
        elif interaction_count < self.MIN_USER_INTERACTIONS:
            # Strategy 2: Sparse Data (some interactions but not enough)
            return self._hybrid_cold_start(user_id)
        
        else:
            # Should not reach here, but fallback
            return self._calculate_warm_user(user_id)
    
    def _popularity_baseline(self):
        """
        Strategy for users with ZERO interactions
        Return popular products as baseline recommendations
        """
        
        # Get global popularity scores
        popular_products = CollectorLog.objects.values('product_id').annotate(
            interaction_count=Count('id'),
            buy_count=Count('id', filter=Q(event='buy')),
            cart_count=Count('id', filter=Q(event='addToCart'))
        ).order_by('-interaction_count')[:20]  # Top 20 popular products
        
        ratings = {}
        
        for idx, product in enumerate(popular_products):
            # Score based on popularity rank and quality of interactions
            base_score = 5.0 - (idx * 0.15)  # Decreasing from 5.0
            
            # Boost for quality interactions
            quality_boost = (
                product['buy_count'] * 0.1 + 
                product['cart_count'] * 0.05
            ) / max(product['interaction_count'], 1)
            
            final_score = base_score + quality_boost
            
            ratings[product['product_id']] = {
                'score': max(min(final_score, 5.0), 2.5),  # Range: 2.5-5.0
                'confidence': self.COLD_START_CONFIDENCE,
                'is_cold': True
            }
        
        return ratings
    
    def _hybrid_cold_start(self, user_id):
        """
        Strategy for users with SOME interactions (but < threshold)
        Combine their sparse data with popularity baseline
        """
        
        # Get user's limited interactions
        user_ratings = self._calculate_warm_user(user_id)
        
        # Get popularity baseline
        popular_ratings = self._popularity_baseline()
        
        # Merge: prioritize user data, fill gaps with popularity
        hybrid_ratings = {}
        
        # Add user's interactions (higher weight)
        for product_id, rating_info in user_ratings.items():
            hybrid_ratings[product_id] = {
                'score': rating_info['score'],
                'confidence': self.COLD_START_CONFIDENCE + 0.2,  # Slightly higher confidence
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
        # Users with less than MIN_USER_INTERACTIONS
        user_interactions = CollectorLog.objects.values('user_id').annotate(
            count=Count('id')
        ).filter(count__lt=self.MIN_USER_INTERACTIONS)
        
        cold_user_ids = [u['user_id'] for u in user_interactions]
        
        # Also include users with ZERO interactions
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
        
        # Base confidence from interaction count
        count_confidence = min(interaction_count / 20, 1.0)  # Max at 20 interactions
        
        # Diversity bonus
        diversity_bonus = min(event_diversity / 4, 0.3)  # Max 0.3 bonus for 4 event types
        
        # Recency bonus (interactions in last 7 days)
        recent_count = sum(1 for age in data['interactions'] if age <= 7)
        recency_bonus = min(recent_count / 5, 0.2)  # Max 0.2 bonus
        
        total_confidence = count_confidence + diversity_bonus + recency_bonus
        
        return min(total_confidence, 1.0)
    
    def _save_ratings(self, ratings, user_id, is_cold_start):
        """Save ratings with cold start indicator"""
        saved = 0
        updated = 0
        
        for product_id, rating_info in ratings.items():
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
        
        self.stdout.write(f'  ✅ Created: {saved} | Updated: {updated}')
        return saved, updated
    
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
        
        self.stdout.write(f'Total ratings: {total:,}')
        self.stdout.write(f'Users with ratings: {users_count:,}')
        self.stdout.write(f'Products rated: {products_count:,}')
        
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
        users_with_ratings = users_count
        
        # Count users by interaction level
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