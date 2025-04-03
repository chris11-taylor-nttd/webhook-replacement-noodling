import logging
import pathlib
import re
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from launch_webhook_aws.bitbucket_server import event as bitbucket_server_event
from launch_webhook_aws.github import event as github_server_event
from launch_webhook_aws.source import (
    BitbucketServerSource,
    GithubSource,
    SourceEvent,
    validate_patterns,
)


@pytest.mark.parametrize(
    "pattern, pattern_raises",
    [
        (None, does_not_raise()),
        ("^.*$", does_not_raise()),
        (re.compile("^.*$"), does_not_raise()),
        (1, pytest.raises(ValueError)),
        ([1, 2, 3], pytest.raises(ValueError)),
        ({"foo": "bar"}, pytest.raises(ValueError)),
        (lambda x: x, pytest.raises(ValueError)),
    ],
)
def test_pattern_validation(pattern, pattern_raises):
    with pattern_raises:
        validate_patterns(pattern)


def test_source_rejects_missing_secret_arn():
    with pytest.raises(ValidationError):
        BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            verify_signature=True,
        )


class TestBitbucketServerSourceMatching:
    def test_project_key_only(self, test_json):
        good_source = BitbucketServerSource(
            type="bitbucket_server", project_key="DSO", events=["pr:opened"]
        )
        bad_source = BitbucketServerSource(
            type="bitbucket_server", project_key="foo", events=["pr:opened"]
        )

        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:opened",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/pr_open.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )

        assert good_source.match(event=transformed_event.event)
        assert not bad_source.match(event=transformed_event)

    def test_include_pattern(self, test_json):
        good_source = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{2}$"],
        )

        bad_source = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{3}$"],
        )

        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:opened",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/pr_open.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )

        assert good_source.match(event=transformed_event.event)
        assert not bad_source.match(event=transformed_event)

    def test_exclude_pattern(self, test_json):
        good_source = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{2}$"],
        )

        bad_source = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{3}$"],
        )

        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:opened",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/pr_open.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )

        assert good_source.match(event=transformed_event.event)
        assert not bad_source.match(event=transformed_event)

    def test_excluded_and_included_pattern(self, test_json):
        """
        If a repository matches both an include and an exclude pattern, the exclude pattern should take precedence.
        """
        both_patterns = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{2}$"],
            exclude_repositories=["^test.+$"],
        )

        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:opened",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/pr_open.json"))
        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()
        assert isinstance(
            transformed_event, bitbucket_server_event.BitbucketServerWebhookEvent
        )

        assert not both_patterns.match(event=transformed_event)

    def test_logging(self, test_json, caplog):
        event_source_mismatch = GithubSource(
            type="github", organization="DSO", events=["pull_request.opened"]
        )
        event_key_mismatch = BitbucketServerSource(
            type="bitbucket_server", project_key="DSO", events=["pr:merged"]
        )
        project_key_mismatch = BitbucketServerSource(
            type="bitbucket_server", project_key="foo", events=["pr:opened"]
        )
        project_key_only = BitbucketServerSource(
            type="bitbucket_server", project_key="DSO", events=["pr:opened"]
        )
        include_match = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{2}$"],
        )
        include_nomatch = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{3}$"],
        )
        exclude_match = BitbucketServerSource(
            type="bitbucket_server",
            project_key="DSO",
            events=["pr:opened"],
            include_repositories=["^test-ap{2}$"],
            exclude_repositories=["^test.+$"],
        )

        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:opened",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/pr_open.json"))

        source_event = SourceEvent(headers=headers, body=body)
        transformed_event = source_event.to_source_event()

        with caplog.at_level(logging.DEBUG):
            assert not event_source_mismatch.match(event=transformed_event.event)
            assert "Event source mismatch" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not event_key_mismatch.match(event=transformed_event.event)
            assert "Event action mismatch" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not project_key_mismatch.match(event=transformed_event.event)
            assert "Project key mismatch" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert project_key_only.match(event=transformed_event.event)
            assert "No source include patterns defined" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert include_match.match(event=transformed_event.event)
            assert "matched source include pattern" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not include_nomatch.match(event=transformed_event.event)
            assert "did not match source include pattern" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not exclude_match.match(event=transformed_event.event)
            assert "matched source exclude pattern" in caplog.text
            caplog.clear()


class TestGithubServerSourceMatching:
    def test_organization_only(self, test_json):
        good_source = GithubSource(
            type="github", organization="example-org", events=["pull_request.opened"]
        )
        bad_source = GithubSource(
            type="github", organization="foo", events=["pull_request.opened"]
        )

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
        assert isinstance(transformed_event, github_server_event.GithubWebhookEvent)

        assert good_source.match(event=transformed_event.event)
        assert not bad_source.match(event=transformed_event)

    def test_include_pattern(self, test_json):
        good_source = GithubSource(
            type="github",
            organization="example-org",
            events=["pull_request.opened"],
            include_repositories=[r"^example-\w{4}$"],
        )
        bad_source = GithubSource(
            type="github",
            organization="foo",
            events=["pull_request.opened"],
            include_repositories=[r"^example-\w{5}$"],
        )

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
        assert isinstance(transformed_event, github_server_event.GithubWebhookEvent)

        assert good_source.match(event=transformed_event.event)
        assert not bad_source.match(event=transformed_event)

    def test_exclude_pattern(self, test_json):
        good_source = GithubSource(
            type="github",
            organization="example-org",
            events=["pull_request.opened"],
            exclude_repositories=[r"^example-\w{5}$"],
        )
        bad_source = GithubSource(
            type="github",
            organization="foo",
            events=["pull_request.opened"],
            exclude_repositories=[r"^example-\w{4}$"],
        )

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
        assert isinstance(transformed_event, github_server_event.GithubWebhookEvent)

        assert good_source.match(event=transformed_event.event)
        assert not bad_source.match(event=transformed_event)

    def test_excluded_and_included_pattern(self, test_json):
        both_patterns = GithubSource(
            type="github",
            organization="example-org",
            events=["pull_request.opened"],
            include_repositories=[r"^example-\w{4}$"],
            exclude_repositories=[r"^example-\w{5}$"],
        )
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
        assert isinstance(transformed_event, github_server_event.GithubWebhookEvent)

        assert both_patterns.match(event=transformed_event.event)

    def test_logging(self, test_json, caplog):
        event_source_mismatch = BitbucketServerSource(
            type="bitbucket_server", project_key="DSO", events=["pr:merged"]
        )
        event_key_mismatch = GithubSource(
            type="github", organization="example-org", events=["push"]
        )
        organization_mismatch = GithubSource(
            type="github", organization="foo", events=["pull_request.opened"]
        )
        organization_only = GithubSource(
            type="github", organization="example-org", events=["pull_request.opened"]
        )
        include_match = GithubSource(
            type="github",
            organization="example-org",
            events=["pull_request.opened"],
            include_repositories=[r"^example-\w{4}$"],
        )
        include_nomatch = GithubSource(
            type="github",
            organization="example-org",
            events=["pull_request.opened"],
            include_repositories=[r"^example-\w{5}$"],
        )
        exclude_match = GithubSource(
            type="github",
            organization="example-org",
            events=["pull_request.opened"],
            include_repositories=[r"^example-repo$"],
            exclude_repositories=[r"^example.+$"],
        )

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

        with caplog.at_level(logging.DEBUG):
            assert not event_source_mismatch.match(event=transformed_event.event)
            assert "Event source mismatch" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not event_key_mismatch.match(event=transformed_event.event)
            assert "Event action mismatch" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not organization_mismatch.match(event=transformed_event.event)
            assert "Organization mismatch" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert organization_only.match(event=transformed_event.event)
            assert "No source repository include patterns defined" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert include_match.match(event=transformed_event.event)
            assert "matched source include pattern" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not include_nomatch.match(event=transformed_event.event)
            assert "did not match source include pattern" in caplog.text
            caplog.clear()

        with caplog.at_level(logging.DEBUG):
            assert not exclude_match.match(event=transformed_event.event)
            assert "matched source exclude pattern" in caplog.text
            caplog.clear()
