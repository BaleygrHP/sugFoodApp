from urllib.parse import quote

from fastapi import HTTPException
from llama_index.core.schema import Document
from llama_index.readers.database import DatabaseReader
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError, ArgumentError, OperationalError
from sqlalchemy.engine.url import make_url

from app.core.logger import logger


class DatabaseQueryService:
    """Database Query Reader"""

    @staticmethod
    def load_from_query(query: str, uri: str) -> list[Document]:
        """
        Load data from database using a query

        Args:
            query: SQL Query to select data
            uri: Database URI

        Returns:
            List of Document objects
        """

        try:
            DatabaseQueryService.test_connection(query=query, uri=uri)
            reader = DatabaseReader(uri=uri)
            documents = reader.load_data(query=query)
            return documents

        except Exception as e:
            logger.error(f"Failed to query from database: {str(e)}")
            raise ValueError(f"Could not query from database: {str(e)}")

    @staticmethod
    def test_connection(query: str, uri: str) -> list:
        try:
            engine = create_engine(uri, connect_args={"connect_timeout": 5})

            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                keys = result.keys()
                return [dict(zip(keys, row)) for row in rows]

        except (ArgumentError, OperationalError) as e:
            raise HTTPException(status_code=400, detail={
                "code": "INVALID_URI",
                "message": str(e)
            })
        except (ProgrammingError, SQLAlchemyError) as query_error:
            raise HTTPException(status_code=400, detail={
                "code": "INVALID_QUERY",
                "message": str(query_error.__cause__ or query_error)
            })
        except Exception as e:
            raise e
