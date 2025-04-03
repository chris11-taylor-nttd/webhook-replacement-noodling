from contextlib import ExitStack as does_not_raise
from typing import Any

import pytest
from pydantic import ValidationError

from launch_webhook_aws.github.event import PullRequestClosed
from launch_webhook_aws.rule import Rule
from launch_webhook_aws.transform import TransformResult


class ExampleTransforms:
    @staticmethod
    def good(event: dict) -> dict: ...

    @staticmethod
    def also_good(event: PullRequestClosed) -> dict: ...

    @staticmethod
    def generic_dictionary_is_fine(event: dict[str, Any]) -> dict[str, Any]: ...

    @staticmethod
    def generic_arg_aliases_are_inspected(event: list[str]) -> dict: ...

    @staticmethod
    def generic_arg_returns_are_inspected(event: dict) -> list[str]: ...

    @staticmethod
    def return_using_transform_type(event: dict) -> TransformResult: ...

    @staticmethod
    def bad_arg_type(event: int) -> dict: ...

    @staticmethod
    def bad_return_type(event: dict) -> int: ...

    @staticmethod
    def bad_missing_arg(foo: dict) -> dict:
        return {}

    @staticmethod
    def bad_missing_arg_annotation(event) -> dict: ...

    @staticmethod
    def bad_missing_return_annotation(event: dict): ...

    @staticmethod
    def bad_wrong_return_annotation(event: dict) -> int: ...


@pytest.mark.parametrize(
    "transform, raises",
    [
        (ExampleTransforms.good, does_not_raise()),
        (ExampleTransforms.also_good, does_not_raise()),
        (ExampleTransforms.generic_dictionary_is_fine, does_not_raise()),
        (
            ExampleTransforms.generic_arg_aliases_are_inspected,
            pytest.raises(ValidationError),
        ),
        (
            ExampleTransforms.generic_arg_returns_are_inspected,
            pytest.raises(ValidationError),
        ),
        (ExampleTransforms.return_using_transform_type, does_not_raise()),
        (ExampleTransforms.bad_arg_type, pytest.raises(ValidationError)),
        (ExampleTransforms.bad_return_type, pytest.raises(ValidationError)),
        (ExampleTransforms.bad_missing_arg, pytest.raises(ValidationError)),
        (ExampleTransforms.bad_missing_arg_annotation, pytest.raises(ValidationError)),
        (
            ExampleTransforms.bad_missing_return_annotation,
            pytest.raises(ValidationError),
        ),
        (ExampleTransforms.bad_wrong_return_annotation, pytest.raises(ValidationError)),
        (["wrong type"], pytest.raises(ValidationError)),
    ],
)
def test_rule_transform_type_checking(transform, raises):
    with raises:
        Rule(
            source={
                "type": "github",
                "organization": "example-org",
                "events": ["pull_request.closed"],
            },
            transform=transform,
            destination={
                "type": "lambdafunction",
                "function_name": "example-function",
                "role_arn": "arn:aws:iam::123456789012:role/example-role",
            },
        )


@pytest.mark.parametrize(
    "target, raises",
    [
        ("test.example_library.sample_transform_function", does_not_raise()),
        (
            "test.example_library.NOT_A_CALLABLE",
            pytest.raises(
                ValidationError,
                match="Rule transform function test.example_library.NOT_A_CALLABLE is not callable",
            ),
        ),
        (
            "foo",
            pytest.raises(
                ValidationError, match="must be in the format 'module.function'"
            ),
        ),
        (
            "test.example_library.missing_transform_function",
            pytest.raises(
                ValidationError,
                match="Rule transform function missing_transform_function not found in module test.example_library",
            ),
        ),
        (
            "test.example_library_does_not_exist.sample_transform_function",
            pytest.raises(
                ValidationError,
                match="Rule transform module test.example_library_does_not_exist not found",
            ),
        ),
    ],
)
def test_transform_provided_as_string(target, raises):
    with raises:
        Rule(
            source={
                "type": "github",
                "organization": "example-org",
                "events": ["pull_request.closed"],
            },
            transform=target,
            destination={
                "type": "lambdafunction",
                "function_name": "example-function",
                "role_arn": "arn:aws:iam::123456789012:role/example-role",
            },
        )


def test_transform_string_not_importable(mocker):
    mocker.patch("importlib.import_module", side_effect=ImportError)
    with pytest.raises(
        ValidationError, match="Rule transform module foo.bar could not be imported!"
    ):
        Rule(
            source={
                "type": "github",
                "organization": "example-org",
                "events": ["pull_request.closed"],
            },
            transform="foo.bar.baz",
            destination={
                "type": "lambdafunction",
                "function_name": "example-function",
                "role_arn": "arn:aws:iam::123456789012:role/example-role",
            },
        )
