from datetime import datetime
from enum import StrEnum
from typing import ForwardRef, Literal

from pydantic import BaseModel, EmailStr, Field

from launch_webhook_aws.type import CommitHash, GitUrl, HttpsUrl


class AuthorAssociation(StrEnum):
    COLLABORATOR = "COLLABORATOR"
    CONTRIBUTOR = "CONTRIBUTOR"
    FIRST_TIMER = "FIRST_TIMER"
    FIRST_TIME_CONTRIBUTOR = "FIRST_TIME_CONTRIBUTOR"
    MANNEQUIN = "MANNEQUIN"
    MEMBER = "MEMBER"
    NONE = "NONE"
    OWNER = "OWNER"


class MergeMethod(StrEnum):
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class UserType(StrEnum):
    BOT = "Bot"
    ORGANIZATION = "Organization"
    USER = "User"


class MergeCommitMessage(StrEnum):
    PR_BODY = "PR_BODY"
    PR_TITLE = "PR_TITLE"
    BLANK = "BLANK"


class MergeCommitTitle(StrEnum):
    PR_TITLE = "PR_TITLE"
    MERGE_MESSAGE = "MERGE_MESSAGE"


class SquashMergeCommitMessage(StrEnum):
    PR_BODY = "PR_BODY"
    COMMIT_MESSAGES = "COMMIT_MESSAGES"
    BLANK = "BLANK"


class SquashMergeCommitTitle(StrEnum):
    PR_TITLE = "PR_TITLE"
    COMMIT_OR_PR_TITLE = "COMMIT_OR_PR_TITLE"


class RepoVisibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"
    INTERNAL = "internal"


class TeamPrivacy(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    SECRET = "secret"  # pragma: allowlist secret


class NotificationSetting(StrEnum):
    NOTIFICATIONS_ENABLED = "notifications_enabled"
    NOTIFICATIONS_DISABLED = "notifications_disabled"


class PullRequestSide(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class RepositorySelection(StrEnum):
    ALL = "all"
    SELECTED = "selected"


class HookConfigContentType(StrEnum):
    FORM = "form"
    JSON = "json"


class IssueActiveLockReason(StrEnum):
    RESOLVED = "resolved"
    OFF_TOPIC = "off-topic"
    TOO_HEATED = "too heated"
    SPAM = "spam"


class MilestoneState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"


class IssueState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"


class IssueCloseReason(StrEnum):
    NOT_PLANNED = "not_planned"
    COMPLETED = "completed"


class PullRequestState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"


class HookType(StrEnum):
    REPOSITORY = "Repository"
    ORGANIZATION = "Organization"
    APP = "App"


class Link(BaseModel):
    href: HttpsUrl


class Links(BaseModel):
    comments: Link
    commits: Link
    html: Link
    issue: Link
    review_comment: Link
    review_comments: Link
    self: Link
    statuses: Link


class Reactions(BaseModel):
    plusone: int = Field(default=0, alias="+1")
    minusone: int = Field(default=0, alias="-1")
    laugh: int = Field(default=0)
    hooray: int = Field(default=0)
    confused: int = Field(default=0)
    heart: int = Field(default=0)
    rocket: int = Field(default=0)
    eyes: int = Field(default=0)
    total_count: int = Field(default=0)
    url: HttpsUrl


class User(BaseModel):
    avatar_url: HttpsUrl
    events_url: HttpsUrl
    deleted: bool | None = Field(default=False)
    followers_url: HttpsUrl
    following_url: HttpsUrl
    gists_url: HttpsUrl
    gravatar_id: str
    html_url: HttpsUrl
    id: int
    login: str
    node_id: str
    organizations_url: HttpsUrl
    received_events_url: HttpsUrl
    repos_url: HttpsUrl
    site_admin: bool
    starred_url: HttpsUrl
    subscriptions_url: HttpsUrl
    type: UserType
    url: HttpsUrl


class RepositoryMetadata(BaseModel):
    full_name: str
    id: int
    name: str
    node_id: str
    private: bool


class Repository(BaseModel):
    archive_url: HttpsUrl
    archived: bool
    assignees_url: HttpsUrl
    blobs_url: HttpsUrl
    branches_url: HttpsUrl
    clone_url: HttpsUrl
    collaborators_url: HttpsUrl
    comments_url: HttpsUrl
    commits_url: HttpsUrl
    compare_url: HttpsUrl
    contents_url: HttpsUrl
    contributors_url: HttpsUrl
    created_at: datetime
    default_branch: str
    delete_branch_on_merge: bool = Field(default=False)
    deployments_url: HttpsUrl
    description: str | None = Field(default=None)
    disabled: bool
    downloads_url: HttpsUrl
    events_url: HttpsUrl
    fork: bool
    forks: int
    forks_count: int
    forks_url: HttpsUrl
    full_name: str
    git_commits_url: HttpsUrl
    git_refs_url: HttpsUrl
    git_tags_url: HttpsUrl
    git_url: GitUrl
    has_discussions: bool
    has_downloads: bool
    has_issues: bool
    has_pages: bool
    has_projects: bool
    has_wiki: bool
    homepage: str | None = Field(default=None)
    hooks_url: HttpsUrl
    html_url: HttpsUrl
    id: int
    is_template: bool
    issue_comment_url: HttpsUrl
    issue_events_url: HttpsUrl
    issues_url: HttpsUrl
    keys_url: HttpsUrl
    labels_url: HttpsUrl
    language: str | None = Field(default=None)
    languages_url: HttpsUrl
    license: dict | None = Field(default=None)
    merge_commit_message: MergeCommitMessage | None = Field(default=None)
    merge_commit_title: MergeCommitTitle | None = Field(default=None)
    merges_url: HttpsUrl
    milestones_url: HttpsUrl
    mirror_url: HttpsUrl | None = Field(default=None)
    name: str
    node_id: str
    notifications_url: HttpsUrl
    open_issues: int
    open_issues_count: int
    owner: User
    private: bool
    pulls_url: HttpsUrl
    pushed_at: datetime
    releases_url: HttpsUrl
    size: int
    squash_merge_commit_message: SquashMergeCommitMessage | None = Field(default=None)
    squash_merge_commit_title: SquashMergeCommitTitle | None = Field(default=None)
    ssh_url: str
    stargazers_count: int
    stargazers_url: HttpsUrl
    statuses_url: HttpsUrl
    subscribers_url: HttpsUrl
    subscription_url: HttpsUrl
    svn_url: HttpsUrl
    tags_url: HttpsUrl
    teams_url: HttpsUrl
    topics: list[str]
    trees_url: HttpsUrl
    updated_at: datetime
    url: HttpsUrl
    use_squash_pr_title_as_default: bool | None = Field(default=None)
    visibility: RepoVisibility
    watchers: int
    watchers_count: int
    web_commit_signoff_required: bool


class BaseRef(BaseModel):
    label: str
    ref: str
    repo: Repository
    sha: CommitHash
    user: User


class HookLastResponse(BaseModel):
    code: int | None = Field(default=None)
    status: str | None = Field(default=None)
    message: str | None = Field(default=None)


class Hook(BaseModel):
    type: HookType
    id: int
    app_id: int | None = Field(default=None)
    name: Literal["web"]
    active: bool
    events: list[str]
    config: dict
    updated_at: datetime
    created_at: datetime
    url: HttpsUrl
    test_url: HttpsUrl
    ping_url: HttpsUrl
    deliveries_url: HttpsUrl
    last_response: HookLastResponse


class Organization(BaseModel):
    login: str
    id: int
    node_id: str
    url: HttpsUrl
    repos_url: HttpsUrl
    events_url: HttpsUrl
    hooks_url: HttpsUrl
    issues_url: HttpsUrl
    members_url: HttpsUrl
    public_members_url: HttpsUrl
    avatar_url: HttpsUrl
    description: str


class UserMetadata(BaseModel):
    date: datetime | None = Field(default=None)
    email: EmailStr
    name: str
    username: str | None = Field(default=None)


Team = ForwardRef("Team")


class Team(BaseModel):
    deleted: bool | None = Field(default=False)
    description: str | None = Field(default=None)
    html_url: HttpsUrl
    id: int
    members_url: HttpsUrl
    name: str
    node_id: str
    notification_setting: NotificationSetting
    parent: Team | None = Field(default=None)
    permission: str
    privacy: TeamPrivacy
    repositories_url: HttpsUrl
    slug: str
    url: HttpsUrl


Team.model_rebuild()


class AutoMergeStatus(BaseModel):
    commit_message: str
    commit_title: str
    enabled_by: User
    merge_method: MergeMethod


class Label(BaseModel):
    color: str
    default: bool
    description: str | None = Field(default=None)
    id: int
    name: str
    node_id: str
    url: HttpsUrl


class PullRequest(BaseModel):
    links: Links = Field(alias="_links")
    active_lock_reason: None
    additions: int | None = Field(default=None)
    assignee: User | None = Field(default=None)
    assignees: list[User]
    author_association: AuthorAssociation
    auto_merge: AutoMergeStatus | None = Field(default=None)
    base: BaseRef
    body: str | None = Field(default=None)
    changed_files: int | None = Field(default=None)
    closed_at: datetime | None = Field(default=None)
    comments: int | None = Field(default=None)
    comments_url: HttpsUrl
    commits: int | None = Field(default=None)
    commits_url: HttpsUrl
    created_at: datetime
    deletions: int | None = Field(default=None)
    diff_url: HttpsUrl
    draft: bool
    head: BaseRef
    html_url: HttpsUrl | None = Field(default=None)
    id: int
    issue_url: HttpsUrl
    labels: list[Label]
    locked: bool
    maintainer_can_modify: bool | None = Field(default=None)
    merge_commit_sha: CommitHash | None = Field(default=None)
    mergeable: bool | None = Field(default=None)
    mergeable_state: str | None = Field(default=None)
    merged: bool | None = Field(default=False)
    merged_at: datetime | None = Field(default=None)
    merged_by: User | None = Field(default=None)
    milestone: str | None = Field(default=None)
    node_id: str
    number: int
    patch_url: HttpsUrl
    rebaseable: bool | None = Field(default=None)
    requested_reviewers: list[User]
    requested_teams: list[Team]
    review_comment_url: HttpsUrl
    review_comments: int | None = Field(default=None)
    review_comments_url: HttpsUrl
    state: PullRequestState
    statuses_url: HttpsUrl
    title: str
    updated_at: datetime
    url: HttpsUrl
    user: dict
