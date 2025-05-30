from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from launch_webhook_aws.bitbucket_server.type import (
    Change,
    CommitHash,
    PullRequest,
    Repository,
    User,
)
from launch_webhook_aws.event import ScmEvent, ScmHeaders


class EventType(StrEnum):
    REPO_REFS_CHANGED = "repo:refs_changed"
    PR_FROM_REF_UPDATED = "pr:from_ref_updated"
    PR_OPENED = "pr:opened"
    PR_MERGED = "pr:merged"


class BitbucketServerHeaders(ScmHeaders):
    x_request_id: str = Field(alias="X-Request-Id")
    x_event_key: str = Field(alias="X-Event-Key")
    # Bitbucket Server only provides a signature when a webhook is configured with a secret
    x_hub_signature: str = Field(default="", alias="X-Hub-Signature")


class BitbucketServerEvent(ScmEvent):
    headers: BitbucketServerHeaders
    date: datetime
    actor: User

    @property
    def signature_hash_sha256(self) -> str:
        # Bitbucket Server provides SHA256 signatures as "X-Hub-Signature"
        return self.headers.x_hub_signature


class Push(BitbucketServerEvent):
    event_key: Literal[EventType.REPO_REFS_CHANGED] = Field(alias="eventKey")
    repository: Repository
    changes: list[Change]

    @property
    def project_key(self) -> str:
        return self.repository.project.key

    @property
    def repository_name(self) -> str:
        return self.repository.name


class SourceBranchUpdated(BitbucketServerEvent):
    event_key: Literal[EventType.PR_FROM_REF_UPDATED] = Field(alias="eventKey")
    pull_request: PullRequest = Field(alias="pullRequest")
    previous_from_hash: CommitHash = Field(alias="previousFromHash")

    @property
    def project_key(self) -> str:
        return self.pull_request.to_ref.repository.project.key

    @property
    def repository_name(self) -> str:
        return self.pull_request.to_ref.repository.name


class PullRequestOpened(BitbucketServerEvent):
    event_key: Literal[EventType.PR_OPENED] = Field(alias="eventKey")
    pull_request: PullRequest = Field(alias="pullRequest")

    @property
    def project_key(self) -> str:
        return self.pull_request.to_ref.repository.project.key

    @property
    def repository_name(self) -> str:
        return self.pull_request.to_ref.repository.name


class PullRequestMerged(BitbucketServerEvent):
    event_key: Literal[EventType.PR_MERGED] = Field(alias="eventKey")
    pull_request: PullRequest = Field(alias="pullRequest")

    @property
    def project_key(self) -> str:
        return self.pull_request.to_ref.repository.project.key

    @property
    def repository_name(self) -> str:
        return self.pull_request.to_ref.repository.name


BitbucketServerEventType = Annotated[
    Union[Push, SourceBranchUpdated, PullRequestOpened, PullRequestMerged],
    Field(discriminator="event_key"),
]


class BitbucketServerWebhookEvent(BaseModel):
    headers: BitbucketServerHeaders
    event: BitbucketServerEventType
