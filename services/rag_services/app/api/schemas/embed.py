from pydantic import BaseModel
from typing import List

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    vectors: List[List[float]]