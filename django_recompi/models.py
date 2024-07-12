from recompi import (
    RecomPIFieldTypeError,
    RecomPIException,
    Tag,
    Profile,
    SecureProfile,
    Location,
    Geo,
    RecomPIResponse,
    RecomPI,
)
from hashlib import md5
from collections import OrderedDict
from typing import Any, Dict, List, Tuple, Optional, Union

from django.conf import settings
from django.db.models.functions import Concat, Coalesce
from django.db.models import Q, F, Func, Value, CharField, QuerySet, Model


class RecomPIModelMixin:
    """Mixin to integrate RecomPI functionalities with Django models."""

    RECOMPI_API_KEY: str = None
    RECOMPI_NONE_SPECIAL_LITERAL: str = str(None)
    RECOMPI_SEARCH_TOKENIZER_PROFILER: str = "search_token"

    RECOMPI_DATA_FIELDS: Union[Dict[str, List[str]], List[str]] = []
    RECOMPI_PROFILE_ID: Union[Dict[str, List[str]], List[str]] = ["pk"]

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

    def __init__(self) -> None:
        """
        Initialize the RecomPIModelMixin with API key and other settings from Django settings.
        """
        self._recompi_api_key = self.RECOMPI_API_KEY or getattr(
            settings, "RECOMPI_API_KEY", None
        )
        self._recompi_secure_url = getattr(settings, "RECOMPI_SECURE_API", True)
        self._recompi_hash_salt = getattr(settings, "RECOMPI_SECURE_HASH_SALT", "")

        if not self._recompi_api_key:
            raise RecomPIException("settings.RECOMPI_API_KEY is not set!")

        if self._recompi_hash_salt:
            RecomPIFieldTypeError.if_not_validated(
                "RecomPIManager.recommend",
                "settings.RECOMPI_SECURE_HASH_SALT",
                self._recompi_hash_salt,
                str,
            )

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
        return RecomPI(
            api_key=api_key or self._recompi_api_key,
            secure_url=self._recompi_secure_url,
            hash_salt=self._recompi_hash_salt if self._recompi_hash_salt else None,
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
                        if callable(next_obj):
                            return next_obj()
                        return next_obj

                    return get_value(next_obj, next_fields)
                except AttributeError:
                    return default

        if hasattr(self, field_path):
            callable_or_result = getattr(self, field_path)
            if callable(callable_or_result):
                result = callable_or_result()
                if result is None:
                    return default
                return result
            return callable_or_result

        parts = field_path.split(".")
        return get_value(instance, parts)

    def _recompi_class_name(self) -> str:
        """Return the class name in 'module.ClassName' format."""
        return f"{self.__module__}.{self.__class__.__name__}"

    def _recompi_labelify(self, label: str) -> str:
        """Labelify by appending the class name."""
        return f"{self._recompi_class_name()}.{label}"

    def _recompi_hashify_value(self, value: Any) -> str:
        """
        Hashes a given value using MD5 encryption concatenated with a hash salt.

        Args:
            value (Any): The value to be hashed.

        Returns:
            str: The MD5 hash of the concatenated value and hash salt.
        """
        return md5((str(value) + self._recompi_hash_salt).encode()).hexdigest()

    @classmethod
    def _recompi_tokenize(cls, query: Union[str, List[str]]) -> List[str]:
        tokens = OrderedDict()

        for index, token in enumerate(
            query.split() if isinstance(query, str) else query
        ):
            token = token.strip().lower()[:64]

            if token:
                # use the pure token
                tokens[token] = 1
                # consider the position of the token in the string
                tokens["<t>:[{}]:<p>[{}]".format(token, index)] = 1

        return list(tokens.keys())

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
                values = self._recompi_getattr(
                    item, term.field, self.RECOMPI_NONE_SPECIAL_LITERAL
                )
                if not isinstance(values, list):
                    values = [values]

                for value in values:
                    if self._recompi_hashify_value(value) == term.value:
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
            # backward step for zero-ranked item
            if rank == 0:
                index -= 1
                break
        # return the items with proper size
        return items[: index + 1]

    def _recompi_get_tags(
        self,
        label: str,
        data_fields: Optional[Union[Dict[str, List[str]], List[str]]] = None,
    ) -> List[Tag]:
        CLASS = self._recompi_class_name()

        FIELDS = self.RECOMPI_DATA_FIELDS if data_fields is None else data_fields
        if isinstance(FIELDS, dict):
            if label not in FIELDS:
                raise RecomPIException(
                    "No `{}.RECOMPI_DATA_FIELDS['{}']` is defined!".format(CLASS, label)
                )

            FIELDS = FIELDS[label]

        if not isinstance(FIELDS, list):
            raise RecomPIException(
                f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS['{label}']` or "
                + f"`{CLASS}.RECOMPI_DATA_FIELDS` to be a list; "
                f"but it's an instance of `{type(FIELDS).__name__}`"
            )

        tags = []
        for index, field in enumerate(FIELDS):
            values = None
            if not isinstance(field, str):
                raise RecomPIException(
                    f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS['{label}'][{index}]` or "
                    + f"`{CLASS}.RECOMPI_DATA_FIELDS[{index}]` to be a string; "
                    + "but it's an instance of `{type(field).__name__}`"
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
                        id="{}:{}".format(field, self._recompi_hashify_value(value)),
                        name=field,
                        desc="{}.{}".format(CLASS, field),
                    )
                )

        return tags

    def recompi_profile_id(
        self, label: str, secure_profile: bool = True
    ) -> Union[SecureProfile, Profile]:
        profile_class = SecureProfile if secure_profile else Profile

        return profile_class(
            "{}_link".format(self._recompi_class_name()),
            "|".join(
                [
                    str(tag.to_json())
                    for tag in self._recompi_get_tags(label, self.RECOMPI_PROFILE_ID)
                ]
            ),
        )

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
            max_polling_size (Optional[int]): Maximum number of records to retrieve from \
                the database for initial ranking.
            return_response (bool): If True, returns the response along with recommendations in a tuple.
            skip_rank_field (bool): If True, excludes the 'recompi_rank' field from the output.
            api_key (Optional[str]): Custom API key for this operation.

        Returns:
            Union[Dict[str, List[Any]], Tuple[Dict[str, List[Any]], RecomPIResponse]]:
                Dictionary of recommended items by label, or tuple containing recommendations \
                    and RecomPI response if return_response=True.

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
            if self.__class__ != queryset.model:
                raise RecomPIException(
                    "The input `queryset` should a queryset for model `{}` class.".format(
                        self._recompi_class_name()
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
                return output, results
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
                    f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS['{label}']` or "
                    + f"`{CLASS}.RECOMPI_DATA_FIELDS` to be a list; "
                    + "but it's an instance of `{type(FIELDS).__name__}`"
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
        profiles: Union[List[Union[Profile, SecureProfile]], Profile, SecureProfile],
        location: Union[str, Location],
        geo: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Any:
        """
        Track user interactions with the system using RecomPI API.

        Args:
            label (str): The label indicating the type of interaction (e.g., "product-view", "click").
            profiles (List[Profile|SecureProfile], Profile, SecureProfile): User profiles as a list, \
                Profile or SecureProfile.
            location (str, Location): The location/url information related to the interaction.
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

        if isinstance(location, str):
            location = Location(url=location)

        return api.push(
            self._recompi_labelify(label),
            self._recompi_get_tags(label),
            profiles,
            location,
            geo,
        )

    @classmethod
    def recompi_search(
        cls,
        query: Union[str, List[str]],
        labels: Optional[Union[str, List[str]]] = None,
        geo: Optional[str] = None,
        query_manager: str = "objects",
        queryset: QuerySet = None,
        size: int = 24,
        max_polling_size: Optional[int] = None,
        return_response: bool = False,
        skip_rank_field: bool = False,
        api_key: Optional[str] = None,
    ):
        """
        Performs a RecomPI search based on a query string, tokenizes the query,
        and recommends items matching each token. Aggregates and ranks the results.

        Args:
            query (Union[str, List[str]]): The search query string or tokenized.
            labels (Optional[Union[str, List[str]]]): List of labels or a single label. \
                Defaults to RecomPIModelMixin.RecomPILabels.SearchConversion.
            geo (Optional[str]): Geographic information for the search.
            query_manager (str): The name of the manager to use for querying objects. Defaults to "objects".
            queryset (QuerySet, optional): An optional queryset to limit the search scope. Defaults to None.
            size (int): The number of results to retrieve per token. Defaults to 24.
            max_polling_size (Optional[int]): Maximum number of results to poll. Defaults to None.
            return_response (bool): Whether to return the raw response from the RecomPI API. Defaults to False.
            skip_rank_field (bool): Whether to skip removing the rank field from objects. Defaults to False.
            api_key (Optional[str]): An optional API key to override the default.

        Returns:
            List[Model]: A list of Django model instances ranked by RecomPI.
        """
        if labels is None:
            labels = RecomPIModelMixin.RecomPILabels.SearchConversion

        if not isinstance(labels, list):
            labels = [labels]

        items = {}
        responses = []

        index = 0
        for token in cls._recompi_tokenize(query):
            objects, resp = cls.recompi_recommend(
                labels=labels,
                profiles=SecureProfile(cls.RECOMPI_SEARCH_TOKENIZER_PROFILER, token),
                geo=geo,
                query_manager=query_manager,
                queryset=queryset,
                size=size,
                max_polling_size=max_polling_size,
                return_response=True,
                skip_rank_field=False,
                api_key=api_key,
            )

            if return_response:
                responses.append(resp)

            for label, objs in objects.items():
                if label not in items:
                    items[label] = {}

                for obj in objs:
                    obj: Model
                    if obj.pk not in items:
                        items[label][obj.pk] = obj
                    else:
                        items[label][obj.pk].recompi_rank += obj.recompi_rank

            index += 1

        for label, subitems in items.items():
            objects: list = list(subitems.values())
            objects.sort(key=lambda obj: obj.recompi_rank, reverse=True)
            items[label] = objects

        if skip_rank_field:
            for obj in objects:
                del obj.recompi_rank

        while isinstance(items, dict) and len(items) == 1:
            items = list(items.values())[0]

        if return_response:
            return items, responses

        return items

    def recompi_search_track(
        self,
        query: Union[str, List[str]],
        location: Optional[Union[str, Location]],
        label: Optional[str] = None,
        geo: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Any:
        """
        Tracks search queries and sends tracking data to RecomPI.

        Args:
            query (Union[str, List[str]]): The search query string or tokenized.
            label (Optional[str]): The label to use for tracking. Defaults to \
                RecomPIModelMixin.RecomPILabels.SearchConversion.
            location (Optional[Union[str, Location]]): The location identifier for the tracking.
            geo (Optional[str]): Geographic information for the tracking.
            api_key (Optional[str]): An optional API key to override the default.
        """
        tokens = self._recompi_tokenize(query)

        if not isinstance(label, str) or not label:
            label = RecomPIModelMixin.RecomPILabels.SearchConversion

        # Track tokens concurrently
        return [
            self.recompi_track(
                label=label,
                profiles=SecureProfile(self.RECOMPI_SEARCH_TOKENIZER_PROFILER, token),
                location=location,
                geo=geo,
                api_key=api_key,
            )
            for token in tokens
        ]

    def recompi_link(
        self,
        instance: "RecomPIModelMixin",
        label: str,
        location: Union[str, Location],
        geo: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Any:
        """
        Links current instance to an other instance.

        Args:
            instance (RecomPIModelMixin): An other instance of `RecomPIModelMixin` which you want \
                to link current instance to that.
            label (str): The label indicating the type of interaction (e.g., "product-view", "click").
            location (str, Location): The location/url information related to the interaction.
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
        return instance.recompi_track(
            label, self.recompi_profile_id(label), location, geo, api_key
        )

    def recompi_recommend_links(
        self,
        model_class: "RecomPIModelMixin",
        labels: Union[str, List[str]],
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
        Recommends items based on the given labels and `model_class`

        Args:
            model_class (Type[RecomPIModelMixin]): The class of the model to use for recommendations; \
                it should be an instance of `RecomPIModelMixin`.
            labels (Union[str, List[str]]): List of labels or a single label.
            geo (Optional[str]): Geographical data relevant to recommendations.
            query_manager (str): Name of the query manager on the model.
            queryset (Optional[QuerySet]): Custom queryset to base recommendations on.
            size (int): Number of items to recommend per label.
            max_polling_size (Optional[int]): Maximum number of records to retrieve from \
                the database for initial ranking.
            return_response (bool): If True, returns the response along with recommendations in a tuple.
            skip_rank_field (bool): If True, excludes the 'recompi_rank' field from the output.
            api_key (Optional[str]): Custom API key for this operation.

        Returns:
            Union[Dict[str, List[Any]], Dict[List[Any], RecomPIResponse]:
                Dictionary of recommended items by label, or tuple containing recommendations \
                    and RecomPI response if return_response=True.

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
        if not isinstance(model_class(), RecomPIModelMixin):
            raise RecomPIFieldTypeError(
                "RecomPI.recompi_recommend_link",
                "model_class",
                model_class(),
                RecomPIModelMixin,
            )

        output = {}

        if not isinstance(labels, list):
            labels = [labels]

        for label in labels:
            result = model_class.recompi_recommend(
                labels=labels,
                profiles=self.recompi_profile_id(label),
                geo=geo,
                query_manager=query_manager,
                queryset=queryset,
                size=size,
                max_polling_size=max_polling_size,
                return_response=return_response,
                skip_rank_field=skip_rank_field,
                api_key=api_key,
            )

            if return_response:
                output[label] = {"objects": result[0][label], "response": result[1]}
            else:
                output.update(result)

        return output

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

        SearchClick = "search-click"
        SearchConversion = "search-conversion"


__all__ = [
    "RecomPIFieldTypeError",
    "RecomPIException",
    "Tag",
    "Profile",
    "SecureProfile",
    "Location",
    "Geo",
    "RecomPIResponse",
    "RecomPI",
    "RecomPIModelMixin",
]
