"""
Streamlit Frontend
"""
import streamlit as st
import uuid
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agent import chatbot
from memory import get_all_threads,get_conversation_title


# ============ Helper Functions ============
def new_thread_id():
    """Create new conversation ID"""
    return uuid.uuid4()


def reset_chat():
    """Start new chat"""
    st.session_state['thread_id'] = new_thread_id()
    st.session_state['message_history'] = []
    st.rerun()

def load_conversation(thread_id):
    """Load old conversation"""
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    messages = state.values.get('messages', None)
    if not messages:
        return None
    return messages


# ============ Initialize Session ============
if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = get_all_threads()

if 'thread_id' not in st.session_state:
    # Try to get the most recent conversation
    all_threads = st.session_state['chat_threads']
    if all_threads:
        # Use the most recent thread (last in the list)
        st.session_state['thread_id'] = all_threads[-1]
    else:
        # No existing threads, create new one
        st.session_state['thread_id'] = new_thread_id()

# Load current conversation if it exists
if 'message_history' not in st.session_state:
    messages = load_conversation(st.session_state['thread_id'])
    if messages:
        temp_messages = []
        for msg in messages:
            role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
            temp_messages.append({'role': role, 'content': msg.content})
        st.session_state['message_history'] = temp_messages
    else:
        st.session_state['message_history'] = []

# ============ Sidebar ============
st.sidebar.title('💬 LangGraph Chatbot')

# New Chat button
if st.sidebar.button('➕ New Chat'):
    reset_chat()
    st.rerun()

# List conversations
st.sidebar.header('📁 My Conversations')
for thread_id in st.session_state['chat_threads'][::-1]:
    title = get_conversation_title(thread_id)  # Get title
    # ============ Chat Title ============
    if st.sidebar.button(title, key=str(thread_id)):
        messages = load_conversation(thread_id)
        if messages:  # Only switch if messages exist
            st.session_state['thread_id'] = thread_id
            temp_messages = []
            for msg in messages:
                role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
                temp_messages.append({'role': role, 'content': msg.content})

            st.session_state['message_history'] = temp_messages
            st.rerun()
# In sidebar
st.sidebar.divider()
if st.sidebar.button("📥 Export Current Chat"):
    messages = st.session_state.get('message_history', [])
    
    # Create markdown export
    export_text = f"# Conversation Export\n\n"
    export_text += f"**Thread ID:** {st.session_state['thread_id']}\n\n"
    export_text += "---\n\n"
    
    for msg in messages:
        role = msg['role'].upper()
        content = msg['content']
        export_text += f"**{role}:**\n{content}\n\n"
    
    st.sidebar.download_button(
        label="Download as Markdown",
        data=export_text,
        file_name=f"chat_{st.session_state['thread_id']}.md",
        mime="text/markdown"
    )
import tiktoken

def count_tokens(text):
    """Count tokens in text"""
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    return len(encoding.encode(text))

# In sidebar, add metrics
st.sidebar.divider()
st.sidebar.subheader("📊 Session Stats")

total_tokens = sum(
    count_tokens(msg['content']) 
    for msg in st.session_state.get('message_history', [])
)

col1, col2 = st.sidebar.columns(2)
col1.metric("Messages", len(st.session_state.get('message_history', [])))
col2.metric("Tokens", total_tokens)

# Estimate cost
cost = (total_tokens / 1000) * 0.00015  # GPT-4o-mini pricing
st.sidebar.caption(f"💰 Est. Cost: ${cost:.4f}")






# ============ Chat Display ============
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])


# ============ Chat Input ============
user_input = st.chat_input('💭 Type your message...')

if user_input:
    # Show user message
    st.session_state["message_history"].append({
        "role": "user",
        "content": user_input
    })
    with st.chat_message("user"):
        st.markdown(user_input)
    # 🆕 Store user message in memory
    from memory import store_memory
    store_memory(st.session_state["thread_id"], user_input, "user")
    
    # Config
    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }
    
    # Get AI response
    with st.chat_message("assistant"):
        status_box = {"box": None}
        
        def ai_stream():
            for msg_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # Show tool usage
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
                
                # Stream response
                if isinstance(msg_chunk, AIMessage):
                    yield msg_chunk.content
        
        ai_message = st.write_stream(ai_stream())
        
        # Close tool status
        if status_box["box"]:
            status_box["box"].update(
                label="✅ Tool finished",
                state="complete",
                expanded=False
            )
    
            # Save response
        st.session_state["message_history"].append({
            "role": "assistant",
            "content": ai_message
        })

        # 🆕 Store assistant response in memory
        store_memory(st.session_state["thread_id"], ai_message, "assistant")

    
