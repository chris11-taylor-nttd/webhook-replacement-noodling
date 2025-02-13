from typing import Callable, TypeAlias

from launch_webhook_aws.event import ScmEvent


def default_transform(event: dict) -> dict:
    return event


RuleTransform: TypeAlias = Callable[[dict | type[ScmEvent]], dict]
