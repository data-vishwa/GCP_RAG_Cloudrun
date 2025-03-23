import os
import tempfile
import logging
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_document(uploaded_file, openai_api_key, local_persist_path):
    """Process an uploaded document, chunk it, and add to the vector store."""
    try:
        # Create a temporary file for the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_file_path = temp_file.name
        
        # Load document
        if uploaded_file.name.endswith('.pdf'):
            loader = PyPDFLoader(temp_file_path)
            logger.info(f"Loading PDF: {uploaded_file.name}")
        else:
            loader = TextLoader(temp_file_path)
            logger.info(f"Loading text file: {uploaded_file.name}")
        
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} document pages")
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Split into {len(chunks)} chunks")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Add documents to Chroma
        try:
            # Try to load existing DB first
            db = Chroma(persist_directory=local_persist_path, embedding_function=embeddings)
            logger.info("Loaded existing ChromaDB")
            # Add new documents
            db.add_documents(chunks)
            logger.info(f"Added {len(chunks)} chunks to existing ChromaDB")
        except Exception as e:
            logger.warning(f"Could not load existing ChromaDB: {str(e)}")
            # Create new DB if loading failed
            db = Chroma.from_documents(chunks, embedding_function=embeddings, persist_directory=local_persist_path)
            logger.info("Created new ChromaDB")
        
        # Persist to disk
        db.persist()
        logger.info("Persisted ChromaDB to disk")
        
        # Clean up the temp file
        os.unlink(temp_file_path)
        
        return True, "Document processed successfully!"
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return False, f"Error processing document: {str(e)}"
