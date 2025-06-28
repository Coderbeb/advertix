import os
import io
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'credentials.json'
BACKUP_DB_FILENAME = 'database.db'

def get_drive_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"[Drive Auth Error] Could not initialize Drive service: {e}")
        return None

def upload_to_drive(filepath, filename, mimetype=None, folder_id=None):
    """Upload a file to Google Drive and return (public_link, file_id)"""
    try:
        service = get_drive_service()
        if not service:
            return None, None

        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaIoBaseUpload(io.FileIO(filepath, 'rb'), mimetype=mimetype)

        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file.get('id')

        # Make file public
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # Return a displayable link and ID
        public_url = f"https://drive.google.com/uc?export=view&id={file_id}"
        return public_url, file_id
    except Exception as e:
        print(f"[Drive Upload Error] {e}")
        return None, None

def delete_file_from_drive(file_id):
    """Delete a file from Google Drive using its file ID"""
    try:
        service = get_drive_service()
        if not service:
            return False
        service.files().delete(fileId=file_id).execute()
        print(f"[Drive Delete] File ID {file_id} deleted.")
        return True
    except Exception as e:
        print(f"[Drive Delete Error] {e}")
        return False

def find_file_by_name(filename):
    """Returns file ID from Google Drive matching the given name"""
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
    """Download latest database.db from Drive if it exists"""
    try:
        service = get_drive_service()
        file_id = find_file_by_name(BACKUP_DB_FILENAME)
        if not file_id:
            print("[Drive Restore] No database backup found on Drive.")
            return False

        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        print("[Drive Restore] Database downloaded successfully.")
        return True
    except Exception as e:
        print(f"[Drive Restore Error] {e}")
        return False

def backup_database_to_drive():
    """Upload the current database.db to Google Drive"""
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
            print("[Drive Backup] Database updated on Drive.")
        else:
            upload_to_drive(filepath, BACKUP_DB_FILENAME, mimetype)
            print("[Drive Backup] New database uploaded to Drive.")
        return True
    except Exception as e:
        print(f"[Drive Backup Error] {e}")
        return False
