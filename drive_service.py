from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
from auth import authenticate_google_drive
from settings import DRIVE_FOLDER_ID

class DriveService:
    def __init__(self):
        self.creds = authenticate_google_drive()
        if self.creds:
            self.service = build('drive', 'v3', credentials=self.creds)
        else:
            self.service = None

    def list_files(self, page_size=10):
        """Lists metadata of the 10 most recent video files."""
        if not self.service:
            return []
            
        # Filter for videos in specific folder
        query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed = false"
        results = self.service.files().list(
            q=query,
            pageSize=page_size, 
            fields="nextPageToken, files(id, name, mimeType)").execute()
        return results.get('files', [])

    def download_file(self, file_id, file_name, destination_folder):
        """Downloads a file to the destination folder."""
        if not self.service:
            return None

        request = self.service.files().get_media(fileId=file_id)
        file_path = os.path.join(destination_folder, file_name)
        
        with io.FileIO(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        
        return file_path
