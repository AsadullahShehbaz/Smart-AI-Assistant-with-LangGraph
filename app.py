import streamlit as st
import uuid
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agent import chatbot
from memory import get_all_threads, get_conversation_title, store_memory

# ============ Page Config ============
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# ============ Helper Functions ============
def new_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    st.session_state['thread_id'] = new_thread_id()
    st.session_state['message_history'] = []
    st.rerun()

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    messages = state.values.get('messages', None)
    if not messages:
        return []
    temp = []
    for msg in messages:
        role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
        temp.append({'role': role, 'content': msg.content})
    return temp

# ============ Session Initialization ============
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "default_user"

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = get_all_threads()

if 'thread_id' not in st.session_state:
    all_threads = st.session_state['chat_threads']
    if all_threads:
        st.session_state['thread_id'] = all_threads[-1]
    else:
        st.session_state['thread_id'] = f"{st.session_state['user_id']}_{new_thread_id()}"

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = load_conversation(st.session_state['thread_id'])

# ============ Sidebar ============
with st.sidebar:
    st.title("🤖 AI Assistant")

    if st.button("➕ New Chat", key="btn_new_chat", use_container_width=True):
        reset_chat()

    st.divider()

    # Conversations
    st.subheader("💬 My Chats")
    for thread_id in st.session_state["chat_threads"][::-1]:
        title = get_conversation_title(thread_id)
        if st.button(title, key=f"thread_{thread_id}", use_container_width=True):
            st.session_state["thread_id"] = thread_id
            st.session_state["message_history"] = load_conversation(thread_id)
            st.rerun()

    st.divider()

    # Export Chat
    if st.button("📥 Export Chat", key="btn_export_chat"):
        msgs = st.session_state["message_history"]
        export_text = "# Chat Export\n\n"
        for msg in msgs:
            export_text += f"### **{msg['role'].upper()}**\n{msg['content']}\n\n"

        st.download_button(
            "💾 Download Markdown",
            export_text,
            file_name="chat_export.md",
            mime="text/markdown",
            key="download_btn"
        )

# ============ Chat History Display ============
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# ============ Chat Input ============
user_input = st.chat_input("💭 Type your message...", key="chat_input")
if user_input:
    st.session_state["message_history"].append({
        "role": "user",
        "content": user_input
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    store_memory(st.session_state["thread_id"], user_input, "user")

    # AI Response
    CONFIG = {
        "configurable": {
            "thread_id": st.session_state["thread_id"],
            "user_id": st.session_state["user_id"]
        },
        "metadata": {
            "thread_id": st.session_state["thread_id"],
            "user_id": st.session_state["user_id"]
        },
        "run_name": "chat_turn",
    }

    with st.chat_message("assistant"):
        status_box = {"box": None}

        def ai_stream():
            for msg_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                if isinstance(msg_chunk, ToolMessage):
                    tool_name = getattr(msg_chunk, "name", "tool")
                    if status_box["box"] is None:
                        status_box["box"] = st.status(
                            f"🔧 Using `{tool_name}` …",
                            expanded=True
                        )
                    else:
                        status_box["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running"
                        )

                if isinstance(msg_chunk, AIMessage):
                    yield msg_chunk.content

        ai_message = st.write_stream(ai_stream())

        if status_box["box"]:
            status_box["box"].update(
                label="✅ Done",
                state="complete",
                expanded=False
            )

    st.session_state["message_history"].append({
        "role": "assistant",
        "content": ai_message
    })
    store_memory(st.session_state["thread_id"], ai_message, "assistant")
