from rest_framework import serializers
 
from promotions.models import Promotion, Media
from establishments.models import Establishment
from categories.models import Category, Subcategory
from locations.models import City, Country
 
class CitySerializer(serializers.ModelSerializer):
    """Сериализатор для модели Города."""
    country_name = serializers.CharField(source='country.name', read_only=True)
    
    class Meta:
        model = City
        fields = ['id', 'name', 'country_name']

class SubcategorySerializer(serializers.ModelSerializer):
    """Сериализатор для Подкатегории."""
    class Meta:
        model = Subcategory
        fields = ['id', 'name']

class EstablishmentSerializer(serializers.ModelSerializer):
    """Сериализатор для Заведения."""
    city = CitySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)

    class Meta:
        model = Establishment
        fields = ['id', 'name', 'instagram_url', 'city', 'subcategory']

class MediaSerializer(serializers.ModelSerializer):
    """Сериализатор для Медиафайлов."""
    class Meta:
        model = Media
        fields = ['id', 'file_path', 'file_type']

class PromotionSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор для Акции.
    Он будет включать в себя всю связанную информацию.
    """
    establishment = EstablishmentSerializer(read_only=True)
    media = MediaSerializer(many=True, read_only=True)

    class Meta:
        model = Promotion
        fields = [
            'id',
            'establishment',
            'raw_text',  
            'edited_text',
            'conditions',
            'status',
            'published_at',
            'created_at',  
            'media',
        ]

class PromotionUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления акций.
    Исключает read-only поля для корректной работы PUT запросов.
    """
    # Делаем поля необязательными для обновления
    raw_text = serializers.CharField(required=False, allow_blank=True)
    edited_text = serializers.CharField(required=False, allow_blank=True)
    conditions = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=True)
    
    class Meta:
        model = Promotion
        fields = [
            'raw_text',  
            'edited_text',
            'conditions',
            'status',
        ]