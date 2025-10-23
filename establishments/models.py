from django.db import models
from locations.models import City
from categories.models import Subcategory

class Establishment(models.Model):
    name = models.CharField(max_length=200, verbose_name="Имя заведения")
    instagram_url = models.URLField(unique=True, verbose_name="Ссылка на Instagram")
    additional_info = models.TextField(blank=True, null=True, verbose_name="Дополнительная информация")
    
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="establishments", verbose_name="Город")
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT, related_name="establishments", verbose_name="Подкатегория")
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Заведение"
        verbose_name_plural = "Заведения"