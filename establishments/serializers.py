# establishments/serializers.py

from rest_framework import serializers
from .models import Establishment
from categories.models import Subcategory
from locations.models import City

class EstablishmentAdminSerializer(serializers.ModelSerializer):
    """Сериализатор для управления заведениями в админ-панели."""
    city_name = serializers.CharField(source='city.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    
    class Meta:
        model = Establishment
        fields = [
            'id', 'name', 'instagram_url', 'additional_info', 
            'city', 'subcategory', 'city_name', 'subcategory_name'
        ]
        extra_kwargs = {
            'city': {'write_only': True},
            'subcategory': {'write_only': True},
        }