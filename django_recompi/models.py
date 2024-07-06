from recompi import *
from django.db.models import Q
from django.conf import settings
from typing import Any, Dict, List, Optional, Union


class RecomPIModelMixin:
    """Mixin to integrate RecomPI functionalities with Django models."""

    RECOMPI_DATA_FIELDS: Union[Dict[str, List[str]], List[str]] = []
    RECOMPI_NONE_SPECIAL_LITERAL: str = "***[None]***"

    class RecomPISearchTerm:
        """Represents a search term for RecomPI with a field, value, and probability."""

        def __init__(self, field: str, value: str, prob: float) -> None:
            self.field = field
            self.value = value
            self.prob = prob

        def to_q(self) -> Q:
            """Converts the search term to a Django Q object."""
            return Q(**{self.field: self.value})

    def _recompi_api(self) -> RecomPI:
        """
        Initialize and return a RecomPI API instance.

        Raises:
            RecomPIException: If RECOMPI_API_KEY is not set in settings.

        Returns:
            RecomPI: Instance of RecomPI API.
        """
        api_key = getattr(settings, "RECOMPI_API_KEY", None)
        secure_url = getattr(settings, "RECOMPI_SECURE_API", True)
        hash_salt = getattr(settings, "RECOMPI_SECURE_PROFILE_HASH_SALT", None)

        if not api_key:
            raise RecomPIException("settings.RECOMPI_API_KEY is not set!")

        if hash_salt:
            RecomPIFieldTypeError.if_not_validated(
                "RecomPIManager.recommend",
                "settings.RECOMPI_SECURE_PROFILE_HASH_SALT",
                hash_salt,
                str,
            )

        return RecomPI(api_key=api_key, secure_url=secure_url, hash_salt=hash_salt)

    def _recompi_getattr(
        self, instance: Any, field_path: str, default: Optional[Any] = None
    ) -> Any:
        """
        Dynamically access the value of a field from an instance.

        Args:
            instance (Any): Django model instance.
            field_path (str): Dot-separated string representing the field path.
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

    def _recompi_rank(
        self,
        items: List[Any],
        search_terms: List["RecomPIModelMixin.RecomPISearchTerm"],
    ) -> List[Any]:
        """
        Rank items based on search terms using a fuzzy integral.

        Args:
            items (List[Any]): List of items to rank.
            search_terms (List[RecomPISearchTerm]): List of search terms.

        Returns:
            List[Any]: Ranked list of items.
        """

        def fuzzy_integral(item):
            rank = 0
            for term in search_terms:
                if str(self._recompi_getattr(item, term.field, None)) == term.value:
                    rank = (term.prob**2 + rank**2) ** 0.5

            if getattr(settings, "RECOMPI_SET_RANK_ON_RECORD", True):
                item.recompi_rank = rank

            return rank

        items.sort(key=fuzzy_integral, reverse=True)
        return items

    @classmethod
    def recompi_recommend(
        cls,
        labels: Union[str, List[str]],
        profiles: Optional[List[str]] = None,
        geo: Optional[str] = None,
        query_manager: str = "objects",
        size: int = 8,
        max_polling_size: Optional[int] = None,
    ) -> Dict[str, List[Any]]:
        """
        Recommend items based on labels and search terms.

        Args:
            labels (Union[str, List[str]]): List of labels or a single label.
            profiles (Optional[List[str]]): List of profiles.
            geo (Optional[str]): Geographical data.
            query_manager (str): Query manager name.
            size (int): Number of items to recommend per label.
            max_polling_size (Optional[int]): The maximum number of records initially retrieved from the database for ranking. Setting this too low may exclude potentially relevant results, whereas setting it to None imposes no limit.

        Returns:
            Dict[str, List[Any]]: Dictionary of recommended items by label.
        """
        self = cls()
        api = self._recompi_api()

        if isinstance(labels, str):
            labels = [labels]

        results = api.recom(
            [self._recompi_labelify(label) for label in labels], profiles, geo
        )

        output = {}

        if not results.is_success():
            return output

        CLASS = self._recompi_class_name()

        class SearchTerms(list):
            def __init__(self, *args, **kwargs):
                super(SearchTerms, self).__init__(*args, **kwargs)

            def to_q(self):
                """Convert the list of search terms to a Django Q object."""
                if not self:
                    return None
                qs = self[0].to_q()

                for i in range(1, len(self)):
                    qs = qs | self[i].to_q()

                return qs

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
                    f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS[{label}]` or `{CLASS}.RECOMPI_DATA_FIELDS` to be a list; but it's an instance of `{type(fields).__name__}`"
                )

            qs = SearchTerms()

            for field in FIELDS:
                for res, prob in result.items():
                    if not res.startswith(f"{field}:"):
                        continue
                    value = res[len(field) + 1 :]
                    qs.append(
                        self.RecomPISearchTerm(field.replace(".", "__"), value, prob)
                    )

            queries = qs.to_q()
            if not queries:
                continue
            items = getattr(cls, query_manager).filter(queries)
            if max_polling_size:
                items = items[:max_polling_size]

            output[label] = self._recompi_rank(list(items), qs)[:size]

        return output

    def recompi_track(
        self, label: str, profiles: List[str], location: str, geo: Optional[str] = None
    ) -> Any:
        """
        Track user interactions with the system.

        Args:
            label (str): Interaction label.
            profiles (List[str]): List of profiles.
            location (str): Location information.
            geo (Optional[str]): Geographical data.

        Returns:
            Any: Response from RecomPI API.
        """
        api = self._recompi_api()

        CLASS = self._recompi_class_name()

        label = self._recompi_labelify(label)

        FIELDS = self.RECOMPI_DATA_FIELDS
        if isinstance(FIELDS, dict):
            if label not in FIELDS:
                return None
            FIELDS = FIELDS[label]

        if not isinstance(FIELDS, list):
            raise RecomPIException(
                f"Expecting `{CLASS}.RECOMPI_DATA_FIELDS[{label}]` or `{CLASS}.RECOMPI_DATA_FIELDS` to be a list; but it's an instance of `{type(fields).__name__}`"
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
                        id="%s:%s" % (field, value),
                        name=field,
                        desc="%s.%s" % (CLASS, field),
                    )
                )

        return api.push(label, tags, profiles, location, geo)

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
