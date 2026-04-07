import uuid
import asyncio
import requests
from llama_index.core.schema import Document
from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode, MemoryAdaptiveDispatcher, CrawlerMonitor, AsyncWebCrawler
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

from app.core.logger import logger


class WebService:
    """Web content loader using crawl4ai for extraction"""

    @staticmethod
    def load_from_url(
        url: str,
        is_recursive: bool = False,
        max_pages: int = 1,
        max_depth: int = 2,
        process_callback = None
    ) -> list[Document]:
        """
        Load content from a web URL with options for recursive crawling

        Args:
            url: The URL to load
            is_recursive: Whether to recursively crawl the site
            max_pages: Maximum number of pages to crawl (only used when is_recursive=True)
            max_depth: Maximum depth for recursive crawling (only used when is_recursive=True)
            process_callback: Optional callback function to process documents as they are loaded.
                            Called with (document, page_number, total_pages) arguments.

        Returns:
            List of Document objects
        """
        root_doc_id = str(uuid.uuid4())

        try:
            # Validate URL accessibility and fetch basic information before crawling
            response_info = WebService._fetch_url(url)
            base_metadata = {
                "root_id": root_doc_id,
                "root_content_length": response_info.get("content_length", 0),
            }
        except Exception as e:
            logger.error(f"Failed to access URL {url}: {str(e)}")
            raise ValueError(f"Could not access URL: {str(e)}")

        # Use crawl4ai for web content extraction (Just working in Linux OS)
        documents = asyncio.run(WebService._extract_with_crawl4ai(
            url,
            base_metadata,
            is_recursive,
            max_pages,
            max_depth,
            process_callback
        ))
        return documents

    @staticmethod
    def _fetch_url(url: str) -> dict:
        """
        Validate URL accessibility and fetch basic information before crawling

        This method performs a lightweight HTTP request to check if the URL is accessible
        and reachable before starting the resource-intensive crawl4ai extraction process.

        Args:
            url: The URL to validate

        Returns:
            Dict containing basic URL information (content_length, status_code, content_type)

        Raises:
            requests.exceptions.RequestException: If the URL cannot be accessed
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        return {
            "content_length": len(response.text),
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
        }

    @staticmethod
    async def _extract_with_crawl4ai(
        url: str,
        base_metadata: dict,
        is_recursive: bool = False,
        max_pages: int = 1,
        max_depth: int = 2,
        process_callback = None
    ) -> list[Document]:
        """Extract content using crawl4ai"""

        browser_config = BrowserConfig(headless=True, verbose=True)

        common_kwargs = {
            "verbose": True,
            "cache_mode": CacheMode.BYPASS,
            "check_robots_txt": True,
            "stream": False
        }

        if is_recursive:
            run_conf = CrawlerRunConfig(
                deep_crawl_strategy=BestFirstCrawlingStrategy(
                    max_pages=max_pages,
                    max_depth=max_depth,
                    include_external=False
                ),
                scraping_strategy=LXMLWebScrapingStrategy(),
                **common_kwargs
            )
        else:
            run_conf = CrawlerRunConfig(**common_kwargs)

        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=70.0,
            check_interval=10.0,
            max_session_permit=10,
            monitor=CrawlerMonitor()
        )

        documents = []

        async with AsyncWebCrawler(config=browser_config) as crawler:
            results = await crawler.arun(
                url=str(url),
                config=run_conf,
                dispatcher=dispatcher
            )

            if not results or not results[0].success:
                logger.error(f"Failed to crawl URL {url}")
                return []

            for index, result in enumerate(results):
                if not result.success:
                    continue

                document = Document(text=result.markdown)

                if document and document.text.strip():
                    doc_id = str(uuid.uuid4())
                    doc_metadata = base_metadata.copy()

                    doc_metadata.update(
                        {
                            "extraction_method": "crawl4ai",
                            "doc_index": index,
                            "total_docs": len(results),
                            "url": result.url,
                        }
                    )

                    if document.metadata:
                        document.metadata.update(doc_metadata)
                    else:
                        document.metadata = doc_metadata

                    document.id_ = doc_id
                    documents.append(document)

                    # Process document immediately if callback is provided
                    if process_callback:
                        try:
                            process_callback(document, index + 1, len(results))
                        except Exception as e:
                            logger.error(f"Error in process callback for document {index + 1}: {str(e)}")

            logger.info(f"Successfully extracted {len(documents)} documents from {url}")
            return documents
