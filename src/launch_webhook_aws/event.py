from abc import abstractmethod

from pydantic import BaseModel


class ScmHeaders(BaseModel):
    pass


class ScmEvent(BaseModel):
    headers: ScmHeaders

    @property
    @abstractmethod
    def signature_hash_sha256(self) -> str | None: ...
