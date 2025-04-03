from typing import Callable, Literal, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from launch_webhook_aws.event import ScmEvent


def default_transform(event: dict) -> dict:
    return event


class CodeBuildVariable(BaseModel):
    name: str
    value: str
    type: Literal["PLAINTEXT", "PARAMETER_STORE", "SECRETS_MANAGER"] = "PLAINTEXT"


class CodeBuildResult(BaseModel):
    project_name: str
    environment_variables_override: Sequence[CodeBuildVariable] = []
    client: Callable | None = None


class CodePipelineVariable(BaseModel):
    name: str
    value: str


class CodePipelineResult(BaseModel):
    pipeline_name: str
    variables: list[CodePipelineVariable] = Field(default_factory=list)
    client: Callable | None = None


class LambdaFunctionResult(BaseModel):
    function_name: str
    payload: None | bytes | str | list | dict = Field(default=None)
    client: Callable | None = None


class TransformResult(BaseModel):
    codebuild: CodeBuildResult | None = None
    codepipeline: dict | None = None
    lambdafunction: dict | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


RuleTransform: TypeAlias = (
    Callable[[dict | type[ScmEvent]], dict | TransformResult] | str
)
