from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from .models import Promotion
from .serializers import PromotionSerializer, PromotionUpdateSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.management import call_command
from django.utils import timezone
import threading

class PromotionListView(generics.ListAPIView):
    """
    API-представление для получения списка опубликованных акций.
    Поддерживает фильтрацию по ID города (параметр ?city=...).
    """
    serializer_class = PromotionSerializer

    def get_queryset(self):
        """
        Этот метод определяет, какие данные отдавать.
        Он переопределен для добавления фильтрации.
        """
        queryset = Promotion.objects.filter(status='published').order_by('-published_at')
        city_id = self.request.query_params.get('city')
        if city_id is not None:
            queryset = queryset.filter(establishment__city_id=city_id)
        
        return queryset

class ModerationListView(generics.ListAPIView):
    """
    API-представление для получения списка акций,
    ожидающих модерации. Доступно только администраторам.
    """
    serializer_class = PromotionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Отдает только акции со статусом 'moderation'."""
        return Promotion.objects.filter(status='moderation').order_by('-created_at')

class ModerationDetailView(generics.RetrieveUpdateAPIView):
    """
    API-представление для получения и обновления одной конкретной акции.
    Доступно только администраторам.
    """
    permission_classes = [permissions.IsAdminUser]
    queryset = Promotion.objects.all()

    def get_serializer_class(self):
        """
        Возвращаем разные сериализаторы для GET и PUT запросов.
        """
        if self.request.method == 'GET':
            return PromotionSerializer
        return PromotionUpdateSerializer

    def update(self, request, *args, **kwargs):
        """
        Переопределяем метод update для лучшей обработки ошибок.
        """
        print(f"=== НАЧАЛО ОБРАБОТКИ PUT ЗАПРОСА ===")
        print(f"URL: {request.path}")
        print(f"Данные запроса: {request.data}")
        print(f"Заголовки: {dict(request.headers)}")
        
        try:
            return super().update(request, *args, **kwargs)
        except ValidationError as e:
            print(f"❌ Ошибка валидации: {e}")
            print(f"Детали ошибки: {e.detail}")
            raise
        except Exception as e:
            print(f"❌ Общая ошибка: {e}")
            raise

    def perform_update(self, serializer):
        """
        Переопределяем метод для добавления логики обновления published_at
        при изменении статуса на 'published'.
        """
        instance = serializer.instance
        old_status = instance.status
        
        print(f"=== ОБНОВЛЕНИЕ АКЦИИ {instance.id} ===")
        print(f"Старый статус: {old_status}")
        print(f"Новые данные: {serializer.validated_data}")
        print(f"Данные запроса: {self.request.data}")
        print(f"Метод запроса: {self.request.method}")
        
        # Сохраняем изменения
        try:
            serializer.save()
            print(f"✅ Акция успешно обновлена. Новый статус: {serializer.instance.status}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            raise
        
        # Если статус изменился на 'published', обновляем published_at
        if old_status != 'published' and serializer.instance.status == 'published':
            serializer.instance.published_at = timezone.now()
            serializer.instance.save(update_fields=['published_at'])
            print(f"Установлена дата публикации: {serializer.instance.published_at}")
        
        print(f"=== КОНЕЦ ОБНОВЛЕНИЯ ===\n")

class TriggerParseView(APIView):
    """
    API-представление для запуска парсера вручную.
    Доступно только администраторам.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        """
        Принимает POST-запрос и запускает команду парсинга в отдельном потоке.
        """
        def run_command_in_thread():
            # Эта функция будет выполняться в фоновом режиме,
            # чтобы не заставлять пользователя ждать завершения парсинга.
            print("Запуск парсинга из API...")
            call_command('parse_instagram')
            print("Парсинг из API завершен.")

        # Запускаем команду в отдельном потоке
        thread = threading.Thread(target=run_command_in_thread)
        thread.start()

        # Сразу же отвечаем пользователю, что задача принята
        return Response(
            {"message": "Процесс парсинга запущен в фоновом режиме. Результаты появятся в разделе модерации через несколько минут."},
            status=status.HTTP_202_ACCEPTED
        )