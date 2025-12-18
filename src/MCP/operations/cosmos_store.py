# /MCP/operations/cosmos_store.py


import os
from typing import Any, Dict, List, Optional

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(override=True)


class TruckingOperationsStore:
    def __init__(self):
        self._endpoint = os.getenv("COSMOS_ENDPOINT")
        self._db_name = os.getenv("COSMOS_DATABASE")
        self._container_name = os.getenv("COSMOS_CONTAINER")

        if not self._endpoint or not self._db_name or not self._container_name:
            missing = [
                name
                for name, value in [
                    ("COSMOS_ENDPOINT", self._endpoint),
                    ("COSMOS_DATABASE", self._db_name),
                    ("COSMOS_CONTAINER", self._container_name),
                ]
                if not value
            ]
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        self._client: Optional[CosmosClient] = None
        self._container = None
        self._credential: Optional[DefaultAzureCredential] = None

    async def _ensure_container(self):
        if self._client is None:
            self._credential = DefaultAzureCredential()
            self._client = CosmosClient(
                self._endpoint,
                credential=self._credential
            )
            database = self._client.get_database_client(self._db_name)
            self._container = database.get_container_client(self._container_name)

    async def get_load_context(self, load_id: str) -> List[Dict[str, Any]]:
        await self._ensure_container()

        query = """
        SELECT * FROM c
        WHERE c.load_id = @load_id
        """

        params = [{"name": "@load_id", "value": load_id}]

        results: List[Dict[str, Any]] = []
        async for item in self._container.query_items(
            query=query,
            parameters=params
        ):
            results.append(item)

        return results

    async def get_exceptions(self, load_id: str) -> List[Dict[str, Any]]:
        await self._ensure_container()

        query = """
        SELECT * FROM c
        WHERE c.type = 'exception'
          AND c.load_id = @load_id
        """

        params = [{"name": "@load_id", "value": load_id}]

        results: List[Dict[str, Any]] = []
        async for item in self._container.query_items(
            query=query,
            parameters=params
        ):
            results.append(item)

        return results
    

    async def get_exceptions_by_type(
        self,
        exception_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve exception records filtered by exception_type.
        Optionally scoped to a specific load_id.
        """
        await self._ensure_container()

    
        query = """
        SELECT * FROM c
        WHERE c.type = 'exception'
            AND c.exception_type = @exception_type
        """
        params = [
            {"name": "@exception_type", "value": exception_type},
        ]

        results: List[Dict[str, Any]] = []
        async for item in self._container.query_items(
            query=query,
            parameters=params
        ):
            results.append(item)

        return results