import json
import logging
import os
from abc import abstractmethod
from typing import Annotated, Literal, TypeAlias, Union

import boto3
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer
from types_boto3_codebuild import Client as CodeBuildClient
from types_boto3_codepipeline import Client as CodePipelineClient
from types_boto3_lambda import Client as LambdaClient
from types_boto3_sts import Client as StsClient

from .transform import CodeBuildVariable

ASSUMED_ROLE_SESSION_DURATION_SECONDS = int(
    os.environ.get("ASSUMED_ROLE_SESSION_DURATION_SECONDS", 900)
)


class AssumedRoleCredentials(BaseModel):
    aws_access_key_id: SecretStr = Field(alias="AccessKeyId")
    aws_secret_access_key: SecretStr = Field(alias="SecretAccessKey")
    aws_session_token: SecretStr = Field(alias="SessionToken")

    @field_serializer(
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        when_used="always",
    )
    def serialize_secret(self, value: SecretStr) -> str:
        return value.get_secret_value()


class Destination(BaseModel):
    @abstractmethod
    def invoke(self, transformed_event: dict[str, str]) -> None: ...


class NoDestination(Destination):
    type: Literal["none"]

    model_config = ConfigDict(extra="ignore")

    def invoke(self, transformed_event: dict[str, str]) -> None:
        self.logger.debug("No destination configured. No action taken.")


class AwsDestination(Destination):
    role_arn: str
    external_id: str | None = Field(default=None)
    region: str | None = Field(default=None)
    session_name: str = Field(default=os.getenv("SESSION_NAME", "launch_webhook_aws"))
    sts_client: StsClient = Field(default_factory=lambda: boto3.client("sts"))
    logger: logging.Logger = Field(
        default_factory=lambda: logging.getLogger("destination")
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def assume_role(self) -> None:
        if not getattr(self, "client"):
            external_id = {"ExternalId": self.external_id} if self.external_id else {}
            assumed_role = self.sts_client.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName=self.session_name,
                DurationSeconds=ASSUMED_ROLE_SESSION_DURATION_SECONDS,
                **external_id,
            )
            creds = AssumedRoleCredentials(**assumed_role["Credentials"])
            client_type = self.type
            if client_type == "lambdafunction":
                client_type = "lambda"

            if self.region:
                self.client = boto3.client(
                    client_type, region_name=self.region, **creds.model_dump()
                )
            else:
                self.client = boto3.client(client_type, **creds.model_dump())
            self.logger.debug(f"Assumed role {self.role_arn}")


class CodeBuild(AwsDestination):
    type: Literal["codebuild"]
    project_name: str
    environment_variables_override: list[CodeBuildVariable] = Field(
        default_factory=list
    )
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
        if len(variables):
            self.client.start_pipeline_execution(
                name=pipeline_name, variables=variables
            )
        else:
            self.client.start_pipeline_execution(name=pipeline_name)


class LambdaFunction(AwsDestination):
    type: Literal["lambdafunction"]
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
    Union[NoDestination, CodeBuild, CodePipeline, LambdaFunction],
    Field(discriminator="type"),
]
