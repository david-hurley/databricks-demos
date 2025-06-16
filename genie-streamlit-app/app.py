import streamlit as st
import requests
import time

# Constants
GENIE_URL = "https://adb-984752964297111.11.azuredatabricks.net"
GENIE_SPACE_ID = "01f046cc67a91cdd83c5a7254315d1fe"
HEADERS = {
    "Authorization": f"Bearer {st.secrets['DATABRICKS_AUTH_TOKEN']}",
    "Content-Type": "application/json"
}

# Helper functions
def has_assistant_message():
    """ Checks if there is an assistant message in the chat history """
    return any(msg.get("role") == "assistant" for msg in st.session_state.messages)

def clear_conversation():
    """ Clears the cache """
    st.session_state.conversation_id = None
    st.session_state.messages = []

def get_latest_user_message():
    """ Genie does not do great with follow up questions, so we need to get the latest user message """
    return next((msg["content"] for msg in reversed(st.session_state.messages) 
                if msg["role"] == "user"), None)

def wait_for_completion(url, timeout=15):
    """ Wait for the Genie API to complete the request, GET is free """
    start_time = time.time()
    status = "PENDING"
    
    while status != "COMPLETED" and (time.time() - start_time) < timeout:
        time.sleep(1)
        response = requests.get(url, headers=HEADERS)
        status = response.json()['status']
    
    if status != "COMPLETED":
        raise TimeoutError(f"Failed to get COMPLETED status after {timeout} seconds")
    
    return response

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# UI Setup
st.title("Genie Streamlit Chat")
st.markdown(("Chatbot that uses Genie API to answer questions about vehicle warranties over data in Unity Catalog."))
st.button('Start New Conversation', on_click=clear_conversation)

# Display chat history
for message in st.session_state.messages:  # Display all messages except the last one
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input and processing
if prompt := st.chat_input("Ask a question about vehicle warranties"):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process with Genie
    with st.chat_message("assistant"):
        with st.spinner("Getting response from Genie..."):
            # Determine if this is a new conversation or continuation
            if not st.session_state.conversation_id:
                post_url = f"{GENIE_URL}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation"
            else:
                post_url = f"{GENIE_URL}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{st.session_state.conversation_id}/messages"
            
            # Make initial request
            response = requests.post(post_url, headers=HEADERS, json={"content": prompt})
            response_json = response.json()
            
            # Cache conversation_id for new conversations
            if not st.session_state.conversation_id:
                st.session_state.conversation_id = response_json.get('conversation_id')
            
            # Wait for completion and get result
            message_id = response_json.get('message_id')
            poll_url = f"{GENIE_URL}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{st.session_state.conversation_id}/messages/{message_id}"
            response = wait_for_completion(poll_url)
            
            # Get attachment and final result
            try:
                attachment_id = response.json()['attachments'][0]['attachment_id']
                result_url = f"{GENIE_URL}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{st.session_state.conversation_id}/messages/{message_id}/query-result/{attachment_id}"
                result = requests.get(result_url, headers=HEADERS).json()['statement_response']['result']['data_array'][0][0]
            except (KeyError, IndexError):
                raise ValueError("No valid response found in completed message")
            
            # Display and store result
            st.markdown(result)
            st.session_state.messages.append({"role": "assistant", "content": result})