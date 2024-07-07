# Django RecomPI

*Django RecomPI* is a Django model mixin that integrates functionalities of RecomPI (Recommender System API) with Django models, enabling easy recommendation and tracking capabilities within Django applications.

## Installation

You can install *Django RecomPI* via pip. Here's how:

```bash
pip install django-recompi
```

## Usage

### Setting up a Django model with RecomPI integration

1. **Define your Django model** (e.g., `Product`) and use `RecomPIModelMixin` as a mixin.

```python
from django.db import models
from django_recompi.models import RecomPIModelMixin

class Product(models.Model, RecomPIModelMixin):
    RECOMPI_DATA_FIELDS = [
        "name",
        "reviews__comment",
        "reviews__rating",
        "reviews__counter.count",
    ]
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()

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

Certainly! Here's an enhanced version of the documentation for the `RecomPILabels` class that includes an explanation about flexibility in adding custom labels:

### RecomPILabels

The `RecomPILabels` class provides predefined labels for tracking various interactions using RecomPI within your Django application. While these labels are provided for convenience, developers are not restricted to using only these predefined labels and can add custom labels as needed.

#### Predefined Labels

Use these labels when tracking user interactions or recommending items:

- **Buy**: Indicates a purchase action.
- **Like**: Indicates a user liking an item.
- **Sell**: Indicates an item being listed for sale.
- **View**: Indicates viewing an item.
- **Click**: Indicates clicking on an item or link.
- **Upload**: Indicates uploading a file or content.
- **Comment**: Indicates leaving a comment on an item.
- **Message**: Indicates sending a message.

These predefined labels are designed to standardize interaction types and facilitate consistent tracking and recommendation processes using RecomPI API.

#### Custom Labels

Developers can also define and use custom labels as per their application's specific needs. There's no restriction on the type or format of labels used with RecomPI. Simply pass the desired label string when tracking interactions or recommending items.

#### Example

```python
# Track a user viewing a product
product = Product.objects.first()
product.recompi_track(
    RecomPILabels.View,
    profiles=SecureProfile("profile_id", "user_id_123"),
    location=Location(url="https://www.example.com/products/1")
)

# Recommend products based on user interactions
recommendations = Product.recompi_recommend(
    labels=["custom_label_1", "custom_label_2"],
    profiles=SecureProfile("profile_id", "user_id_123"),
    size=5,
)

print(recommendations)
```

By using `RecomPILabels`, you can leverage predefined labels or introduce custom labels, offering flexibility in tracking and recommending items based on user interactions within your Django application.

## Settings Configuration

*Django RecomPI* can be customized through the following settings in your `settings.py` file:

### `RECOMPI_API_KEY`

- **Type:** `str`
- **Description:** API key for accessing the RecomPI service. Required for integration.
- **Note:** To obtain `RECOMPI_API_KEY`, register on the [RecomPI panel](https://panel.recompi.com/clients/sign_in). After registration, [add a campaign](https://panel.recompi.com/campaigns/new) in the panel, and a campaign token will be generated instantly. Use this token as your API key in the code.

### `RECOMPI_SECURE_API`

- **Type:** `bool`
- **Default:** `True`
- **Description:** Flag indicating whether to use secure API connections.

### `RECOMPI_SECURE_HASH_SALT`

- **Type:** `str` or `None`
- **Description:** Salt used to hash profile information securely. Profiles hashed with this salt before sending data to RecomPI servers using `SecureProfile`.

## Error Handling and Exceptions

When using *Django RecomPI*, you may encounter the following exceptions:

- **`RecomPIException`**: Raised when essential settings are not properly configured or when errors occur during API interactions. Handle these exceptions to provide appropriate feedback or logging.

## Security Considerations

Ensure the following security best practices when using *Django RecomPI*:

- **Secure API Key Handling**: Keep `RECOMPI_API_KEY` secure and avoid exposing it in version control or public repositories.
- **Data Encryption**: Use HTTPS (`RECOMPI_SECURE_API`) to encrypt data transmitted between your Django application and the RecomPI service.
- **Secure Profile Hashing**: Utilize `RECOMPI_SECURE_HASH_SALT` to hash profile IDs before sending them to RecomPI servers. This helps protect user data by obscuring identifiable information during transmission.

## Examples and Use Cases

Explore these examples to understand how *Django RecomPI* can be applied:

- **E-commerce Recommendation**: Track user interactions on product pages and recommend related products based on their behavior.
- **Content Personalization**: Customize content recommendations based on user preferences and historical interactions.

## Performance Considerations

To optimize performance with *Django RecomPI*:

- **Query Optimization**: Enhance performance by leveraging Django's queryset optimizations (`select_related`, `prefetch_related`) to minimize database queries when retrieving recommendations. Pass the optimized queryset directly as the `queryset` parameter to `recompi_recommend`.
- **Caching**: Implement caching strategies to store and retrieve frequently accessed recommendation data efficiently.

## Contributing and Development

We welcome contributions to *Django RecomPI*! If you'd like to contribute, please follow these steps:

- Fork the repository and clone it to your local environment.
- Install dependencies and set up a development environment.
- Make changes, write tests, and ensure all tests pass.
- Submit a pull request with a detailed description of your changes.

## Support

For support or questions, please submit a [ticket](https://panel.recompi.com/tickets/new) or [open an issue](https://github.com/recompi/django-recompi/issues) on GitHub.