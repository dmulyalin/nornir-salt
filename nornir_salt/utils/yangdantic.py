import logging
import inspect

from functools import wraps
from pydantic import BaseModel, create_model
from typing import Optional, List, Any, Dict, Callable

log = logging.getLogger(__name__)


class ValidateFuncArgs:
    """
    Class based decorator to validate functions input arguments.

    :param model: pydantic model to use to check function arguments
    :param mixins: list of additional functions to augment model fields with
    :param mixins_skip_args: list of argument names to not add as fields to the ``model``,
        by default skips arguments named ``self``
    :param config: model configuration dictionary to use while dynamically forming model
        for decorated function, ignored if ``model`` argument provided

    .. warning:: all model fields derived from ``mixins`` functions forced to be optional,
        all required arguments must be defined in ``model``.
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
        def wrapper(*args, **kwargs):
            self._validate(args, kwargs)
            return self.function(*args, **kwargs)

        return wrapper

    def _merge_args_to_kwargs(self, args: List, kwargs: Dict) -> Dict:
        """
        Function to merge args with kwargs using function argspec, this is to
        make sure that pydantic only get **kwargs to instantiate a model and
        run validation.

        :param args: argument values passed to decorated function
        :param kwargs: key word arguments passed to decorated function
        """
        merged_kwargs = {}

        (
            fun_args,  # list of the positional parameter names
            fun_varargs,  # name of the * parameter or None
            fun_varkw,  # name of the ** parameter or None
            fun_defaults,  # tuple of default argument values of the last n positional parameters
            fun_kwonlyargs,  # list of keyword-only parameter names
            fun_kwonlydefaults,  # dictionary mapping kwonlyargs parameter names to default values
            fun_annotations,  # dictionary mapping parameter names to annotations
        ) = inspect.getfullargspec(self.function)

        # "def foo(a, b):" - combine "foo(1, 2)" args with "a, b" fun_args
        args_to_kwargs = dict(zip(fun_args, args))

        # "def foo(a, *b):" - combine "foo(1, 2, 3)" 2|3 args with "*b" fun_varargs
        if fun_varargs:
            args_to_kwargs[fun_varargs] = args[len(fun_args) :]

        merged_kwargs = {**kwargs, **args_to_kwargs}

        return merged_kwargs

    def _get_model(self) -> None:
        """
        Function to return model if it was provided on instantiation or
        dynamically create model using decorated function type hints.
        """
        if self.model is None:
            fields_spec = self._form_fields_spec(self.function, make_optional=False)

            class Config:
                pass

            # add configuration parameters to Config object
            for k, v in self.config.items():
                setattr(Config, k, v)

            self.model = create_model(
                "model_{}".format(self.function.__name__),
                **fields_spec,
                __config__=Config
            )

        return self.model

    def _form_fields_spec(
        self,
        function: Callable,
        skip_fields: List[str] = None,
        make_optional: bool = True,
    ) -> Dict:
        """
        Function to form a dictionary of arguments and their types in
        {arg1: (type, default_value), arg2: default_value, arg3: {type, ...}}
        formats

        :param function: function to form fields spec for
        :param skip_fields: list of arguments names to ignore
        :param make_optional: boolean to indicate if all arguments to be made optional
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
        """Function to augment model fields with mixins functions arguments using their type hints"""
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

    def _validate(self, args: List, kwargs: Dict) -> None:
        """Function to validate provided arguments against model"""
        merged_kwargs = self._merge_args_to_kwargs(args, kwargs)
        model = self._get_model()
        model = self._add_mixins(model)
        # if below step succeeds, kwargs passed model validation
        _ = model(**merged_kwargs)
