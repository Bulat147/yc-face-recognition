terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
      version = "0.80.0"
    }
    telegram = {
      source  = "yi-jiayu/telegram"
      version = "0.3.1"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  cloud_id                = var.cloud_id
  folder_id               = var.folder_id
  service_account_key_file = pathexpand(var.key_file_path)
  zone                     = "ru-central1-c"
}

// даем роль для вызова ф-ции нашему сервиному аккаунту terraform
resource "yandex_resourcemanager_folder_iam_member" "adm_function_invoker_iam" {
  folder_id = var.folder_id
  role      = "functions.functionInvoker"
  member    = "serviceAccount:${var.sa_account}"
}

// создаим static key (IAM) для сервисного аккаунта, чтобы юзать для бакета
resource "yandex_iam_service_account_static_access_key" "sa_static_key" {
  service_account_id = var.sa_account
}

resource "yandex_storage_bucket" "photos_bucket" {
  bucket               = var.photos_bucket
  acl                  = "private"
  default_storage_class = "standard"
  max_size             = 5368709120
  access_key           = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key           = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

resource "yandex_storage_bucket" "faces_bucket" {
  bucket               = var.faces_bucket
  acl                  = "private"
  default_storage_class = "standard"
  max_size             = 5368709120
  access_key           = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key           = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

// Загрузим фотографию в наш бакет
resource "yandex_storage_object" "photo_object" {
  bucket = yandex_storage_bucket.photos_bucket.bucket
  key   = "photo.jpg"
  source = "../tgbot/faces.jpg"
  access_key           = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key           = yandex_iam_service_account_static_access_key.sa_static_key.secret_key

  depends_on = [yandex_function_trigger.photo_trigger]
}

resource "yandex_function" "face_detection" {
  name               = var.face_detection_func_name
  entrypoint         = "face_detection.handle_event"
  memory             = "512"
  runtime            = "python312"
  service_account_id = var.sa_account
  user_hash          =  archive_file.zip.output_sha256
  content {
    zip_filename = archive_file.zip.output_path
  }
  environment = {
    ACCESS_KEY      = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    SECRET_KEY      = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
    QUEUE_NAME = yandex_message_queue.tasks_queue.name
  }
}

resource "yandex_function" "face_cutting" {
  name               = var.face_cutting_func_name
  entrypoint         = "face_cutting.handle_event"
  memory             = "512"
  runtime            = "python312"
  service_account_id = var.sa_account
  user_hash          =  archive_file.zip.output_sha256
  content {
    zip_filename = archive_file.zip.output_path
  }
  environment = {
    ACCESS_KEY      = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    SECRET_KEY      = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
    QUEUE_NAME = yandex_message_queue.tasks_queue.name
    PHOTO_BUCKET_NAME = yandex_storage_bucket.photos_bucket.bucket
    FACE_BUCKET_NAME = yandex_storage_bucket.faces_bucket.bucket
  }
}

resource "yandex_function" "bot" {
  name               = var.bot_func_name
  entrypoint         = "bot.handler"
  memory             = "128"
  runtime            = "python312"
  service_account_id = var.sa_account
  user_hash          = archive_file.zip.output_sha256
  content {
    zip_filename = archive_file.zip.output_path
  }
  environment = {
    TELEGRAM_BOT_TOKEN = var.tg_bot_key
    ACCESS_KEY         = yandex_iam_service_account_static_access_key.sa_static_key.access_key
    SECRET_KEY         = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
    FACE_BUCKET_NAME       = var.faces_bucket
    API_GW_URL = "https://${yandex_api_gateway.api_gw.domain}"
  }
}

// Делаем ф-цию bot публичной
resource "yandex_function_iam_binding" "bot-function-iam" {
  function_id = yandex_function.bot.id
  role        = "functions.functionInvoker"
  members = [
    "system:allUsers",
  ]
}

resource "yandex_api_gateway" "api_gw" {
  name = var.api_gw_name
  spec = <<EOT
openapi: "3.0.0"
info:
  version: 1.0.0
  title: Faces API
paths:
  /:
    get:
      summary: "Get face"
      parameters:
        - name: "face"
          in: "query"
          required: true
          schema:
            type: "string"
      x-yc-apigateway-integration:
        type: "object-storage"
        bucket: "${yandex_storage_bucket.faces_bucket.bucket}"
        object: "{face}"
        service_account_id: "${var.sa_account}"
      responses:
        '200':
          description: "Image found"
        '404':
          description: "Image not found"
  /originals/{photo}:
    get:
      summary: "Get photo from Object Storage"
      parameters:
        - name: "photo"
          in: "path"
          required: true
          schema:
            type: "string"
      x-yc-apigateway-integration:
        type: "object-storage"
        bucket: "${yandex_storage_bucket.photos_bucket.bucket}"
        сontent_type: "image/jpeg"
        object: "{photo}"
        service_account_id: "${var.sa_account}"
      responses:
        "200":
          description: "Photo retrieved successfully"
          content:
            image/jpeg: {}
            image/png: {}
        "404":
          description: "Photo not found"
EOT
}


// Ставим вебхук
resource "null_resource" "set_tg_webhook" {
  provisioner "local-exec" {
    command = "curl 'https://api.telegram.org/bot${var.tg_bot_key}/setWebhook?url=https://functions.yandexcloud.net/${yandex_function.bot.id}'"
  }

  depends_on = [yandex_function.bot]
}

// Убираем вебхук
resource "null_resource" "delete_tf_webhook" {
  triggers = {
    tg_token = var.tg_bot_key
  }

  provisioner "local-exec" {
    when = destroy
    command = "curl 'https://api.telegram.org/bot${self.triggers.tg_token}/deleteWebhook'"
  }
}

resource "archive_file" "zip" {
  type        = "zip"
  source_dir  = "../tgbot"
  output_path = "../bot.zip"
}

# Очередь сообщений для задач
resource "yandex_message_queue" "tasks_queue" {
  name        = var.queue_name
  access_key  = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key  = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

# Триггер для face-detection
resource "yandex_function_trigger" "photo_trigger" {
  name        = "vvot29-photo"

  // ф-ция для вызова при событии
  function {
    id                 = yandex_function.face_detection.id
    service_account_id = var.sa_account
  }

  // событие триггера - изменение в баккете с файлами .jpg, а именно операция create
  object_storage {
    bucket_id = yandex_storage_bucket.photos_bucket.id
    suffix    = ".jpg"
    create    = true
  }
}

# Триггер для задач
resource "yandex_function_trigger" "task_trigger" {
  name        = "vvot29-task"

  function {
    id                 = yandex_function.face_cutting.id
    service_account_id = var.sa_account
    retry_attempts     = 3
    retry_interval     = 30
  }

  message_queue {
    queue_id           = yandex_message_queue.tasks_queue.arn
    service_account_id = var.sa_account
    batch_cutoff       = "10"
    batch_size         = "1"
  }
}
