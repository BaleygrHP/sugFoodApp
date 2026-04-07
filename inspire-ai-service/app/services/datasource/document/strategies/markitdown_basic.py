import re
from markitdown import MarkItDown
from llama_index.core.schema import Document

from app.services.datasource.document.strategies.base import DocumentConversionStrategy

class MarkItDownBasicStrategy(DocumentConversionStrategy):
    """Strategy for converting files using MarkItDown without LLM support"""

    def __init__(self):
        self.md = MarkItDown()

    def _preprocess_content(self, content: str) -> str:
        """
        Preprocess content to preserve links in a format that survives embedding.
        Args:
            content (str): The raw content with potential links
        Returns:
            str: Processed content with preserved links
        """
        # Match URLs in the text - this regex pattern matches most common URL formats
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'

        # Replace each URL with a special format that's more likely to survive embedding
        def replace_url(match):
            url = match.group(0)
            return f"[LINK_START]{url}[LINK_END]"

        processed_content = re.sub(url_pattern, replace_url, content)
        return processed_content

    def convert(self, file_path: str, metadata: dict = {}) -> list[Document]:
        result = self.md.convert(file_path)
        documents = [Document(text=self._preprocess_content(result.text_content), metadata=metadata)]
        return documents
