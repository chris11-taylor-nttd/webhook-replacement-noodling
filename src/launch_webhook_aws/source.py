import logging
from enum import StrEnum
from re import Pattern, compile
from typing import Annotated, Any, Literal, Self, TypeAlias, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    model_validator,
)

from launch_webhook_aws.bitbucket_server import event as bitbucket_server_event
from launch_webhook_aws.event import discriminate_headers
from launch_webhook_aws.github import event as github_event
from launch_webhook_aws.type import Arn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SourceType(StrEnum):
    BITBUCKET_SERVER = "bitbucket_server"
    BITBUCKET_CLOUD = "bitbucket_cloud"
    GITHUB = "github"
    GITHUB_ENTERPRISE = "github_enterprise"


class SourceEvent(BaseModel):
    headers: Annotated[
        (
            Annotated[
                bitbucket_server_event.BitbucketServerHeaders, Tag("bitbucket_server")
            ]
            | Annotated[github_event.GithubHeaders, Tag("github")]
        ),
        Discriminator(discriminate_headers),
    ]
    body: dict[str, Any]

    def to_source_event(
        self,
    ) -> (
        bitbucket_server_event.BitbucketServerWebhookEvent
        | github_event.GithubWebhookEvent
    ):
        if isinstance(self.headers, bitbucket_server_event.BitbucketServerHeaders):
            return bitbucket_server_event.BitbucketServerWebhookEvent(
                headers=self.headers, event={"headers": self.headers, **self.body}
            )
        elif isinstance(self.headers, github_event.GithubHeaders):
            return github_event.GithubWebhookEvent(
                headers=self.headers,
                event={
                    "headers": self.headers,
                    "header_event": self.headers.x_github_event,
                    **self.body,
                },
            )


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

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_signature_secret_configuration(self) -> Self:
        if self.verify_signature and self.signature_secret is None:
            raise ValueError("signature_secret must be set if verify_signature is True")
        return self


class GithubSource(SourceBase):
    type: Literal[SourceType.GITHUB]
    organization: str
    events: list[github_event.EventType]

    def match(self, event: github_event.GithubEvent) -> bool:
        if not issubclass(type(event), github_event.GithubEvent):
            logger.debug(
                f"Event source mismatch: {type(event)} is not a {github_event.GithubEvent}"
            )
            return False
        if event.action_type not in self.events:
            logger.debug(
                f"Event action mismatch: {event.action_type} not in {self.events}"
            )
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
    project_key: str
    events: list[bitbucket_server_event.EventType]

    def match(self, event: bitbucket_server_event.BitbucketServerEvent) -> bool:
        if not issubclass(type(event), bitbucket_server_event.BitbucketServerEvent):
            logger.debug(
                f"Event source mismatch: {type(event)} is not a {bitbucket_server_event.BitbucketServerEvent}"
            )
            return False
        if event.event_key not in [event_type.value for event_type in self.events]:
            logger.debug(
                f"Event action mismatch: {event.event_key} not in {self.events}"
            )
            return False
        if event.project_key != self.project_key:
            logger.debug(
                f"Project key mismatch: {event.project_key} != {self.project_key}"
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
                if include_repo.search(event.repository_name):
                    logger.debug(
                        f"Repository name {event.repository_name} matched source include pattern {include_repo}"
                    )
                    inclusion_match = True
                else:
                    logger.debug(
                        f"Repository name {event.repository_name} did not match source include pattern {include_repo}"
                    )
        if self.exclude_repositories:
            for exclude_repo in self.exclude_repositories:
                if exclude_repo.search(event.repository_name):
                    logger.debug(
                        f"Repository name {event.repository_name} matched source exclude pattern {exclude_repo}"
                    )
                    exclusion_match = True

        if inclusion_match and not exclusion_match:
            return True
        return False


SourceSpec: TypeAlias = Annotated[
    Union[GithubSource, BitbucketServerSource], Field(discriminator="type")
]
