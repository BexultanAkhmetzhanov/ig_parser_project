from django.db import models
from establishments.models import Establishment

class Promotion(models.Model):
    STATUS_MODERATION = 'moderation'
    STATUS_PUBLISHED = 'published'
    STATUS_DELETED = 'deleted'
    
    STATUS_CHOICES = [
        (STATUS_MODERATION, 'На модерации'),
        (STATUS_PUBLISHED, 'Опубликовано'),
        (STATUS_DELETED, 'Удалено'),
    ]

    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name="promotions", verbose_name="Заведение")
    
    raw_text = models.TextField(verbose_name="Сырой текст из Instagram")
    edited_text = models.TextField(blank=True, null=True, verbose_name="Отредактированный текст")
    conditions = models.TextField(blank=True, null=True, verbose_name="Условия и дни проведения")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_MODERATION, verbose_name="Статус")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата публикации")

    def __str__(self):
        return f"Акция от {self.establishment.name} (Статус: {self.get_status_display()})"

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

class Media(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="media", verbose_name="Акция")
    file_path = models.CharField(max_length=500, verbose_name="Путь к файлу")
    
    file_type = models.CharField(max_length=10, choices=[('image', 'Изображение'), ('video', 'Видео')], verbose_name="Тип файла")

    def __str__(self):
        return f"Медиафайл для акции #{self.promotion.id}"

    class Meta:
        verbose_name = "Медиафайл"
        verbose_name_plural = "Медиафайлы"