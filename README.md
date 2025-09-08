# AI Conversation Manager

A cloud-deployed Streamlit web application to manage professional contacts and multi-threaded email conversations with AI-assisted reply generation.

## Features

- **Contact Management:** Add and maintain detailed profiles for multiple contacts including name, email, role, company, and notes.
- **Conversation Threads:** Create and manage multiple conversation threads per contact to track different discussions separately.
- **Messaging Interface:** Chat-style sent and received messages allowing easy tracking of correspondence history.
- **AI Reply Generation:** Integrated with Google Gemini AI to generate professional replies based on the conversational context and user intent.
- **User Control:** Review, edit, and manually add AI-generated replies ensuring professional and personalized communication.
- **Cloud Deployment:** Runs on Google Cloud Run for scalable, serverless hosting accessible anywhere securely.
- **Lightweight Database:** Uses SQLite for data persistence within the ephemeral Cloud Run environment.

## Technology Stack

- Python 3.x, Streamlit UI Framework
- Google Gemini AI API for generative intents
- SQLite for local lightweight storage
- Docker containerization and Google Cloud Run cloud deployment

## Getting Started

### Prerequisites

- Google Cloud account with Cloud Run enabled
- Gemini API key for AI integration
- `gcloud` CLI installed (optional for CLI deployments)

### Deployment

1. Clone the repository.
2. Set the `GEMINI_API_KEY` environment variable in Cloud Run settings.
3. Build and deploy the Docker container image to Cloud Run.
4. Access the public URL provided by Cloud Run for your app.

### Running Locally

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_api_key
streamlit run conversation_app.py
```

## Usage

- Add contacts with business details.
- Start multiple conversation threads per contact.
- Add sent and received messages.
- Generate AI-assisted replies by specifying the purpose of your response.
- Copy, edit, and send AI-generated replies seamlessly.

## Why It Matters

This application empowers professionals and teams to efficiently organize complex communications. By automating the drafting of well-contextualized professional replies, it saves time, ensures consistent tone, and enhances follow-up accuracy — key for relationship management and business productivity.
