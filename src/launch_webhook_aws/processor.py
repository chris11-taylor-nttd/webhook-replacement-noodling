import hashlib
import hmac
import inspect
import json
import logging
from typing import Callable

import boto3
from arn import Arn
from pydantic import BaseModel, Field

from launch_webhook_aws.rule import Rule
from launch_webhook_aws.source import SourceEvent

logger = logging.getLogger("processor")
logger.setLevel(logging.DEBUG)


class EventProcessor(BaseModel):
    rules: list[Rule]
    secretsmanager_client: Callable = Field(
        default_factory=lambda: boto3.client("secretsmanager")
    )

    def process_raw_event(self, headers: dict[str, str], body: str) -> None:
        body = json.loads(body)
        raw_event = SourceEvent(headers=headers, body=body)
        source_event = raw_event.to_source_event()

        for rule in self.rules:
            if rule.match(source_event.event):
                if rule.source_spec.verify_signature:
                    if not self.verify_event_signature(
                        event_signature=source_event.event.signature_hash_sha256,
                        raw_event_body=body,
                        signature_secret=rule.source_spec.signature_secret,
                    ):
                        raise RuntimeError(
                            "Signature verification failed. This event will not be processed."
                        )
                transform_signature = inspect.signature(rule.transform)
                if transform_signature.parameters["event"].annotation is dict:
                    event = source_event.event.model_dump()
                else:
                    event = source_event.event
                logger.debug("Transforming event...")
                transformed_event = rule.transform(event=event)
                logger.debug("Event transform complete, invoking destination")
                rule.destination_spec.invoke(transformed_event=transformed_event)

    def verify_event_signature(
        self, event_signature: str, raw_event_body: str, signature_secret: Arn
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

        hash_object = hmac.new(
            secret.encode("utf-8"),
            msg=raw_event_body.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        calculated_signature = f"sha256={hash_object.hexdigest()}"
        print(f"{calculated_signature=}, {event_signature=}")
        if hmac.compare_digest(calculated_signature, event_signature):
            return True
        logger.error(
            f"Signature verification failed for {event_signature=}; {calculated_signature=}."
        )
        return False
