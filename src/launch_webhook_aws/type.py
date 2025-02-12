from typing import Annotated, TypeAlias

from pydantic import HttpUrl, StringConstraints, UrlConstraints

SshUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(scheme="ssh")]
HttpsUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(scheme="https")]
CommitHash: TypeAlias = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{40}$")]
