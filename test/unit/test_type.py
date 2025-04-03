import pytest
from arn import Arn as ArnType

from launch_webhook_aws.type import validate_arn


class TestArnValidation:
    @pytest.mark.parametrize(
        "raw_arn",
        [
            "arn:aws:iam::123456789012:user/johndoe",
            "arn:aws:iam::123456789012:role/foo",
            "arn:aws:codebuild:us-east-1:123456789012:project/unit-test-project",
            "arn:aws:codepipeline:us-east-1:123456789012::unit-test-pipeline",
            "arn:aws:lambda:us-east-1:123456789012:unit-test-function",
        ],
    )
    def test_valid_arns(self, raw_arn: str):
        validated = validate_arn(raw_arn)
        assert isinstance(validated, ArnType)
        assert str(validated) == raw_arn

    @pytest.mark.parametrize(
        "raw_arn",
        [
            "arn:aws:::123456789012:user/johndoe",
            "arn:aws:iam!:role/foo",
            "arn:aws:codebuild:us-east",
        ],
    )
    def test_invalid_arns_rejected(self, raw_arn: str):
        with pytest.raises(Exception):
            validate_arn(raw_arn)
