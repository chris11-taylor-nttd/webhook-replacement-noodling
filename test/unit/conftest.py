import hashlib
import hmac
import json
import os
import pathlib
import zipfile
from typing import Callable
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from types_boto3_codebuild import CodeBuildClient
from types_boto3_codepipeline import CodePipelineClient
from types_boto3_iam import IAMClient
from types_boto3_lambda import LambdaClient
from types_boto3_secretsmanager import SecretsManagerClient


@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"  # pragma: allowlist secret
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["MOTO_ACCOUNT_ID"] = "123456789012"


@pytest.fixture
def test_file():
    def _test_file(path: pathlib.Path) -> dict:
        return path.read_text()

    return _test_file


@pytest.fixture
def test_json(test_file):
    def _test_json(path: pathlib.Path) -> dict:
        return json.loads(test_file(path))

    return _test_json


def make_hmac_signature(
    body: str,
    secret: str,
    digest_function: Callable = hashlib.sha256,
    prefix: str | None = None,
) -> str:
    signature_hash = hmac.new(
        secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=digest_function,
    ).hexdigest()

    if prefix is None:
        if digest_function == hashlib.sha256:
            prefix = "sha256"
        elif digest_function == hashlib.sha1:
            prefix = "sha1"

    return f"{prefix}={signature_hash}"


@pytest.fixture
def test_event():
    def _test_event(event_source: str, file_name: str) -> tuple[dict, str]:
        event_header_file = pathlib.Path(
            f"test/data/headers/{event_source}/{file_name}"
        )
        event_headers = json.loads(event_header_file.read_text())
        event_body = pathlib.Path(
            f"test/data/events/{event_source}/{file_name}"
        ).read_text()

        if "X-Request-Id" in event_headers:
            event_headers["X-Hub-Signature"] = make_hmac_signature(
                body=event_body, secret="unit-test"  # pragma: allowlist secret
            )
        if "X-Github-Delivery" in event_headers:
            event_headers["X-Hub-Signature"] = make_hmac_signature(
                body=event_body,
                secret="unit-test",  # pragma: allowlist secret
                digest_function=hashlib.sha1,
            )
            event_headers["X-Hub-Signature-256"] = make_hmac_signature(
                body=event_body, secret="unit-test"  # pragma: allowlist secret
            )

        return event_headers, event_body

    return _test_event


@pytest.fixture
def mock_rules_from_file(test_json):
    def _mock_rules_from_file(file_path: str) -> list[dict]:
        rules = test_json(pathlib.Path(file_path))
        for rule in rules:
            rule["sts_client"] = MagicMock()
        return rules

    return _mock_rules_from_file


@pytest.fixture
def mock_assumable_role(aws_credentials):
    with mock_aws():
        iam_client: IAMClient = boto3.client("iam")
        result = iam_client.create_role(
            RoleName="unit-test-assumable-role",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                            "Action": "sts:AssumeRole",
                            "Condition": {
                                "StringEquals": {"sts:ExternalId": "unit-test"}
                            },
                        }
                    ],
                }
            ),
        )
        yield result["Role"]["Arn"]


@pytest.fixture
def mock_secretsmanager_secret(aws_credentials):
    with mock_aws():
        client: SecretsManagerClient = boto3.client("secretsmanager")
        result = client.create_secret(Name="unit-test-secret", SecretString="unit-test")
        yield result["ARN"]


@pytest.fixture
def build_zipped_lambda_code(tmp_path):
    function_zip = tmp_path.joinpath("function.zip")
    with zipfile.ZipFile(function_zip, "w") as zf:
        zf.writestr(
            "lambda_function.py",
            pathlib.Path("test/data/sample_function.py").read_text(),
        )
    yield function_zip.read_bytes()


@pytest.fixture
def mock_lambda_function(
    aws_credentials, mock_assumable_role, build_zipped_lambda_code
):
    with mock_aws():
        iam_client: IAMClient = boto3.client("iam")
        lambda_client: LambdaClient = boto3.client("lambda")
        iam_role = iam_client.create_role(
            RoleName="unit-test-lambda-role",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )

        result = lambda_client.create_function(
            FunctionName="unit-test-function",
            Code={"ZipFile": build_zipped_lambda_code},
            Handler="lambda_function.lambda_handler",
            Role=iam_role["Role"]["Arn"],
            Runtime="python3.13",
        )

        yield result["FunctionArn"]


@pytest.fixture
def mock_s3_bucket(aws_credentials):
    with mock_aws():
        s3_client = boto3.client("s3")
        bucket_name = "unit-test-bucket"
        s3_client.create_bucket(Bucket=bucket_name)
        yield bucket_name


@pytest.fixture
def mock_codepipeline_pipeline(aws_credentials, mock_assumable_role, mock_s3_bucket):
    with mock_aws():
        iam_client: IAMClient = boto3.client("iam")
        codepipeline_client: CodePipelineClient = boto3.client("codepipeline")

        iam_role = iam_client.create_role(
            RoleName="unit-test-codepipeline-role",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "codepipeline.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )

        result = codepipeline_client.create_pipeline(
            pipeline={
                "name": "unit-test-pipeline",
                "roleArn": iam_role["Role"]["Arn"],
                "artifactStore": {
                    "type": "S3",
                    "location": mock_s3_bucket,
                },
                "stages": [
                    {
                        "name": "Source",
                        "actions": [
                            {
                                "name": "SourceAction",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "configuration": {
                                    "S3Bucket": mock_s3_bucket,
                                    "S3ObjectKey": "source.zip",
                                },
                                "outputArtifacts": [{"name": "SourceOutput"}],
                                # Additional parameters can be added here
                            }
                        ],
                    },
                    # Pipelines must have >1 stage, so we add a second copy of the source stage
                    # to get around this limitation.
                    {
                        "name": "Source",
                        "actions": [
                            {
                                "name": "SourceAction",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "configuration": {
                                    "S3Bucket": mock_s3_bucket,
                                    "S3ObjectKey": "source.zip",
                                },
                                "outputArtifacts": [{"name": "SourceOutput"}],
                                # Additional parameters can be added here
                            }
                        ],
                    },
                ],
            }
        )

        yield result["pipeline"]["name"]


@pytest.fixture
def mock_codebuild_project(aws_credentials, mock_assumable_role):
    with mock_aws():
        iam_client: IAMClient = boto3.client("iam")
        codebuild_client: CodeBuildClient = boto3.client("codebuild")

        iam_role = iam_client.create_role(
            RoleName="unit-test-codebuild-role",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "codebuild.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )

        result = codebuild_client.create_project(
            name="unit-test-project",
            source={
                "type": "S3",
                "location": "s3://unit-test-bucket/source.zip",
            },
            serviceRole=iam_role["Role"]["Arn"],
            artifacts={
                "type": "NO_ARTIFACTS",
            },
            environment={
                "type": "LINUX_CONTAINER",
                "image": "aws/codebuild/standard:5.0",
                "computeType": "BUILD_GENERAL1_SMALL",
            },
        )

        yield result["project"]["name"]
