import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------------------
# Logging & config
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
load_dotenv()

# ----------------------------
# Flask app
# ----------------------------
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev_change_me"),
    JSON_AS_ASCII=False,
)

# ----------------------------
# Database config (SQLite)
# ----------------------------
DEFAULT_SQLITE = "sqlite:///conversations.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------------------
# Models (Enhanced with Context Summary)
# ----------------------------
class Contact(db.Model):
    __tablename__ = "contacts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(320))
    designation = db.Column(db.String(255))
    company = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship("Conversation", backref="contact", lazy=True)

class Conversation(db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=False)
    title = db.Column(db.String(255))
    status = db.Column(db.String(50), default="active")
    context_summary = db.Column(db.Text)  # 🧠 NEW: Rolling context summary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship("ConversationMessage", backref="conversation", lazy=True, order_by="ConversationMessage.sequence")

class ConversationMessage(db.Model):
    __tablename__ = "conversation_messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.String(20), nullable=False)  # 'sent' or 'received'
    sequence = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------
# Enhanced Gemini wrapper with Context Management
# ----------------------------
class EmailGenerator:
    def __init__(self):
        self._configure_gemini()
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

    def _configure_gemini(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=api_key)
        logger.info("Successfully initialized Gemini model")

    def generate_conversation_summary(self, messages: list) -> str:
        """Generate a concise summary of the conversation history"""
        if not messages:
            return ""
        
        # Build conversation history for summarization
        history_text = ""
        for msg in sorted(messages, key=lambda m: m.sequence):
            sender = "You" if msg.direction == "sent" else "Contact"
            history_text += f"{sender}: {msg.content}\n\n"
        
        prompt = f"""
Summarize this email conversation concisely in 2-3 sentences. Focus on:
- Main topics discussed
- Key decisions or agreements made  
- Current status or next steps
- Overall relationship tone

Conversation:
{history_text}

Summary:
"""
        
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def generate_contextual_reply(self, contact: Contact, context_summary: str, recent_messages: list, intent: str) -> str:
        """Generate reply using context summary + recent messages instead of full history"""
        
        # Get the last few messages for immediate context
        recent_context = ""
        for msg in recent_messages[-3:]:  # Last 3 messages for immediate context
            sender = "You" if msg.direction == "sent" else contact.name
            recent_context += f"{sender}: {msg.content}\n\n"
        
        prompt = f"""
You are helping compose a professional email reply in an ongoing conversation.

Contact Information:
- Name: {contact.name}
- Role: {contact.designation or 'Not specified'} 
- Company: {contact.company or 'Not specified'}
- Email: {contact.email or 'Not specified'}

Conversation Context Summary:
{context_summary or 'This is the start of the conversation.'}

Recent Exchange:
{recent_context}

Your intent for the reply: {intent}

Generate a professional email response that:
1. Maintains appropriate tone for their professional role
2. References the conversation context appropriately
3. Directly addresses their latest message
4. Accomplishes the stated intent
5. Continues the conversation naturally
6. Is ready to copy and paste into an email

Email Response:
"""
        
        response = self.model.generate_content(prompt)
        return response.text.strip()

# Initialize generator
try:
    email_generator = EmailGenerator()
except Exception as e:
    logger.error(f"Failed to initialize email generator: {str(e)}")
    raise

# ----------------------------
# Context Management Helper Functions
# ----------------------------
def update_conversation_context(conversation: Conversation) -> str:
    """Update the conversation's context summary after new messages"""
    try:
        messages = ConversationMessage.query.filter_by(
            conversation_id=conversation.id
        ).order_by(ConversationMessage.sequence).all()
        
        if len(messages) <= 1:
            # Not enough messages to summarize yet
            return ""
        
        # Generate new summary
        new_summary = email_generator.generate_conversation_summary(messages)
        
        # Update conversation
        conversation.context_summary = new_summary
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated context summary for conversation {conversation.id}")
        return new_summary
        
    except Exception as e:
        logger.error(f"Error updating conversation context: {str(e)}")
        return conversation.context_summary or ""

# ----------------------------
# DB bootstrap
# ----------------------------
with app.app_context():
    db.create_all()

# ----------------------------
# Routes - Pages (same as before)
# ----------------------------
@app.route("/")
def home():
    try:
        return render_template("conversations.html")
    except Exception as e:
        logger.error(f"Error rendering conversations.html: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route("/conversations")
def conversations_page():
    try:
        return render_template("conversations.html")
    except Exception as e:
        logger.error(f"Error rendering conversations.html: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route("/conversation/<int:conversation_id>")
def conversation_thread_page(conversation_id):
    try:
        return render_template("conversation_thread.html")
    except Exception as e:
        logger.error(f"Error rendering conversation_thread.html: {str(e)}")
        return f"Error: {str(e)}", 500

# ----------------------------
# API Routes - Contacts (same as before)
# ----------------------------
@app.route("/api/contacts", methods=["GET", "POST"])
def contacts():
    if request.method == "POST":
        try:
            data = request.get_json() or {}
            required_fields = ["name"]
            
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400
            
            contact = Contact(
                name=data["name"],
                email=data.get("email"),
                designation=data.get("designation"),
                company=data.get("company"),
                notes=data.get("notes")
            )
            db.session.add(contact)
            db.session.commit()
            
            logger.info(f"Contact created: {contact.name}")
            return jsonify({
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "designation": contact.designation,
                "company": contact.company
            })
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # GET: list contacts
    try:
        contacts = Contact.query.all()
        result = []
        for contact in contacts:
            result.append({
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "designation": contact.designation,
                "company": contact.company,
                "created_at": contact.created_at.isoformat(),
                "conversation_count": len(contact.conversations)
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing contacts: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# API Routes - Conversations (same as before)
# ----------------------------
@app.route("/api/conversations", methods=["GET", "POST"])
def conversations_api():
    if request.method == "POST":
        try:
            data = request.get_json() or {}
            required_fields = ["contact_id", "title"]
            
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400
            
            # Verify contact exists
            contact = Contact.query.get(data["contact_id"])
            if not contact:
                return jsonify({"error": "Contact not found"}), 404
            
            conversation = Conversation(
                contact_id=data["contact_id"],
                title=data["title"],
                status=data.get("status", "active"),
                context_summary=""  # Start with empty summary
            )
            db.session.add(conversation)
            db.session.commit()
            
            logger.info(f"Conversation created: {conversation.title} with {contact.name}")
            return jsonify({
                "id": conversation.id,
                "title": conversation.title,
                "status": conversation.status,
                "contact_name": contact.name
            })
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # GET: list conversations (same as before)
    try:
        conversations = db.session.query(Conversation).join(Contact).all()
        result = []
        for conversation in conversations:
            last_message = ConversationMessage.query.filter_by(
                conversation_id=conversation.id
            ).order_by(ConversationMessage.sequence.desc()).first()
            
            result.append({
                "id": conversation.id,
                "title": conversation.title,
                "status": conversation.status,
                "contact_name": conversation.contact.name,
                "contact_company": conversation.contact.company,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "message_count": len(conversation.messages),
                "last_message": last_message.content[:100] + "..." if last_message else "No messages",
                "context_summary": conversation.context_summary[:150] + "..." if conversation.context_summary else "No context yet"
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        messages = ConversationMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(ConversationMessage.sequence).all()
        
        result = {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status,
            "context_summary": conversation.context_summary,  # Include context summary
            "contact": {
                "id": conversation.contact.id,
                "name": conversation.contact.name,
                "email": conversation.contact.email,
                "designation": conversation.contact.designation,
                "company": conversation.contact.company
            },
            "messages": []
        }
        
        for message in messages:
            result["messages"].append({
                "id": message.id,
                "content": message.content,
                "direction": message.direction,
                "sequence": message.sequence,
                "created_at": message.created_at.isoformat()
            })
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# API Routes - Enhanced Messages with Context Update
# ----------------------------
@app.route("/api/conversations/<int:conversation_id>/messages", methods=["POST"])
def add_message(conversation_id):
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        data = request.get_json() or {}
        
        content = data.get("content")
        direction = data.get("direction")
        
        if not content or direction not in ["sent", "received"]:
            return jsonify({"error": "Invalid content or direction"}), 400
        
        # Get next sequence number
        last_message = ConversationMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(ConversationMessage.sequence.desc()).first()
        
        next_sequence = (last_message.sequence + 1) if last_message else 1
        
        message = ConversationMessage(
            conversation_id=conversation_id,
            content=content,
            direction=direction,
            sequence=next_sequence
        )
        
        db.session.add(message)
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 🧠 Update context summary after adding message
        update_conversation_context(conversation)
        
        logger.info(f"Message added to conversation {conversation_id}: {direction}")
        return jsonify({
            "id": message.id,
            "content": message.content,
            "direction": message.direction,
            "sequence": message.sequence
        })
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/conversations/<int:conversation_id>/generate-reply", methods=["POST"])
def generate_reply(conversation_id):
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        data = request.get_json() or {}
        
        intent = data.get("intent")
        if not intent:
            return jsonify({"error": "Missing intent"}), 400
        
        # Get recent messages for immediate context
        recent_messages = ConversationMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(ConversationMessage.sequence).all()
        
        # 🧠 Generate reply using context summary + recent messages
        reply = email_generator.generate_contextual_reply(
            conversation.contact, 
            conversation.context_summary,
            recent_messages, 
            intent
        )
        
        # Save reply as a message
        next_sequence = (recent_messages[-1].sequence + 1) if recent_messages else 1
        
        message = ConversationMessage(
            conversation_id=conversation_id,
            content=reply,
            direction="sent",
            sequence=next_sequence
        )
        
        db.session.add(message)
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 🧠 Update context summary after generating reply
        update_conversation_context(conversation)
        
        logger.info(f"Reply generated for conversation {conversation_id} using context summary")
        return jsonify({
            "reply": reply,
            "message_id": message.id,
            "sequence": message.sequence,
            "context_updated": True
        })
    except Exception as e:
        logger.error(f"Error generating reply: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Health check
# ----------------------------
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({
        "status": "ok", 
        "time": datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
