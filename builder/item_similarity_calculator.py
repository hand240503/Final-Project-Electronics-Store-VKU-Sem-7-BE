"""
Item (Product) Similarity Calculator
Tính toán độ tương đồng giữa các sản phẩm dựa trên collaborative filtering

Usage:
    # Xuất CSV
    python -m builder.item_similarity_calculator
    
    # Lưu vào database
    python -m builder.item_similarity_calculator --save-to-db
    
    # Advanced
    python -m builder.item_similarity_calculator --min-overlap 20 --min-sim 0.3 --save-to-db
"""

import os
import sys
import argparse
import pandas as pd
import logging
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import coo_matrix
from datetime import datetime

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "electronics_store_vku_backend.settings")

import django
django.setup()

# Import sau khi Django setup
from api.rating.models import Rating
from api.products.models import Product
from django.contrib.auth.models import User
from electronics_store_vku_backend import settings

# Setup logging
logging.basicConfig(
    format='%(asctime)s : %(levelname)s : %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('ItemSimilarityCalculator')


class ItemSimilarityMatrixBuilder:
    """
    Xây dựng ma trận độ tương đồng giữa các items (products)
    """

    def __init__(self, min_overlap=15, min_sim=0.2):
        """
        Args:
            min_overlap: Số user tối thiểu phải rate chung 2 products
            min_sim: Ngưỡng similarity tối thiểu để lưu
        """
        self.min_overlap = min_overlap
        self.min_sim = min_sim
        self.db = settings.DATABASES['default']['ENGINE']

    def build(self, ratings, save=True, save_format='csv'):
        """
        Xây dựng ma trận similarity
        
        Args:
            ratings: DataFrame với columns ['user_id', 'product_id', 'score', 'rating_type']
            save: Có lưu hay không
            save_format: 'csv' hoặc 'database'
            
        Returns:
            tuple: (similarity_matrix, product_dict)
        """
        logger.info("=" * 70)
        logger.info("Calculating similarities ... using {} ratings".format(len(ratings)))
        start_time = datetime.now()

        logger.info("Creating ratings matrix")
        
        # Chuẩn bị dữ liệu
        ratings['score'] = ratings['score'].astype(float)
        
        # Normalize rating theo từng user để loại bỏ bias
        logger.info("Normalizing ratings by user...")
        ratings['normalized_score'] = ratings.groupby('user_id')['score'].transform(
            lambda x: self._normalize(x)
        )

        ratings['normalized_score'] = ratings['normalized_score'].astype(float)
        ratings['user_id'] = ratings['user_id'].astype('category')
        ratings['product_id'] = ratings['product_id'].astype('category')

        # Tạo sparse matrix: rows = products, columns = users
        logger.info("Building sparse matrix...")
        coo = coo_matrix((
            ratings['normalized_score'].astype(float),
            (ratings['product_id'].cat.codes.copy(),
             ratings['user_id'].cat.codes.copy())
        ))

        logger.info("Calculating overlaps between products...")
        # Tính số users đã rate chung giữa các products
        overlap_matrix = coo.astype(bool).astype(int).dot(
            coo.transpose().astype(bool).astype(int)
        )

        number_of_overlaps = (overlap_matrix > self.min_overlap).count_nonzero()
        logger.info("Overlap matrix leaves {} out of {} with min_overlap={}".format(
            number_of_overlaps,
            overlap_matrix.count_nonzero(),
            self.min_overlap
        ))

        logger.info("Rating matrix (size {}x{}) finished, in {} seconds".format(
            coo.shape[0],
            coo.shape[1],
            (datetime.now() - start_time).total_seconds()
        ))

        # Tính sparsity level
        sparsity_level = 1 - (ratings.shape[0] / (coo.shape[0] * coo.shape[1]))
        logger.info("Sparsity level is {:.4f}%".format(sparsity_level * 100))

        # Tính cosine similarity
        start_time = datetime.now()
        logger.info("Calculating cosine similarity...")
        cor = cosine_similarity(coo, dense_output=False)

        # Lọc theo threshold
        cor = cor.multiply(cor > self.min_sim)
        cor = cor.multiply(overlap_matrix > self.min_overlap)

        # Map product codes về product IDs
        products = dict(enumerate(ratings['product_id'].cat.categories))
        
        logger.info('Correlation finished, done in {} seconds'.format(
            (datetime.now() - start_time).total_seconds()
        ))

        if save:
            start_time = datetime.now()
            
            if save_format == 'csv':
                logger.info('Saving similarities to CSV file...')
                self._save_to_csv(cor, products)
            elif save_format == 'database':
                logger.info('Saving similarities to database...')
                self._save_to_database(cor, products)
            else:
                logger.error(f'Unknown save format: {save_format}')

            logger.info('Save finished, done in {} seconds'.format(
                (datetime.now() - start_time).total_seconds()
            ))

        logger.info("=" * 70)
        return cor, products

    def _normalize(self, x):
        """
        Normalize ratings của một user
        Công thức: (rating - mean) / (max - min)
        """
        x = x.astype(float)
        x_sum = x.sum()
        x_num = x.astype(bool).sum()
        
        if x_num == 0:
            return 0.0
            
        x_mean = x_sum / x_num

        if x_num == 1 or x.std() == 0:
            return 0.0
        
        x_range = x.max() - x.min()
        if x_range == 0:
            return 0.0
            
        return (x - x_mean) / x_range

    def _save_to_csv(self, sm, index):
        """
        Lưu similarities vào CSV file
        """
        start_time = datetime.now()
        
        # Convert sang COO format để dễ iterate
        coo = coo_matrix(sm)
        csr = coo.tocsr()

        logger.info('Converting to COO matrix in {} seconds'.format(
            (datetime.now() - start_time).total_seconds()
        ))
        logger.info('{} similarities to save'.format(coo.count_nonzero()))

        similarities = []
        xs, ys = coo.nonzero()
        
        for x, y in tqdm(zip(xs, ys), total=len(xs), desc="Processing similarities"):
            # Skip diagonal (product với chính nó)
            if x == y:
                continue

            sim = csr[x, y]

            if sim < self.min_sim:
                continue

            similarities.append({
                'source_id': index[x],
                'target_id': index[y],
                'similarity_score': float(sim)
            })

        # Save to CSV
        df = pd.DataFrame(similarities)
        output_file = 'product_similarities.csv'
        df.to_csv(output_file, index=False)
        
        logger.info('{} Similarity items saved to {}'.format(
            len(similarities),
            output_file
        ))

    def _save_to_database(self, sm, index):
        """
        Lưu similarities vào database Django
        """
        try:
            from api.recommender.models import ProductSimilarity
        except ImportError:
            logger.error("Cannot import ProductSimilarity model!")
            logger.error("Please create api/recommender app first or use --save-to-csv")
            return
        
        start_time = datetime.now()
        
        # Clear old data
        logger.info("Deleting old similarities...")
        deleted_count = ProductSimilarity.objects.all().delete()[0]
        logger.info(f"Deleted {deleted_count} old records")
        
        # Convert to COO
        coo = coo_matrix(sm)
        csr = coo.tocsr()
        
        xs, ys = coo.nonzero()
        
        similarities = []
        created_at = datetime.now()
        
        logger.info(f"Processing {len(xs)} similarity pairs...")
        
        for x, y in tqdm(zip(xs, ys), total=len(xs), desc="Saving to DB"):
            # Skip diagonal
            if x == y:
                continue
            
            sim = csr[x, y]
            
            if sim < self.min_sim:
                continue
            
            similarities.append(
                ProductSimilarity(
                    source_id=index[x],
                    target_id=index[y],
                    similarity_score=float(sim),
                    created_at=created_at
                )
            )
            
            # Bulk create every 10000 records
            if len(similarities) >= 10000:
                ProductSimilarity.objects.bulk_create(similarities, ignore_conflicts=True)
                logger.info(f"Saved batch of {len(similarities)} records")
                similarities = []
        
        # Save remaining
        if similarities:
            ProductSimilarity.objects.bulk_create(similarities, ignore_conflicts=True)
            logger.info(f"Saved final batch of {len(similarities)} records")
        
        total_saved = ProductSimilarity.objects.count()
        logger.info(f"Total {total_saved} similarity records in database")


def load_all_ratings(min_ratings=1, rating_type=None):
    """
    Load tất cả ratings từ database
    
    Args:
        min_ratings: Số rating tối thiểu của user
        rating_type: 'explicit', 'implicit' hoặc None (cả 2)
        
    Returns:
        DataFrame với columns: user_id, product_id, score, rating_type
    """
    columns = ['user_id', 'product_id', 'score', 'rating_type']

    # Query ratings từ database
    logger.info("Loading ratings from database...")
    query = Rating.objects.all()
    
    if rating_type:
        query = query.filter(rating_type=rating_type)
    
    ratings_data = query.values(*columns)
    ratings = pd.DataFrame.from_records(ratings_data, columns=columns)

    logger.info(f"Loaded {len(ratings)} ratings from database")

    if len(ratings) == 0:
        logger.warning("No ratings found in database!")
        return ratings

    # Lọc users có ít nhất min_ratings đánh giá
    user_count = ratings[['user_id', 'product_id']].groupby('user_id').count()
    user_count = user_count.reset_index()
    user_ids = user_count[user_count['product_id'] > min_ratings]['user_id']
    ratings = ratings[ratings['user_id'].isin(user_ids)]

    logger.info(f"After filtering: {len(ratings)} ratings from {len(user_ids)} users")

    ratings['score'] = ratings['score'].astype(float)
    return ratings


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Calculate product similarities based on user ratings'
    )
    
    parser.add_argument(
        '--min-overlap',
        type=int,
        default=10,
        help='Minimum number of common users between products (default: 10)'
    )
    
    parser.add_argument(
        '--min-sim',
        type=float,
        default=0.1,
        help='Minimum similarity threshold to save (default: 0.1)'
    )
    
    parser.add_argument(
        '--min-ratings',
        type=int,
        default=5,
        help='Minimum number of ratings per user (default: 5)'
    )
    
    parser.add_argument(
        '--rating-type',
        type=str,
        choices=['explicit', 'implicit', 'all'],
        default='all',
        help='Type of ratings to use (default: all)'
    )
    
    parser.add_argument(
        '--save-to-db',
        action='store_true',
        help='Save to database instead of CSV'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving results'
    )
    
    return parser.parse_args()


def main():
    """
    Main function để chạy tính toán similarity
    """
    # Parse arguments
    args = parse_arguments()
    
    logger.info("=" * 70)
    logger.info("PRODUCT SIMILARITY CALCULATION")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Parameters:")
    logger.info(f"  - Min overlap: {args.min_overlap}")
    logger.info(f"  - Min similarity: {args.min_sim}")
    logger.info(f"  - Min ratings per user: {args.min_ratings}")
    logger.info(f"  - Rating type: {args.rating_type}")
    logger.info(f"  - Save to DB: {args.save_to_db}")
    logger.info(f"  - Dry run: {args.dry_run}")
    logger.info("")

    # Load ratings
    logger.info("Loading ratings...")
    rating_type_filter = None if args.rating_type == 'all' else args.rating_type
    
    try:
        all_ratings = load_all_ratings(
            min_ratings=args.min_ratings,
            rating_type=rating_type_filter
        )
    except Exception as e:
        logger.error(f"Error loading ratings: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    if len(all_ratings) == 0:
        logger.error("No ratings found! Please check your database.")
        return

    # Build similarity matrix
    logger.info("Building similarity matrix...")
    builder = ItemSimilarityMatrixBuilder(
        min_overlap=args.min_overlap,
        min_sim=args.min_sim
    )
    
    # Determine save format
    save_format = 'database' if args.save_to_db else 'csv'
    
    try:
        similarity_matrix, products = builder.build(
            all_ratings, 
            save=not args.dry_run,
            save_format=save_format
        )
    except Exception as e:
        logger.error(f"Error building matrix: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    logger.info("")
    logger.info("=" * 70)
    logger.info("✓ COMPLETED!")
    logger.info(f"Total products: {len(products)}")
    logger.info(f"Total similarities: {similarity_matrix.count_nonzero():,}")
    
    if args.dry_run:
        logger.info("")
        logger.info("⚠ DRY RUN - No data was saved")
    else:
        logger.info("")
        if args.save_to_db:
            logger.info("✓ Data saved to database successfully")
        else:
            logger.info("✓ Data saved to product_similarities.csv successfully")
    
    logger.info("=" * 70)


if __name__ == '__main__':
    main()