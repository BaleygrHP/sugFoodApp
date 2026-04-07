import os
import subprocess
from pathlib import Path
from app.core.logger import get_logger

logger = get_logger(__name__)

class OfficeConverter:
    LEGACY_SUPPORTED_FORMATS = {
        ".doc": "docx",
        ".ppt": "pptx",
        ".pptm": "pptx",
        ".xlsm": "xlsx",
        ".xls": "xlsx",
        ".xlsb": "xlsx",
    }


    @staticmethod
    def convert_to_modern_format(file_path: str):
        input_path = Path(file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"{file_path} not found")

        # Use LibreOffice in headless mode to convert
        result = subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to", OfficeConverter.LEGACY_SUPPORTED_FORMATS.get(input_path.suffix, input_path.suffix),
            "--outdir", str(input_path.parent),
            str(input_path)
        ], capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Convert to modern format failed: {result.stderr}")
            return file_path
        else:
            logger.info(f"Convert to modern format success: {result.stdout}")
            return os.path.join(input_path.parent, input_path.stem + "." + OfficeConverter.LEGACY_SUPPORTED_FORMATS.get(input_path.suffix, input_path.suffix))
