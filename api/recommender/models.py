from django.db import models
from api.products.models import Product


class ProductSimilarity(models.Model):
    """
    Bảng lưu độ tương đồng giữa các sản phẩm
    Được tính toán bằng collaborative filtering (cosine similarity)
    """
    source = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='similar_to',
        help_text="Sản phẩm nguồn"
    )
    
    target = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='similar_from',
        help_text="Sản phẩm tương tự"
    )
    
    similarity_score = models.FloatField(
        help_text="Điểm tương đồng (0-1), càng cao càng giống"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Thời điểm tính toán"
    )

    class Meta:
        db_table = 'product_similarities'
        unique_together = ['source', 'target']
        indexes = [
            models.Index(fields=['source', '-similarity_score']),
            models.Index(fields=['target', '-similarity_score']),
            models.Index(fields=['similarity_score']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-similarity_score']

    def __str__(self):
        return f"{self.source.name} → {self.target.name}: {self.similarity_score:.3f}"

    @classmethod
    def get_similar_products(cls, product, limit=10, min_score=0.1):
        """
        Lấy danh sách sản phẩm tương tự
        
        Args:
            product: Product object hoặc product_id
            limit: Số lượng sản phẩm tối đa
            min_score: Điểm tương đồng tối thiểu
            
        Returns:
            QuerySet of Product objects
            
        Usage:
            similar = ProductSimilarity.get_similar_products(product, limit=10)
            for p in similar:
                print(p.name, p.similarity_score)
        """
        if isinstance(product, int):
            product_id = product
        else:
            product_id = product.id

        similar_ids = cls.objects.filter(
            source_id=product_id,
            similarity_score__gte=min_score
        ).order_by('-similarity_score').values_list('target_id', flat=True)[:limit]

        # Lấy Product objects và attach similarity score
        products = Product.objects.filter(id__in=similar_ids)
        
        # Tạo dictionary để map similarity scores
        similarity_map = {
            sim.target_id: sim.similarity_score
            for sim in cls.objects.filter(
                source_id=product_id,
                target_id__in=similar_ids
            )
        }
        
        # Attach similarity score vào từng product
        for p in products:
            p.similarity_score = similarity_map.get(p.id, 0.0)
        
        # Sort theo similarity score
        products = sorted(products, key=lambda x: x.similarity_score, reverse=True)
        
        return products

    @classmethod
    def get_similar_products_raw(cls, product_id, limit=10, min_score=0.1):
        """
        Version nhanh hơn, trả về raw data thay vì Product objects
        
        Returns:
            List of dicts: [{'target_id': 123, 'score': 0.85}, ...]
            
        Usage:
            similar = ProductSimilarity.get_similar_products_raw(product_id, limit=10)
            for item in similar:
                product_id = item['target_id']
                score = item['similarity_score']
        """
        return list(cls.objects.filter(
            source_id=product_id,
            similarity_score__gte=min_score
        ).order_by('-similarity_score').values('target_id', 'similarity_score')[:limit])

    @classmethod
    def get_bidirectional_similar(cls, product_id, limit=10):
        """
        Lấy sản phẩm tương tự theo cả 2 chiều (source->target và target->source)
        Merge và sort theo similarity score
        
        Usage:
            similar = ProductSimilarity.get_bidirectional_similar(product_id, limit=10)
        """
        # Lấy cả 2 chiều
        forward = cls.objects.filter(
            source_id=product_id
        ).values_list('target_id', 'similarity_score')
        
        backward = cls.objects.filter(
            target_id=product_id
        ).values_list('source_id', 'similarity_score')
        
        # Merge và sort
        all_similar = {}
        for pid, score in forward:
            all_similar[pid] = max(all_similar.get(pid, 0), score)
        
        for pid, score in backward:
            all_similar[pid] = max(all_similar.get(pid, 0), score)
        
        # Sort và limit
        sorted_similar = sorted(
            all_similar.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'product_id': pid, 'similarity_score': score}
            for pid, score in sorted_similar
        ]

    @classmethod
    def get_statistics(cls):
        """
        Lấy thống kê về similarity matrix
        
        Returns:
            dict với các metrics
        """
        from django.db.models import Avg, Max, Min, Count
        
        stats = cls.objects.aggregate(
            total_pairs=Count('id'),
            avg_score=Avg('similarity_score'),
            max_score=Max('similarity_score'),
            min_score=Min('similarity_score'),
        )
        
        # Đếm số products có similarities
        products_with_sim = cls.objects.values('source_id').distinct().count()
        
        stats['products_with_similarities'] = products_with_sim
        
        return stats