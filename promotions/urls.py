from django.urls import path
from .views import PromotionListView, ModerationListView, ModerationDetailView,TriggerParseView

urlpatterns = [
    path('promotions/', PromotionListView.as_view(), name='promotion-list'),    

    path('moderation-list/', ModerationListView.as_view(), name='moderation-list'),
    path('moderation-promo/<int:pk>/', ModerationDetailView.as_view(), name='moderation-detail'),
    path('trigger-parse/', TriggerParseView.as_view(), name='trigger-parse'),
]