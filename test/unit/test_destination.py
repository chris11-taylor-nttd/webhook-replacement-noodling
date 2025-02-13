import logging
import sys
from contextlib import ExitStack as does_not_raise
from unittest.mock import MagicMock

import pytest
from types_boto3_codebuild import Client as CodeBuildClient
from types_boto3_codepipeline import Client as CodePipelineClient
from types_boto3_lambda import Client as LambdaClient
from types_boto3_sts import Client as StsClient

from launch_webhook_aws.destination import (
    AssumedRoleCredentials,
    CodeBuild,
    CodePipeline,
    LambdaFunction,
)


@pytest.mark.parametrize(
    "input, expected, raises",
    [
        (None, b"", does_not_raise()),
        ("string", b"string", does_not_raise()),
        (b"bytes", b"bytes", does_not_raise()),
        ({"foo": "bar"}, b'{"foo": "bar"}', does_not_raise()),
        ([1, 2, 3], b"[1, 2, 3]", does_not_raise()),
        (123, None, pytest.raises(ValueError)),
        (123.45, None, pytest.raises(ValueError)),
    ],
)
def test_convert_lambda_payload(input, expected, raises):
    with raises:
        LambdaFunction.convert_lambda_payload(input) == expected


def test_assumed_role_credentials_do_not_log(caplog, capsys):
    """
    Use of the SecretStr type in AssumedRoleCredentials should prevent the
    credentials from leaking into logs or stdout.
    """

    creds = AssumedRoleCredentials(
        AccessKeyId="hunter2",
        SecretAccessKey="hunter2",  # pragma: allowlist secret
        SessionToken="hunter2",
    )

    logger = logging.getLogger("unit-test")

    with caplog.at_level(logging.DEBUG):
        logger.debug(creds)
        logger.debug(creds.model_dump())

    print("Nothing sensitive here.")
    print(f"My creds are: {creds}")
    print(f"Don't look at my {creds}", file=sys.stderr)

    captured = capsys.readouterr()

    assert "Nothing sensitive here." in captured.out
    assert "hunter2" not in captured.out
    assert "hunter2" not in captured.err
    assert "hunter2" not in caplog.text


class MockStsClient(MagicMock):
    @property
    def __class__(self):
        return StsClient


class MockCodeBuildClient(MagicMock):
    @property
    def __class__(self):
        return CodeBuildClient


class MockCodePipelineClient(MagicMock):
    @property
    def __class__(self):
        return CodePipelineClient


class MockLambdaClient(MagicMock):
    @property
    def __class__(self):
        return LambdaClient


class TestInvokeOverridesClassValuesWithEventValues:
    def test_codebuild(self):
        sts_client = MockStsClient()
        service_client = MockCodeBuildClient()

        codebuild = CodeBuild(
            type="codebuild",
            role_arn="arn:aws:iam::123456789012:role/example-role",
            project_name="cool-project",
            environment_variables_override={"foo": "bar"},
            sts_client=sts_client,
            client=service_client,
        )

        codebuild.invoke(
            transformed_event={
                "codebuild": {
                    "project_name": "override-project",
                    "environment_variables_override": {"baz": "qux"},
                }
            }
        )

        service_client.start_build.assert_called_once_with(
            projectName="override-project", environmentVariablesOverride={"baz": "qux"}
        )

    def test_codepipeline(self):
        sts_client = MockStsClient()
        service_client = MockCodePipelineClient()

        codepipeline = CodePipeline(
            type="codepipeline",
            role_arn="arn:aws:iam::123456789012:role/example-role",
            pipeline_name="my-ci-pipeline",
            variables=[
                {
                    "name": "foo",
                    "value": "bar",
                }
            ],
            sts_client=sts_client,
            client=service_client,
        )

        codepipeline.invoke(
            transformed_event={
                "codepipeline": {
                    "pipeline_name": "override-pipeline",
                    "variables": [{"name": "baz", "value": "qux"}],
                }
            }
        )

        service_client.start_pipeline_execution.assert_called_once_with(
            name="override-pipeline",
            variables=[{"name": "baz", "value": "qux"}],
        )

    def test_lambda_function(self):
        sts_client = MockStsClient()
        service_client = MockLambdaClient()

        lambda_function = LambdaFunction(
            type="lambda",
            role_arn="arn:aws:iam::123456789012:role/example-role",
            function_name="my-lambda-function",
            payload="foo",
            sts_client=sts_client,
            client=service_client,
        )

        lambda_function.invoke(
            transformed_event={
                "lambda": {
                    "function_name": "override-lambda-function",
                    "payload": "bar",
                }
            }
        )

        service_client.invoke.assert_called_once_with(
            FunctionName="override-lambda-function", Payload=b"bar"
        )


class TestRoleAssumptionBehavior:
    def test_role_assumption_passes_model_values(self, mocker):
        mocked_boto3 = mocker.patch("launch_webhook_aws.destination.boto3")
        sts_client = MockStsClient()
        cred_response = {
            "Credentials": {
                "AccessKeyId": "foo",
                "SecretAccessKey": "bar",  # pragma: allowlist secret
                "SessionToken": "baz",
            }
        }
        sts_client.assume_role.return_value = cred_response

        lambda_function = LambdaFunction(
            type="lambda",
            role_arn="arn:aws:iam::123456789012:role/example-role",
            external_id="external-id",
            region="us-west-2",
            session_name="unit-test-session",
            function_name="my-lambda-function",
            payload="foo",
            sts_client=sts_client,
        )

        lambda_function.assume_role()

        sts_client.assume_role.assert_called_once_with(
            RoleArn="arn:aws:iam::123456789012:role/example-role",
            RoleSessionName="unit-test-session",
            ExternalId="external-id",
            DurationSeconds=900,
        )

        mocked_boto3.client.assert_called_once_with(
            "lambda",
            region_name="us-west-2",
            **AssumedRoleCredentials(**cred_response["Credentials"]).model_dump(),
        )

    def test_unset_region_is_not_passed(self, mocker):
        mocked_boto3 = mocker.patch("launch_webhook_aws.destination.boto3")
        sts_client = MockStsClient()
        cred_response = {
            "Credentials": {
                "AccessKeyId": "foo",
                "SecretAccessKey": "bar",  # pragma: allowlist secret
                "SessionToken": "baz",
            }
        }
        sts_client.assume_role.return_value = cred_response

        lambda_function = LambdaFunction(
            type="lambda",
            role_arn="arn:aws:iam::123456789012:role/example-role",
            external_id="external-id",
            session_name="unit-test-session",
            function_name="my-lambda-function",
            payload="foo",
            sts_client=sts_client,
        )

        lambda_function.assume_role()

        sts_client.assume_role.assert_called_once_with(
            RoleArn="arn:aws:iam::123456789012:role/example-role",
            RoleSessionName="unit-test-session",
            ExternalId="external-id",
            DurationSeconds=900,
        )

        mocked_boto3.client.assert_called_once_with(
            "lambda",
            **AssumedRoleCredentials(**cred_response["Credentials"]).model_dump(),
        )
