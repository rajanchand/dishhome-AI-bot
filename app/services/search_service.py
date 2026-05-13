"""
Elasticsearch service: indices for call transcripts, tickets, customers, FAQ.
"""

from typing import List, Optional
from loguru import logger

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

from config.settings import settings


INDEX_CALL_TRANSCRIPTS = f"{settings.elasticsearch_index_prefix}-call-transcripts"
INDEX_TICKETS = f"{settings.elasticsearch_index_prefix}-tickets"
INDEX_CUSTOMERS = f"{settings.elasticsearch_index_prefix}-customers"
INDEX_FAQ = f"{settings.elasticsearch_index_prefix}-faq"


CALL_TRANSCRIPT_MAPPING = {
    "mappings": {
        "properties": {
            "session_id": {"type": "keyword"},
            "customer_id": {"type": "keyword"},
            "language": {"type": "keyword"},
            "content": {"type": "text"},
            "timestamp": {"type": "date"},
            "sentiment": {"type": "keyword"},
            "duration_seconds": {"type": "float"},
        }
    }
}

TICKET_MAPPING = {
    "mappings": {
        "properties": {
            "ticket_number": {"type": "keyword"},
            "customer_id": {"type": "keyword"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "category": {"type": "keyword"},
            "status": {"type": "keyword"},
            "priority": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    }
}

CUSTOMER_MAPPING = {
    "mappings": {
        "properties": {
            "customer_code": {"type": "keyword"},
            "full_name": {"type": "text"},
            "phone_primary": {"type": "keyword"},
            "phone_secondary": {"type": "keyword"},
            "email": {"type": "keyword"},
            "account_status": {"type": "keyword"},
            "preferred_language": {"type": "keyword"},
        }
    }
}

FAQ_MAPPING = {
    "mappings": {
        "properties": {
            "question": {"type": "text"},
            "answer": {"type": "text"},
            "category": {"type": "keyword"},
            "language": {"type": "keyword"},
            "keywords": {"type": "text"},
        }
    }
}


class SearchService:
    def __init__(self) -> None:
        self._client: Optional[AsyncElasticsearch] = None

    @property
    def client(self) -> AsyncElasticsearch:
        if self._client is None:
            self._client = AsyncElasticsearch(hosts=[settings.elasticsearch_url])
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def initialize(self) -> None:
        """Create indices if they don't exist."""
        indices = [
            (INDEX_CALL_TRANSCRIPTS, CALL_TRANSCRIPT_MAPPING),
            (INDEX_TICKETS, TICKET_MAPPING),
            (INDEX_CUSTOMERS, CUSTOMER_MAPPING),
            (INDEX_FAQ, FAQ_MAPPING),
        ]
        for name, mapping in indices:
            try:
                exists = await self.client.indices.exists(index=name)
                if not exists:
                    await self.client.indices.create(index=name, body=mapping)
                    logger.success(f"ES index created: {name}")
            except Exception as e:
                logger.warning(f"ES init {name} failed: {e}")

    # ── Call transcripts ─────────────────────────────────────────────────
    async def index_call_transcript(self, doc: dict) -> Optional[str]:
        try:
            r = await self.client.index(index=INDEX_CALL_TRANSCRIPTS, document=doc)
            return r.get("_id")
        except Exception as e:
            logger.warning(f"ES index call failed: {e}")
            return None

    async def search_transcripts(self, query: str, size: int = 20) -> List[dict]:
        try:
            r = await self.client.search(
                index=INDEX_CALL_TRANSCRIPTS,
                body={"query": {"match": {"content": query}}, "size": size},
            )
            return [hit["_source"] | {"_id": hit["_id"]} for hit in r["hits"]["hits"]]
        except Exception as e:
            logger.warning(f"ES search failed: {e}")
            return []

    # ── Tickets ──────────────────────────────────────────────────────────
    async def index_ticket(self, doc: dict) -> Optional[str]:
        try:
            r = await self.client.index(index=INDEX_TICKETS, id=str(doc["ticket_number"]), document=doc)
            return r.get("_id")
        except Exception as e:
            logger.warning(f"ES index ticket failed: {e}")
            return None

    async def search_tickets(self, query: str, size: int = 20) -> List[dict]:
        try:
            r = await self.client.search(
                index=INDEX_TICKETS,
                body={
                    "query": {
                        "multi_match": {"query": query, "fields": ["title^2", "description"]}
                    },
                    "size": size,
                },
            )
            return [hit["_source"] for hit in r["hits"]["hits"]]
        except Exception as e:
            return []

    # ── Customers ────────────────────────────────────────────────────────
    async def index_customer(self, doc: dict) -> Optional[str]:
        try:
            r = await self.client.index(index=INDEX_CUSTOMERS, id=doc["customer_code"], document=doc)
            return r.get("_id")
        except Exception as e:
            logger.warning(f"ES index customer failed: {e}")
            return None

    async def search_customers(self, query: str, size: int = 20) -> List[dict]:
        try:
            r = await self.client.search(
                index=INDEX_CUSTOMERS,
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["full_name^3", "phone_primary", "phone_secondary", "email", "customer_code"],
                        }
                    },
                    "size": size,
                },
            )
            return [hit["_source"] for hit in r["hits"]["hits"]]
        except Exception as e:
            return []

    # ── FAQ ──────────────────────────────────────────────────────────────
    async def index_faq(self, doc: dict) -> Optional[str]:
        try:
            r = await self.client.index(index=INDEX_FAQ, document=doc)
            return r.get("_id")
        except Exception as e:
            logger.warning(f"ES index faq failed: {e}")
            return None

    async def search_faq(self, query: str, language: str = "ne", size: int = 5) -> List[dict]:
        try:
            r = await self.client.search(
                index=INDEX_FAQ,
                body={
                    "query": {
                        "bool": {
                            "must": [{"multi_match": {"query": query, "fields": ["question^2", "answer", "keywords"]}}],
                            "filter": [{"term": {"language": language}}],
                        }
                    },
                    "size": size,
                },
            )
            return [hit["_source"] for hit in r["hits"]["hits"]]
        except Exception as e:
            return []


search_service = SearchService()
