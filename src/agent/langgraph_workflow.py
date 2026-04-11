from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain.chat_models import init_chat_model

from src.tools.exposure_tool import calculate_sector_exposure
from src.tools.sql_query_tool import generate_fetch_data
from src.utils.logger import get_logger

logger = get_logger(__name__)


# -----------------------------
# Agent State
# -----------------------------
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# -----------------------------
# LLM Initialization
# -----------------------------
llm = init_chat_model(
    "groq:llama-3.3-70b-versatile"
)

# -----------------------------
# Tools
# -----------------------------
tools = [
    calculate_sector_exposure,
    generate_fetch_data,
]

llm_with_tools = llm.bind_tools(tools)


# -----------------------------
# LLM Node
# -----------------------------
def llm_node(state: AgentState):

    logger.info("Running LLM node")

    response = llm_with_tools.invoke(state["messages"])

    return {"messages": [response]}


# -----------------------------
# Tool Node
# -----------------------------
tool_node = ToolNode(tools)


# -----------------------------
# Router Logic
# -----------------------------
def router(state: AgentState):

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tool_node"

    return END


# -----------------------------
# Graph Definition
# -----------------------------
workflow = StateGraph(AgentState)

workflow.add_node("llm_node", llm_node)
workflow.add_node("tool_node", tool_node)

workflow.add_edge(START, "llm_node")

workflow.add_conditional_edges(
    "llm_node",
    router,
    {
        "tool_node": "tool_node",
        END: END,
    },
)

workflow.add_edge("tool_node", "llm_node")


# -----------------------------
# Compile Agent
# -----------------------------
agent = workflow.compile()

