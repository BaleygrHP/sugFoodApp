from abc import ABC, abstractmethod
from llama_index.core.schema import Document

class DocumentConversionStrategy(ABC):
    @abstractmethod
    def convert(self, file_path: str, metadata: dict = {}) -> list[Document]:
        """Convert a file to a list of Documents"""
        pass
