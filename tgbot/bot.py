import json
import logging
import os
import requests

from pyexpat.errors import messages

class TgHelper:

    def __init__(self):
        self.telegram_api_url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"

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
                logging.info(f"Ошибка отправки сообщения в чат '{chat_id}': {response.text}")
        except Exception as e:
            logging.info(f"Ошибка при отправке сообщения в Telegram: {str(e)}")

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
                logging.info(f"Ошибка отправки фото в чат '{chat_id}': {response.text}")
                return None
        except Exception as e:
            logging.info(f"Ошибка при отправке фото в Telegram: {str(e)}")
            return None

tg_helper = TgHelper()

def handler(event, context):
    update = json.loads(event.get("body", "{}"))
    message = update.get("message")
    if message:
        text = message.get("text")
        chat_id = message["chat"]["id"]
        reply_to_message_id = message.get("message_id")
        tg_helper.send_telegram_message(chat_id, text, reply_to_message_id)
    return {
        "statusCode": 200,
        "body": "OK"
    }

