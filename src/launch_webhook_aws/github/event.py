from typing import Annotated, Literal, Union

from pydantic import ConfigDict, Field

from launch_webhook_aws.event import ScmEvent, ScmHeaders


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


class Push(GithubEvent):
    header_event: Literal["push"]
    action: Literal["push"]


class PullRequestEvent(GithubEvent):
    header_event: Literal["pull_request"]


class PullRequestOpened(PullRequestEvent):
    action: Literal["opened"]


class PullRequestClosed(PullRequestEvent):
    action: Literal["closed"]


class PullRequestSynchronize(PullRequestEvent):
    action: Literal["synchronize"]


GithubPullRequestEventType = Annotated[
    Union[PullRequestOpened, PullRequestClosed, PullRequestSynchronize],
    Field(discriminator="action"),
]

GithubEventType = Annotated[
    Union[Push, GithubPullRequestEventType],
    Field(discriminator="action"),
]
