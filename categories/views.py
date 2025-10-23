# categories/views.py

from rest_framework import generics, viewsets, permissions
from .models import Category, Subcategory
from .serializers import CategoryAdminSerializer, SubcategoryAdminSerializer

# --- View для админки (получение категорий с подкатегориями) ---
class CategoryWithSubcategoriesView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CategoryAdminSerializer
    queryset = Category.objects.prefetch_related('subcategories').all()

# --- Новые ViewSet'ы для админ-панели ---
class CategoryViewSet(viewsets.ModelViewSet):
    """API для CRUD-операций с Категориями."""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CategoryAdminSerializer
    queryset = Category.objects.prefetch_related('subcategories').all()

class SubcategoryViewSet(viewsets.ModelViewSet):
    """API для CRUD-операций с Подкатегориями."""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SubcategoryAdminSerializer
    queryset = Subcategory.objects.all()