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

