import os
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient, PartitionKey

class CosmosStore:
    def __init__(self):
        self.endpoint = os.environ["COSMOS_ENDPOINT"]
        self.database_name = os.environ["COSMOS_DATABASE"]
        self.container_name = os.environ["COSMOS_CONTAINER"]

        self.client = CosmosClient(
            self.endpoint,
            credential=DefaultAzureCredential()
        )

        self.database = self.client.create_database_if_not_exists(
            id=self.database_name
        )

        self.container = self.database.create_container_if_not_exists(
            id=self.container_name,
            partition_key=PartitionKey(path="/load_id"),
            offer_throughput=400
        )

    def upsert_items(self, items: list[dict]):
        for item in items:
            self.container.upsert_item(item)

    def query_items(self, query: str, parameters=None):
        return list(
            self.container.query_items(
                query=query,
                parameters=parameters or [],
                enable_cross_partition_query=True
            )
        )
