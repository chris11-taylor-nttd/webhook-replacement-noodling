import json
import os
from abc import abstractmethod
from typing import Annotated, Literal, TypeAlias, Union

import boto3
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from types_boto3_codebuild import Client as CodeBuildClient
from types_boto3_codepipeline import Client as CodePipelineClient
from types_boto3_lambda import Client as LambdaClient
from types_boto3_sts import Client as StsClient

ASSUMED_ROLE_SESSION_DURATION_SECONDS = int(
    os.environ.get("ASSUMED_ROLE_SESSION_DURATION_SECONDS", 900)
)


class AssumedRoleCredentials(BaseModel):
    aws_access_key_id: SecretStr = Field(alias="AccessKeyId")
    aws_secret_access_key: SecretStr = Field(alias="SecretAccessKey")
    session_token: SecretStr = Field(alias="SessionToken")


class AwsDestination(BaseModel):
    role_arn: str
    external_id: str | None = Field(default=None)
    region: str | None = Field(default=None)
    session_name: str = Field(default=os.getenv("SESSION_NAME", "launch_webhook_aws"))
    sts_client: StsClient = Field(default_factory=lambda: boto3.client("sts"))

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def invoke(self, transformed_event: dict[str, str]) -> None: ...

    def assume_role(self) -> None:
        if not getattr(self, "client"):
            assumed_role = self.sts_client.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName=self.session_name,
                ExternalId=self.external_id,
                DurationSeconds=ASSUMED_ROLE_SESSION_DURATION_SECONDS,
            )
            creds = AssumedRoleCredentials(**assumed_role["Credentials"])
            if self.region:
                self.client = boto3.client(
                    self.type, region_name=self.region, **creds.model_dump()
                )
            else:
                self.client = boto3.client(self.type, **creds.model_dump())


class CodeBuild(AwsDestination):
    type: Literal["codebuild"]
    project_name: str
    environment_variables_override: dict[str, str] = Field(default_factory=dict)
    client: CodeBuildClient | None = Field(default=None)

    def invoke(self, transformed_event: dict[str, str]) -> None:
        self.assume_role()

        project_name = transformed_event.get(self.type, {}).get(
            "project_name", self.project_name
        )
        environment_variables_override = transformed_event.get(self.type, {}).get(
            "environment_variables_override", self.environment_variables_override
        )

        self.client.start_build(
            projectName=project_name,
            environmentVariablesOverride=environment_variables_override,
        )


class CodePipeline(AwsDestination):
    type: Literal["codepipeline"]
    pipeline_name: str
    variables: list[dict[str, str]] = Field(default_factory=list)
    client: CodePipelineClient | None = Field(default=None)

    def invoke(self, transformed_event: dict[str, str]) -> None:
        self.assume_role()

        pipeline_name = transformed_event.get(self.type, {}).get(
            "pipeline_name", self.pipeline_name
        )
        variables = transformed_event.get(self.type, {}).get(
            "variables", self.variables
        )

        self.client.start_pipeline_execution(name=pipeline_name, variables=variables)


class LambdaFunction(AwsDestination):
    type: Literal["lambda"]
    function_name: str
    payload: None | bytes | str | list | dict = Field(default=None)
    client: LambdaClient | None = Field(default=None)

    @staticmethod
    def convert_lambda_payload(payload: None | bytes | str | list | dict) -> bytes:
        if payload is None:
            return b""
        elif isinstance(payload, bytes):
            return payload
        elif isinstance(payload, str):
            return payload.encode("utf-8")
        elif isinstance(payload, list) or isinstance(payload, dict):
            return json.dumps(payload).encode("utf-8")
        raise ValueError(f"Unsupported type for Lambda payload: {type(payload)}")

    def invoke(self, transformed_event: dict[str, str]) -> None:
        self.assume_role()

        function_name = transformed_event.get(self.type, {}).get(
            "function_name", self.function_name
        )
        payload = LambdaFunction.convert_lambda_payload(
            payload=transformed_event.get(self.type, {}).get("payload", self.payload)
        )

        self.client.invoke(FunctionName=function_name, Payload=payload)


DestinationSpec: TypeAlias = Annotated[
    Union[CodeBuild, CodePipeline, LambdaFunction],
    Field(discriminator="type"),
]
