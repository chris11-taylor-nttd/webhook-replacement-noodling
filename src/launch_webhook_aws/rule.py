from pydantic import BaseModel, ConfigDict, Field

from launch_webhook_aws.bitbucket_server.event import BitbucketServerEvent
from launch_webhook_aws.destination import DestinationSpec
from launch_webhook_aws.github.event import GithubEvent
from launch_webhook_aws.source import SourceSpec
from launch_webhook_aws.transform import RuleTransform, default_transform


class Rule(BaseModel):
    source_spec: SourceSpec
    transform: RuleTransform = Field(default=default_transform)
    destination_spec: DestinationSpec

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def match(self, event: GithubEvent | BitbucketServerEvent) -> bool:
        return self.source_spec.match(event)
