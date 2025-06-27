import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Google Drive API scope – file-level access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Path to your Google Service Account JSON file
SERVICE_ACCOUNT_FILE = 'credentials.json'  # should be in project root or mounted on Render

# Initialize Google Drive API service
def get_drive_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"[Drive Auth Error] Could not initialize Drive service: {e}")
        return None

# Upload a file to Google Drive and return its public link
def upload_to_drive(filepath, filename, mimetype=None, folder_id=None):
    try:
        service = get_drive_service()
        if not service:
            return None

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

        # Make the file public
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # Return a direct link
        return f"https://drive.google.com/uc?id={file_id}"

    except Exception as e:
        print(f"[Drive Upload Error] {e}")
        return None
