from typing import List, Dict, Any
from llama_index.core.schema import Document
from llama_index.core.node_parser import BaseNodeParser
from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.text_splitter import TextSplitter
from app.core.logger import get_logger

logger = get_logger(__name__)


class TabularNodeParser(BaseNodeParser):
    """
    Specialized node parser for tabular data that preserves table structure
    and prevents ID truncation across chunk boundaries.
    """

    def __init__(
        self,
        chunk_size: int = 50,
        chunk_overlap: int = 5,
        preserve_headers: bool = True,
        preserve_ids: bool = True,
        **kwargs
    ):
        """
        Initialize the tabular node parser.

        Args:
            chunk_size: Number of rows per chunk
            chunk_overlap: Number of rows to overlap between chunks
            preserve_headers: Whether to include headers in each chunk
            preserve_ids: Whether to ensure ID columns are not split
        """
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_headers = preserve_headers
        self.preserve_ids = preserve_ids

    def _parse_nodes(
        self,
        nodes: List[BaseNode],
        show_progress: bool = False
    ) -> List[BaseNode]:
        """
        Parse nodes with tabular-specific logic.
        """
        all_nodes = []

        for node in nodes:
            if isinstance(node, TextNode):
                # Check if this is tabular data
                if self._is_tabular_data(node):
                    tabular_nodes = self._parse_tabular_node(node)
                    all_nodes.extend(tabular_nodes)
                else:
                    # Use default parsing for non-tabular data
                    all_nodes.append(node)
            else:
                all_nodes.append(node)

        return all_nodes

    def _is_tabular_data(self, node: TextNode) -> bool:
        """
        Check if a node contains tabular data based on metadata.
        """
        metadata = node.metadata or {}
        return (
            metadata.get("file_type") == "tabular" or
            metadata.get("file_extension") in [".xlsx", ".xls", ".csv"] or
            "chunk_start_row" in metadata
        )

    def _parse_tabular_node(self, node: TextNode) -> List[BaseNode]:
        """
        Parse a tabular node with smart chunking.
        """
        text = node.text
        metadata = node.metadata or {}

        # If already chunked by TabularDataStrategy, return as-is
        if "chunk_start_row" in metadata:
            return [node]

        # Parse the tabular text and create smart chunks
        chunks = self._create_smart_chunks(text, metadata)

        nodes = []
        for i, chunk_text in enumerate(chunks):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_type": "tabular"
            }

            chunk_node = TextNode(
                text=chunk_text,
                metadata=chunk_metadata
            )
            nodes.append(chunk_node)

        return nodes

    def _create_smart_chunks(self, text: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Create smart chunks that preserve table structure.
        """
        lines = text.split('\n')
        chunks = []

        # Find header lines
        header_lines = []
        data_lines = []

        for line in lines:
            if line.startswith("Headers:") or line.startswith("Sheets:"):
                header_lines.append(line)
            elif line.startswith("Row "):
                data_lines.append(line)

        # Create chunks with overlap
        chunk_size = self.chunk_size
        overlap = self.chunk_overlap

        for i in range(0, len(data_lines), chunk_size - overlap):
            end_idx = min(i + chunk_size, len(data_lines))
            chunk_lines = data_lines[i:end_idx]

            # Build chunk with headers and data
            chunk_parts = []

            # Add context information
            if "Table Data" in text:
                chunk_parts.append(f"Table Data (Chunk {len(chunks) + 1}):")

            # Add headers to each chunk if requested
            if self.preserve_headers and header_lines:
                chunk_parts.extend(header_lines)
                chunk_parts.append("")

            # Add data lines
            chunk_parts.extend(chunk_lines)

            chunk_text = '\n'.join(chunk_parts)
            chunks.append(chunk_text)

        return chunks


class TabularTextSplitter(TextSplitter):
    """
    Specialized text splitter for tabular data that preserves structure.
    """

    def __init__(
        self,
        chunk_size: int = 50,
        chunk_overlap: int = 5,
        **kwargs
    ):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)

    def split_text(self, text: str) -> List[str]:
        """
        Split tabular text while preserving table structure.
        """
        lines = text.split('\n')
        chunks = []

        # Group lines by logical sections
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line)

            # If adding this line would exceed chunk size, start a new chunk
            if current_size + line_size > self.chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))

                # Start new chunk with overlap
                overlap_lines = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                current_chunk = overlap_lines + [line]
                current_size = sum(len(l) for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_size

        # Add the last chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks


def create_tabular_chunker(
    chunk_size: int = 50,
    chunk_overlap: int = 5,
    preserve_headers: bool = True,
    preserve_ids: bool = True
) -> TabularNodeParser:
    """
    Factory function to create a tabular chunker with specified parameters.
    """
    return TabularNodeParser(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        preserve_headers=preserve_headers,
        preserve_ids=preserve_ids
    )
