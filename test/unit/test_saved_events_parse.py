import pathlib

from launch_webhook_aws.bitbucket_server import event as bitbucket_server_event
from launch_webhook_aws.github import event as github_event


class TestBitbucketServerEventsParse:
    def test_pr_merged(self, test_json):
        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:merged",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(
            pathlib.Path("test/data/events/bitbucket_server/pr_merged.json")
        )
        event = bitbucket_server_event.PullRequestMerged(headers=headers, **body)
        print(event)

    def test_pr_open(self, test_json):
        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:opened",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/pr_open.json"))
        event = bitbucket_server_event.PullRequestOpened(headers=headers, **body)
        print(event)

    def test_source_updated(self, test_json):
        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "pr:from_ref_updated",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(
            pathlib.Path("test/data/events/bitbucket_server/pr_source_updated.json")
        )
        event = bitbucket_server_event.SourceBranchUpdated(headers=headers, **body)
        print(event)

    def test_push(self, test_json):
        headers = {
            "X-Request-Id": "unit-test",
            "X-Event-Key": "repo:refs_changed",
            "X-Hub-Signature": "unit-test",
        }
        body = test_json(pathlib.Path("test/data/events/bitbucket_server/push.json"))
        event = bitbucket_server_event.Push(headers=headers, **body)
        print(event)


class TestGithubEventsParse:
    def test_ping(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "ping",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }

        body = test_json(pathlib.Path("test/data/events/github/ping.json"))
        event = github_event.Ping(headers=headers, **body)
        print(event)

    def test_push(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "push",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }

        body = test_json(pathlib.Path("test/data/events/github/push.json"))
        event = github_event.Push(headers=headers, **body)
        print(event)

    def test_pull_request_opened(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "pull_request",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }

        body = test_json(pathlib.Path("test/data/events/github/pr_open.json"))
        event = github_event.PullRequestOpened(headers=headers, **body)
        print(event)

    def test_pull_request_merged(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "pull_request",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }

        body = test_json(pathlib.Path("test/data/events/github/pr_merged.json"))
        event = github_event.PullRequestClosed(headers=headers, **body)
        print(event)

    def test_pull_request_source_updated(self, test_json):
        headers = {
            "X-Github-Hook-Id": "unit-test",
            "X-Github-Event": "pull_request",
            "X-Github-Delivery": "unit-test",
            "X-Hub-Signature": "unit-test",
            "X-Hub-Signature-256": "unit-test",
        }

        body = test_json(pathlib.Path("test/data/events/github/pr_source_updated.json"))
        event = github_event.PullRequestSynchronize(headers=headers, **body)
        print(event)
