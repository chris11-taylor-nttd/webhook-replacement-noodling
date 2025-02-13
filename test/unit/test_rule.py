from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from launch_webhook_aws.github.event import PullRequestClosed
from launch_webhook_aws.rule import Rule


class ExampleTransforms:
    @staticmethod
    def good(event: dict) -> dict:
        return event

    @staticmethod
    def also_good(event: PullRequestClosed) -> dict:
        return event

    @staticmethod
    def bad_arg_type(event: int) -> dict:
        return event

    @staticmethod
    def bad_return_type(event: dict) -> int:
        return event

    @staticmethod
    def bad_missing_arg(foo: dict) -> dict:
        return {}

    @staticmethod
    def bad_missing_arg_annotation(event) -> dict:
        return event

    @staticmethod
    def bad_missing_return_annotation(event: dict):
        return event

    @staticmethod
    def bad_wrong_return_annotation(event: dict) -> int:
        return event


@pytest.mark.parametrize(
    "transform, raises",
    [
        (ExampleTransforms.good, does_not_raise()),
        (ExampleTransforms.also_good, does_not_raise()),
        (ExampleTransforms.bad_arg_type, pytest.raises(ValidationError)),
        (ExampleTransforms.bad_return_type, pytest.raises(ValidationError)),
        (ExampleTransforms.bad_missing_arg, pytest.raises(ValidationError)),
        (ExampleTransforms.bad_missing_arg_annotation, pytest.raises(ValidationError)),
        (
            ExampleTransforms.bad_missing_return_annotation,
            pytest.raises(ValidationError),
        ),
        (ExampleTransforms.bad_wrong_return_annotation, pytest.raises(ValidationError)),
    ],
)
def test_rule_transform_type_checking(transform, raises):
    with raises:
        Rule(
            source_spec={
                "type": "github",
                "organization": "example-org",
                "events": ["pull_request.closed"],
            },
            transform=transform,
            destination_spec={
                "type": "lambda",
                "function_name": "example-function",
                "role_arn": "arn:aws:iam::123456789012:role/example-role",
            },
        )
