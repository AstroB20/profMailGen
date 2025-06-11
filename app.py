from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_very_secret_key_in_dev_change_for_prod')

model = genai.GenerativeModel(model_name='models/gemini-1.5-pro-latest', 
                            system_instruction='You are a helpful assistant that writes professional emails. Talk in first name basis. Try to be as short and specific as possible.')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/reply-page')
def reply_page():
    return render_template('reply.html')

@app.route('/generate', methods=['POST'])
def generate_email():
    data = request.json
    name = data.get("name")
    context = data.get("context")
    relationship = data.get("relationship")

    prompt = (
        f"Write a professional email to {name}. "
        f"The context of the email is: {context}. "
        f"My relationship with {name} is: {relationship}. "
        f"Ensure the tone suits that relationship."
    )

    try:
        response = model.generate_content(prompt)
        return jsonify({"email": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reply', methods=['POST'])
def generate_reply():
    data = request.json
    original_email = data.get("original_email")
    intent = data.get("intent")
    relationship = data.get("relationship")

    prompt = (
        f"You received the following email:\n\n{original_email}\n\n"
        f"Your intent for the reply is:\n{intent}\n\n"
        f"Your relationship with the sender is: {relationship}.\n"
        f"Generate a formal reply email that reflects this context and maintains a professional tone."
    )

    try:
        response = model.generate_content(prompt)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/optimize-reply', methods=['POST'])
def optimize_reply():
    data = request.json
    reply_text = data.get('reply')
    optimize_type = data.get('optimize_type')

    if not reply_text or optimize_type not in ['longer', 'shorter']:
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
    try:
        response = model.generate_content(prompt)
        optimized_reply = response.text.strip()
        return jsonify({"optimized_reply": optimized_reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
