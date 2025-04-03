# launch-webhook-aws

## Overview

This framework allows for ingestion of webhook events originating from a given **Source**, the application of a user-defined **Transform** function, and the invocation of a **Destination** AWS resource with the results of the transformation through a construct known as a **Processor**. These source-transform-destination flows are called **Rules** and many can be associated with a single **Processor**, allow you to define a complex set of actions that can apply to incoming messages.

## Features

- Recognizes and classifies incoming webhook payloads from two webhook sources (GitHub and Bitbucket Server), extensible to cover events of any shape.
- Allows users to query and transform incoming event data, manipulating it as necessary before invoking an AWS resource
- Invokes common targets like AWS CodeBuild, AWS CodePipeline, and AWS Lambda Functions
- Fits into any AWS account strategy by supporting cross-account role assumption

## Rule Definitions

A **Rule** instructs the system how to handle events that meet certain criteria. A rule is composed of three parts:

- The **Source**, which defines what incoming events should be matched
- The **Transform**, an optional user-provided function to perform validation, transformation, or manipulation of data
- The **Destination**, which is invoked with the transformed data

### Source

The source specifies which event or events should be matched by the rule. The two sources in the initial release of the library are centered around SCM systems publishing events, but a Source could be any structured JSON that you can define with a pydantic model.

The Source has a few base fields which are present across all SCM configurations:

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `type` | string | "github" | Narrows the incoming event to a particular Source type. |
| `include_repositories` | List of regular expressions | ["^tf-.+$"] | This example would include any repository prefixed with 'tf-' in its name. If you do not define an `include_repositories` value, all repositories are considered included. |
| `exclude_repositories` | List of regular expressions | ["^.{20,}$"] | This example would exclude any repository with 20 or more characters in its name. |
| `verify_signature`    | boolean | true | When true, the sha256 signature associated with this event is validated against the `signature_secret`. |
| `signature_secret` | ARN | "arn:aws:secretsmanager:us-east-1:123456789012:secret:secret-name-here" | SecretsManager Secret ARN containing the shared secret for event signature validation. This is only required if `verify_signature` is true. |

Additional fields are available depending on the `type` you choose.

#### Github Source

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `organization` | string | "launchbynttdata" | This field is required. A rule cannot apply to more than a single organization at a time. |
| `events` | List of strings | ["pull_request.opened", "pull_request.synchronize"] | The example would only match PR events where the PR was being opened or updated. These event strings match the X-Github-Event header, and if there are sub-types, there will be a dot followed by the "action" field, like in the case of the pull_request events in the example. |

#### Recognized Github Events:

- [ping](https://docs.github.com/en/webhooks/webhook-events-and-payloads#ping)
- [push](https://docs.github.com/en/webhooks/webhook-events-and-payloads#push)
- [pull_request.opened](https://docs.github.com/en/webhooks/webhook-events-and-payloads?actionType=opened#pull_request)
- [pull_request.closed](https://docs.github.com/en/webhooks/webhook-events-and-payloads?actionType=closed#pull_request)
- [pull_request.synchronize](https://docs.github.com/en/webhooks/webhook-events-and-payloads?actionType=synchronize#pull_request)

#### Bitbucket Server Source

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `project_key` | string | "devops" | This field is required. A rule cannot apply to more than a single project_key at a time. |
| `events` | List of strings | ["pr:opened", "pr:from_ref_updated"] | The example would only match PR events where the PR was being opened or updated. These event strings match the "eventKey" field in the payload. |

#### Recognized Bitbucket Server Events:

- [repo:refs_changed](https://confluence.atlassian.com/bitbucketserver/event-payload-938025882.html#Eventpayload-repo-push)
- [pr:from_ref_updated](https://confluence.atlassian.com/bitbucketserver/event-payload-938025882.html#Eventpayload-sourcebranchupdated)
- [pr:opened](https://confluence.atlassian.com/bitbucketserver/event-payload-938025882.html#Eventpayload-pr-opened)
- [pr:merged](https://confluence.atlassian.com/bitbucketserver/event-payload-938025882.html#Eventpayload-pr-merged)

### Transform

A transform is a Python function that accepts the incoming event and returns a transformation that can be used by the **Destination** defined on the **Rule**.

A transform can be passed as a callable when instantiating a **Processor** object, but can also be provided as a reference to import; this framework will attempt to import and invoke the import path you specify.

A default transform is included with the framework that effectively performs a no-op on the incoming event. If not otherwise specified, the default transform will be used and no transformation will occur before invoking the destination. The default transform function is equivalent to:

```py
def default_transform(event: dict) -> dict:
    return event
```

This framework requires that the transform function passed to it meets the following criteria:

- The function takes a single parameter called 'event'
- The 'event' parameter is type-hinted with a dict or with a subtype of launch_webhook_aws.event.ScmEvent
- The function has its return annotated with dict or launch_webhook_aws.transform.TransformResult

If the transform function does not meet these criteria, the **Rule** will raise a ValidationError.

### Destination

A **Destination** represents a target which will be invoked upon successful matching and transformation of an event. One non-AWS destination (launch_webhook_aws.destination.NoDestination, "none") is included for testing purposes. All of the rest of the AWS Destinations share the following commmon fields:

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `type` | string | "codebuild" | Controls the type of Destination invoked. |
| `role_arn` | ARN | "arn:aws:iam::123456789012:role/my-role-name" | Role to be assumed prior to invoking the destination. This field is required; every invocation type (except NoDestination) requires a role to invoke. |
| `external_id` | string | "foo" | An optional External ID used with a Role's Trust Policy Conditions |
| `region`    | string | "us-east-1" | If provided, the client used to invoke will be created in this region. If not provided, the default region from the environment will be used. |
| `session_name` | string | "webhook_invocation" | A session name to include with the assumed role for tracking purposes. Defaults to 'launch_webhook_aws' if not specified. |


Beyond these common fields, each **Destination** has some ability to control its invocation parameters:

#### CodeBuild Destination

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `project_name` | str | "my-build-project" | Name of the build project to start. This field is required. |
| `environment_variables_override` | List of [environment variable objects](https://docs.aws.amazon.com/codebuild/latest/APIReference/API_EnvironmentVariable.html) | [{"name": "MY_VAR", "value": "foobar", "type": "PLAINTEXT"}] | Environment variables to be overridden from the Build Project's definition. |

#### CodePipeline Destination

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `pipeline_name` | str | "my-pipeline" | Name of the pipeline to start. This field is required. |
| `variables` | List of [pipeline variables](https://docs.aws.amazon.com/codepipeline/latest/APIReference/API_PipelineVariable.html) | [{"name": "MY_VAR", "value": "baz"}] | Pipeline variables to be passed when starting pipeline execution. |

#### Lambda Function Destination

| Field Name    | Type | Example Value | Notes |
| ------------- | ---- | ------------- | ----- |
| `function_name` | str | "my-function" | Name of the function to invoke. This field is required. |
| `payload` | None, bytes, string, list, or dict | "{\\"json\\": \\"payload\\"}" | Payload passed to the Lambda function. |

### Modifying Destination Behavior with Transforms

An AWS **Destination** defined in a **Rule** can have its destination-specific attributes overridden by a **Transform** function. Consider the following scenario where we want to gather some information from the event and pass it to the Lambda function we wish to invoke:

```py
# my_transforms.py
from launch_webhook_aws.github.event import Push
from launch_webhook_aws.transform import TransformResult

def user_extraction_transform(event: Push) -> TransformResult:
    return TransformResult(
        lambdafunction={
            "payload": {
                "commit_hash": event.after,
                "pushed_by": event.sender.login,
            }
        }
    )
```

We'll bind this transformation function in a rule like so:

```json
{
    "source": {
        "type": "github",
        "include_repositories": ["^my-repo$"],
        "organization": "example-org",
        "events": ["push"]
    },
    "transform": "my_transforms.user_extraction_transform",
    "destination": {
        "type": "lambdafunction",
        "role_arn": "arn:aws:iam::123456789012:role/role-to-assume",
        "function_name": "my-lambda-function",
        "payload": null
    }
}
```

Then, if a `push` event comes from the `my-repo` repository in the `example-org` organization, we'll extract the commit hash and the pusher from the payload and send it to our Lambda function's payload.

A **Destination** will only observe its overrides in a matching key, but this behavior enables a single transform function to provide overrides for any sort of destination. If we wanted to write a transform that would set the pusher's name as a pipeline variable or environment variable during a build in a similar manner and be useful regardless of which **Destination** type we choose, we might adjust our transform function as follows:

```py
# my_transforms.py
from launch_webhook_aws.github.event import Push
from launch_webhook_aws.transform import TransformResult

def user_extraction_transform(event: Push) -> TransformResult:
    return TransformResult(
        codebuild={
            "environment_variables_override": [
                {
                    "name": "SENDER",
                    "value": event.sender.login,
                    "type": "PLAINTEXT"
                }
            ]
        },
        codepipeline={
            "variables": [
                {
                    "name": "SENDER",
                    "value": event.sender.login
                }
            ]
        },
        lambdafunction={
            "payload": {
                "commit_hash": event.after,
                "pushed_by": event.sender.login,
            }
        }
    )
```

Of course, the actions taken in the transform are not limited to manipulating the received event data alone. You could query a database, use a remote API, or do anything else that the Lambda function running the **Processor** is entitled to do.



### Running tests

This repository comes with a default configuration for pytest.

To execute tests with the project's dependencies, issue the `uv run pytest` command. You may use the `pytest` command directly only if you activate a virtual environment.

After you have run `make configure` during the initial setup, two targets are available as shortcuts:

- `make test` will run `uvx run pytest`
- `make coverage` will run `make test`, generate coverage reports, and then open the HTML version of the coverage report in a browser for ease of use.

## Further reading

- [Set up VSCode](./docs/ide-vscode.md) for an improved development experience
- [Set up PyPI](./docs/pypi-configuration.md) for package distribution
- Learn how the [release workflows](./docs/release-workflow.md) operate
