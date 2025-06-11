from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Check if API key is available
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=api_key)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_very_secret_key_in_dev_change_for_prod')

# Initialize the model
try:
    model = genai.GenerativeModel('gemini-pro')
    logger.info("Successfully initialized Gemini model")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    raise

@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return "Internal Server Error", 500

@app.route('/reply-page')
def reply_page():
    try:
        return render_template('reply.html')
    except Exception as e:
        logger.error(f"Error in reply_page route: {str(e)}")
        return "Internal Server Error", 500

@app.route('/generate', methods=['POST'])
def generate_email():
    try:
        data = request.json
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        name = data.get("name")
        context = data.get("context")
        relationship = data.get("relationship")

        if not all([name, context, relationship]):
            logger.error("Missing required fields")
            return jsonify({"error": "Missing required fields"}), 400

        prompt = (
            f"Write a professional email to {name}. "
            f"The context of the email is: {context}. "
            f"My relationship with {name} is: {relationship}. "
            f"Ensure the tone suits that relationship. Keep it concise and professional."
        )

        logger.info(f"Generating email with prompt: {prompt}")
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            logger.error("Empty response from Gemini API")
            return jsonify({"error": "Failed to generate email"}), 500

        return jsonify({"email": response.text})
    except Exception as e:
        logger.error(f"Error in generate_email: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reply', methods=['POST'])
def generate_reply():
    try:
        data = request.json
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        original_email = data.get("original_email")
        intent = data.get("intent")
        relationship = data.get("relationship")

        if not all([original_email, intent, relationship]):
            logger.error("Missing required fields")
            return jsonify({"error": "Missing required fields"}), 400

        prompt = (
            f"You received the following email:\n\n{original_email}\n\n"
            f"Your intent for the reply is:\n{intent}\n\n"
            f"Your relationship with the sender is: {relationship}.\n"
            f"Generate a formal reply email that reflects this context and maintains a professional tone."
        )

        logger.info(f"Generating reply with prompt: {prompt}")
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            logger.error("Empty response from Gemini API")
            return jsonify({"error": "Failed to generate reply"}), 500

        return jsonify({"reply": response.text})
    except Exception as e:
        logger.error(f"Error in generate_reply: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/optimize-reply', methods=['POST'])
def optimize_reply():
    try:
        data = request.json
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        reply_text = data.get('reply')
        optimize_type = data.get('optimize_type')

        if not reply_text or optimize_type not in ['longer', 'shorter']:
            logger.error("Invalid input for optimize_reply")
            return jsonify({"error": "Invalid input"}), 400

        if optimize_type == 'longer':
            prompt = (
                f"Here is an email reply:\n\n{reply_text}\n\n"
                "Please rewrite it to be more detailed and longer, "
                "while keeping the professional tone."
            )
        else:  
            prompt = (
                f"Here is an email reply:\n\n{reply_text}\n\n"
                "Please rewrite it to be more concise and shorter, "
                "while keeping the professional tone."
            )

        logger.info(f"Optimizing reply with prompt: {prompt}")
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            logger.error("Empty response from Gemini API")
            return jsonify({"error": "Failed to optimize reply"}), 500

        optimized_reply = response.text.strip()
        return jsonify({"optimized_reply": optimized_reply})
    except Exception as e:
        logger.error(f"Error in optimize_reply: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
