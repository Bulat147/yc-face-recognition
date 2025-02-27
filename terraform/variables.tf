variable "sa_account" {
  description = "Идентификатор cервиcного аккаунта"
  type        = string
}

variable "cloud_id" {
  description = "Идентификатор облака"
  type        = string
}

variable "folder_id" {
  description = "Идентификатор папки"
  type        = string
}

variable "photos_bucket" {
  description = "Бакет оригинала фотографий"
  type        = string
}

variable "key_file_path" {
  type        = string
  description = "Ключ сервисного аккаунта"
}

variable "tg_bot_key" {
  description = "Токен tg-бота"
  type        = string
  sensitive   = true
}

variable "face_detection_func_name" {
  description = "Название ф-ции face_detection"
  type = string
}

variable "queue_name" {
  description = "Название очереди"
  type = string
}

variable "face_cutting_func_name" {
  description = "Назание ф-ции face_cutting"
  type = string
}

variable "faces_bucket" {
  description = "Бакет фотографий лиц"
  type = string
}

variable "bot_func_name" {
  description = "Название ф-ции bot"
  type = string
}

variable "api_gw_name" {
  description = "Название api gw"
  type = string
}
