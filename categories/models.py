from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

class Subcategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название подкатегории")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories", verbose_name="Категория")

    def __str__(self):
        return f"{self.category.name} -> {self.name}"

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"