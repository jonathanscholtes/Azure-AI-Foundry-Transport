# data_generator/search_index.py

import os
from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SearchIndexerDataUserAssignedIdentity
)

from openai import AzureOpenAI


# ============================================================
# Embedding Client (Azure OpenAI) – Best Azure Pattern
# ============================================================

class EmbeddingClient:
    """
    Thin wrapper around Azure OpenAI embeddings.

    Pattern:
    - App-generated embeddings
    - Explicit vectors stored in Azure AI Search
    - Agent / MCP friendly
    """

    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version="2024-02-15-preview",
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
        )

        self.deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        """
        response = self.client.embeddings.create(
            model=self.deployment,
            input=texts,
        )

        return [item.embedding for item in response.data]


# ============================================================
# Azure AI Search Index Wrapper
# ============================================================

class TruckingSearchIndex:
    """
    Azure AI Search wrapper supporting:
    - Hybrid (keyword + vector) search
    - Explicit embeddings (agent-friendly)
    - MCP-ready retrieval
    """

    VECTOR_DIMENSIONS = 3072  # text-embedding-3-large

    def __init__(self):
        self.endpoint = os.environ["SEARCH_ENDPOINT"]
        self.index_name = os.environ["SEARCH_INDEX"]
        self.api_key = os.environ["SEARCH_API_KEY"]

        credential = AzureKeyCredential(self.api_key)

        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=credential,
        )

        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=credential,
        )

        self.embedder = EmbeddingClient()

    # --------------------------------------------------------
    # Index Management
    # --------------------------------------------------------

    def create_index_if_not_exists(self) -> None:
        """
        Create a hybrid (keyword + vector) index if it does not exist.
        """
        existing_indexes = [idx.name for idx in self.index_client.list_indexes()]
        if self.index_name in existing_indexes:
            print(f"ℹ️ Search index '{self.index_name}' already exists")
            return

        fields = [
            SimpleField(
                name="id",
                type="Edm.String",
                key=True,
            ),
            SimpleField(
                name="doc_type",
                type="Edm.String",
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="load_id",
                type="Edm.String",
                filterable=True,
            ),
            SearchableField(
                name="content",
                type="Edm.String",
                analyzer_name="en.lucene",
            ),
            SearchField(
                name="content_vector",
                type="Collection(Edm.Single)",
                vector_search_dimensions=self.VECTOR_DIMENSIONS,
                vector_search_profile_name="vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    kind=VectorSearchAlgorithmKind.HNSW,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config",
                    vectorizer_name="my-vectorizer"
                )
            ],
            vectorizers=[
                    AzureOpenAIVectorizer(
                        vectorizer_name="my-vectorizer",
                        kind= "azureOpenAI",
                         parameters=AzureOpenAIVectorizerParameters(
                                resource_url=os.environ["AZURE_OPENAI_ENDPOINT"],   
                                deployment_name=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
                                model_name=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
                                auth_identity= SearchIndexerDataUserAssignedIdentity(odata_type="#Microsoft.Azure.Search.DataUserAssignedIdentity",
                                 resource_id=str(os.environ["AZURE_CLIENT_RESOURCE_ID"]))
                                )
                        )
                ]
        )

        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
        )

        self.index_client.create_index(index)
        print(f"✅ Created Azure AI Search index '{self.index_name}'")

    # --------------------------------------------------------
    # Document Ingestion
    # --------------------------------------------------------

    def upload_documents(self, documents: List[dict]) -> None:
        """
        Upload documents to the search index with embeddings.

        Expected document format:
        {
            "id": str,
            "doc_type": str,
            "load_id": str,
            "content": str
        }
        """
        if not documents:
            return

        texts = [doc["content"] for doc in documents]
        embeddings = self.embedder.embed(texts)

        enriched_docs = [
            {
                "id": doc["id"],
                "doc_type": doc["doc_type"],
                "load_id": doc["load_id"],
                "content": doc["content"],
                "content_vector": vector,
            }
            for doc, vector in zip(documents, embeddings)
        ]

        result = self.search_client.upload_documents(documents=enriched_docs)

        failed = [r for r in result if not r.succeeded]
        if failed:
            raise RuntimeError(f"❌ Failed to index {len(failed)} documents")

        print(f"✅ Indexed {len(enriched_docs)} documents")

    # --------------------------------------------------------
    # Hybrid Search (RAG Retrieval)
    # --------------------------------------------------------

    def search(
        self,
        query: str,
        load_id: Optional[str] = None,
        top: int = 5,
    ) -> List[dict]:
        """
        Perform hybrid keyword + vector search.
        """
        query_vector = self.embedder.embed([query])[0]
        filter_expr = f"load_id eq '{load_id}'" if load_id else None

        results = self.search_client.search(
            search_text=query,
            filter=filter_expr,
            vector_queries=[
                {
                    "vector": query_vector,
                    "k": top,
                    "fields": "content_vector",
                }
            ],
            top=top,
        )

        return [
            {
                "id": r["id"],
                "doc_type": r["doc_type"],
                "load_id": r["load_id"],
                "content": r["content"],
                "score": r["@search.score"],
            }
            for r in results
        ]
