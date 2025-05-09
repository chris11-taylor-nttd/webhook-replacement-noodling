import json
import pathlib

import pytest
from pydantic import ValidationError

from launch_webhook_aws.bitbucket_server import event as bitbucket_server_event
from launch_webhook_aws.github import event as github_event
from launch_webhook_aws.source import SourceEvent


class TestBitbucketServerEventsDiscriminate:
    def test_pr_merged(self, test_event):
        headers, body = test_event("bitbucket_server", "pr_merged.json")
        source_event = SourceEvent(headers=headers, body=json.loads(body))
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )
        assert isinstance(
            transformed_event.event, bitbucket_server_event.PullRequestMerged
        )

    def test_pr_open(self, test_event):
        headers, body = test_event("bitbucket_server", "pr_open.json")
        source_event = SourceEvent(headers=headers, body=json.loads(body))
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )
        assert isinstance(
            transformed_event.event, bitbucket_server_event.PullRequestOpened
        )

    def test_source_updated(self, test_event):
        headers, body = test_event("bitbucket_server", "pr_source_updated.json")
        source_event = SourceEvent(headers=headers, body=json.loads(body))
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )
        assert isinstance(
            transformed_event.event, bitbucket_server_event.SourceBranchUpdated
        )

    def test_push(self, test_event):
        headers, body = test_event("bitbucket_server", "push.json")
        source_event = SourceEvent(headers=headers, body=json.loads(body))
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )
        assert isinstance(transformed_event.event, bitbucket_server_event.Push)

    def test_bitbucket_cloud_headers_fails_to_discriminate(self, test_event):
        """
        Bitbucket cloud is not implemented, so we expect a failure if someone tries to use it.

        Whoever ends up implementing this source should remove this test.
        """
        headers, body = test_event("bitbucket_server", "pr_merged.json")
        headers["X-Hook-UUID"] = "only-bitbucket-cloud-has-this"

        with pytest.raises(ValidationError):
            # Bitbucket server is not implemented, so we expect a failure if someone tries to use it.
            # Whoever ends up implementing that source should remove this test.
            _ = SourceEvent(headers=headers, body=json.loads(body))


class TestGithubEventsDiscriminate:
    def test_ping(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "ping",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }

        body = test_json(pathlib.Path("test/data/events/github/ping.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(transformed_event, github_event.GithubWebhookEvent)
        assert isinstance(transformed_event.event, github_event.Ping)

    def test_push(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "push",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/github/push.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(transformed_event, github_event.GithubWebhookEvent)
        assert isinstance(transformed_event.event, github_event.Push)

    def test_pr_open(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "pull_request",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/github/pr_open.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(transformed_event, github_event.GithubWebhookEvent)
        assert isinstance(transformed_event.event, github_event.PullRequestOpened)

    def test_pr_merged(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "pull_request",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/github/pr_merged.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(transformed_event, github_event.GithubWebhookEvent)
        assert isinstance(transformed_event.event, github_event.PullRequestClosed)

    def test_pr_source_updated(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "pull_request",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/github/pr_source_updated.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(transformed_event, github_event.GithubWebhookEvent)
        assert isinstance(transformed_event.event, github_event.PullRequestSynchronize)


def test_unrecognized_headers_fail_source_event_discrimination():
    headers = {
        "Y-Request-Id": "unit-test",
        "Y-Event-Key": "pr:merged",
        "Y-Hub-Signature": "unit-test",
        "Y-Hook-UUID": "only-bitbucket-cloud-has-this",
    }
    body = {}
    with pytest.raises(ValueError, match="Failed to discriminate header source"):
        _ = SourceEvent(headers=headers, body=body)
