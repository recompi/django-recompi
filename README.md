# Django RecomPI

*Django RecomPI* is a Django model mixin that integrates functionalities of RecomPI (Recommender System API) with Django models, enabling easy recommendation and tracking capabilities within Django applications.

## Installation

You can install *Django RecomPI* via pip. Here's how:

```bash
pip install django-recompi
```

---

## Quick Start

### Setting up a Django model with RecomPI integration

1. **Define your Django model** (e.g., `Product`) and use `RecomPIModelMixin` as a mixin.

```python
from typing import List
from django.db import models
from django_recompi.models import RecomPIModelMixin

class Product(models.Model, RecomPIModelMixin):
    RECOMPI_DATA_FIELDS = [
        "name", # current model's field
        "reviews__comment", # join operation
        "reviews__counter.count", # join and `dot` operations
        "callable_method_single_return", # callable method with signle return
        "callable_method_list_return", # callable method with list return
        "reviews__counter.callable_method", # join and method-call operations
    ]
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()

    def callable_method_single_return(self) -> str:
        return "a-value"

    def callable_method_list_return(self) -> List[str]:
        return ["list", "of", "values"]

    def __str__(self):
        return self.name
```

2. **Define related models** such as `Review` and `ReviewCounter` with appropriate fields.

```python
from django.db import models

class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    comment = models.CharField(max_length=200, db_index=True)
    rating = models.CharField(choices=RatingChoices.choices, max_length=1, db_index=True)
    counter = models.ForeignKey("ReviewCounter", related_name="reviews", on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Review of {self.product.name} - {self.rating}"

class ReviewCounter(models.Model):
    count = models.IntegerField(default=0)
```

### Tracking interactions

```python
# Track user interaction with a product
product = Product.objects.first()

# Using SecureProfile to hash profile identifiers before sending to RecomPI
profile = SecureProfile("profile_id", "user_profile_id")

# Providing location information including optional data
location = Location(
    ip="1.1.1.1",          # Optional: IP address of the user
    url="https://www.example.com/products/1",
    referer="REFERER_URL", # Optional: Referring URL
    useragent="USERAGENT"  # Optional: User agent of the client
)

# Tracking the interaction using RecomPI integration
product.recompi_track(
    "product-view",  # Interaction label
    profile,         # SecureProfile instance
    location         # Location instance
)
```

This revised version clarifies the usage of `SecureProfile` and `Location` classes while also providing a clear example of how to track user interactions with a product using the `recompi_track` method. We encourage you to refer to the original [RecomPI package documentation](https://pypi.org/project/recompi/) for detailed information on these classes and other useful utilities like `Profile`.

### Getting recommendations

```python
# Get product recommendations for a user
recommendations = Product.recompi_recommend(
    "product-view",
    SecureProfile("profile_id", "user_profile_id"),
)

# Example of printing recommendations
print(
    {
        k: {"name": p.name, "recommedation-rank": p.recompi_rank}
        for k, pp in recommendations.items()
        for p in pp
    }
)
```
---

## RecomPI as a Recommendation-Based Search Engine

The `django-recompi` package provides a fast, reliable, and secure recommendation-based search engine.

### Perform a Search
```python
results = Product.recompi_search(
    query="awesome product",
    labels="product-view"
)
```

### Track a Click
```python
product = Product.objects.get(pk=1395)
product.recompi_search_track(
    query="awesome product",
    location=Location(url="https://www.example.com/search-page"),
    labels="product-view"
)
```

For more detailed information, check out our [advanced documentation](https://github.com/recompi/django-recompi/blob/develop/docs/advanced.md#6-search-methods-in-recompimodelmixin). You can also learn how to pre-train RecomPI's A.I. to boost results from day one with a single script [here](https://github.com/recompi/django-recompi/blob/develop/docs/advanced.md#pre-train-data-for-optimal-search-engine-performance).

### Examples and Use Cases

Explore these examples to understand how *Django RecomPI* can be applied:

- **E-commerce Recommendation**: Track user interactions on product pages and recommend related products based on their behavior.
- **Content Personalization**: Customize content recommendations based on user preferences and historical interactions.

---

## Linking two objects with each other using recommendation system

Linking two models requires additional data fields to create a `SecureProfile` instance. By default, the package uses the primary key (`pk`) as the profile ID. However, in scenarios where linking models based on a series of fields is necessary—such as suggesting products based on client attributes like gender, age, and tourist status—using `pk` as the profile ID may not be suitable. For instance, if a user is a one-time visitor unlikely to return soon, a more tailored approach is needed.

### Example: Customizing `Client` Profile Fields

```python
class Client(AbstractUser, RecomPIModelMixin):
    RECOMPI_PROFILE_ID = [
        "gender",
        "age",
        "if_tourist",
        # Add more relevant fields as needed
    ]
```

### Recommending Products to Clients

To recommend products to a given `Client`, use the following example:

```python
client = Client.objects.get(**criteria)
recommended_products = client.recompi_recommend_links(
    model_class=Product,
    labels=["buy", "interested"]
)

for label, products in recommended_products.items():
    for product in products:
        print("Recommend Product #{} for '{}'".format(product.pk, label))
```

### Linking Client Interests to Products

After gathering client information and observing their interactions, link clients to products:

```python
products_bought = Product.objects.filter(pk__in=BOUGHT_PRODUCT_IDS)
products_of_interest = Product.objects.filter(pk__in=INTERESTED_PRODUCT_IDS)

for product in products_bought:
    client.recompi_link(
        instance=product,
        label="buy",
        location="https://www.example.com/product/{}".format(product.pk),
    )

for product in products_of_interest:
    client.recompi_link(
        instance=product,
        label="interested",
        location="https://www.example.com/product/{}".format(product.pk),
    )
```

This example can be extended to any scenario where you need to establish links between two models and receive recommended objects in return.

### Benefits of Linked Objects Using RecomPI

- **Enhanced Personalization:** Tailor recommendations based on user interactions.
- **Improved Engagement:** Guide users through related items for increased interaction.
- **Behavioral Insights:** Understand user preferences to refine recommendations.
- **Optimized Search:** Deliver precise search results by understanding item relationships.
- **Accelerated Learning:** Quickly optimize recommendations by pre-training with linked objects.
- **Detailed Analytics:** Analyze user interactions to inform decision-making and strategy.

### Example Use Cases

1. **E-commerce:** Enhance product discovery with complementary item recommendations.
2. **Content Platforms:** Keep users engaged with relevant articles or videos based on interests.
3. **Social Networks:** Foster community engagement by suggesting connections based on shared interests.

For advanced features and more detailed information, refer to our [advanced documentation](https://github.com/recompi/django-recompi/blob/develop/docs/advanced.md#7-linking-two-records-from-two-different-models).

---

## Settings Configuration

*Django RecomPI* can be customized through the following settings in your `settings.py` file, you can read the full documentation [here](https://github.com/recompi/django-recompi/blob/main/docs/settings.md); but the most important settings you **much set** in your `settings.py` is `RECOMPI_API_KEY`:

### `RECOMPI_API_KEY`

- **Type:** `str`
- **Description:** API key for accessing the RecomPI service. Required for integration.
- **Note:** To obtain `RECOMPI_API_KEY`, register on the [RecomPI panel](https://panel.recompi.com/clients/sign_in). After registration, [add a campaign](https://panel.recompi.com/campaigns/new) in the panel, and a campaign token will be generated instantly. Use this token as your API key in the code.

---

## Security Considerations

Ensure the following security best practices when using *Django RecomPI*:

- **Secure API Key Handling**: Keep `RECOMPI_API_KEY` secure and avoid exposing it in version control or public repositories.
- **Data Encryption**: Use HTTPS (`RECOMPI_SECURE_API`) to encrypt data transmitted between your Django application and the RecomPI service.
- **Secure Profile Hashing**: Utilize `RECOMPI_SECURE_HASH_SALT` to hash profile IDs and other data obscuring before sending them to RecomPI servers. This helps protect user data by obscuring identifiable information during transmission and afterward.

---

## In-Depth Guide

Explore our in-depth guide to uncover advanced topics and features of the `django-recompi` package. This section provides essential insights for developing sophisticated recommendation systems using RecomPI. For detailed information, visit the [Advanced Documentation](https://github.com/recompi/django-recompi/blob/main/docs/advanced.md).

---

## Basic Usage

The `django-recompi` package is built on top of the core `recompi` package. Therefore, understanding the foundational concepts and functionalities in the `recompi` package is essential. For an introduction to the basic usage of `django-recompi`, including how to work with essential classes like `SecureProfile` and `Profile`, please refer to our [PyPI page](https://pypi.org/project/recompi/). This resource offers comprehensive examples and instructions to help you get started with implementing fundamental features of the RecomPI recommendation system.

---

## Contributing and Development

We welcome contributions to *Django RecomPI*! If you'd like to contribute, please follow these steps:

- Fork the repository and clone it to your local environment.
- Install dependencies and set up a development environment.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install --hook-type pre-commit --hook-type pre-push
```

- Make changes, write tests, and ensure all tests pass.
- Submit a pull request with a detailed description of your changes.

## Support

For support or questions, please submit a [ticket](https://panel.recompi.com/tickets/new) or [open an issue](https://github.com/recompi/django-recompi/issues) on GitHub.
