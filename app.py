from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import google.generativeai as genai
import os
from dotenv import load_dotenv
from models import db, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_very_secret_key_in_dev_change_for_prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///profmailgen_users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # The function name of your login route

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

model = genai.GenerativeModel(model_name='models/gemini-1.5-pro-latest', system_instruction='You are a helpful assistant that writes professional emails.Talk in first name basis. Try to be as short and specific as possible.')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        description = request.form.get('description')
        if not username or not password or not description:
            flash('Username, password, and description are required.', 'danger')
            return redirect(url_for('register'))
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'warning')
            return redirect(url_for('register'))
        try:
            prompt = f"Rewrite this user bio to sound professional and concise: '{description}'"
            response = model.generate_content(prompt)
            cleaned_description = response.text.strip()
        except Exception as e:
            flash(f"Error enhancing description: {e}", 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, description=cleaned_description)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html') # You'll need to create this HTML file

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

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
@login_required
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
@login_required
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

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables() # Ensure tables are created before running
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
