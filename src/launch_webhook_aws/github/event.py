import warnings
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from launch_webhook_aws.event import ScmEvent, ScmHeaders
from launch_webhook_aws.github.type import (
    Hook,
    PullRequest,
    Repository,
    User,
    UserMetadata,
)
from launch_webhook_aws.type import CommitHash, HttpsUrl

# Pydantic raises warnings when we shadow the header_event from GithubEvent
# on the subclasses, but this isn't useful information so we can filter them
# out.
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


class GithubHeaders(ScmHeaders):
    x_github_hook_id: str = Field(alias="X-Github-Hook-Id")
    x_github_event: str = Field(alias="X-Github-Event")
    x_github_delivery: str = Field(alias="X-Github-Delivery")
    x_hub_signature: str = Field(alias="X-Hub-Signature")
    x_hub_signature_256: str = Field(alias="X-Hub-Signature-256")

    model_config = ConfigDict(extra="allow")


class GithubEvent(ScmEvent):
    headers: GithubHeaders

    def signature_hash_sha256(self) -> str:
        return self.headers.x_hub_signature_256

    @property
    def header_event(self) -> str:
        return self.headers.x_github_event

    @property
    def organization_name(self) -> str:
        return getattr(getattr(self, "repository"), "full_name").split("/")[0]


class Ping(GithubEvent):
    header_event: Literal["ping"]
    zen: str
    hook_id: int
    hook: Hook
    repository: Repository
    sender: User


class Push(GithubEvent):
    header_event: Literal["push"]

    after: CommitHash
    base_ref: None
    before: CommitHash
    commits: list
    compare: HttpsUrl
    created: bool
    deleted: bool
    forced: bool
    head_commit: dict
    pusher: UserMetadata
    ref: str
    repository: Repository
    sender: User


class PullRequestEvent(GithubEvent):
    header_event: Literal["pull_request"]
    number: int
    pull_request: PullRequest
    repository: Repository
    sender: User


class PullRequestOpened(PullRequestEvent):
    action: Literal["opened"]


class PullRequestClosed(PullRequestEvent):
    action: Literal["closed"]


class PullRequestSynchronize(PullRequestEvent):
    action: Literal["synchronize"]
    after: CommitHash
    before: CommitHash


GithubPullRequestEventType = Annotated[
    Union[PullRequestOpened, PullRequestClosed, PullRequestSynchronize],
    Field(discriminator="action"),
]

GithubEventType = Annotated[
    Union[Ping, Push, GithubPullRequestEventType],
    Field(discriminator="header_event"),
]

# For events that contain an "action" key, we concatenate
# the header_event, a dot, and the action.
GithubEventName = Literal[
    "ping",
    "push",
    "pull_request.opened",
    "pull_request.closed",
    "pull_request.synchronize",
]


class GithubWebhookEvent(BaseModel):
    headers: GithubHeaders
    event: GithubEventType
