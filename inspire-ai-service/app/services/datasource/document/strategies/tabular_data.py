import pandas as pd
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from llama_index.core.schema import Document
from app.services.datasource.document.strategies.base import DocumentConversionStrategy
from app.core.logger import get_logger

logger = get_logger(__name__)


class TabularDataStrategy(DocumentConversionStrategy):
    """
    Specialized strategy for Excel/CSV files that preserves table structure,
    prevents ID truncation, and maintains header context across chunks.
    """

    def convert(self, file_path: str, metadata: dict = {}) -> List[Document]:
        """
        Convert Excel/CSV files to documents with smart chunking that preserves
        table structure and prevents data truncation.

        Args:
            file_path: Path to the Excel/CSV file
            metadata: Additional metadata to attach to documents

        Returns:
            List of Document objects with preserved table structure
        """
        try:
            file_extension = Path(file_path).suffix.lower()

            # Read the file based on extension
            if file_extension == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8', dtype=str)
            elif file_extension in ['.xlsx', '.xls']:
                # Read all sheets and combine them
                excel_file = pd.ExcelFile(file_path)
                all_sheets = []

                for sheet_name in excel_file.sheet_names:
                    try:
                        sheet_df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
                        if not sheet_df.empty:
                            # Add sheet name as a column for context
                            sheet_df['_sheet_name'] = sheet_name
                            all_sheets.append(sheet_df)
                            logger.info(f"Loaded sheet '{sheet_name}' with {len(sheet_df)} rows")
                    except Exception as e:
                        logger.warning(f"Failed to read sheet '{sheet_name}': {str(e)}")
                        continue

                if not all_sheets:
                    logger.warning(f"No readable sheets found in {file_path}")
                    return []

                # Combine all sheets
                df = pd.concat(all_sheets, ignore_index=True)
            else:
                logger.error(f"Unsupported file type for tabular data: {file_extension}")
                return []

            if df.empty:
                logger.warning(f"Empty file: {file_path}")
                return []

            logger.info(f"Loaded tabular data with {len(df)} rows and {len(df.columns)} columns")

            # Create documents with smart chunking
            documents = self._create_tabular_documents(df, file_path, metadata)

            return documents

        except Exception as e:
            logger.error(f"Error processing tabular file {file_path}: {str(e)}")
            return []

    def _create_tabular_documents(self, df: pd.DataFrame, file_path: str, metadata: dict) -> List[Document]:
        """
        Create documents from DataFrame with smart chunking that preserves table structure.
        """
        documents = []

        # Get column names for header context
        columns = df.columns.tolist()
        header_row = " | ".join(columns)

        # Identify potential ID columns (common patterns)
        id_columns = self._identify_id_columns(df)

        # Create chunks that preserve table structure
        chunk_size = 50  # Number of rows per chunk (adjustable)
        overlap = 5      # Number of rows to overlap between chunks

        for start_idx in range(0, len(df), chunk_size - overlap):
            end_idx = min(start_idx + chunk_size, len(df))

            # Get chunk data
            chunk_df = df.iloc[start_idx:end_idx]

            # Create structured text representation
            chunk_text = self._format_tabular_chunk(
                chunk_df,
                columns,
                header_row,
                start_idx,
                end_idx,
                id_columns
            )

            # Create document with enhanced metadata
            doc_metadata = {
                **metadata,
                "chunk_start_row": start_idx + 1,  # 1-indexed for user reference
                "chunk_end_row": end_idx,
                "total_rows": len(df),
                "columns": columns,
                "id_columns": id_columns,
                "file_type": "tabular",
                "has_sheet_info": "_sheet_name" in columns
            }

            # Add sheet information if available
            if "_sheet_name" in chunk_df.columns:
                unique_sheets = chunk_df["_sheet_name"].unique()
                doc_metadata["sheets"] = unique_sheets.tolist()

            document = Document(
                text=chunk_text,
                metadata=doc_metadata
            )

            documents.append(document)
            logger.debug(f"Created chunk {len(documents)}: rows {start_idx+1}-{end_idx}")

        logger.info(f"Created {len(documents)} documents from {len(df)} rows")
        return documents

    def _identify_id_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Identify potential ID columns based on common patterns.
        """
        id_columns = []

        for col in df.columns:
            col_lower = col.lower()
            col_values = df[col].dropna().astype(str)

            # Check for common ID patterns
            if any(pattern in col_lower for pattern in ['id', 'key', 'code', 'ref', 'number']):
                id_columns.append(col)
            # Check if column contains mostly unique values (potential ID)
            else:
                total = len(col_values)
                if total == 0:
                    continue
                uniqueness_ratio = len(col_values.unique()) / total
                if uniqueness_ratio > 0.8:
                    id_columns.append(col)

        logger.debug(f"Identified ID columns: {id_columns}")
        return id_columns

    def _format_tabular_chunk(
        self,
        chunk_df: pd.DataFrame,
        columns: List[str],
        header_row: str,
        start_idx: int,
        end_idx: int,
        id_columns: List[str]
    ) -> str:
        """
        Format a chunk of tabular data with proper structure and context.
        """
        # Start with context information
        text_parts = [
            f"Table Data (Rows {start_idx + 1}-{end_idx}):",
            f"Headers: {header_row}",
            ""
        ]

        # Add sheet information if available
        if "_sheet_name" in chunk_df.columns:
            unique_sheets = chunk_df["_sheet_name"].unique()
            text_parts.append(f"Sheets: {', '.join(unique_sheets)}")
            text_parts.append("")

        # Format each row with proper structure
        for idx, (_, row) in enumerate(chunk_df.iterrows()):
            row_num = start_idx + idx + 1

            # Create row representation that preserves structure
            row_parts = []
            for col in columns:
                if col == "_sheet_name":
                    continue  # Skip internal sheet column

                value = str(row[col]) if pd.notna(row[col]) else ""
                row_parts.append(f"{col}: {value}")

            # Emphasize ID columns for better retrieval
            if id_columns:
                id_values = [f"{col}: {row[col]}" for col in id_columns if col in row and pd.notna(row[col])]
                if id_values:
                    text_parts.append(f"Row {row_num} - IDs: {' | '.join(id_values)}")

            # Add full row data
            text_parts.append(f"Row {row_num}: {' | '.join(row_parts)}")
            text_parts.append("")  # Empty line for readability

        return "\n".join(text_parts)

    def _validate_data_integrity(self, df: pd.DataFrame, file_path: str) -> Dict[str, Any]:
        """
        Validate that no data was lost during processing.
        """
        validation_info = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "empty_cells": df.isnull().sum().sum(),
            "duplicate_rows": df.duplicated().sum(),
            "file_size_mb": os.path.getsize(file_path) / (1024 * 1024)
        }

        # Check for potential data loss indicators
        if validation_info["empty_cells"] > len(df) * 0.5:
            logger.warning(f"High number of empty cells in {file_path}: {validation_info['empty_cells']}")

        if validation_info["duplicate_rows"] > 0:
            logger.info(f"Found {validation_info['duplicate_rows']} duplicate rows in {file_path}")

        return validation_info
