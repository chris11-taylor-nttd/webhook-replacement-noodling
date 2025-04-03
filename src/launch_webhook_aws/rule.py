import importlib
import inspect
from types import GenericAlias
from typing import Callable, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from launch_webhook_aws.bitbucket_server.event import BitbucketServerEvent
from launch_webhook_aws.destination import DestinationSpec
from launch_webhook_aws.event import ScmEvent
from launch_webhook_aws.github.event import GithubEvent
from launch_webhook_aws.source import SourceSpec
from launch_webhook_aws.transform import (
    RuleTransform,
    TransformResult,
    default_transform,
)


class Rule(BaseModel):
    source: SourceSpec
    transform: RuleTransform = Field(default=default_transform)
    destination: DestinationSpec

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def match(self, event: GithubEvent | BitbucketServerEvent) -> bool:
        return self.source.match(event)

    @field_validator("transform", mode="before")
    @classmethod
    def handle_transform_import(cls, value: RuleTransform) -> Callable:
        """Transforms a provided string"""
        if callable(value):
            return value
        elif isinstance(value, str):
            parts = value.split(".")
            if len(parts) < 2:
                raise ValueError(
                    "Rule transform provided as a string must be in the format 'module.function'"
                )
            module_name = ".".join(parts[:-1])
            function_name = parts[-1]
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                raise ValueError(f"Rule transform module {module_name} not found!")
            except ImportError:
                raise ValueError(
                    f"Rule transform module {module_name} could not be imported!"
                )

            try:
                func = getattr(module, function_name)
            except AttributeError:
                raise ValueError(
                    f"Rule transform function {function_name} not found in module {module_name}!"
                )

            if not callable(func):
                raise ValueError(f"Rule transform function {value} is not callable!")
            return func
        else:
            raise ValueError("Provided transform must be a callable or a string!")

    @model_validator(mode="after")
    def check_transform_signature(self) -> Self:
        """Checks the signature of the transform function to ensure it accepts and returns the correct types.

        The transform function must accept a parameter named event, which must be annotated as a dict or a
        subclass of ScmEvent. The function must annotate its return type as dict.
        """
        transform_signature = inspect.signature(self.transform)

        if "event" not in transform_signature.parameters:
            raise ValueError("Rule transform function must accept an event parameter!")

        event_annotation = transform_signature.parameters["event"].annotation

        if event_annotation is not dict and type(event_annotation) is GenericAlias:
            if event_annotation.__origin__ is not dict:
                raise ValueError(
                    "Rule transform event parameter must be annotated to accept a dict or a subclass of ScmEvent"
                )
        elif event_annotation is not dict:
            if not issubclass(event_annotation, ScmEvent):
                raise ValueError(
                    "Rule transform event parameter must be annotated to accept a dict or a subclass of ScmEvent"
                )

        if type(transform_signature.return_annotation) is GenericAlias:
            if transform_signature.return_annotation.__origin__ is not dict:
                raise ValueError(
                    "Rule transform return annotation must be dict if using generics!"
                )
        elif transform_signature.return_annotation is dict:
            pass
        elif transform_signature.return_annotation is TransformResult:
            pass
        else:
            raise ValueError(
                "Rule transform return annotation must be TransformResult or dict!"
            )
        return self
