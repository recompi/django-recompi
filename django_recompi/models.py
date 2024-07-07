from recompi import *
from hashlib import md5
from typing import Any, Dict, List, Tuple, Optional, Union

from django.conf import settings
from django.db.models.functions import Concat, Coalesce
from django.db.models import Q, F, Func, Value, CharField, QuerySet


class RecomPIModelMixin:
    """Mixin to integrate RecomPI functionalities with Django models."""

    RECOMPI_API_KEY: str = None
    RECOMPI_NONE_SPECIAL_LITERAL: str = str(None)
    RECOMPI_DATA_FIELDS: Union[Dict[str, List[str]], List[str]] = []

    class RecomPISearchTerm:
        """Represents a search term for RecomPI with a field, value, and probability."""

        def __init__(self, field: str, value: str, prob: float) -> None:
            self.field = field
            self.value = value
            self.prob = prob

        def to_q(self, qs: QuerySet) -> Q:
            """
            Converts the search term to a Django Q object with MD5 hashing.

            Args:
                qs (QuerySet): The queryset to apply the annotation.

            Returns:
                Q: A Django Q object representing the search term with MD5 hashed field.
            """
            KEY = f"__{self.field}_md5"
            return qs.annotate(
                **{
                    KEY: Func(
                        Concat(
                            Coalesce(
                                F(self.field),
                                Value(RecomPIModelMixin.RECOMPI_NONE_SPECIAL_LITERAL),
                            ),
                            Value(getattr(settings, "RECOMPI_SECURE_HASH_SALT", "")),
                        ),
                        function="MD5",
                        output_field=CharField(default=""),
                    )
                }
            ), Q(**{KEY: self.value})

        def __str__(self) -> str:
            return str(
                {
                    "field": self.field,
                    "value": self.value,
                    "prob": self.prob,
                }
            )

        def __repr__(self) -> str:
            return str(self)

    def _recompi_api(self, api_key: Optional[str] = None) -> RecomPI:
        """
        Initialize and return a RecomPI API instance.

        Args:
            api_key (Optional[str]): Custom API key for this operation.

        Raises:
            RecomPIException: If RECOMPI_API_KEY is not set in Django settings.

        Returns:
            RecomPI: An instance of the RecomPI API.

        Notes:
            This method initializes a RecomPI API instance using either the provided `api_key` or the
            one set in Django settings. If `api_key` is not provided and RECOMPI_API_KEY is not set
            in settings, a RecomPIException is raised.
        """

        api_key = (
            api_key
            or self.RECOMPI_API_KEY
            or getattr(settings, "RECOMPI_API_KEY", None)
        )
        secure_url = getattr(settings, "RECOMPI_SECURE_API", True)
        self.hash_salt = getattr(settings, "RECOMPI_SECURE_HASH_SALT", "")

        if not api_key:
            raise RecomPIException("settings.RECOMPI_API_KEY is not set!")

        if self.hash_salt:
            RecomPIFieldTypeError.if_not_validated(
                "RecomPIManager.recommend",
                "settings.RECOMPI_SECURE_HASH_SALT",
                self.hash_salt,
                str,
            )

        return RecomPI(
            api_key=api_key,
            secure_url=secure_url,
            hash_salt=self.hash_salt if self.hash_salt else None,
        )

    def _recompi_getattr(
        self, instance: Any, field_path: str, default: Optional[Any] = None
    ) -> Any:
        """
        Dynamically access the value of a field from an instance.

        Args:
            instance (Any): Django model instance.
            field_path (str): Dot or double-underline separated string representing the field path.
            default (Optional[Any]): Default value to return if the field is not found.

        Returns:
            Any: Value of the field or default if not found.
        """

        def get_value(obj, parts):
            if not parts:
                return default
            if "__" in parts[0]:
                relation, rest = parts[0].split("__", 1)
                try:
                    related_manager = getattr(obj, relation)
                    if hasattr(related_manager, "all"):
                        return [
                            get_value(related_obj, [rest] + parts[1:])
                            for related_obj in related_manager.all()
                        ]
                    else:
                        return get_value(related_manager, [rest] + parts[1:])
                except AttributeError:
                    return default
            else:
                try:
                    current_field, next_fields = parts[0], parts[1:]
                    next_obj = getattr(obj, current_field)
                    if not next_fields:
                        return next_obj
                    return get_value(next_obj, next_fields)
                except AttributeError:
                    return default

        parts = field_path.split(".")
        return get_value(instance, parts)

    def _recompi_class_name(self) -> str:
        """Return the class name in 'module.ClassName' format."""
        return f"{self.__module__}.{self.__class__.__name__}"

    def _recompi_labelify(self, label: str) -> str:
        """Labelify by appending the class name."""
        return f"{self._recompi_class_name()}.{label}"

    def _hashify_value(self, value: Any) -> str:
        """
        Hashes a given value using MD5 encryption concatenated with a hash salt.

        Args:
            value (Any): The value to be hashed.

        Returns:
            str: The MD5 hash of the concatenated value and hash salt.
        """
        return md5((str(value) + self.hash_salt).encode()).hexdigest()

    def _recompi_rank(
        self,
        items: List[Any],
        search_terms: List["RecomPIModelMixin.RecomPISearchTerm"],
        size: int = 8,
        remove_rank_field: bool = False,
    ) -> List[Any]:
        """
        Rank items based on search terms using a fuzzy integral.

        Args:
            items (List[Any]): List of items to rank.
            search_terms (List[RecomPISearchTerm]): List of search terms defining ranking criteria.
            size (int): Number of ranked items to return.
            remove_rank_field (bool): If True, excludes the 'recompi_rank' field from the output.

        Returns:
            List[Any]: Ranked list of items based on the provided search terms.
        """

        def fuzzy_integral(item):
            rank = 0
            for term in search_terms:
                if (
                    self._hashify_value(
                        self._recompi_getattr(
                            item, term.field, self.RECOMPI_NONE_SPECIAL_LITERAL
                        )
                    )
                    == term.value
                ):
                    rank = (term.prob**2 + rank**2) ** 0.5

            item.recompi_rank = rank
            return rank

        items.sort(key=fuzzy_integral, reverse=True)

        index = 0
        # Iterate over the items and prune the zero-rank items
        for index, item in enumerate(items):
            # Consult with the input size to adjust the returned array
            if size is not None and size <= index:
                index -= 1
                break
            # Fetch the rank
            rank = item.recompi_rank
            # Remove the rank field if we should remove it?
            if remove_rank_field:
                del item.recompi_rank
            #
            if rank == 0:
                index -= 1
                break
        # return the items with proper size
        return items[: index + 1]

    @classmethod
    def recompi_recommend(
        cls,
        labels: Union[str, List[str]],
        profiles: Optional[List[str]] = None,
        geo: Optional[str] = None,
        query_manager: str = "objects",
        queryset: QuerySet = None,
        size: int = 8,
        max_polling_size: Optional[int] = None,
        return_response: bool = False,
        skip_rank_field: bool = False,
        api_key: Optional[str] = None,
    ) -> Union[Dict[str, List[Any]], Tuple[Dict[str, List[Any]], RecomPIResponse]]:
        """
        Recommend items based on labels and search terms.

        Args:
            labels (Union[str, List[str]]): List of labels or a single label.
            profiles (Optional[List[str]]): List of profiles identifying users.
            geo (Optional[str]): Geographical data relevant to recommendations.
            query_manager (str): Name of the query manager on the model.
            queryset (Optional[QuerySet]): Custom queryset to base recommendations on.
            size (int): Number of items to recommend per label.
            max_polling_size (Optional[int]): Maximum number of records to retrieve from the database for initial ranking.
            return_response (bool): If True, returns the response along with recommendations in a tuple.
            skip_rank_field (bool): If True, excludes the 'recompi_rank' field from the output.
            api_key (Optional[str]): Custom API key for this operation.

        Returns:
            Union[Dict[str, List[Any]], Tuple[Dict[str, List[Any]], RecomPIResponse]]:
                Dictionary of recommended items by label, or tuple containing recommendations and RecomPI response if return_response=True.

        Notes:
            This method generates recommendations based on specified labels and optional search terms.
            If `api_key` is provided, it overrides the default API key set in Django settings and
            the `RECOMPI_API_KEY` property defined in the class.

            The recommendations are retrieved from RecomPI API, utilizing the provided `labels`,
            `profiles`, and optional `geo` parameters. The method also supports custom `queryset`
            and `query_manager` for fetching items from the database.

            If `return_response` is True, the method returns a tuple containing both the recommendations
            and the detailed response from RecomPI API. By default, the 'recompi_rank' field is attached
            to the output response unless `skip_rank_field` is set to True.
        """

        self = cls()
        CLASS = self._recompi_class_name()

        if queryset is not None:
            if not isinstance(queryset, QuerySet):
                raise RecomPIException(
                    "The input `queryset` needs to be an instance of `QuerySet`; but got an instance of `{}`".format(
                        type(queryset).__name__
                    )
                )
            if cls != queryset.model:
                raise RecomPIException(
                    "The input `queryset` should a queryset for model `{}` class.".format(
                        CLASS
                    )
                )

        api = self._recompi_api(api_key)

        if isinstance(labels, str):
            labels = [labels]

        results = api.recom(
            [self._recompi_labelify(label) for label in labels], profiles, geo
        )

        output = {}

        if not results.is_success():
            if return_response:
                return output, getattr(cls, query_manager).none()
            return output

        class SearchTerms(list):
            def __init__(self, *args, **kwargs):
                super(SearchTerms, self).__init__(*args, **kwargs)

            def to_q(self, qs):
                """Convert the list of search terms to a Django Q object."""
                if not self:
                    return None
                qs, filters = self[0].to_q(qs)

                for i in range(1, len(self)):
                    qs, subfilters = self[i].to_q(qs)
                    filters = filters | subfilters

                return qs, filters

        for label in labels:
            labelified = self._recompi_labelify(label)

            if not isinstance(results.body, dict) or labelified not in results.body:
                continue

            result = results.body[labelified]

            FIELDS = self.RECOMPI_DATA_FIELDS
            if isinstance(FIELDS, dict):
                if label not in FIELDS:
                    return None
                FIELDS = FIELDS[label]

            if not isinstance(FIELDS, list):
                raise RecomPIException(
                    f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS[{label}]` or `{CLASS}.RECOMPI_DATA_FIELDS` to be a list; but it's an instance of `{type(FIELDS).__name__}`"
                )

            st = SearchTerms()

            for field in FIELDS:
                for res, prob in result.items():
                    if not res.startswith(f"{field}:"):
                        continue
                    value = res[len(field) + 1 :]
                    st.append(
                        self.RecomPISearchTerm(field.replace(".", "__"), value, prob)
                    )

            if not st:
                continue

            # Fetch the initial queryset
            # Assume the input queryset is the reference queryset
            qs = queryset
            # If the input queryset is not a QuerySet
            if not isinstance(qs, QuerySet):
                # Try to fetch through the default manager
                qs = getattr(cls, query_manager).all()
            # Convert the queryset into the filters + new queryset
            qs, filters = st.to_q(qs)
            # Apply the filters
            items = qs.filter(filters)
            # limit the results if necessary
            if max_polling_size:
                items = items[:max_polling_size]
            # Perform the ranking based on the given results
            output[label] = self._recompi_rank(list(items), st, size, skip_rank_field)

        if return_response:
            return output, results

        return output

    def recompi_track(
        self,
        label: str,
        profiles: List[str],
        location: str,
        geo: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Any:
        """
        Track user interactions with the system using RecomPI API.

        Args:
            label (str): The label indicating the type of interaction (e.g., "product-view", "click").
            profiles (List[str]): List of profile identifiers associated with the interaction.
            location (str): The location information related to the interaction.
            geo (Optional[str]): Geographical data related to the interaction (default: None).
            api_key (Optional[str]): Custom API key for this tracking operation (default: None).

        Returns:
            Any: Response from the RecomPI API for tracking the interaction.

        Notes:
            This method sends a tracking request to RecomPI API to record user interactions,
            including the interaction label, profiles, location, and optional geographical data.
            If `api_key` is provided, it overrides the default API key set in Django settings and
            the `RECOMPI_API_KEY` property defined in the class.
        """

        api = self._recompi_api(api_key)

        CLASS = self._recompi_class_name()

        FIELDS = self.RECOMPI_DATA_FIELDS
        if isinstance(FIELDS, dict):
            if label not in FIELDS:
                return None
            FIELDS = FIELDS[label]

        if not isinstance(FIELDS, list):
            raise RecomPIException(
                f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS[{label}]` or `{CLASS}.RECOMPI_DATA_FIELDS` to be a list; but it's an instance of `{type(FIELDS).__name__}`"
            )

        tags = []
        for index, field in enumerate(FIELDS):
            values = None
            if not isinstance(field, str):
                raise RecomPIException(
                    f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS[{label}][{index}]` or `{CLASS}.RECOMPI_DATA_FIELDS[{index}]` to be a string; but it's an instance of `{type(field).__name__}`"
                )

            values = self._recompi_getattr(
                self, field, self.RECOMPI_NONE_SPECIAL_LITERAL
            )

            if values is None:
                values = self.RECOMPI_NONE_SPECIAL_LITERAL

            if not isinstance(values, list):
                values = [values]

            for value in values:
                tags.append(
                    Tag(
                        id="{}:{}".format(field, self._hashify_value(value)),
                        name=field,
                        desc="{}.{}".format(CLASS, field),
                    )
                )

        return api.push(self._recompi_labelify(label), tags, profiles, location, geo)

    class RecomPILabels:
        """Predefined labels for RecomPI interactions."""

        Buy = "buy"
        Like = "like"
        Sell = "sell"
        View = "view"
        Click = "click"
        Upload = "upload"
        Comment = "comment"
        Message = "message"
