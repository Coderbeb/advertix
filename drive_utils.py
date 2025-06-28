import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# Correct path for Render secret file
SERVICE_ACCOUNT_FILE = '/etc/secrets/credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
BACKUP_DB_FILENAME = 'database.db'
UPLOAD_FOLDER_ID = '1ltiyKEsuxsOJRE39HUrAlOY-IEehdwjx'  # Your shared folder

def get_drive_service():
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"[Drive Error] Missing credentials file: {SERVICE_ACCOUNT_FILE}")
            return None
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"[Drive Auth Error] {e}")
        return None

def upload_to_drive(filepath, filename, mimetype=None):
    try:
        service = get_drive_service()
        if not service:
            return None, None

        file_metadata = {
            'name': filename,
            'parents': [UPLOAD_FOLDER_ID]
        }

        media = MediaIoBaseUpload(io.FileIO(filepath, 'rb'), mimetype=mimetype)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file.get('id')

        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        public_url = f"https://drive.google.com/uc?export=view&id={file_id}"
        return public_url, file_id
    except Exception as e:
        print(f"[Drive Upload Error] {e}")
        return None, None

def delete_file_from_drive(file_id):
    try:
        service = get_drive_service()
        if not service:
            return False
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"[Drive Delete Error] {e}")
        return False

def find_file_by_name(filename):
    try:
        service = get_drive_service()
        if not service:
            return None
        response = service.files().list(
            q=f"name='{filename}' and trashed=false",
            fields="files(id, name)"
        ).execute()
        files = response.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        print(f"[Drive Find Error] {e}")
        return None

def download_database_from_drive(local_path='database.db'):
    try:
        service = get_drive_service()
        file_id = find_file_by_name(BACKUP_DB_FILENAME)
        if not file_id:
            print("[Drive Restore] No backup found.")
            return False
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        print("[Drive Restore] Downloaded database.")
        return True
    except Exception as e:
        print(f"[Drive Restore Error] {e}")
        return False

def backup_database_to_drive():
    try:
        filepath = BACKUP_DB_FILENAME
        mimetype = 'application/x-sqlite3'
        file_id = find_file_by_name(BACKUP_DB_FILENAME)
        service = get_drive_service()
        if not service:
            return False

        media = MediaIoBaseUpload(io.FileIO(filepath, 'rb'), mimetype=mimetype)
        if file_id:
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            print("[Drive Backup] Updated existing backup.")
        else:
            upload_to_drive(filepath, BACKUP_DB_FILENAME, mimetype)
            print("[Drive Backup] Uploaded new database.")
        return True
    except Exception as e:
        print(f"[Drive Backup Error] {e}")
        return False
