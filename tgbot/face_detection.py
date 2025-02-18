import json
import logging
import os
from email import message_from_bytes

import boto3
import cv2
import numpy as np

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

class StorageManager:
    def __init__(self):
        self.client = boto3.client(
            service_name="s3",
            aws_access_key_id=os.getenv("ACCESS_KEY"),
            aws_secret_access_key=os.getenv("SECRET_KEY"),
            region_name="ru-central1",
            endpoint_url="https://storage.yandexcloud.net",
        )

    def get_object(self, bucket, object_key) -> bytes:
        response = self.client.get_object(Bucket=bucket, Key=object_key)
        return response["Body"].read()

queue_manager = QueueManager()
storage_manager = StorageManager()

def detect_faces(data):
    # Получаем изображение из байтов
    np_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    # Готовая модель для обнаружения лиц
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    # Преобразуем в серый для облегчения распознавания лиц
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Само распознавание
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return [list(map(int, face)) for face in faces]

def handle_event(event, context):
    event_details = event["messages"][0]["details"]
    bucket_name = event_details["bucket_id"]
    object_key = event_details["object_id"]

    logging.info("Object key " + object_key)

    data = storage_manager.get_object(bucket_name, object_key)

    rectangle_arr = detect_faces(data)

    for face_rectangle in rectangle_arr:
        message = {
            "source_key": object_key,
            "face_rectangle": face_rectangle
        }

        logging.error(message)

        queue_manager.set_message(message)

    return {
        "statusCode": 200,
        "body": None
    }



