import inspect
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from launch_webhook_aws.bitbucket_server.event import BitbucketServerEvent
from launch_webhook_aws.destination import DestinationSpec
from launch_webhook_aws.event import ScmEvent
from launch_webhook_aws.github.event import GithubEvent
from launch_webhook_aws.source import SourceSpec
from launch_webhook_aws.transform import RuleTransform, default_transform


class Rule(BaseModel):
    source_spec: SourceSpec
    transform: RuleTransform = Field(default=default_transform)
    destination_spec: DestinationSpec

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def match(self, event: GithubEvent | BitbucketServerEvent) -> bool:
        return self.source_spec.match(event)

    @model_validator(mode="after")
    def check_transform_signature(self) -> Self:
        transform_signature = inspect.signature(self.transform)
        if "event" not in transform_signature.parameters:
            raise ValueError("Rule transform function must accept an event parameter!")
        if transform_signature.parameters["event"].annotation is not dict:
            if not issubclass(
                transform_signature.parameters["event"].annotation, ScmEvent
            ):
                raise ValueError(
                    "Rule transform event parameter must be annotated to accept a dict or a subclass of ScmEvent"
                )
        if transform_signature.return_annotation is not dict:
            raise ValueError("Rule transform return annotation must be dict!")
        return self
