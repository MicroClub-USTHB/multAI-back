from itertools import count

from qdrant_client import QdrantClient
from collections import Counter

class VectorStore:
    def __init__(self , vectore_size: int , collection_name: str):
        self.vectore_size = vectore_size
        self.client = self.init_vector_store(collection_name)
        self.collection_name = collection_name

    def init_vector_store(self, collection_name: str):
        self.collection_name = collection_name
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config={
                "size": self.vectore_size,
                "distance": "Cosine"
            }
        )
    
    def add_embedding(self,id: str, vector:list[float], metadata:dict):
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                {
                    "id": id,
                    "vector": vector,
                    "payload": metadata
                }
            ]
        )
    
    def search(self, vector:list[float], top_k:int)->list[dict]:
        search_result = self.client.search(
            collection_name=self.collection_name,
            vector=vector,
            limit=top_k
        )
        ids=[hit.id for hit in search_result]
        counts = Counter(ids)
        total_count = len(ids)
        for item_id, count in counts.most_common():
             percentage = (count / total_count) * 100
        return zip(search_result, percentage)
