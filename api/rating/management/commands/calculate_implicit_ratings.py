"""
Implicit Rating Calculator - Fixed for Current Model

Changes:
1. Use 'score' instead of 'rating'
2. Use 'created_at' instead of 'rating_timestamp'
3. Add 'confidence' field
4. Add 'source' field
5. Follow Rating model structure correctly
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count, Q
from api.rating.models import CollectorLog, Rating
from api.products.models import Product
from collections import defaultdict


class Command(BaseCommand):
    help = 'Calculate implicit ratings based on user interactions'
    
    WEIGHTS = {
        'buy': 100,
        'addToCart': 50,
        'moreDetails': 35,
        'details': 15,
    }
    
    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                          help='Clear all implicit ratings and exit')
        parser.add_argument('--stats', action='store_true',
                          help='Show statistics only')
        parser.add_argument('--user', type=int,
                          help='Calculate for specific user ID')
        parser.add_argument('--no-clear', action='store_true',
                          help='Skip automatic clearing')
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 IMPLICIT RATING CALCULATOR'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Handle --clear flag
        if options['clear']:
            self._clear_all_implicit_ratings()
            self.stdout.write(self.style.SUCCESS('\n✅ Cleared all implicit ratings. Exiting...'))
            return
        
        # Handle --stats flag
        if options['stats']:
            self._show_statistics()
            return
        
        # Auto-clear old ratings (unless --no-clear)
        if not options.get('no_clear', False):
            self._clear_all_implicit_ratings()
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  Skipping auto-clear (--no-clear flag set)\n'))
        
        # Calculate ratings
        if options['user']:
            self._calculate_for_user(options['user'])
        else:
            self._calculate_for_all_users()
    
    def _clear_all_implicit_ratings(self):
        """Clear ALL implicit ratings before recalculation"""
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
    
    def _get_users_with_interactions(self):
        """
        Get only users who have at least 1 interaction
        Equivalent to: SELECT DISTINCT(user_id) FROM collector_logs
        """
        user_ids = CollectorLog.objects.filter(
            user__isnull=False
        ).values_list('user_id', flat=True).distinct()
        
        return User.objects.filter(id__in=user_ids)
    
    def _get_user_explicit_products(self, user_id):
        """Get set of product IDs that user has already rated explicitly"""
        explicit_product_ids = Rating.objects.filter(
            user_id=user_id,
            rating_type=Rating.EXPLICIT
        ).values_list('product_id', flat=True)
        
        return set(explicit_product_ids)
    
    def _calculate_for_all_users(self):
        """Calculate for all users who have interactions"""
        
        users = self._get_users_with_interactions()
        total_users = users.count()
        
        if total_users == 0:
            self.stdout.write(self.style.ERROR('❌ No users with interactions found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'👥 Found {total_users} users with interactions\n'))
        
        total_saved = 0
        total_skipped_explicit = 0
        total_skipped_zero = 0
        users_skipped_no_valid = 0
        
        for idx, user in enumerate(users, 1):
            user_id = user.id
            interaction_count = CollectorLog.objects.filter(user_id=user_id).count()
            
            self.stdout.write(f'[{idx}/{total_users}] User {user_id} ({interaction_count} interactions)')
            
            saved, skipped_explicit, skipped_zero, has_valid = self._calculate_and_save(user_id)
            
            total_saved += saved
            total_skipped_explicit += skipped_explicit
            total_skipped_zero += skipped_zero
            
            if not has_valid:
                users_skipped_no_valid += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ COMPLETED'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total users processed: {total_users}')
        self.stdout.write(f'Users with no valid ratings: {users_skipped_no_valid}')
        self.stdout.write(f'Ratings saved: {total_saved:,}')
        self.stdout.write(f'Skipped (explicit exists): {total_skipped_explicit:,}')
        self.stdout.write(f'Skipped (rating = 0): {total_skipped_zero:,}')
        
        if total_users > 0:
            avg_per_user = total_saved / total_users
            self.stdout.write(f'Average ratings per user: {avg_per_user:.2f}')
    
    def _calculate_for_user(self, user_id):
        """Calculate for specific user"""
        try:
            user = User.objects.get(id=user_id)
            interaction_count = CollectorLog.objects.filter(user_id=user_id).count()
            
            if interaction_count == 0:
                self.stdout.write(self.style.ERROR(f'❌ User {user_id} has no interactions'))
                return
            
            self.stdout.write(f'Processing {user.username} ({interaction_count} interactions)\n')
            
            saved, skipped_explicit, skipped_zero, has_valid = self._calculate_and_save(user_id)
            
            if not has_valid:
                self.stdout.write(self.style.WARNING(f'⚠️  No valid ratings to save (all skipped or zero)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ Saved: {saved} | Skipped (explicit): {skipped_explicit} | Skipped (zero): {skipped_zero}'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User {user_id} not found'))
    
    def _calculate_and_save(self, user_id):
        """Main calculation logic"""
        
        # Get products user has already rated explicitly
        explicit_products = self._get_user_explicit_products(user_id)
        
        if explicit_products:
            self.stdout.write(f'  ⚠️  User has {len(explicit_products)} explicit ratings - will skip those')
        
        # Calculate ratings
        ratings = self._calculate_implicit_ratings_for_user(user_id)
        
        # Save ratings
        return self._save_ratings(ratings, user_id, explicit_products)
    
    def _calculate_implicit_ratings_for_user(self, user_id):
        """
        Calculate implicit ratings based on user interactions
        
        Steps:
        1. Aggregate events per product (count each event type)
        2. Calculate raw score: weighted sum of events
        3. Normalize to 0-5 scale (max rating = 5)
        
        Formula: rating = (weighted_sum / max_weighted_sum) * 5
        """
        
        # Get all logs for user
        logs = CollectorLog.objects.filter(user_id=user_id)
        
        # Aggregate interactions per product
        product_data = defaultdict(lambda: defaultdict(int))
        
        for log in logs:
            product_id = log.product_id
            event_type = log.event
            
            # Only count events that have weights
            if event_type in self.WEIGHTS:
                product_data[product_id][event_type] += 1
        
        # Calculate raw scores
        ratings = {}
        max_rating = 0
        
        for product_id, events in product_data.items():
            # Calculate weighted sum
            raw_score = (
                self.WEIGHTS['buy'] * events.get('buy', 0) +
                self.WEIGHTS['addToCart'] * events.get('addToCart', 0) +
                self.WEIGHTS['moreDetails'] * events.get('moreDetails', 0) +
                self.WEIGHTS['details'] * events.get('details', 0)
            )
            
            max_rating = max(max_rating, raw_score)
            ratings[product_id] = raw_score
        
        # Normalize to 1-5 scale
        if max_rating > 0:
            for product_id in ratings.keys():
                # Normalize: (score / max_score) * 4 + 1 to get range 1-5
                normalized = (ratings[product_id] / max_rating) * 4.0 + 1.0
                ratings[product_id] = round(normalized, 2)
        
        return ratings
    
    def _calculate_confidence(self, interaction_count):
        """
        Calculate confidence score based on number of interactions
        More interactions = higher confidence
        """
        if interaction_count >= 20:
            return 1.0
        elif interaction_count >= 10:
            return 0.8
        elif interaction_count >= 5:
            return 0.6
        else:
            return 0.4
    
    def _save_ratings(self, ratings, user_id, explicit_products):
        """
        Save ratings to database using correct Rating model fields
        
        Skip conditions:
        1. Product has explicit rating
        2. Rating = 0 or None
        """
        saved = 0
        skipped_explicit = 0
        skipped_zero = 0
        
        for product_id, rating_score in ratings.items():
            # Skip if rating = 0 or None
            if not rating_score or rating_score == 0:
                skipped_zero += 1
                continue
            
            # Skip if user already has explicit rating for this product
            if product_id in explicit_products:
                skipped_explicit += 1
                continue
            
            try:
                user = User.objects.get(id=user_id)
                product = Product.objects.get(id=product_id)
                
                # Count interactions for confidence calculation
                interaction_count = CollectorLog.objects.filter(
                    user_id=user_id,
                    product_id=product_id
                ).count()
                
                confidence = self._calculate_confidence(interaction_count)
                
                # Save or update rating - CORRECT MODEL FIELDS
                Rating.objects.update_or_create(
                    user=user,
                    product=product,
                    rating_type=Rating.IMPLICIT,
                    defaults={
                        'score': rating_score,  # NOT 'rating'
                        'confidence': confidence,
                        'source': 'calculated',
                        # created_at and updated_at are auto-managed
                    }
                )
                
                saved += 1
                    
            except (User.DoesNotExist, Product.DoesNotExist) as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))
                continue
        
        has_valid = saved > 0
        
        if saved > 0:
            msg = f'  ✅ Saved: {saved}'
            if skipped_explicit > 0:
                msg += f' | Skipped (explicit): {skipped_explicit}'
            if skipped_zero > 0:
                msg += f' | Skipped (zero): {skipped_zero}'
            self.stdout.write(msg)
        else:
            self.stdout.write(f'  ⚠️  No ratings saved (explicit: {skipped_explicit}, zero: {skipped_zero})')
        
        return saved, skipped_explicit, skipped_zero, has_valid
    
    def _show_statistics(self):
        """Show statistics"""
        self.stdout.write(self.style.SUCCESS('\n📊 STATISTICS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Rating counts
        implicit_ratings = Rating.objects.filter(rating_type=Rating.IMPLICIT)
        explicit_ratings = Rating.objects.filter(rating_type=Rating.EXPLICIT)
        
        implicit_count = implicit_ratings.count()
        explicit_count = explicit_ratings.count()
        
        if implicit_count == 0:
            self.stdout.write('No implicit ratings found')
            return
        
        # General stats
        users_with_implicit = implicit_ratings.values('user').distinct().count()
        products_with_implicit = implicit_ratings.values('product').distinct().count()
        
        self.stdout.write(f'📊 Rating Overview:')
        self.stdout.write(f'  Explicit ratings: {explicit_count:,}')
        self.stdout.write(f'  Implicit ratings: {implicit_count:,}')
        self.stdout.write(f'  Total ratings: {explicit_count + implicit_count:,}')
        
        self.stdout.write(f'\n👥 Implicit Rating Coverage:')
        self.stdout.write(f'  Users with implicit ratings: {users_with_implicit:,}')
        self.stdout.write(f'  Products with implicit ratings: {products_with_implicit:,}')
        
        if users_with_implicit > 0:
            avg_per_user = implicit_count / users_with_implicit
            self.stdout.write(f'  Average ratings per user: {avg_per_user:.2f}')
        
        # Score distribution
        self.stdout.write(f'\n⭐ Score Distribution (Implicit):')
        score_ranges = [
            ('5 stars (4.5-5.0)', 4.5, 5.01),
            ('4 stars (3.5-4.5)', 3.5, 4.5),
            ('3 stars (2.5-3.5)', 2.5, 3.5),
            ('2 stars (1.5-2.5)', 1.5, 2.5),
            ('1 star (1.0-1.5)', 1.0, 1.5),
        ]
        
        for label, min_score, max_score in score_ranges:
            count = implicit_ratings.filter(
                score__gte=min_score, 
                score__lt=max_score
            ).count()
            if implicit_count > 0:
                pct = (count / implicit_count) * 100
                self.stdout.write(f'  {label}: {count:,} ({pct:.1f}%)')
        
        # Confidence distribution
        self.stdout.write(f'\n🎯 Confidence Distribution:')
        high_conf = implicit_ratings.filter(confidence__gte=0.8).count()
        med_conf = implicit_ratings.filter(confidence__gte=0.5, confidence__lt=0.8).count()
        low_conf = implicit_ratings.filter(confidence__lt=0.5).count()
        
        if implicit_count > 0:
            self.stdout.write(f'  High (≥0.8): {high_conf:,} ({high_conf/implicit_count*100:.1f}%)')
            self.stdout.write(f'  Medium (0.5-0.8): {med_conf:,} ({med_conf/implicit_count*100:.1f}%)')
            self.stdout.write(f'  Low (<0.5): {low_conf:,} ({low_conf/implicit_count*100:.1f}%)')
        
        # User interaction stats
        self.stdout.write(f'\n👤 User Activity:')
        
        all_users = User.objects.all().count()
        users_with_interactions = CollectorLog.objects.filter(
            user__isnull=False
        ).values('user_id').distinct().count()
        users_without_interactions = all_users - users_with_interactions
        
        self.stdout.write(f'  Total users: {all_users:,}')
        self.stdout.write(f'  Users with interactions: {users_with_interactions:,}')
        self.stdout.write(f'  Users without interactions: {users_without_interactions:,}')
        
        # Interaction distribution
        user_interactions = CollectorLog.objects.filter(
            user__isnull=False
        ).values('user_id').annotate(
            count=Count('id')
        )
        
        low = sum(1 for u in user_interactions if u['count'] < 10)
        medium = sum(1 for u in user_interactions if 10 <= u['count'] < 50)
        high = sum(1 for u in user_interactions if u['count'] >= 50)
        
        self.stdout.write(f'\n📈 Interaction Levels:')
        self.stdout.write(f'  Low (1-9): {low:,}')
        self.stdout.write(f'  Medium (10-49): {medium:,}')
        self.stdout.write(f'  High (50+): {high:,}')
        
        # Data integrity check
        self.stdout.write(f'\n🔍 Data Integrity:')
        conflicts = Rating.objects.values('user_id', 'product_id').annotate(
            explicit_count=Count('id', filter=Q(rating_type=Rating.EXPLICIT)),
            implicit_count=Count('id', filter=Q(rating_type=Rating.IMPLICIT))
        ).filter(explicit_count__gt=0, implicit_count__gt=0).count()
        
        if conflicts > 0:
            self.stdout.write(self.style.ERROR(f'  ⚠️  Found {conflicts} conflicts (products with BOTH explicit and implicit ratings)'))
            self.stdout.write(self.style.ERROR(f'      This should not happen - please investigate!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ No conflicts - explicit and implicit ratings are properly separated'))