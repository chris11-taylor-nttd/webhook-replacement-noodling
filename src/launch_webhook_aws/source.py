import logging
from enum import StrEnum
from re import Pattern, compile
from typing import Annotated, Literal, Self, TypeAlias, Union

from pydantic import BaseModel, BeforeValidator, Field, model_validator

from launch_webhook_aws.bitbucket_server.type import (
    EventType as BitbucketServerEventType,
)
from launch_webhook_aws.github.event import GithubEvent
from launch_webhook_aws.github.type import EventType as GithubEventType
from launch_webhook_aws.type import Arn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SourceType(StrEnum):
    BITBUCKET_SERVER = "bitbucket_server"
    BITBUCKET_CLOUD = "bitbucket_cloud"
    GITHUB = "github"
    GITHUB_ENTERPRISE = "github_enterprise"
    GENERIC = "generic"


def validate_patterns(value: ...) -> list[Pattern]:
    patterns = []
    if value is None:
        return []
    if isinstance(value, (str, Pattern)):
        value = [value]
    if not isinstance(value, list):
        raise ValueError(
            "must be a list of patterns or strings that can become patterns"
        )
    for pattern in value:
        if isinstance(pattern, Pattern):
            patterns.append(pattern)
        else:
            try:
                patterns.append(compile(pattern))
            except Exception as e:
                raise ValueError(
                    "must be a list of patterns or strings that can become patterns"
                ) from e
    return patterns


PatternList = Annotated[list[Pattern], BeforeValidator(validate_patterns)]


class SourceBase(BaseModel):
    type: SourceType
    include_repositories: PatternList = Field(default_factory=list)
    exclude_repositories: PatternList = Field(default_factory=list)
    verify_signature: bool = Field(default=False)
    signature_secret: Arn | None = Field(default=None)

    @model_validator(mode="after")
    def check_signature_secret_configuration(self) -> Self:
        if self.verify_signature and self.signature_secret is None:
            raise ValueError("signature_secret must be set if verify_signature is True")
        return self


class GithubSource(SourceBase):
    type: Literal[SourceType.GITHUB]
    organization: str
    events: list[GithubEventType] = Field(default_factory=list)

    def match(self, event: GithubEvent) -> bool:
        if not issubclass(type(event), GithubEvent):
            logger.debug(f"Event source mismatch: {type(event)} is not a {GithubEvent}")
            return False
        if event.action not in self.events:
            logger.debug(f"Event action mismatch: {event.action} not in {self.events}")
            return False
        if event.organization_name != self.organization:
            logger.debug(
                f"Organization mismatch: {event.organization_name} != {self.organization}"
            )
            return False

        inclusion_match = False
        exclusion_match = False

        if not self.include_repositories:
            logger.debug(
                "No source include patterns defined, this repository is included by default."
            )
            inclusion_match = True
        else:
            for include_repo in self.include_repositories:
                if include_repo.search(event.repository.name):
                    logger.debug(
                        f"Repository name {event.repository.name} matched source include pattern {include_repo}"
                    )
                    inclusion_match = True
                else:
                    logger.debug(
                        f"Repository name {event.repository.name} did not match source include pattern {include_repo}"
                    )
        if self.exclude_repositories:
            for exclude_repo in self.exclude_repositories:
                if exclude_repo.search(event.repository.name):
                    logger.debug(
                        f"Repository name {event.repository.name} matched source exclude pattern {exclude_repo}"
                    )
                    exclusion_match = True

        if inclusion_match and not exclusion_match:
            return True
        return False


class BitbucketServerSource(SourceBase):
    type: Literal[SourceType.BITBUCKET_SERVER]
    project: str
    events: list[BitbucketServerEventType]


SourceSpec: TypeAlias = Annotated[
    Union[GithubSource, BitbucketServerSource], Field(discriminator="type")
]
