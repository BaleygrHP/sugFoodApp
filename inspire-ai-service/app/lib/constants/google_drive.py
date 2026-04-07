"""Constants for Google Drive integration"""

# Socket timeout for Google Drive API calls
SOCKET_TIMEOUT = 300

# MIME type for Google Drive folders
FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

# Supported MIME types for Google Drive files
SUPPORTED_MIME_TYPES = {
    'application/pdf': 'pdf',
    'application/vnd.google-apps.document': 'google-doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/msword': 'doc',
    'text/plain': 'txt',
    'text/csv': 'csv',
    'application/vnd.google-apps.spreadsheet': 'google-sheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.google-apps.presentation': 'google-slides',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'application/vnd.ms-powerpoint': 'ppt',
    'text/markdown': 'md',
    'text/html': 'html',
    'application/rtf': 'rtf',
    'application/json': 'json',
}
