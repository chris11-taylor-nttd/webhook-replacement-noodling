import json
import logging
import pathlib
from contextlib import ExitStack as does_not_raise

from moto import mock_aws

from launch_webhook_aws.bitbucket_server.event import PullRequestMerged
from launch_webhook_aws.github.event import PullRequestClosed
from launch_webhook_aws.processor import EventProcessor


class TestProcessorInstantiation:
    def test_instantiates_with_no_rules(self):
        processor = EventProcessor(rules=[])
        assert processor.rules == []

    def test_instantiates_with_rules(self):
        def example_github_transform(event: PullRequestClosed) -> dict:
            return event

        def example_bitbucket_transform(event: PullRequestMerged) -> dict:
            return event

        rules = [
            {
                "source": {
                    "type": "github",
                    "organization": "example-org",
                    "events": ["pull_request.closed"],
                },
                "transform": example_github_transform,
                "destination": {
                    "type": "lambdafunction",
                    "role_arn": "arn:aws:iam::123456789012:role/example-role",
                    "function_name": "my-function",
                    "payload": "foo",
                },
            },
            {
                "source": {
                    "type": "bitbucket_server",
                    "project_key": "DSO",
                    "events": ["pr:merged"],
                },
                "transform": example_bitbucket_transform,
                "destination": {
                    "type": "lambdafunction",
                    "role_arn": "arn:aws:iam::123456789012:role/example-role",
                    "function_name": "my-function",
                    "payload": "foo",
                },
            },
        ]

        processor = EventProcessor(rules=rules)
        assert len(processor.rules) == 2

    def test_load_rules_from_json(self):
        contents = pathlib.Path("test/data/rules/example_rules.json").read_text()
        processor = EventProcessor(rules=json.loads(contents))
        assert len(processor.rules) == 2


@mock_aws
class TestProcessorRuleMatching:
    def test_match_happy_path(self, test_event):
        contents = pathlib.Path("test/data/rules/example_rules.json").read_text()
        processor = EventProcessor(rules=json.loads(contents))
        assert len(processor.rules) == 2
        headers, body = test_event("github", "pr_merged.json")

        with does_not_raise():
            processor.process_raw_event(headers=headers, body=body)

        headers, body = test_event("bitbucket_server", "pr_merged.json")

        with does_not_raise():
            processor.process_raw_event(headers=headers, body=body)

    def test_event_not_matched(self, test_event, caplog):
        contents = pathlib.Path("test/data/rules/example_rules.json").read_text()
        processor = EventProcessor(rules=json.loads(contents))
        assert len(processor.rules) == 2
        headers, body = test_event("github", "pr_open.json")

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                # The Github rule is set for pr_closed and should not match the pr_open event
                assert (
                    "Event action mismatch: pull_request.opened not in ['pull_request.closed']"
                    in caplog.text
                )
                # The Bitbucket rule should not match the Github event
                assert (
                    "Event source mismatch: <class 'launch_webhook_aws.github.event.PullRequestOpened'> is not a BitbucketServerEvent"
                    in caplog.text
                )

    # def test_one_event_matching_multiple_rules(
    #     self, test_event, caplog, mock_rules_from_file
    # ):
    #     rules = mock_rules_from_file("test/data/rules/multiple_matches.json")

    #     processor = EventProcessor(rules=rules)
    #     assert len(processor.rules) == 2
    #     headers, body = test_event("github", "pr_merged.json")

    #     print(rules)

    #     with caplog.at_level(logging.DEBUG):
    #         with does_not_raise():
    #             processor.process_raw_event(headers=headers, body=body)
    #             # The Github rule is set for pr_closed and should not match the pr_open event
    #             breakpoint()


@mock_aws
class TestProcessorEventSignatureValidation:
    def test_valid_signature(
        self,
        test_event,
        caplog,
        mock_secretsmanager_secret,
        mock_lambda_function,
        mock_assumable_role,
    ):
        contents = pathlib.Path(
            "test/data/rules/simple_lambdafunction.json"
        ).read_text()
        processor = EventProcessor(rules=json.loads(contents))
        processor.rules[0].source.verify_signature = True
        processor.rules[0].source.signature_secret = mock_secretsmanager_secret
        processor.rules[0].destination.role_arn = mock_assumable_role
        processor.rules[0].destination.function_name = mock_lambda_function
        headers, body = test_event("github", "pr_merged.json")

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                assert "Invoked destination successfully" in caplog.text

    def test_invalid_signature(self, test_event, caplog, mock_secretsmanager_secret):
        contents = pathlib.Path(
            "test/data/rules/simple_lambdafunction.json"
        ).read_text()
        processor = EventProcessor(rules=json.loads(contents))
        processor.rules[0].source.verify_signature = True
        processor.rules[0].source.signature_secret = mock_secretsmanager_secret
        headers, body = test_event("github", "pr_merged.json")
        headers["X-Hub-Signature-256"] = "invalid_signature"

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                assert (
                    "Signature verification failed for event_signature='invalid_signature'"
                    in caplog.text
                )

    def test_missing_signature_secret(self, test_event, caplog):
        contents = pathlib.Path(
            "test/data/rules/simple_lambdafunction.json"
        ).read_text()
        processor = EventProcessor(rules=json.loads(contents))
        processor.rules[0].source.verify_signature = True
        processor.rules[0].source.signature_secret = (
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:does-not-exist"
        )
        headers, body = test_event("github", "pr_merged.json")

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                assert "Failure while verifying event signature" in caplog.text
                assert "Secrets Manager can't find the specified secret" in caplog.text


class TestProcessorDestinationInvocation:
    def test_codebuild_invocation(
        self, caplog, test_event, mock_assumable_role, mock_codebuild_project
    ):
        contents = pathlib.Path("test/data/rules/simple_codebuild.json").read_text()
        processor = EventProcessor(rules=json.loads(contents))
        processor.rules[0].destination.role_arn = mock_assumable_role
        processor.rules[0].destination.project_name = mock_codebuild_project
        headers, body = test_event("github", "pr_merged.json")

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                assert "Invoked destination successfully" in caplog.text

    def test_codepipeline_invocation(
        self,
        caplog,
        test_event,
        mock_assumable_role,
        mock_codepipeline_pipeline,
        mocker,
    ):
        contents = pathlib.Path("test/data/rules/simple_codepipeline.json").read_text()
        processor = EventProcessor(rules=json.loads(contents))
        processor.rules[0].destination.role_arn = mock_assumable_role
        processor.rules[0].destination.pipeline_name = mock_codepipeline_pipeline
        headers, body = test_event("github", "pr_merged.json")

        # moto doesn't have full support for invoking a CodePipeline so this is mocked for now
        # TODO: look into https://docs.getmoto.org/en/latest/docs/services/patching_other_services.html
        processor.rules[0].destination = mocker.MagicMock()
        processor.rules[0].destination.invoke.return_value = {
            "pipelineExecutionId": "unit-test"
        }

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                assert "Invoked destination successfully" in caplog.text

    def test_lambda_invocation(
        self, caplog, test_event, mock_assumable_role, mock_lambda_function
    ):
        contents = pathlib.Path(
            "test/data/rules/simple_lambdafunction.json"
        ).read_text()
        processor = EventProcessor(rules=json.loads(contents))
        processor.rules[0].destination.role_arn = mock_assumable_role
        processor.rules[0].destination.function_name = mock_lambda_function
        headers, body = test_event("github", "pr_merged.json")

        with caplog.at_level(logging.DEBUG):
            with does_not_raise():
                processor.process_raw_event(headers=headers, body=body)
                assert "Invoked destination successfully" in caplog.text
