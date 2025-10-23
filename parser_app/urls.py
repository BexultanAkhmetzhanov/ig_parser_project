 
from django.urls import path
from .views import ScrapeInstagramView

urlpatterns = [
    path('scrape/', ScrapeInstagramView.as_view(), name='scrape_instagram'),
]