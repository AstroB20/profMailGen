from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
import sys
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EmailGenerator:
    def __init__(self):
        """Initialize the EmailGenerator with Gemini AI configuration."""
        self._configure_gemini()
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def _configure_gemini(self) -> None:
        """Configure Gemini AI with API key from environment variables."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=api_key)
        logger.info("Successfully initialized Gemini model")

    def generate_email(self, name: str, context: str, relationship: str) -> str:
        """Generate a professional email based on given parameters."""
        prompt = (
            f"Write a professional email to {name}. "
            f"The context of the email is: {context}. "
            f"My relationship with {name} is: {relationship}. "
            f"Ensure the tone suits that relationship. Keep it concise and professional."
        )
        response = self.model.generate_content(prompt)
        return response.text

    def generate_reply(self, original_email: str, intent: str, relationship: str) -> str:
        """Generate a reply to an existing email."""
        prompt = (
            f"You received the following email:\n\n{original_email}\n\n"
            f"Your intent for the reply is:\n{intent}\n\n"
            f"Your relationship with the sender is: {relationship}.\n"
            f"Generate a formal reply email that reflects this context and maintains a professional tone."
        )
        response = self.model.generate_content(prompt)
        return response.text

    def optimize_reply(self, reply_text: str, optimize_type: str) -> str:
        """Optimize an existing reply to be longer or shorter."""
        if optimize_type not in ['longer', 'shorter']:
            raise ValueError("optimize_type must be either 'longer' or 'shorter'")

        prompt = (
            f"Here is an email reply:\n\n{reply_text}\n\n"
            f"Please rewrite it to be more {'detailed and longer' if optimize_type == 'longer' else 'concise and shorter'}, "
            "while keeping the professional tone."
        )
        response = self.model.generate_content(prompt)
        return response.text.strip()

# Create Flask app
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your_very_secret_key_in_dev_change_for_prod'),
    JSON_AS_ASCII=False
)

# Initialize email generator
try:
    email_generator = EmailGenerator()
except Exception as e:
    logger.error(f"Failed to initialize email generator: {str(e)}")
    raise

@app.route('/')
def home() -> str:
    """Render the home page."""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/reply-page')
def reply_page() -> str:
    """Render the reply page."""
    try:
        return render_template('reply.html')
    except Exception as e:
        logger.error(f"Error rendering reply.html: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/generate', methods=['POST'])
def generate_email() -> tuple[Dict[str, Any], int]:
    """Generate a new email based on provided parameters."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["name", "context", "relationship"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        email = email_generator.generate_email(
            name=data["name"],
            context=data["context"],
            relationship=data["relationship"]
        )
        return jsonify({"email": email})
    except Exception as e:
        logger.error(f"Error in generate_email: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reply', methods=['POST'])
def generate_reply() -> tuple[Dict[str, Any], int]:
    """Generate a reply to an existing email."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["original_email", "intent", "relationship"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        reply = email_generator.generate_reply(
            original_email=data["original_email"],
            intent=data["intent"],
            relationship=data["relationship"]
        )
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"Error in generate_reply: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/optimize-reply', methods=['POST'])
def optimize_reply() -> tuple[Dict[str, Any], int]:
    """Optimize an existing reply to be longer or shorter."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if not data.get('reply') or data.get('optimize_type') not in ['longer', 'shorter']:
            return jsonify({"error": "Invalid input"}), 400

        optimized_reply = email_generator.optimize_reply(
            reply_text=data['reply'],
            optimize_type=data['optimize_type']
        )
        return jsonify({"optimized_reply": optimized_reply})
    except Exception as e:
        logger.error(f"Error in optimize_reply: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
