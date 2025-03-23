# DocuChat: RAG-Powered Document Chatbot

[![Python](https://img.shields.io/badge/Python-3.9-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32.0-FF4B4B.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-0.0.310-yellow.svg)](https://github.com/langchain-ai/langchain)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Run-4285F4.svg)](https://cloud.google.com/run)

A Streamlit application that allows users to upload documents, process them, and chat with their content using OpenAI's large language models. The app uses Retrieval-Augmented Generation (RAG) to provide accurate, context-aware responses based on document content.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
  - [Document Processing Flow](#document-processing-flow)
  - [Query Flow](#query-flow)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Local Development](#local-development)
- [Deployment to Google Cloud](#deployment-to-google-cloud)
  - [Understanding Critical Storage Paths](#understanding-critical-storage-paths)
  - [Using the Deployment Script](#using-the-deployment-script)
  - [Manual Deployment Steps](#manual-deployment-steps)
  - [Critical Deployment Parameters](#critical-deployment-parameters)
  - [Why Volume Mounting is Essential for RAG Applications](#why-volume-mounting-is-essential-for-rag-applications)
  - [Setting Environment Variables](#setting-environment-variables)
- [RAG Application Lifecycle](#rag-application-lifecycle)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
  - [Logs and Monitoring](#logs-and-monitoring)
  - [Common Issues](#common-issues)
- [Scaling Considerations](#scaling-considerations)
- [Security Recommendations](#security-recommendations)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Features

- 📄 Upload and process PDF and text documents
- 🔍 Extract, chunk, and embed document content
- 💾 Persist vector database to Google Cloud Storage
- 💬 Chat interface for document Q&A
- ☁️ Designed for deployment on Google Cloud Run
- 🔄 Maintains state across container restarts

## Architecture

DocuChat uses a RAG (Retrieval-Augmented Generation) architecture for document Q&A:

### Document Processing Flow

1. **Document Upload**: Users upload PDF or text documents through the Streamlit interface
2. **Text Extraction**: The application uses PyPDFLoader or TextLoader to extract text from the documents
3. **Text Chunking**: The extracted text is split into smaller chunks (1000 characters with 100-character overlap)
4. **Embedding Generation**: OpenAI's embedding model converts these text chunks into vector embeddings
5. **Vector Storage**: The embeddings are stored in ChromaDB, a vector database
6. **Persistence**: The vector database is persisted both locally and in Google Cloud Storage

### Query Flow

1. **User Question**: The user types a question about their documents
2. **Similarity Search**: The question is converted to an embedding and used to search ChromaDB for similar text chunks
3. **Context Assembly**: The most relevant chunks are assembled into context
4. **LLM Response Generation**: The context and question are sent to the OpenAI LLM
5. **Response Display**: The LLM's response is displayed to the user

## Project Structure

```
docuchat/
├── app.py                # Main Streamlit application
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── deploy-commands.sh    # Deployment script
└── utils/                # Utility modules
    ├── __init__.py
    ├── document_processor.py
    ├── gcs_utils.py
    └── chat_engine.py
```

## Prerequisites

- Python 3.9+
- Google Cloud Platform account
- OpenAI API key
- Google Cloud CLI installed (for deployment)
- Docker installed locally (for local testing and building)

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/docuchat.git
cd docuchat
```

Install required packages:

```bash
pip install -r requirements.txt
```

## Local Development

1. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

2. Run the Streamlit application:

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

## Deployment to Google Cloud

### Understanding Critical Storage Paths

Your application uses specific paths that must be preserved for proper functioning with Cloud Run volume mounts:

```python
# Storage paths 
GCS_BASE_PATH = f"/gcs/uploaded_files"    # For user-uploaded files
GCS_PERSIST_PATH = f"/gcs/persistentdb"    # For ChromaDB persistence
LOCAL_PERSIST_PATH = "./local_chromadb"    # Local working directory
```

These paths are configured to work with Cloud Run's volume mounting system. The `/gcs` path will be mounted to your Google Cloud Storage bucket, allowing persistent storage across container restarts.

### Using the Deployment Script

The easiest way to deploy is using the provided `deploy-commands.sh` script:

1. Edit the script with your project details if needed:

```bash
PROJECT_ID="document-ai-project"
REGION="us-central1"
SERVICE_NAME="docuchat"
BUCKET_NAME="docuchat_storage"
```

2. Make the script executable and run it:

```bash
chmod +x deploy-commands.sh
./deploy-commands.sh
```

### Manual Deployment Steps

If you prefer to deploy manually:

#### 1. Create a Cloud Storage Bucket

```bash
# Create the bucket for storing your files and ChromaDB
gcloud storage buckets create gs://docuchat_storage --location=us-central1 --project=document-ai-project
```

#### 2. Build and Push Docker Image

```bash
# Enable Container Registry API
gcloud services enable containerregistry.googleapis.com

# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Build and tag the image
gcloud builds submit --tag gcr.io/document-ai-project/docuchat
```

#### 3. Deploy to Cloud Run with Volume Mounting

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Deploy to Cloud Run
gcloud run deploy docuchat \
    --image gcr.io/document-ai-project/docuchat \
    --platform managed \
    --region us-central1 \
    --port 8080 \
    --allow-unauthenticated \
    --execution-environment gen2 \
    --memory 2Gi \
    --set-env-vars GCS_BUCKET_NAME=docuchat_storage,PROJECT_ID=document-ai-project \
    --add-volume=name=gcs-volume,type=cloud-storage,bucket=docuchat_storage \
    --add-volume-mount=volume=gcs-volume,mount-path=/gcs
```

### Critical Deployment Parameters

The following parameters in the deployment command are essential for your RAG application to function properly:

#### 1. Execution Environment

```
--execution-environment gen2
```

This specifies Cloud Run's second-generation execution environment, which is required for volume mounting.

#### 2. Volume Definition

```
--add-volume=name=gcs-volume,type=cloud-storage,bucket=docuchat_storage
```

This creates a volume named `gcs-volume` linked to your GCS bucket `docuchat_storage`.

#### 3. Volume Mounting

```
--add-volume-mount=volume=gcs-volume,mount-path=/gcs
```

This mounts the previously defined volume at the path `/gcs` inside your container, matching the paths in your application code.

### Why Volume Mounting is Essential for RAG Applications

Without proper persistence:
- Every container restart would wipe out all processed documents
- Users would need to re-upload and re-process all documents
- Chat history and context would be lost
- The application would incur unnecessary embedding API costs

### Setting Environment Variables

After deployment, set your OpenAI API key through the Cloud Run Console:

1. Go to the Google Cloud Console
2. Navigate to Cloud Run
3. Select your service (`docuchat`)
4. Click "Edit & Deploy New Revision"
5. Under "Variables & Secrets", add `OPENAI_API_KEY` with your API key value
6. Click "Deploy"

## RAG Application Lifecycle

Understanding the lifecycle of your RAG application can help troubleshoot issues:

1. **Document Upload**: User uploads a document through Streamlit
2. **Text Extraction**: Application extracts text using document loaders
3. **Chunking**: Text is split into manageable chunks
4. **Embedding Generation**: OpenAI API creates vector embeddings for each chunk
5. **Vector Storage**: Embeddings are stored in ChromaDB at `./local_chromadb`
6. **Persistence**: ChromaDB files are synced to `/gcs/persistentdb` (GCS bucket)
7. **Retrieval**: User questions trigger similarity searches in the vector database
8. **Generation**: Retrieved context and question are sent to OpenAI for response

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (set in Cloud Run console)
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name (default: "docuchat_storage")
- `PROJECT_ID`: GCP project ID (default: "document-ai-project")

## Troubleshooting

### Logs and Monitoring

Check Cloud Run logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=docuchat" --limit=50
```

### Common Issues

1. **GCS Access Problems**: Ensure the service account has proper storage permissions.
2. **Memory Limitations**: If your app crashes during document processing, try increasing the memory allocation.
3. **Volume Mount Issues**: Verify that you're using the gen2 execution environment and the paths match what the application expects.
4. **OpenAI API Issues**: Check the logs for authentication errors related to the OpenAI API key.

## Scaling Considerations

As your document collection grows, consider:

1. **Memory**: Increase memory allocation if processing larger documents
2. **CPU**: Add more CPU if response time slows down
3. **Concurrency**: Adjust concurrency settings based on expected user load
4. **Min Instances**: Set to 1 to avoid cold starts if consistent usage is expected

## Security Recommendations

For production deployments:

1. **API Key Management**: Use Secret Manager for storing the OpenAI API key
2. **Authentication**: Add Identity-Aware Proxy (IAP) to restrict access
3. **Network Security**: Configure VPC Service Controls if needed
4. **Data Encryption**: Enable default encryption for your GCS bucket

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain) for the document processing and RAG implementation
- [Streamlit](https://streamlit.io/) for the web interface
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [OpenAI](https://openai.com/) for embeddings and language models
- [Google Cloud Run](https://cloud.google.com/run) for serverless container deployment
