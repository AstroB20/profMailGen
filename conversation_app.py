import streamlit as st
import sqlite3
import datetime
from typing import List, Dict
import google.generativeai as genai
import os

# Configure Streamlit
st.set_page_config(
    page_title="AI Conversation Manager", 
    page_icon="💬", 
    layout="wide"
)

# Configure Gemini AI
@st.cache_resource
def setup_ai():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Please set GEMINI_API_KEY environment variable in Cloud Run")
        st.stop()
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")

model = setup_ai()

# Database setup
@st.cache_resource
def init_database():
    db_path = '/tmp/conversations.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute('PRAGMA foreign_keys = ON')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            designation TEXT DEFAULT '',
            company TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            contact_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            context_summary TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('sent', 'received')),
            sequence INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    return conn

db = init_database()

# Minimal CSS (Only for chat bubbles)
st.markdown("""
<style>
.user-message {
    background: #2196F3;
    color: white;
    padding: 12px 16px;
    border-radius: 18px;
    border-bottom-right-radius: 4px;
    margin: 8px 0;
    max-width: 70%;
    float: right;
    clear: both;
}

.contact-message {
    background: #e4e6ea;
    color: #050505;
    padding: 12px 16px;
    border-radius: 18px;
    border-bottom-left-radius: 4px;
    margin: 8px 0;
    max-width: 70%;
    float: left;
    clear: both;
}

.message-time {
    font-size: 11px;
    opacity: 0.7;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# Helper functions
def add_contact(name, email="", designation="", company="", notes=""):
    cursor = db.execute(
        "INSERT INTO contacts (name, email, designation, company, notes) VALUES (?, ?, ?, ?, ?)",
        (name, email or "", designation or "", company or "", notes or "")
    )
    db.commit()
    return cursor.lastrowid

def get_contacts():
    return db.execute(
        "SELECT id, name, email, designation, company, notes, created_at FROM contacts ORDER BY name"
    ).fetchall()

def get_contact(contact_id):
    return db.execute(
        "SELECT id, name, email, designation, company, notes, created_at FROM contacts WHERE id = ?", 
        (contact_id,)
    ).fetchone()

def get_conversations_for_contact(contact_id):
    return db.execute("""
        SELECT c.id, c.contact_id, c.title, c.status, c.context_summary, 
               c.created_at, c.updated_at, COUNT(m.id) as message_count,
               MAX(m.created_at) as last_message_time
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.contact_id = ?
        GROUP BY c.id, c.contact_id, c.title, c.status, c.context_summary, c.created_at, c.updated_at
        ORDER BY c.updated_at DESC
    """, (contact_id,)).fetchall()

def add_conversation(contact_id, title):
    cursor = db.execute(
        "INSERT INTO conversations (contact_id, title) VALUES (?, ?)",
        (contact_id, title)
    )
    db.commit()
    return cursor.lastrowid

def get_conversation(conversation_id):
    return db.execute("""
        SELECT c.id, c.contact_id, c.title, c.status, c.context_summary, 
               c.created_at, c.updated_at, ct.name, ct.email, ct.designation, ct.company
        FROM conversations c
        JOIN contacts ct ON c.contact_id = ct.id
        WHERE c.id = ?
    """, (conversation_id,)).fetchone()

def add_message(conversation_id, content, direction):
    result = db.execute(
        "SELECT MAX(sequence) FROM messages WHERE conversation_id = ?", 
        (conversation_id,)
    ).fetchone()
    next_seq = (result[0] or 0) + 1
    
    cursor = db.execute(
        "INSERT INTO messages (conversation_id, content, direction, sequence) VALUES (?, ?, ?, ?)",
        (conversation_id, content, direction, next_seq)
    )
    
    db.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    
    db.commit()
    return cursor.lastrowid

def get_messages(conversation_id):
    return db.execute(
        "SELECT id, conversation_id, content, direction, sequence, created_at FROM messages WHERE conversation_id = ? ORDER BY sequence",
        (conversation_id,)
    ).fetchall()

def generate_ai_reply_content(conversation_id, intent):
    conv = get_conversation(conversation_id)
    messages = get_messages(conversation_id)
    
    conv_id, contact_id, title, status, context_summary, created_at, updated_at, contact_name, email, designation, company = conv
    
    recent_context = ""
    for msg in messages[-5:]:
        msg_id, conv_id, content, direction, sequence, msg_created_at = msg
        sender = "You" if direction == "sent" else contact_name
        recent_context += f"{sender}: {content}\n\n"
    
    prompt = f"""
You are helping compose a professional email reply in an ongoing conversation.

Contact Information:
- Name: {contact_name}
- Role: {designation or 'Not specified'}
- Company: {company or 'Not specified'}

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
    
    response = model.generate_content(prompt)
    return response.text.strip()

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "contacts"
if "current_contact" not in st.session_state:
    st.session_state.current_contact = None
if "current_conversation" not in st.session_state:
    st.session_state.current_conversation = None
if "ai_reply_content" not in st.session_state:
    st.session_state.ai_reply_content = ""
if "show_ai_reply" not in st.session_state:
    st.session_state.show_ai_reply = False
if "sent_message_text" not in st.session_state:
    st.session_state.sent_message_text = ""

# Navigation
def navigate_to(page, contact_id=None, conversation_id=None):
    st.session_state.page = page
    if contact_id:
        st.session_state.current_contact = contact_id
    if conversation_id:
        st.session_state.current_conversation = conversation_id
    st.rerun()

# Main app
st.title("💬 AI Conversation Manager")

# PAGE 1: CONTACTS LIST (SIMPLE VERSION)
if st.session_state.page == "contacts":
    st.header("👥 Your Contacts")
    
    # Add Contact Section
    with st.expander("➕ Add New Contact"):
        with st.form("add_contact"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name*")
                email = st.text_input("Email")
            with col2:
                designation = st.text_input("Job Title")
                company = st.text_input("Company")
            
            notes = st.text_area("Notes (optional)")
            
            if st.form_submit_button("Create Contact"):
                if name.strip():
                    contact_id = add_contact(name.strip(), email.strip(), 
                                           designation.strip(), company.strip(), notes.strip())
                    st.success(f"✅ Created contact: {name}")
                    st.rerun()
                else:
                    st.error("Name is required")
    
    st.divider()
    
    # Simple Contact Display (NO HTML)
    contacts = get_contacts()
    
    if contacts:
        for contact in contacts:
            contact_id, name, email, designation, company, notes, created_at = contact
            
            # Simple layout - just name and button
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.write(f"**👤 {name}**")
            
            with col2:
                if st.button("View Conversations", key=f"view_{contact_id}"):
                    navigate_to("conversations", contact_id)
            
            st.divider()
    else:
        st.info("📭 No contacts yet. Add your first contact above!")

# PAGE 2: CONVERSATIONS FOR SELECTED CONTACT
elif st.session_state.page == "conversations":
    contact = get_contact(st.session_state.current_contact)
    
    if contact:
        contact_id, name, email, designation, company, notes, created_at = contact
        
        # Navigation
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button("← Back"):
                navigate_to("contacts")
        
        st.header(f"💬 Conversations with {name}")
        
        # New conversation section
        with st.expander("🆕 Start New Conversation"):
            with st.form("new_conversation"):
                conv_title = st.text_input("Conversation Topic", 
                                          placeholder="e.g., Project Discussion, Meeting Follow-up")
                
                if st.form_submit_button("Create Conversation"):
                    if conv_title.strip():
                        conv_id = add_conversation(contact_id, conv_title.strip())
                        st.success(f"✅ Created conversation: {conv_title}")
                        navigate_to("chat", conversation_id=conv_id)
                    else:
                        st.error("Please enter a conversation topic")
        
        st.divider()
        
        # Display conversations
        conversations = get_conversations_for_contact(contact_id)
        
        if conversations:
            st.subheader("📋 Conversation History")
            
            for conv in conversations:
                conv_id, contact_id, title, status, context_summary, created_at, updated_at, message_count, last_message_time = conv
                
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.write(f"**💬 {title}**")
                    st.caption(f"📊 {message_count or 0} messages • Status: {status}")
                
                with col2:
                    if st.button("Open Chat", key=f"open_{conv_id}"):
                        navigate_to("chat", conversation_id=conv_id)
                
                st.divider()
        else:
            st.info(f"🔍 No conversations with {name} yet. Start a new conversation above!")

# PAGE 3: CHAT THREAD
elif st.session_state.page == "chat":
    conv = get_conversation(st.session_state.current_conversation)
    
    if conv:
        conv_id, contact_id, title, status, context_summary, created_at, updated_at, contact_name, email, designation, company = conv
        
        # Navigation
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button("← Back"):
                navigate_to("conversations", contact_id)
        
        st.header(f"💬 {title}")
        st.caption(f"With {contact_name}")
        
        # Display messages
        messages = get_messages(st.session_state.current_conversation)
        
        st.subheader("Chat Messages")
        
        if messages:
            for msg in messages:
                msg_id, conv_id, content, direction, sequence, created_at = msg
                timestamp = datetime.datetime.fromisoformat(created_at).strftime("%H:%M")
                
                if direction == 'received':
                    st.markdown(f"""
                    <div class="contact-message">
                        {content}
                        <div class="message-time">{contact_name} • {timestamp}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="user-message">
                        {content}
                        <div class="message-time">You • {timestamp}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown('<div style="clear: both;"></div>', unsafe_allow_html=True)
        else:
            st.info("💭 No messages yet. Start the conversation below!")
        
        st.divider()
        
        # AI Reply section
        st.subheader("🤖 AI Reply Assistant")
        
        with st.form("ai_reply", clear_on_submit=True):
            intent = st.text_input("What do you want to accomplish with your reply?", 
                                  placeholder="e.g., Schedule a meeting, Ask for project update")
            
            if st.form_submit_button("🎯 Generate AI Reply"):
                if intent.strip():
                    with st.spinner("🤖 AI is crafting your reply..."):
                        try:
                            reply_text = generate_ai_reply_content(st.session_state.current_conversation, intent.strip())
                            
                            st.session_state.ai_reply_content = reply_text
                            st.session_state.show_ai_reply = True
                            
                            st.success("✅ AI Reply Generated!")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ AI Error: {str(e)}")
                else:
                    st.error("Please describe what you want to accomplish")
        
        # Display AI reply
        if st.session_state.show_ai_reply and st.session_state.ai_reply_content:
            st.subheader("📋 AI Generated Reply")
            st.info("💡 Copy this reply or click 'Use This Reply' to paste it in your message box below.")
            
            st.code(st.session_state.ai_reply_content)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Use This Reply"):
                    st.session_state.sent_message_text = st.session_state.ai_reply_content
                    st.success("💬 AI reply copied to your message box!")
                    st.rerun()
                    
            with col2:
                if st.button("🔄 Regenerate"):
                    st.session_state.show_ai_reply = False
                    st.rerun()
                    
            with col3:
                if st.button("❌ Clear"):
                    st.session_state.ai_reply_content = ""
                    st.session_state.show_ai_reply = False
                    st.rerun()
        
        st.divider()
        
        # Input section
        st.subheader("Add Messages")
        
        col1, col2 = st.columns(2)
        
        # Left - Received messages
        with col1:
            st.markdown("**📥 Message from contact**")
            with st.form("add_received", clear_on_submit=True):
                received_text = st.text_area("Paste what they sent:", height=120)
                
                if st.form_submit_button("Add Received Message"):
                    if received_text.strip():
                        add_message(st.session_state.current_conversation, 
                                   received_text.strip(), "received")
                        st.success("✅ Message added!")
                        st.rerun()
                    else:
                        st.error("Please enter a message")
        
        # Right - Sent messages
        with col2:
            st.markdown("**📤 Your message**")
            
            sent_text = st.text_area("Type or paste your message:", 
                                   height=120,
                                   value=st.session_state.sent_message_text,
                                   key=f"sent_textarea_{st.session_state.current_conversation}")
            
            st.session_state.sent_message_text = sent_text
            
            if st.button("Add Sent Message"):
                if sent_text.strip():
                    add_message(st.session_state.current_conversation, 
                               sent_text.strip(), "sent")
                    st.success("✅ Message added!")
                    
                    # Clear after successful send
                    st.session_state.sent_message_text = ""
                    st.session_state.ai_reply_content = ""
                    st.session_state.show_ai_reply = False
                    
                    st.rerun()
                else:
                    st.error("Please enter a message")

# Footer
st.markdown("---")
st.caption("💡 Built with Streamlit & Gemini AI")
