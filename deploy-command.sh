#!/bin/bash

# Exit on any error
set -e

# Configuration
PROJECT_ID="document-ai-project"
REGION="us-central1"
SERVICE_NAME="docuchat"
BUCKET_NAME="docuchat_storage"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Setting up DocuChat deployment ===${NC}"

# 1. Create GCS bucket if it doesn't exist
echo -e "\n${GREEN}Creating GCS bucket for persistence...${NC}"
gsutil ls -b gs://$BUCKET_NAME > /dev/null 2>&1 || gsutil mb -l $REGION gs://$BUCKET_NAME

# 2. Build and push the Docker image to Google Container Registry
echo -e "\n${GREEN}Building and pushing Docker image...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 3. Deploy to Cloud Run with GCS volume mounting
echo -e "\n${GREEN}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --port 8080 \
    --allow-unauthenticated \
    --execution-environment gen2 \
    --memory 2Gi \
    --set-env-vars GCS_BUCKET_NAME=$BUCKET_NAME,PROJECT_ID=$PROJECT_ID \
    --add-volume=name=gcs-volume,type=cloud-storage,bucket=$BUCKET_NAME \
    --add-volume-mount=volume=gcs-volume,mount-path=/gcs

echo -e "\n${YELLOW}=== Deployment complete! ===${NC}"
echo -e "Your DocuChat application is now deployed to Cloud Run."
echo -e "Don't forget to set your OpenAI API key as an environment variable in the Cloud Console.\n"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format="value(status.url)"