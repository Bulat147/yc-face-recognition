import json
import logging
import os
import boto3

ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
QUEUE_NAME = os.getenv("QUEUE_NAME")

class QueueManager:

    def __init__(self):
        self.client = boto3.client(
            service_name="sqs",
            endpoint_url="https://message-queue.api.cloud.yandex.net",
            region_name="ru-central1",
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
        )
        self.queue_url = self.client.get_queue_url(QueueName=QUEUE_NAME).get("QueueUrl")

    def set_message(self, message):
        logging.info("Пытаемся отпрваить в очередь сообщение: " + str(message))

        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message)
        )

queue_manager = QueueManager()

def handle_event(event, context):
    event_details = event["messages"][0]["details"]
    bucket_name = event_details["bucket_id"]
    object_key = event_details["object_id"]

    logging.error("Object key " + object_key)

    queue_manager.set_message({
        "source_key": object_key
    })

