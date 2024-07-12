# Django RecomPI Advanced Usage Guide

Welcome to the advanced guide for using the `RecomPIModelMixin` in Django! This document provides detailed explanations of various features and customization options available to developers.

---

## 1. Setting the API Key (`RECOMPI_API_KEY`)

Developers can set the API key for the RecomPI service in two ways:

- **Class-Level API Key**: Define the `RECOMPI_API_KEY` in the model that includes the `RecomPIModelMixin`.

  ```python
  class MyModel(models.Model, RecomPIModelMixin):
      RECOMPI_API_KEY = "your_api_key_here"
  ```

- **Method-Level API Key**: Pass the API key each time a public method in the mixin is used.

  ```python
  recommendations = MyModel.recompi_recommend(
      labels="product-view",
      api_key="your_api_key_here"
  )
  ```

---

## 2. Special Literal for Null Values (`RECOMPI_NONE_SPECIAL_LITERAL`)

The `RECOMPI_NONE_SPECIAL_LITERAL` is used to handle `None` values in the data fields. This literal ensures that fields with `None` values are appropriately managed during the hashing and ranking processes.

```python
class MyModel(models.Model, RecomPIModelMixin):
    RECOMPI_NONE_SPECIAL_LITERAL = str(None)
```

---

## 3. Search Tokenizer Profiler (`RECOMPI_SEARCH_TOKENIZER_PROFILER`)

The `RECOMPI_SEARCH_TOKENIZER_PROFILER` is a predefined profile used for tokenizing search queries. This profiler helps in breaking down search queries into manageable tokens that can be processed for recommendations.

```python
class MyModel(models.Model, RecomPIModelMixin):
    RECOMPI_SEARCH_TOKENIZER_PROFILER = "search_token"
```

---

## 4. Data Fields for Recommendations (`RECOMPI_DATA_FIELDS`)
`RECOMPI_DATA_FIELDS` is a key configuration in the `RecomPIModelMixin` that defines the data fields to be used in recommendations and tracking. This configuration can either be a list of fields applicable to all labels or a dictionary that maps specific labels to their respective fields.



### 1. List of Fields for All Labels

When `RECOMPI_DATA_FIELDS` is a list, it applies the same fields for all recommendation and tracking labels. This is a straightforward approach and is suitable when the fields used in recommendations do not vary across different labels.

#### Example:

```python
RECOMPI_DATA_FIELDS = [
    "name",
    "reviews__comment",
    "reviews__rating",
    "reviews__counter.count",
]
```

In this example, the `RecomPIModelMixin` will use the fields `name`, `reviews__comment`, `reviews__rating`, and `reviews__counter.count` for all labels. Each field can be a direct field of the model or a related field accessed via Django's double-underscore notation.

### 2. Dictionary of Fields for Each Label

When `RECOMPI_DATA_FIELDS` is a dictionary, it allows specifying different fields for different labels. This provides more flexibility, especially in scenarios where different types of interactions or events need different sets of fields.

#### Example:

```python
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
    ]
}
```

In this example:

- For the `product-view` label, the fields `name`, `reviews__comment`, `reviews__rating`, and `reviews__counter.count` are used.
- For the `product-click` label, the fields `name` and `reviews__comment` are used.

This approach is highly useful when different types of interactions (e.g., viewing a product vs. clicking on a product) require different sets of data fields to be considered.

### How to Use `RECOMPI_DATA_FIELDS`

1. **Define the Fields:**
   - Decide if you want a universal set of fields (list) or specific fields per label (dictionary).
   - Use Django's double-underscore notation to specify related fields.

2. **Configure in Your Model:**
   - Add `RECOMPI_DATA_FIELDS` as a class attribute in your model that uses `RecomPIModelMixin`.

#### Example Model Configuration:

```python
from django.db import models
from recompi_django import RecomPIModelMixin

class Product(models.Model, RecomPIModelMixin):
    name = models.CharField(max_length=255)
    reviews = models.ManyToManyField('Review')

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
        ],
    }
```

In this example, the `Product` model defines `RECOMPI_DATA_FIELDS` with specific fields for `product-view` and `product-click` labels.

### Summary

`RECOMPI_DATA_FIELDS` is a flexible configuration that allows you to specify which fields should be used for recommendations and tracking. Whether you use a list or a dictionary depends on whether you need the same fields for all labels or different fields for different labels. This flexibility ensures that your recommendation logic is both powerful and tailored to your specific needs.

---

## 5. Overriding the `_recompi_hashify_value` Method

Developers can implement their own hashing mechanism for enhanced security by overriding the `_recompi_hashify_value` method.

```python
class MyModel(models.Model, RecomPIModelMixin):
    def _recompi_hashify_value(self, value: Any) -> str:
        # Custom hashing logic
        return custom_hash_function(value + self.hash_salt)
```

---

## 6. Search Methods in `RecomPIModelMixin`

### 1. `recompi_search`

`recompi_search` is a method provided by the `RecomPIModelMixin` that allows you to perform searches on the model's data using the fields specified in `RECOMPI_DATA_FIELDS`. This method is useful for retrieving data based on search criteria.

#### Basic Usage

Here is an example of how you might use `recompi_search`:

```python
results = Product.recompi_search("search_term")
```

This method will search across the fields specified in `RECOMPI_DATA_FIELDS` for the `Product` model using the term "search_term".

#### Parameters

- **query (Union[str, List[str]])**: The search query string or tokenized -- look into **Customizing the Tokenizer** to understand how you can provide more tuned and efficient query.
- **labels (Optional[Union[str, List[str]]])**: List of labels or a single label. Defaults to RecomPIModelMixin.RecomPILabels.SearchConversion.
- **geo (Optional[str])**: Geographic information for the search.
- **query_manager (str)**: The name of the manager to use for querying objects. Defaults to "objects".
- **queryset (QuerySet, optional)**: An optional queryset to limit the search scope. Defaults to None.
- **size (int)**: The number of results to retrieve per token. Defaults to 24.
- **max_polling_size (Optional[int])**: Maximum number of results to poll. Defaults to None.
- **return_response (bool)**: Whether to return the raw response from the RecomPI API. Defaults to False.
- **skip_rank_field (bool)**: Whether to skip removing the rank field from objects. Defaults to False.
- **api_key (Optional[str])**: An optional API key to override the default.

#### Example

```python
results = Product.recompi_search(
    query="awesome product",
    labels="product-view",
    queryset=Product.objects.filter(reviews__rating__gte=4),
)
```

In this example:
- The search term is "awesome product".
- Queryset ensure that only products with a rating of 4 or higher are included.
- The fields specified under the `product-view` label in `RECOMPI_DATA_FIELDS` are used for the search.

### 2. `recompi_search_track`

`recompi_search_track` is a tracker that tracks the search activity. This is useful for analytics and recommendation systems that rely on tracking user interactions with search results. By using method recompi can provide more related search results for the given queries.

#### Basic Usage

Here is an example of how you might use `recompi_search_track`:

```python
product: Product = Product.objects.get(pk=request.GET["pk"])
product.recompi_search_track(
    query="awesome product",
    location=Location(url="https://www.example.com/search?blah=blah"),
    labels="product-view",
)
```

This method will signal the RecomPI's A.I.'s core that given product is being viewed (in this example/use case) using the term `'awesome product'` considering the fields specified in `RECOMPI_DATA_FIELDS` for the `Product` mode; so the RecomPI's engine can track the search activity performance for the given the search term.

#### Parameters

- **query (Union[str, List[str]])**: The search query string or tokenized.
- **label (Optional[str])**: The label to use for tracking. Defaults to `RecomPIModelMixin.RecomPILabels.SearchConversion`.
- **location (Optional[Union[str, Location]])**: The location identifier for the tracking.
- **geo (Optional[str])**: Geographic information for the tracking.
- **api_key (Optional[str])**: An optional API key to override the default.

### How to Use These Methods

1. **Define Searchable Fields:**
   - Ensure `RECOMPI_DATA_FIELDS` is properly defined in your model.

2. **Perform a Search:**
   - Use `recompi_search` for search operations which will consider the recommendations for a search term.
   - Use `recompi_search_track` when user interacted with an item in the search result -- such as `click`, `hover` or maybe a `purchase` events can be a good signal for signaling the RecomPI's A.I engine for future optimizations.

#### Example Model Configuration and Usage

```python
from django.db import models
from recompi_django import RecomPIModelMixin

class Product(models.Model, RecomPIModelMixin):
    name = models.CharField(max_length=255)
    reviews = models.ManyToManyField('Review')

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
        ],
    }

# Example usage:
results = Product.recompi_search(
    query="awesome product",
    labels="product-view"
)

# For example user clicked on the product# 1395 afterward
product: Product = Product.objects.get(pk=1395)
product.recompi_search_track(
    query="awesome product",
    location=Location(url="https://www.example.com/search-page"),
    labels="product-view"
)
```

### Pre-train Data for Optimal Search Engine Performance

To enhance RecomPI's A.I. understanding of your system and user queries, you can pre-train it with historical search data. While RecomPI will learn and optimize over time, pre-training can significantly speed up this process, reducing the optimization phase from weeks or months to just days or weeks. This involves sending historical search data or generating related queries and linking them to items in your database.

> **Note:** Each item in your database can be linked to multiple queries.

#### Example of Pre-training RecomPI's A.I. on Search

```python
def generate_queries_for(product: Product, chunk_size: int = 4) -> List[str]:
    # a tokenizer method
    def query_builder(string: str, chunk_size: int = 4) -> List[str]:
        queries = []
        title_tokens = string.split()
        for i in range(0, len(title_tokens) - chunk_size + 1):
            queries.append(" ".join(title_tokens[i : i + chunk_size]))

        return queries

    # Add more sophisticated query generation as needed

    return query_builder(product.title, chunk_size) + query_builder(
        product.description, chunk_size
    )


for product in Product.objects.all():
    for query in generate_queries_for(product, chunk_size=4):
        product.recompi_search_track(
            query=query,
            location=Location(url="https://www.example.com/search-page"),
            labels="product-view",
        )
```

In this example, the `generate_queries_for` function generates a list of example queries that link a `Product` to a query. By using this function, you can accelerate RecomPI's learning phase, optimizing search performance in a shorter time frame.

### Summary

- **`recompi_search`**: Performs a search based on the fields defined in `RECOMPI_DATA_FIELDS`.
- **`recompi_search_track`**: Tracks the search activity.

These methods enable flexible and powerful search capabilities within models that use `RecomPIModelMixin`, supporting both searches and advanced tracking of search interactions and performance.

---

## 7. Linking two records from two different models

### `recompi_link`

The `recompi_link` method links the current instance to another instance, recording the interaction with specific details.

#### Basic Usage
```python
# Link current product to another product instance
product1 = Product.objects.get(pk=1)
product2 = Product.objects.get(pk=2)

product1.recompi_link(
    instance=product2,
    label="product-view",
    location="https://www.example.com/product/123",
)
```

#### Parameters
- **instance**: Another `RecomPIModelMixin` instance to link to.
- **label**: Interaction type (e.g., "product-view", "click").
- **location**: URL or `Location` object related to the interaction.
- **geo**: Geographical data (optional).
- **api_key**: Custom API key (optional).

### `recompi_recommend_links`

The `recompi_recommend_links` method generates item recommendations based on specified labels and a model class.

#### Basic Usage
```python
# Recommend related products
recommendations = product.recompi_recommend_links(
    model_class=Product,
    labels=["product-view", "click"],
    size=5
)
```

#### Parameters
- **model_class**: The model class for recommendations.
- **labels**: Label(s) for recommendations.
- **geo**: Geographical data (optional).
- **query_manager**: Query manager name (default: "objects").
- **queryset**: Custom queryset (optional).
- **size**: Number of items to recommend per label (default: 8).
- **max_polling_size**: Maximum records to retrieve for initial ranking (optional).
- **return_response**: Return raw response along with recommendations (default: False).
- **skip_rank_field**: Exclude 'recompi_rank' field (default: False).
- **api_key**: Custom API key (optional).

#### Example
```python
# Get product recommendations
recommendations = product.recompi_recommend_links(
    model_class=Product,
    labels=["product-view", "click"],
    size=5,
)
```
### Customizing `Profile` Fields for Model Linking

Linking two models effectively requires additional data fields to create a `SecureProfile` instance. By default, the profile ID is the `pk` (primary key), but in many cases, this may not be ideal. For example, if you want to link models based on multiple fields such as `gender`, `age`, and `if_tourist`, using the `pk` alone may not suffice, especially if the user is a one-time client.

To address this, you can customize the profile ID by specifying a list of fields in your model. Here's how you can do it:

```python
class Client(AbstractUser):
    RECOMPI_PROFILE_ID = [
        "gender",
        "age",
        "if_tourist",
        # Add other relevant fields
    ]
```

#### Recommending a `Product` to a `Client`

To recommend a `Product` to a `Client` based on the specified profile fields:

```python
client = Client.objects.get(**criteria)
recommendations = client.recompi_recommend_links(
    model_class=Product,
    labels=["buy", "interested"]
)

for label, products in recommendations.items():
    for product in products:
        print("To `{}` you need to recommend Product# {}".format(label, product.pk))
```

#### Linking a `Client` to `Products`

Once you have observed client interactions, you can link the client to products based on their behavior:

```python
# Products that the client bought
products_bought = Product.objects.filter(pk__in=BOUGHT_PRODUCT_IDS)

# Products that the client showed interest in
products_interested = Product.objects.filter(pk__in=INTERESTED_PRODUCT_IDS)

for product in products_bought:
    client.recompi_link(
        instance=product,
        label="buy",
        location="https://www.example.com/product/{}".format(product.pk)
    )

for product in products_interested:
    client.recompi_link(
        instance=product,
        label="interested",
        location="https://www.example.com/product/{}".format(product.pk)
    )
```

With this setup, the next time a similar client visits, the system will know which products to recommend, increasing the likelihood of purchases or interest.

> **Note:** Don't forget to leverage [pre-training](#pre-train-data-for-optimal-search-engine-performance) to boost results from day one by linking records based on historical data. This can significantly enhance the performance of your recommendation system right from the start.

---

## 8. Customizing the Tokenizer (`_recompi_tokenize`)

Developers can override the `_recompi_tokenize` method to implement more advanced tokenizers, such as those from the [`nltk`](https://pypi.org/project/nltk/) package.

```python
class MyModel(models.Model, RecomPIModelMixin):
    @classmethod
    def _recompi_tokenize(cls, query: Union[str, List[str]]) -> List[str]:
        # Custom tokenization logic using nltk
        import nltk
        tokens = nltk.word_tokenize(query)
        return tokens
```

---

## 9. Recommendation Rank (`recompi_rank`)

The `recompi_rank` field indicates the recommendation rank for each output. This field can be included or excluded from the results.

```python
results = MyModel.recompi_recommend(
    labels="product-view",
    SecureProfile("profile_id", "user_profile_id"),
    skip_rank_field=True
)
```

---

## 10. Query Manager and QuerySet

### Query Manager

The `query_manager` parameter allows specifying the manager to use for querying objects.

```python
results = MyModel.recompi_recommend(
    labels="product-view",
    SecureProfile("profile_id", "user_profile_id"),
    query_manager="available_products")
```

### QuerySet

The `queryset` parameter allows passing a custom queryset to control the search scope and improve performance.

```python
custom_queryset = MyModel.objects.filter(active=True)
results = MyModel.recompi_recommend(
    labels="product-view",
    SecureProfile("profile_id", "user_profile_id"),
    queryset=custom_queryset
)
```

---

## 11. Polling Size (`max_polling_size`) vs. Size (`size`)

### `max_polling_size`

`max_polling_size` refers to the maximum number of items that can be retrieved in a single polling operation when interacting with a data source, such as a database or an external API. This is particularly useful when dealing with large datasets or when the data source has restrictions on the amount of data that can be fetched at once.

#### Key Points

- **Purpose**: To limit the maximum number of items retrieved in a single polling operation to prevent overloading the data source or exceeding its limitations.
- **Use Case**: Useful when the data source has a limit on how many items can be fetched at once, or when the dataset is too large to be retrieved in a single query.
- **Example**: If `max_polling_size` is set to 100, polling operation will retrieve at most 100 items, even if more items are available -- setting this field too low can result in inaccureate rankings.

### `size`

`size` refers to the total number of items that you want to retrieve for a specific search or query. This parameter dictates how many results you want the search method to return in total, up to the `max_polling_size` if being set.

#### Key Points

- **Purpose**: To specify the total number of items to be retrieved for a particular search or query.
- **Use Case**: Useful when you have a specific number of results you need, such as displaying a set number of items per page in a paginated view.
- **Example**: If `size` is set to 50, the search method will return up to 50 items in total.

### Summary

- **`max_polling_size`**: Controls the maximum number of items fetched in a polling operation, useful for managing large datasets and adhering to data source limits.
- **`size`**: Specifies the total number of items you want to retrieve for a particular search or query, ensuring you get the desired number of results.

By understanding and utilizing these parameters effectively, you can optimize data retrieval processes, ensuring efficient and performant access to large datasets.

---

## 12. Returning the Response (`return_response`)

The `return_response` parameter can be used for debugging purposes, providing the raw response from the RecomPI API.

```python
results, response = MyModel.recompi_recommend(
    labels="product-view",
    SecureProfile("profile_id", "user_profile_id"),
    return_response=True
)
```

---

## 13. RecomPILabels

The `RecomPILabels` class provides predefined labels for tracking various interactions using RecomPI within your Django application. While these labels are provided for convenience, developers are not restricted to using only these predefined labels and can add custom labels as needed.

### Predefined Labels

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

### Custom Labels

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

---

## 14. Error Handling and Exceptions

When using *Django RecomPI*, you may encounter the following exceptions:

- **`RecomPIException`**: Raised when essential settings are not properly configured or when errors occur during API interactions. Handle these exceptions to provide appropriate feedback or logging.

---

## 15. Performance Considerations

To optimize performance with *Django RecomPI*:

- **Query Optimization**: Enhance performance by leveraging Django's queryset optimizations (`select_related`, `prefetch_related`) to minimize database queries when retrieving recommendations. Pass the optimized queryset directly as the `queryset` parameter to `recompi_recommend`.
- **Caching**: Implement caching strategies to store and retrieve frequently accessed recommendation data efficiently.

## Conclusion

This advanced guide covers various features and customization options available in the `RecomPIModelMixin`. By leveraging these features, developers can integrate powerful recommendation and search capabilities into their Django applications, providing a more personalized and relevant user experience.