"""
Agent and graph setup
"""
from typing import Annotated, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import config
import memory
import tools


# ============ State Definition ============
class ChatState(TypedDict):
    """What data flows through the graph"""
    messages: Annotated[list[BaseMessage], add_messages]


# ============ LLM Setup ============
llm = ChatOpenAI(
    model=config.LLM_MODEL,
    openai_api_key=config.OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1",
    max_tokens=config.MAX_TOKENS
)

llm_with_tools = llm.bind_tools(tools.all_tools)


# ============ Agent Node ============
def chat_node(state: ChatState, config):
    """
    Main brain of chatbot
    """
    # Get thread ID and messages
    thread_id = config["configurable"]["thread_id"]
    messages = state["messages"]
    user_message = messages[-1].content
    
    # Get relevant memories
    past_memories = memory.retrieve_memory(thread_id, user_message)
    
    # Add memories to context
    if past_memories:
        memory_text = (
            "Past memories from this conversation:\n" +
            "\n".join(f"- {m}" for m in past_memories)
        )
        enriched_messages = [SystemMessage(content=memory_text)] + messages
    else:
        enriched_messages = messages
    
    # Get AI response
    response = llm_with_tools.invoke(enriched_messages)
    
    # Save to memory
    memory.store_memory(thread_id, user_message, "user")
    if hasattr(response, 'content') and response.content:
        memory.store_memory(thread_id, response.content, "assistant")
    
    return {"messages": [response]}


# ============ Build Graph ============
graph = StateGraph(ChatState)

# Add nodes
graph.add_node("chat_node", chat_node)
graph.add_node("tools", ToolNode(tools.all_tools))

# Add edges
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

# Compile
chatbot = graph.compile(checkpointer=memory.checkpointer)

print("✅ Chatbot ready!")