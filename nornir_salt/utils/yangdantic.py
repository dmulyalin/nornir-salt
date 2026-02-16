import logging
import inspect

from functools import wraps
from pydantic import BaseModel, create_model
from typing import Optional, List, Any, Dict, Callable

log = logging.getLogger(__name__)


class ValidateFuncArgs:
    """
    Class-based decorator to validate function input arguments.

    :param model: Pydantic model to use for validating function arguments.
    :param mixins: List of additional functions to augment model fields.
    :param mixins_skip_args: List of argument names to exclude from the ``model``.
        Defaults to skipping arguments named ``self``.
    :param config: Model configuration dictionary for dynamically forming the model
        for the decorated function. Ignored if ``model`` is provided.

    .. warning:: All model fields derived from ``mixins`` functions are forced to be optional.
        Required arguments must be defined in the ``model``.
    """

    __slots__ = ["model", "mixins", "mixins_skip_args", "config", "function"]

    def __init__(
        self,
        model: Optional[BaseModel] = None,
        mixins: Optional[List[Any]] = None,
        mixins_skip_args: Optional[List[str]] = None,
        config: Optional[Dict] = None,
    ) -> None:
        self.model = model
        self.mixins = mixins or []
        self.mixins_skip_args = mixins_skip_args or ["self"]
        self.config = config or {}

    def __call__(self, function: Callable) -> Callable:
        self.function = function

        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self._validate(args, kwargs)
            return self.function(*args, **kwargs)

        return wrapper

    def _merge_args_to_kwargs(self, args: List[Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge positional arguments with keyword arguments using the function's argspec.

        :param args: Positional argument values passed to the decorated function.
        :param kwargs: Keyword arguments passed to the decorated function.
        :return: Merged dictionary of arguments.
        """
        merged_kwargs = {}

        (
            fun_args,  # List of the positional parameter names
            fun_varargs,  # Name of the * parameter or None
            fun_varkw,  # Name of the ** parameter or None
            fun_defaults,  # Tuple of default argument values of the last n positional parameters
            fun_kwonlyargs,  # List of keyword-only parameter names
            fun_kwonlydefaults,  # Dictionary mapping kwonlyargs parameter names to default values
            fun_annotations,  # Dictionary mapping parameter names to annotations
        ) = inspect.getfullargspec(self.function)

        # Combine positional arguments with their names
        args_to_kwargs = dict(zip(fun_args, args))

        # Combine *args with their names
        if fun_varargs:
            args_to_kwargs[fun_varargs] = args[len(fun_args) :]

        merged_kwargs = {**kwargs, **args_to_kwargs}

        return merged_kwargs

    def _get_model(self) -> BaseModel:
        """
        Return the model provided during initialization or dynamically create one
        using the decorated function's type hints.
        """
        if self.model is None:
            fields_spec = self._form_fields_spec(self.function, make_optional=False)

            class Config:
                pass

            # Add configuration parameters to the Config object
            for k, v in self.config.items():
                setattr(Config, k, v)

            self.model = create_model(
                f"model_{self.function.__name__}",
                **fields_spec,
                __config__=Config
            )

        return self.model

    def _form_fields_spec(
        self,
        function: Callable,
        skip_fields: Optional[List[str]] = None,
        make_optional: bool = True,
    ) -> Dict[str, Any]:
        """
        Form a dictionary of arguments and their types.

        :param function: Function to form fields spec for.
        :param skip_fields: List of argument names to ignore.
        :param make_optional: Whether to make all arguments optional.
        :return: Dictionary of fields.
        """
        skip_fields = skip_fields or []

        # if default value for argument is None, it is considered optional, while if it is
        # ellipsis ... it is considered required by pydantic
        default_val = None if make_optional else ...

        (
            fun_args,  # list of the positional parameter names
            fun_varargs,  # name of the * parameter or None
            fun_varkw,  # name of the ** parameter or None
            fun_defaults,  # tuple of default argument values of the last n positional parameters
            fun_kwonlyargs,  # list of keyword-only parameter names
            fun_kwonlydefaults,  # dictionary mapping kwonlyargs parameter names to default values
            fun_annotations,  # dictionary mapping parameter names to annotations
        ) = inspect.getfullargspec(function)

        # form a dictionary keyed by args with their default values
        args_with_defaults = dict(
            zip(reversed(fun_args or []), reversed(fun_defaults or []))
        )

        # form a dictionary keyed by args that has no defaults with values set to
        # (Any, None) tuple if make_optional is True else set yo (Any, ...)
        args_no_defaults = {
            k: (Any, default_val) for k in fun_args if k not in args_with_defaults
        }

        # form dictionary keyed by args with annotations and tuple values
        args_with_hints = {
            k: (v, args_with_defaults.get(k, default_val))
            for k, v in fun_annotations.items()
        }

        # form mered kwargs giving preference to type hint annotations
        merged_kwargs = {**args_no_defaults, **args_with_defaults, **args_with_hints}

        # form final dictionary of fields
        fields_spec = {
            k: v
            for k, v in merged_kwargs.items()
            if (
                k not in skip_fields
                and k not in self.mixins_skip_args
                #  argspec key "return" is for function return value annotation (if any)
                and k not in ["return", fun_varargs, fun_varkw]
            )
        }

        return fields_spec

    def _add_mixins(self, model: BaseModel) -> BaseModel:
        """Augment model fields with mixin function arguments using their type hints."""
        for mixin_function in self.mixins:
            # check if mixin is not defined
            if mixin_function is None:
                continue
            # get a list of model existing fields - pydantic gives error if tries to override them
            existing_fields = list(model.construct().__fields__.keys())

            new_fields = self._form_fields_spec(
                mixin_function, skip_fields=existing_fields
            )

            # extend model to augment mixin function arguments
            if new_fields:
                model = create_model(model.__name__, __base__=model, **new_fields)

        return model

    def _validate(self, args: List[Any], kwargs: Dict[str, Any]) -> None:
        """Validate provided arguments against the model."""
        merged_kwargs = self._merge_args_to_kwargs(args, kwargs)
        model = self._get_model()
        model = self._add_mixins(model)
        # if below step succeeds, kwargs passed model validation
        _ = model(**merged_kwargs)
