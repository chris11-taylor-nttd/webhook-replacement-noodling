from abc import abstractmethod
from typing import Any

from pydantic import BaseModel


class ScmHeaders(BaseModel):
    pass


class ScmEvent(BaseModel):
    headers: ScmHeaders

    @property
    @abstractmethod
    def signature_hash_sha256(self) -> str | None: ...


def discriminate_headers(v: Any) -> str:
    if "X-Github-Hook-Id" in v:
        return "github"
    if "X-Request-Id" in v:
        if "X-Hook-UUID" in v:
            return "bitbucket_cloud"
        return "bitbucket_server"
    raise ValueError("Unknown headers")
