import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- НАСТРОЙКИ, КОТОРЫЕ НУЖНО ПРОВЕРИТЬ ---

# ID ПАПКИ НА GOOGLE ДИСКЕ (ИЗ ВАШЕГО СКРИНШОТА)
# Это папка "DN KIRA Calls", куда будут загружаться аудио.
DRIVE_FOLDER_ID = '1qq81ICz-ZMedSm7EloiTgbBEUkw7f_iIe'

# ID ВАШЕГО GOOGLE ДОКУМЕНТА
# Замените на реальный ID документа, куда пишутся логи.
# Вы его, скорее всего, передаете через AGENT_4_DOC_ID
DOC_ID = os.getenv('AGENT_4_DOC_ID', 'YOUR_GOOGLE_DOC_ID_HERE') 

# ОБЛАСТИ ДОСТУПА (SCOPES)
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']


def get_credentials():
    """
    Получает учетные данные из переменных окружения (как в GitHub Actions).
    """
    google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if not google_creds_json:
        raise ValueError("Секрет GOOGLE_CREDENTIALS_JSON не найден в переменных окружения")
    
    creds_info = json.loads(google_creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    print("Аутентификация через сервисный аккаунт прошла успешно.")
    return creds


def upload_file_to_drive(drive_service, file_path, file_name):
    """
    Загружает файл на Google Диск в указанную папку.
    Возвращает ID файла и ссылку для просмотра.
    """
    print(f"Начало загрузки файла '{file_name}' на Google Диск...")
    try:
        #
        # ===== ГЛАВНОЕ ИЗМЕНЕНИЕ ЗДЕСЬ =====
        # Мы явно указываем ID родительской папки ('parents').
        # Это заставляет Google использовать ваше хранилище, а не хранилище сервисного аккаунта.
        #
        file_metadata = {
            'name': file_name,
            'parents': [DRIVE_FOLDER_ID] 
        }

        media = MediaFileUpload(file_path, mimetype='audio/mpeg', resumable=True)

        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        file_id = file.get('id')
        web_link = file.get('webViewLink')
        print(f"Файл успешно загружен. ID: {file_id}")
        return file_id, web_link

    except Exception as e:
        # Выводим ошибку, если она все еще есть
        print(f"!!! ОШИБКА ЗАГРУЗКИ НА GOOGLE DRIVE: {e}")
        return None, None


def add_text_to_google_doc(docs_service, text_to_add):
    """
    Добавляет переданный текст в начало Google Документа.
    """
    try:
        # Запрос на вставку текста в начало документа
        requests = [
            {
                'insertText': {
                    'location': { 'index': 1 },
                    'text': text_to_add + "\n\n"
                }
            }
        ]
        docs_service.documents().batchUpdate(documentId=DOC_ID, body={'requests': requests}).execute()
        print("Запись успешно добавлена в Google Doc.")
    except Exception as e:
        print(f"!!! ОШИБКА ДОБАВЛЕНИЯ ЗАПИСИ В GOOGLE DOC: {e}")


def main_process():
    """
    Основной логический блок скрипта.
    Вам нужно будет встроить сюда вашу логику получения и обработки звонков.
    """
    print("Начало работы скрипта...")
    
    # 1. Аутентификация
    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    docs_service = build('docs', 'v1', credentials=credentials)

    # 2. Здесь должен быть ваш код, который скачивает аудио
    #    Для примера я создам фейковый файл:
    
    conversation_id = "conv_01_example"
    local_audio_path = f"{conversation_id}.mp3"
    with open(local_audio_path, 'w') as f:
        f.write("dummy content") # Создаем пустой файл для теста

    print(f"--- Обработка новой записи: {conversation_id} ---")
    if not os.path.exists(local_audio_path):
        print("Ошибка: Локальный аудиофайл не найден.")
        return

    # 3. Загрузка на Google Диск
    drive_file_id, drive_file_link = upload_file_to_drive(
        drive_service=drive_service,
        file_path=local_audio_path,
        file_name=os.path.basename(local_audio_path)
    )

    # 4. Запись в Google Doc
    if drive_file_link:
        log_message = f"Обработан звонок: {conversation_id}\nСсылка на аудио: {drive_file_link}"
    else:
        log_message = f"Ошибка при загрузке аудио для звонка: {conversation_id}"
    
    add_text_to_google_doc(docs_service, log_message)
    
    # 5. Очистка (удаляем временный файл)
    os.remove(local_audio_path)
    
    print("\nРабота скрипта завершена.")


# Точка входа в программу
if __name__ == '__main__':
    main_process()
