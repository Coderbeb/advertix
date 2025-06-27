import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Scope for file-level access only
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Path to service account JSON (place it safely in your project root)
SERVICE_ACCOUNT_FILE = 'credentials.json'

# Authenticate and return the Google Drive service client
def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials)

# Uploads a file to Google Drive and returns a public direct link
def upload_to_drive(filepath, filename, mimetype=None, folder_id=None):
    try:
        service = get_drive_service()

        # Set metadata (filename + optional folder)
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Prepare file for upload
        media = MediaIoBaseUpload(io.FileIO(filepath, 'rb'), mimetype=mimetype)

        # Upload the file
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file.get('id')

        # Make file publicly accessible
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()

        # Return public download URL
        return f"https://drive.google.com/uc?id={file_id}"

    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return None
