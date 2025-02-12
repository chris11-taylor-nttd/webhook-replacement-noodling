import hashlib
import hmac
import inspect
import json
import logging
from typing import Callable

import boto3
from arn import Arn
from pydantic import BaseModel, Field

from launch_webhook_aws.bitbucket_server.event import ParsedBitbucketServerEvent
from launch_webhook_aws.github.event import ParsedGithubEvent
from launch_webhook_aws.rule import Rule

logger = logging.getLogger("processor")
logger.setLevel(logging.DEBUG)


class WebhookEvent(BaseModel):
    http_headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers received with the incoming request.",
    )
    body: str = Field(..., description="Raw body of the incoming request.")


class EventProcessor(BaseModel):
    rules: list[Rule]
    secretsmanager_client: Callable = Field(
        default_factory=lambda: boto3.client("secretsmanager")
    )

    def process_raw_event(self, headers: dict[str, str], body: str) -> None:
        event_body = json.loads(self.body)

        if "X-Github-Event" in self.http_headers:
            if "action" not in event_body:
                event_body["action"] = self.http_headers["X-Github-Event"]
            else:
                event_body["action"] = ".".join(
                    [self.http_headers["X-Github-Event"], event_body["action"]]
                )
            # Github header is present, need to determine if it's enterprise or not
            if "X-Github-Enterprise-Version" in self.http_headers:
                raise NotImplementedError("GitHub Enterprise is not yet supported.")
            return ParsedGithubEvent(**self.model_dump(), event=event_body)
        elif "X-Event-Key" in self.http_headers:
            # Bitbucket header is present, need to determine if it's server or not
            if "X-Hook-UUID" in self.http_headers:
                raise NotImplementedError("Bitbucket Cloud is not yet supported.")
            return ParsedBitbucketServerEvent(**self.model_dump(), event=event_body)
        raise NotImplementedError("This event is not yet implemented.")

    def verify_event_signature(
        self, headers: dict[str, str], body: str, signature_secret: Arn
    ) -> bool:
        try:
            secret = self.secretsmanager_client.get_secret_value(
                SecretId=signature_secret
            )["SecretString"]
        except Exception:
            logger.exception(
                f"Failed to retrieve {signature_secret=} from Secrets Manager!"
            )
            raise

        envelope.http_headers.get("X-Hub-Signature")

        hash_object = hmac.new(
            secret.encode("utf-8"),
            msg=envelope.body_raw.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        calculated_signature = f"sha256={hash_object.hexdigest()}"
        print(f"{calculated_signature=}, {envelope.signature_hash=}")
        if hmac.compare_digest(calculated_signature, envelope.signature_hash):
            return True
        logger.error(
            f"Signature verification failed for {envelope.signature_hash=}; {calculated_signature=}."
        )
        return False

    def process_event(self, envelope: ParsedEvent) -> dict:
        for rule in self.rules:
            if rule.match(envelope.event):
                if rule.source_spec.verify_signature:
                    if not self.verify_event_signature(
                        envelope=envelope,
                        signature_secret=rule.source_spec.signature_secret,
                    ):
                        raise RuntimeError(
                            "Signature verification failed. This event will not be processed."
                        )
                transform_signature = inspect.signature(rule.transform)
                if transform_signature.parameters["event"].annotation is dict:
                    event = envelope.event.model_dump()
                else:
                    event = envelope.event
                logger.debug("Transforming event...")
                transformed_event = rule.transform(event=event)
                logger.debug("Event transform complete, invoking destination")
                rule.destination_spec.invoke(transformed_event=transformed_event)
