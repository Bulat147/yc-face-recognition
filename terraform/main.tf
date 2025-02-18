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

// Загрузим фотографию в наш бакет
resource "yandex_storage_object" "photo_object" {
  bucket = yandex_storage_bucket.photos_bucket.bucket
  key   = "photo.jpg"
  source = "../tgbot/faces.jpg"
  access_key           = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key           = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
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