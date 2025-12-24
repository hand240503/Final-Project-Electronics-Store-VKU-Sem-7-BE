

from django.urls import path
from api.recommender import views

app_name = 'recommender'

urlpatterns = [

    path('popular/', views.get_popular_products, name='popular-products'),
    path('<int:product_id>/similar/',views.get_similar_products,name='similar-products'),
    path('<int:product_id>/hybrid/',views.get_product_recommendations,name='product-recommendations'),
]
