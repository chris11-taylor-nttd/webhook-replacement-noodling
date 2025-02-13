from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from launch_webhook_aws.type import CommitHash, HttpsUrl, SshUrl


class UserType(StrEnum):
    NORMAL = "NORMAL"


class ProjectType(StrEnum):
    NORMAL = "NORMAL"


class RefType(StrEnum):
    BRANCH = "BRANCH"
    TAG = "TAG"


class ChangeType(StrEnum):
    UPDATE = "UPDATE"


class PullRequestState(StrEnum):
    OPEN = "OPEN"
    MERGED = "MERGED"


class RepositoryState(StrEnum):
    AVAILABLE = "AVAILABLE"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"


class ParticipantRole(StrEnum):
    AUTHOR = "AUTHOR"
    REVIEWER = "REVIEWER"
    PARTICIPANT = "PARTICIPANT"


class ApprovalStatus(StrEnum):
    APPROVED = "APPROVED"
    NEEDS_WORK = "NEEDS_WORK"
    UNAPPROVED = "UNAPPROVED"


class SshLink(BaseModel):
    href: SshUrl
    name: Literal["ssh"]


class HttpLink(BaseModel):
    href: HttpsUrl
    name: Literal["http"]


class BareLink(BaseModel):
    href: HttpsUrl


class Links(BaseModel):
    clone: list[HttpLink | SshLink] | None = Field(default=None)
    self: list[BareLink]


class Project(BaseModel):
    key: str
    id: int
    name: str
    public: bool
    type: ProjectType
    links: Links


class RefInfo(BaseModel):
    id: str
    display_id: str = Field(alias="displayId")
    type: RefType


class Change(BaseModel):
    ref: RefInfo
    ref_id: str = Field(alias="refId")
    from_hash: CommitHash = Field(alias="fromHash")
    to_hash: CommitHash = Field(alias="toHash")
    type: ChangeType


class Repository(BaseModel):
    slug: str
    id: int
    name: str
    hierarchy_id: str = Field(alias="hierarchyId")
    scm_id: str = Field(alias="scmId")
    state: RepositoryState
    status_message: str = Field(alias="statusMessage")
    forkable: bool
    project: Project
    public: bool
    links: Links


class User(BaseModel):
    name: str
    email_address: EmailStr = Field(alias="emailAddress")
    active: bool
    display_name: str = Field(alias="displayName")
    id: int
    slug: str
    type: UserType
    links: Links


class Participant(BaseModel):
    user: User
    role: ParticipantRole
    approved: bool
    status: ApprovalStatus


class Ref(RefInfo):
    id: str
    display_id: str = Field(alias="displayId")
    latest_commit: CommitHash = Field(alias="latestCommit")
    type: RefType
    repository: Repository


class PullRequest(BaseModel):
    id: int
    version: int
    title: str
    state: PullRequestState
    open: bool
    closed: bool
    created_date: datetime = Field(alias="createdDate")
    updated_date: datetime = Field(alias="updatedDate")
    from_ref: Ref = Field(alias="fromRef")
    to_ref: Ref = Field(alias="toRef")
    locked: bool
    author: Participant
    reviewers: list[Participant]
    participants: list[Participant]
    links: Links
