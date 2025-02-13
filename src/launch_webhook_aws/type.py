from typing import Annotated, TypeAlias

from pydantic import HttpUrl, StringConstraints, UrlConstraints

SshUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["ssh"])]
HttpsUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"])]
GitUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["git"])]
CommitHash: TypeAlias = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{40}$")]
