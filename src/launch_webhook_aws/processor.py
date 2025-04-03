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
        raw_event = SourceEvent(headers=headers, body=json.loads(body))
        source_event = raw_event.to_source_event()

        for rule in self.rules:
            if not rule.match(source_event.event):
                continue

            if rule.source.verify_signature:
                try:
                    if not self.verify_event_signature(
                        event_signature=source_event.event.signature_hash_sha256,
                        raw_event_body=body,
                        signature_secret=rule.source.signature_secret,
                    ):
                        continue
                except Exception:
                    logger.exception(
                        f"Failure while verifying event signature for {rule.source=}! This rule will not be processed further."
                    )
                    continue

            try:
                transform_signature = inspect.signature(rule.transform)
            except Exception:
                logger.exception(
                    "Failed to inspect transform function signature! This rule will not be processed further."
                )
                continue

            try:
                if transform_signature.parameters["event"].annotation is dict:
                    event = source_event.event.model_dump()
                else:
                    event = source_event.event
            except Exception:
                logger.exception(
                    "Failed to transform event into the expected type! This rule will not be processed further."
                )
                continue

            try:
                logger.debug("Transforming event...")
                transformed_event = rule.transform(event=event)
                logger.debug("Event transform complete, invoking destination")
            except Exception:
                logger.exception(
                    "Failed to transform event! This rule will not be processed further."
                )
                continue

            try:
                rule.destination.invoke(transformed_event=transformed_event)
                logger.debug("Invoked destination successfully")
            except Exception:
                logger.exception(
                    "Failed to invoke destination! Nothing further can be processed for this rule."
                )
                continue

    def verify_event_signature(
        self, event_signature: str, raw_event_body: str, signature_secret: Arn
    ) -> bool:
        try:
            secret = self.secretsmanager_client.get_secret_value(
                SecretId=str(signature_secret)
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
        if hmac.compare_digest(calculated_signature, event_signature):
            return True
        logger.error(
            f"Signature verification failed for {event_signature=}; {calculated_signature=}."
        )
        return False
