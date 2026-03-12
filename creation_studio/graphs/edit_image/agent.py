from langgraph.graph import StateGraph, START, END

from .state import EditImageState
from .nodes.download_image import download_image_node
from .nodes.edit_with_gemini import edit_with_gemini_node
from .nodes.edit_with_openai import edit_with_openai_node
from .nodes.upload_and_save import upload_and_save_node


def _after_gemini(state: EditImageState) -> str:
    if state.get("gemini_failed"):
        return "edit_with_openai"
    return "upload_and_save"


def build_edit_image_agent():
    graph = StateGraph(EditImageState)

    graph.add_node("download_image", download_image_node)
    graph.add_node("edit_with_gemini", edit_with_gemini_node)
    graph.add_node("edit_with_openai", edit_with_openai_node)
    graph.add_node("upload_and_save", upload_and_save_node)

    graph.add_edge(START, "download_image")
    graph.add_edge("download_image", "edit_with_gemini")
    graph.add_conditional_edges("edit_with_gemini", _after_gemini)
    graph.add_edge("edit_with_openai", "upload_and_save")
    graph.add_edge("upload_and_save", END)

    return graph.compile()
