from django.db import models
# Create your models here.


class RecipeURL(models.Model):
    url = models.URLField()
    group_name = models.TextField()


class Assignment(models.Model):
    url = models.ForeignKey(RecipeURL)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    token = models.TextField()


class ScrapedRecipe(models.Model):
    scraped_by = models.ForeignKey(Assignment)
    title = models.TextField()
    image_url = models.URLField(null=True, blank=True)
    ingredients = models.TextField()
    instruction = models.TextField()