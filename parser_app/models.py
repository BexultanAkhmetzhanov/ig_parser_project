from django.db import models

class ScrapeHistory(models.Model):
    username = models.CharField(max_length=255)
    scraped_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    media_path = models.CharField(max_length=255)