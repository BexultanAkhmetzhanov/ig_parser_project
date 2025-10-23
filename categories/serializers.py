# categories/serializers.py

from rest_framework import serializers
from .models import Category, Subcategory

class SubcategoryAdminSerializer(serializers.ModelSerializer):
    """Сериализатор для управления Подкатегориями в админке."""
    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'category']

class CategoryAdminSerializer(serializers.ModelSerializer):
    """Сериализатор для Категории с вложенным списком её подкатегорий."""
    subcategories = SubcategoryAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'subcategories']