import os
import tempfile
import streamlit as st
from google.cloud import storage
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
import logging
from utils import download_directory_from_gcs, upload_directory_to_gcs, process_document, get_conversational_chain, get_response

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App title and description
st.set_page_config(page_title="DocuChat - Intelligent Document Search 🤖", layout="wide")
st.title("DocuChat - Intelligent Document Search 🤖")
st.markdown("Upload documents and chat with your data using LLM technology.")

# Environment variables
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "docuchat_storage")
PROJECT_ID = os.getenv("PROJECT_ID", "document-ai-project")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "docuchat_collection")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Storage paths 
GCS_BASE_PATH = f"/gcs/uploaded_files"
GCS_PERSIST_PATH = f"/gcs/persistentdb"
LOCAL_PERSIST_PATH = "./local_chromadb"

logger.info(f"GCS_BUCKET_NAME: {GCS_BUCKET_NAME}")
logger.info(f"GCS_BASE_PATH: {GCS_BASE_PATH}")
logger.info(f"GCS_PERSIST_PATH: {GCS_PERSIST_PATH}")

# Initialize GCS client
storage_client = storage.Client()

# Make sure local directories exist
os.makedirs(LOCAL_PERSIST_PATH, exist_ok=True)
os.makedirs(os.path.dirname(GCS_BASE_PATH), exist_ok=True)

# Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chroma_ready" not in st.session_state:
    st.session_state.chroma_ready = False

if "conversation_chain" not in st.session_state:
    st.session_state.conversation_chain = None

# Create a sidebar for document upload
with st.sidebar:
    st.header("Document Upload")
    uploaded_file = st.file_uploader("Upload a PDF or text file", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        if st.button("Process Document"):
            with st.spinner("Processing document..."):
                success, message = process_document(uploaded_file, OPENAI_API_KEY, LOCAL_PERSIST_PATH)
                if success:
                    upload_count = upload_directory_to_gcs(LOCAL_PERSIST_PATH, GCS_BUCKET_NAME, GCS_PERSIST_PATH)
                    st.success(f"{message} Uploaded {upload_count} files to cloud storage.")
                    st.session_state.chroma_ready = True
                    
                    # Initialize conversation chain
                    st.session_state.conversation_chain = get_conversational_chain(
                        OPENAI_API_KEY, 
                        LOCAL_PERSIST_PATH
                    )
                else:
                    st.error(message)
    
    # Add a button to initialize chat from existing DB
    if not st.session_state.chroma_ready:
        if st.button("Initialize Chat with Existing Data"):
            with st.spinner("Loading database..."):
                try:
                    download_count = download_directory_from_gcs(GCS_PERSIST_PATH, LOCAL_PERSIST_PATH, GCS_BUCKET_NAME)
                    if download_count > 0:
                        st.success(f"Loaded {download_count} files from existing database")
                        st.session_state.chroma_ready = True
                        
                        # Initialize conversation chain
                        st.session_state.conversation_chain = get_conversational_chain(
                            OPENAI_API_KEY, 
                            LOCAL_PERSIST_PATH
                        )
                    else:
                        st.warning("No existing database found")
                except Exception as e:
                    st.error(f"Error loading database: {str(e)}")

# Display chat interface
st.header("Chat with Your Documents")

# Show messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Only show chat input if ChromaDB is ready
if st.session_state.chroma_ready:
    user_input = st.chat_input("Ask a question about your documents")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Get response using conversation chain
                    if st.session_state.conversation_chain:
                        response = get_response(st.session_state.conversation_chain, user_input)
                    else:
                        # Fallback if chain wasn't initialized
                        st.session_state.conversation_chain = get_conversational_chain(OPENAI_API_KEY, LOCAL_PERSIST_PATH)
                        response = get_response(st.session_state.conversation_chain, user_input)
                    
                    # Display response
                    st.markdown(response)
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"Error generating response: {str(e)}"
                    st.error(error_msg)
                    logger.error(error_msg)
else:
    st.info("Please upload and process a document or initialize chat with existing data to begin chatting.")

# Add a button to clear chat history
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.experimental_rerun()