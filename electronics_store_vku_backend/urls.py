from django.contrib import admin
from django.urls import path, include  

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('api.accounts.urls')),   # Auth
    path('api/products/', include('api.products.urls')),
    path('api/cart/', include('api.cart.urls')),
    path('api/orders/', include('api.orders.urls')),
    path('api/payments/', include('api.payments.urls')),
]
