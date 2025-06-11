# Professional Email Generator

A Flask application that generates professional emails using Google's Generative AI.

## Deployment to Google Cloud Run

### Prerequisites

1. Google Cloud SDK installed
2. Docker installed
3. A Google Cloud project created
4. Git repository set up

### Deployment Steps

1. **Enable required APIs**

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

2. **Set your project ID**

```bash
gcloud config set project YOUR_PROJECT_ID
```

3. **Build and deploy using Cloud Build**

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/profmailgen
gcloud run deploy profmailgen \
  --image gcr.io/YOUR_PROJECT_ID/profmailgen \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

4. **Set environment variables**
   After deployment, set your environment variables in the Google Cloud Console:

- Go to Cloud Run > profmailgen > Edit & Deploy New Revision
- Under "Variables & Secrets", add your environment variables:
  - `GOOGLE_API_KEY`

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python app.py
```

The application will be available at `http://localhost:5000`
