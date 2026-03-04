from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class BrandDNAState(TypedDict):
    messages: Annotated[list, add_messages]
    brand_input: str
    brand_dna: dict
