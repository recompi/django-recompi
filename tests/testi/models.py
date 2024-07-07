from django.db import models
from django_recompi.models import RecomPIModelMixin


# Product model to represent items in an e-commerce platform
class Product(models.Model, RecomPIModelMixin):
    RECOMPI_DATA_FIELDS = {
        "product-view": [
            "name",
            "reviews__comment",
            "reviews__rating",
            "reviews__counter.count",
        ],
        "product-click": [
            "name",
            "reviews__comment",
            "reviews__rating",
            "reviews__counter.count",
        ],
        "test": ["name"],
    }
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()

    def __str__(self):
        return self.name


# Choices for review rating
class RatingChoices(models.TextChoices):
    ONE = "1", "One"
    TWO = "2", "Two"
    THREE = "3", "Three"
    FOUR = "4", "Four"
    FIVE = "5", "Five"


# Review model to represent user reviews on products
class Review(models.Model):
    product = models.ForeignKey(
        Product, related_name="reviews", on_delete=models.CASCADE
    )
    comment = models.CharField(max_length=200, db_index=True)
    rating = models.CharField(
        choices=RatingChoices.choices, max_length=1, db_index=True
    )
    counter = models.ForeignKey(
        "ReviewCounter",
        related_name="reviews",
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Review of {self.product.name} - {self.rating}"


# Simple counter model for review-related statistics
class ReviewCounter(models.Model):
    count = models.IntegerField(default=0)


# Example:
# from recompi import SecureProfile, Location
# from testi.models import Product

# # Track user interaction with a product
# product = Product.objects.first()
# product.recompi_track(
#     "product-view",
#     SecureProfile("user_id", "some_unique_user_id"),
#     Location(url="https://www.example.com/products/1"),
# )

# # # Get product recommendations for a user
# recommendations = Product.recompi_recommend(
#     "product-view",
#     SecureProfile("user_id", "some_unique_user_id"),
# )

# print({k:{"name": p.name, "recommedation-rank": p.recompi_rank} for k, pp in recommendations.items() for p in pp})
