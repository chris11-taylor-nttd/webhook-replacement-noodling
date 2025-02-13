from typing import Annotated, Any, TypeAlias

import arn
from pydantic import (
    BeforeValidator,
    HttpUrl,
    StringConstraints,
    UrlConstraints,
)

SshUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["ssh"])]
HttpsUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"])]
GitUrl: TypeAlias = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["git"])]
CommitHash: TypeAlias = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{40}$")]


def validate_arn(v: Any) -> arn.Arn:
    return arn.Arn(v)


Arn: TypeAlias = Annotated[arn.Arn, BeforeValidator(validate_arn)]
