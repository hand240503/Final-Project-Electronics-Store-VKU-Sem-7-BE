

from django.urls import path
from api.recommender import views

app_name = 'recommender'

urlpatterns = [
    path('popular/', views.get_popular_products, name='popular-products'),
]
