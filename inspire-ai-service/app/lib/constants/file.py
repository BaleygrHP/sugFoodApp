from enum import Enum


class FileExtension(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    CSV = "csv"
    PPTX = "pptx"
    RTF = "rtf"
    MD = "md"
    JSON = "json"
