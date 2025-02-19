import base64
import json
import logging
import os
from json import JSONEncoder

import boto3
import requests

ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
FACE_BUCKET_NAME = os.getenv("FACE_BUCKET_NAME")
API_GW_URL = os.getenv("API_GW_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class TgHelper:

    def __init__(self):
        self.telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    def send_telegram_message(self, chat_id, text, reply_to_message_id=None):
        url = f"{self.telegram_api_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_to_message_id:
            payload["reply_parameters"] = {"message_id": reply_to_message_id}
        try:
            response = requests.post(url=url, json=payload)
            if response.status_code == 200:
                logging.info(f"Сообщение успешно отправлено в чат '{chat_id}': {text}")
            else:
                logging.error(f"Ошибка отправки сообщения в чат '{chat_id}': {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения в Telegram: {str(e)}")

    def send_telegram_media_group(self, chat_id, photo_urls, reply_to_message_id=None):
        url = f"{self.telegram_api_url}/sendMediaGroup"

        media = [{"type": "photo", "media": photo_url} for photo_url in photo_urls]

        payload = {
            "chat_id": chat_id,
            "media": media
        }

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logging.info(f"Медиагруппа успешно отправлена в чат '{chat_id}'.")
            else:
                logging.error(f"Ошибка отправки медиагруппы в чат '{chat_id}': {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при отправке медиагруппы в Telegram: {str(e)}")

    def send_telegram_photo(self, chat_id, photo_url, reply_to_message_id=None):
        url = f"{self.telegram_api_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
        }
        if reply_to_message_id:
            payload["reply_parameters"] = {"message_id": reply_to_message_id}
        try:
            response = requests.post(url=url, json=payload)
            if response.status_code == 200:
                file_unique_id = response.json()["result"]["photo"][-1]["file_unique_id"]
                logging.info(f"Фото успешно отправлено в чат '{chat_id}'. File Unique ID: {file_unique_id}")
                return file_unique_id
            else:
                logging.error(f"Ошибка отправки фото в чат '{chat_id}': {response.text}")
                return None
        except Exception as e:
            logging.error(f"Ошибка при отправке фото в Telegram: {str(e)}")
            return None

class StorageManager:

    def __init__(self):
        self.client = boto3.client(
            service_name="s3",
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name="ru-central1",
            endpoint_url="https://storage.yandexcloud.net",
        )

    def get_object_list(self, bucket):
        try:
            response = self.client.list_objects(Bucket=bucket)
            objects = [obj["Key"] for obj in response.get("Contents", [])]
            return objects
        except Exception as e:
            logging.error(f"Ошибка: не получилось достать обхекты из бакета {bucket}")

    def get_object_metadata(self, bucket, object_key):
        try:
            response = self.client.get_object(Bucket=bucket, Key=object_key)
            metadata = {
                key: base64.b64decode(value).decode("utf-8")
                for key, value in response["Metadata"].items()
            }
            return metadata
        except Exception as e:
            logging.error("Ошибка при получении метадаты")
            return {}

    def add_metadata(self, bucket, object_key, new_metadata):
        try:
            old_metadata = self.get_object_metadata(bucket, object_key)
            combined_metadata = {**old_metadata, **new_metadata}

            encoded_metadata = {
                key: base64.b64encode(value.encode("utf-8")).decode("ascii")
                for key, value in combined_metadata.items()
            }
            self.client.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": object_key},
                Key=object_key,
                Metadata=encoded_metadata,
                MetadataDirective="REPLACE",
            )
        except Exception as e:
            logging.error("Ошибка при обновлении метадаты")

def get_unnamed_face():
    images = storage_manager.get_object_list(FACE_BUCKET_NAME)
    for image in images:
        metadata = storage_manager.get_object_metadata(FACE_BUCKET_NAME, image)
        if not metadata.get("Name"):
            return image
    return None

def get_originals_by_name(name):
    originals = []
    images = storage_manager.get_object_list(FACE_BUCKET_NAME)
    for image in images:
        metadata = storage_manager.get_object_metadata(FACE_BUCKET_NAME, image)
        if metadata.get("Name") == name:
            originals.append(metadata["Original"])
    return originals

def get_photo_by_tg_unique_id(unique_id):
    images = storage_manager.get_object_list(FACE_BUCKET_NAME)
    for image in images:
        metadata = storage_manager.get_object_metadata(FACE_BUCKET_NAME, image)
        if metadata.get("Tg-Unique-Id") == unique_id:
            return image
    return None

def process_message(message):
    text = message.get("text")
    chat_id = message["chat"]["id"]
    message_id = message.get("message_id") # чтобы давать ответ на конкретное сообщение

    if text == "/start":
        tg_helper.send_telegram_message(
            chat_id,
            "Привет! Я работаю с лицами :)",
            message_id)
    elif text == "/help":
        tg_helper.send_telegram_message(
            chat_id,
            "Я телеграм бот, распознающий лица, отправль мне команду /getface",
            message_id)

    elif text == "/getface":
        unnamed_face = get_unnamed_face()
        if not unnamed_face:
            tg_helper.send_telegram_message(
                chat_id,
                "Простите, но все фотографии лиц уже подписаны",
                message_id
            )
            return
        # Отправляем фото (лежащее по этому урлу) и получаем id
        file_unique_id = tg_helper.send_telegram_photo(
            chat_id,
            f"{API_GW_URL}?face={unnamed_face}",
            message_id
        )
        if file_unique_id:
            new_metadata = {"Tg-Unique-Id": file_unique_id}
            storage_manager.add_metadata(FACE_BUCKET_NAME, unnamed_face, new_metadata)

    # Если пользователь отвечает на сообщение с фотографией
    elif text and "reply_to_message" in message and "photo" in message["reply_to_message"]:
        photo = message["reply_to_message"]["photo"][-1]
        photo_tg_unique_id = photo["file_unique_id"]
        face_object_key = get_photo_by_tg_unique_id(photo_tg_unique_id)
        if face_object_key:
            storage_manager.add_metadata(FACE_BUCKET_NAME, face_object_key, {"Name": text})
            tg_helper.send_telegram_message(
                chat_id,
                f"Хорошо, лицо получило имя: {text}"
            )

    elif text.startswith("/find"):
        name = text[len("/find"):].strip()
        original_photos = get_originals_by_name(name)
        if not original_photos:
            tg_helper.send_telegram_message(
                chat_id,
                f"Фотографии с именем {name} не найдены.",
                message_id
            )
            return
        media_urls = [f"{API_GW_URL}/originals/{photo}" for photo in original_photos]

        if len(media_urls) > 1:
            tg_helper.send_telegram_media_group(chat_id, media_urls, message_id)
        else:
            tg_helper.send_telegram_message(chat_id, media_urls[0], message_id)

    else:
        tg_helper.send_telegram_message(
            chat_id,
            "Команда не распознана (Сделайте /start или /help)"
        )

tg_helper = TgHelper()
storage_manager = StorageManager()

def handler(event, context):
    update = json.loads(event.get("body", "{}"))
    message = update.get("message")
    if message:
        process_message(message)
    return {
        "statusCode": 200,
        "body": "OK"
    }

