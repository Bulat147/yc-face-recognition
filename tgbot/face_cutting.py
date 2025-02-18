import json
import logging
import os
import base64

import boto3
import cv2
import numpy as np
import uuid

ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
QUEUE_NAME = os.getenv("QUEUE_NAME")
PHOTO_BUCKET_NAME = os.getenv("PHOTO_BUCKET_NAME")
FACE_BUCKET_NAME = os.getenv("FACE_BUCKET_NAME")

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

    def add_object(self, bucket, object_key, body, content_type="binary/octet-stream", metadata=None):
        if metadata:
            encoded_metadata = {
                key: base64.b64encode(value.encode("utf-8")).decode("ascii")
                for key, value in metadata.items()
            }
        else:
            encoded_metadata = {}

        self.client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=body,
            ContentType=content_type,
            Metadata=encoded_metadata
        )

storage_manager = StorageManager()

def extract_face(data, face_rectangle):
    np_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    # Извлекаем координаты
    x, y, w, h = face_rectangle

    # Вырезаем лицо
    face_img = img[y:y + h, x:x + w]

    # Кодируем обрезанное изображение в байты (JPEG)
    _, face_encoded = cv2.imencode(".jpg", face_img)
    return face_encoded.tobytes()

def handle_event(event, context):
    message_body = json.loads(event["messages"][0]["details"]["message"]["body"])
    object_key = message_body["object_key"]
    face_rectangle = message_body["face_rectangle"]

    data = storage_manager.get_object(PHOTO_BUCKET_NAME, object_key)

    face_image = extract_face(data, face_rectangle)

    random_uuid = uuid.uuid4() # случайный ключ
    cut_object_key = f"{random_uuid}.jpg"

    metadata = {"Original": object_key}
    storage_manager.add_object(FACE_BUCKET_NAME, cut_object_key, face_image, "image/jpeg", metadata)

    return {
        "statusCode": 200,
        "body": None,
    }

