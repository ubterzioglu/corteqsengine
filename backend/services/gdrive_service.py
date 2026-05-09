"""
Google Drive Integration Service
Fetches files, folders, and documents from Google Drive
"""

import os
import json
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]


class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.is_configured = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Google Drive service"""
        if not GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_JSON == "placeholder":
            return
        
        try:
            # Parse JSON from environment variable
            credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=SCOPES
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            self.is_configured = True
            print("Google Drive service initialized successfully")
        except Exception as e:
            print(f"Google Drive initialization error: {e}")
            self.is_configured = False
    
    def list_files(
        self, 
        folder_id: str = None,
        page_size: int = 50,
        file_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """List files in Google Drive or a specific folder"""
        if not self.is_configured:
            return []
        
        try:
            # Build query
            query_parts = ["trashed = false"]
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            if file_types:
                type_queries = []
                for ft in file_types:
                    if ft == "document":
                        type_queries.append("mimeType = 'application/vnd.google-apps.document'")
                    elif ft == "spreadsheet":
                        type_queries.append("mimeType = 'application/vnd.google-apps.spreadsheet'")
                    elif ft == "presentation":
                        type_queries.append("mimeType = 'application/vnd.google-apps.presentation'")
                    elif ft == "pdf":
                        type_queries.append("mimeType = 'application/pdf'")
                    elif ft == "folder":
                        type_queries.append("mimeType = 'application/vnd.google-apps.folder'")
                if type_queries:
                    query_parts.append(f"({' or '.join(type_queries)})")
            
            query = " and ".join(query_parts)
            
            results = self.service.files().list(
                pageSize=page_size,
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, owners, webViewLink, parents, description)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append({
                    "id": item['id'],
                    "name": item['name'],
                    "mime_type": item['mimeType'],
                    "size": item.get('size'),
                    "created_at": item.get('createdTime'),
                    "modified_at": item.get('modifiedTime'),
                    "owners": [o.get('displayName', o.get('emailAddress')) for o in item.get('owners', [])],
                    "web_link": item.get('webViewLink'),
                    "parent_folders": item.get('parents', []),
                    "description": item.get('description'),
                    "is_folder": item['mimeType'] == 'application/vnd.google-apps.folder'
                })
            
            return files
        except Exception as e:
            print(f"Google Drive list files error: {e}")
            return []
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific file"""
        if not self.is_configured:
            return None
        
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, owners, webViewLink, parents, description, permissions"
            ).execute()
            
            return {
                "id": file['id'],
                "name": file['name'],
                "mime_type": file['mimeType'],
                "size": file.get('size'),
                "created_at": file.get('createdTime'),
                "modified_at": file.get('modifiedTime'),
                "owners": [o.get('displayName', o.get('emailAddress')) for o in file.get('owners', [])],
                "web_link": file.get('webViewLink'),
                "parent_folders": file.get('parents', []),
                "description": file.get('description'),
                "permissions": file.get('permissions', [])
            }
        except Exception as e:
            print(f"Google Drive get file error: {e}")
            return None
    
    def get_file_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """Get content of a Google Doc/Sheet as text"""
        if not self.is_configured:
            return None
        
        try:
            # For Google Docs, export as plain text
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            # For Google Sheets, export as CSV
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
            # For Google Slides, export as plain text
            elif mime_type == 'application/vnd.google-apps.presentation':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            # For other files, try to download directly
            else:
                request = self.service.files().get_media(fileId=file_id)
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            content = fh.read()
            
            # Try to decode as text
            try:
                return content.decode('utf-8')[:10000]  # Limit content size
            except UnicodeDecodeError:
                return content.decode('latin-1')[:10000]
                
        except Exception as e:
            print(f"Google Drive get content error: {e}")
            return None
    
    def search_files(self, query: str, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search files by name or content"""
        if not self.is_configured:
            return []
        
        try:
            search_query = f"name contains '{query}' and trashed = false"
            
            results = self.service.files().list(
                pageSize=page_size,
                q=search_query,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append({
                    "id": item['id'],
                    "name": item['name'],
                    "mime_type": item['mimeType'],
                    "size": item.get('size'),
                    "modified_at": item.get('modifiedTime'),
                    "web_link": item.get('webViewLink')
                })
            
            return files
        except Exception as e:
            print(f"Google Drive search error: {e}")
            return []
    
    def list_folders(self, parent_id: str = None) -> List[Dict[str, Any]]:
        """List folders in Drive or within a parent folder"""
        if not self.is_configured:
            return []
        
        try:
            query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                pageSize=100,
                q=query,
                fields="files(id, name, createdTime, modifiedTime)"
            ).execute()
            
            return [
                {
                    "id": f['id'],
                    "name": f['name'],
                    "created_at": f.get('createdTime'),
                    "modified_at": f.get('modifiedTime')
                }
                for f in results.get('files', [])
            ]
        except Exception as e:
            print(f"Google Drive list folders error: {e}")
            return []
    
    def get_recent_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently modified files"""
        if not self.is_configured:
            return []
        
        try:
            results = self.service.files().list(
                pageSize=limit,
                orderBy='modifiedTime desc',
                q="trashed = false and mimeType != 'application/vnd.google-apps.folder'",
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink, owners)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append({
                    "id": item['id'],
                    "name": item['name'],
                    "mime_type": item['mimeType'],
                    "size": item.get('size'),
                    "modified_at": item.get('modifiedTime'),
                    "web_link": item.get('webViewLink'),
                    "owners": [o.get('displayName', o.get('emailAddress')) for o in item.get('owners', [])]
                })
            
            return files
        except Exception as e:
            print(f"Google Drive recent files error: {e}")
            return []
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Google Drive connection"""
        if not self.is_configured:
            return {"connected": False, "error": "Google Drive not configured"}
        
        try:
            about = self.service.about().get(fields="user").execute()
            user = about.get('user', {})
            
            return {
                "connected": True,
                "email": user.get('emailAddress'),
                "display_name": user.get('displayName'),
                "photo_link": user.get('photoLink')
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Singleton instance
gdrive_service = GoogleDriveService()
