"""
Agent and graph setup - FIXED VERSION without document tools
"""
from typing import Annotated, TypedDict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import config
import memory
import tools  # Assuming tools.all_tools includes document tools, we will remove them below


# ============ State Definition ============
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ============ LLM Setup ============
# llm = ChatOpenAI(
#     model=config.LLM_MODEL,
#     openai_api_key=config.OPENROUTER_API_KEY,
#     openai_api_base="https://openrouter.ai/api/v1",
#     max_tokens=config.MAX_TOKENS
# )
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model='gemini-2.5-pro')

# Remove document-related tools from tools.all_tools if any
# For example, if your document tools are named 'doc_tool', remove them:
non_doc_tools = [tool for tool in tools.all_tools if tool.name != "doc_tool"]
llm_with_tools = llm.bind_tools(non_doc_tools)


# ============ Chat Node (FIXED) ============
def chat_node(state: ChatState, config: Any = None):
    """Main chat node with proper tool handling"""

    if config is None:
        config = {}

    thread_id = config.get("configurable", {}).get("thread_id", "default-thread")
    messages = state.get("messages", [])

    if not messages:
        return {"messages": []}

    # Debug message types
    print(f"\n📨 Processing {len(messages)} messages")
    for i, msg in enumerate(messages[-3:]):
        print(f"  Message {i}: {type(msg).__name__}")

    last_message = messages[-1]
    is_user_message = isinstance(last_message, HumanMessage)

    if is_user_message:
        user_message = last_message.content

        try:
            relevant_memories = memory.retrieve_memory(thread_id, user_message, limit=3)

            if relevant_memories:
                context = "\n".join([f"- {m}" for m in relevant_memories])
                enriched_last = HumanMessage(
                    content=f"{user_message}\n\nRelevant context:\n{context}"
                )
                enriched_messages = messages[:-1] + [enriched_last]
            else:
                enriched_messages = messages

        except Exception as e:
            print(f"⚠️ Memory retrieval skipped: {e}")
            enriched_messages = messages

        memory.store_memory(thread_id, user_message, "user")

    else:
        enriched_messages = messages

    try:
        response = llm_with_tools.invoke(enriched_messages)
    except Exception as e:
        print(f"❌ LLM invocation failed: {e}")
        raise

    if hasattr(response, 'content') and response.content:
        memory.store_memory(thread_id, response.content, "assistant")

    return {"messages": [response]}


# ============ Build LangGraph (FIXED) ============
graph = StateGraph(ChatState)

# Add nodes
graph.add_node("chat_node", chat_node)
graph.add_node("tools", ToolNode(non_doc_tools))

# Start with chat
graph.add_edge(START, "chat_node")

# Proper conditional routing
graph.add_conditional_edges(
    "chat_node",
    tools_condition,
    {
        "tools": "tools",
        END: END
    }
)

# After tools execute, go back to chat_node
graph.add_edge("tools", "chat_node")

# Compile with checkpointer
chatbot = graph.compile(checkpointer=memory.checkpointer)

print("✅ Chatbot ready without document tools!")
