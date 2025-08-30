import streamlit as st
import sqlite3
import datetime
from typing import List, Dict
import google.generativeai as genai
import os

# Configure Streamlit with clean layout
st.set_page_config(
    page_title="AI Conversation Manager", 
    page_icon="💬", 
    layout="wide",
    initial_sidebar_state="collapsed"
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

# Modern Clean CSS
st.markdown("""
<style>
/* Global styles */
.main > div {
    padding-top: 2rem;
}

/* Contact Cards */
.contact-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin: 16px 0;
    border: 1px solid #e1e5e9;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: all 0.2s ease;
}

.contact-card:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
}

.contact-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 8px;
}

.contact-detail {
    color: #6b7280;
    font-size: 0.875rem;
    margin: 4px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.contact-stats {
    background: #f8fafc;
    padding: 12px;
    border-radius: 8px;
    margin-top: 12px;
    border-left: 4px solid #3b82f6;
}

/* Conversation Cards */
.conversation-card {
    background: white;
    border-radius: 10px;
    padding: 20px;
    margin: 12px 0;
    border-left: 4px solid #3b82f6;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.conversation-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 8px;
}

.conversation-meta {
    color: #6b7280;
    font-size: 0.8rem;
}

/* Chat Messages */
.user-message {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    padding: 12px 16px;
    border-radius: 18px;
    border-bottom-right-radius: 4px;
    margin: 8px 0;
    max-width: 70%;
    float: right;
    clear: both;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.contact-message {
    background: #f1f5f9;
    color: #1e293b;
    padding: 12px 16px;
    border-radius: 18px;
    border-bottom-left-radius: 4px;
    margin: 8px 0;
    max-width: 70%;
    float: left;
    clear: both;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.message-time {
    font-size: 11px;
    opacity: 0.7;
    margin-top: 4px;
}

/* AI Reply Box */
.ai-reply-box {
    background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
    border: 2px solid #10b981;
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
}

.ai-reply-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #059669;
    margin-bottom: 12px;
}

/* Header styling */
.page-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    text-align: center;
}

.page-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.page-subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
}

/* Section headers */
.section-header {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1f2937;
    margin: 1.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e5e7eb;
}

/* Stats badges */
.stat-badge {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-right: 8px;
}

.success-badge {
    background: #dcfce7;
    color: #166534;
}

.warning-badge {
    background: #fef3c7;
    color: #92400e;
}

/* Form improvements */
.stTextInput > div > div > input {
    border-radius: 8px;
    border: 1px solid #d1d5db;
    padding: 0.75rem;
}

.stTextArea > div > div > textarea {
    border-radius: 8px;
    border: 1px solid #d1d5db;
    padding: 0.75rem;
}

/* Button improvements */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s ease;
}

/* Responsive design */
@media (max-width: 768px) {
    .contact-card {
        padding: 16px;
        margin: 12px 0;
    }
    
    .user-message, .contact-message {
        max-width: 85%;
    }
    
    .page-title {
        font-size: 2rem;
    }
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

# Main App Header
st.markdown("""
<div class="page-header">
    <div class="page-title">💬 AI Conversation Manager</div>
    <div class="page-subtitle">Manage your professional email conversations with AI assistance</div>
</div>
""", unsafe_allow_html=True)

# PAGE 1: CONTACTS LIST
if st.session_state.page == "contacts":
    
    # Add Contact Section
    with st.expander("➕ Add New Contact", expanded=False):
        with st.form("add_contact"):
            st.markdown("#### Contact Information")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *", placeholder="Enter contact's name")
                email = st.text_input("Email Address", placeholder="contact@company.com")
            with col2:
                designation = st.text_input("Job Title", placeholder="e.g., Project Manager")
                company = st.text_input("Company", placeholder="e.g., Acme Corp")
            
            notes = st.text_area("Notes (Optional)", placeholder="Additional information about this contact...")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col2:
                if st.form_submit_button("✅ Create Contact", use_container_width=True):
                    if name.strip():
                        contact_id = add_contact(name.strip(), email.strip(), 
                                               designation.strip(), company.strip(), notes.strip())
                        st.success(f"✅ Successfully added {name} to your contacts!")
                        st.rerun()
                    else:
                        st.error("Please enter a contact name")
    
    # Display contacts
    contacts = get_contacts()
    
    if contacts:
        st.markdown(f'<div class="section-header">👥 Your Contacts ({len(contacts)})</div>', unsafe_allow_html=True)
        
        # Contact grid
        for i, contact in enumerate(contacts):
            contact_id, name, email, designation, company, notes, created_at = contact
            
            conv_count = db.execute(
                "SELECT COUNT(*) FROM conversations WHERE contact_id = ?", 
                (contact_id,)
            ).fetchone()[0]
            
            # Contact Card
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                <div class="contact-card">
                    <div class="contact-name">👤 {name}</div>
                    
                    <div class="contact-detail">
                        📧 {email if email else 'No email provided'}
                    </div>
                    
                    <div class="contact-detail">
                        💼 {designation if designation else 'No title'} 
                        {f'at {company}' if company else ''}
                    </div>
                    
                    {f'<div class="contact-detail">📝 {notes}</div>' if notes else ''}
                    
                    <div class="contact-stats">
                        <span class="stat-badge {'success-badge' if conv_count > 0 else ''}">
                            💬 {conv_count} conversation{'s' if conv_count != 1 else ''}
                        </span>
                        <span class="stat-badge">
                            📅 Added {datetime.datetime.fromisoformat(created_at).strftime('%b %d, %Y')}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("💬 View Conversations", key=f"view_{contact_id}", use_container_width=True):
                    navigate_to("conversations", contact_id)
                    
                if st.button("✏️ Edit", key=f"edit_{contact_id}", use_container_width=True):
                    st.info("Edit feature coming soon!")
    else:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #6b7280;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
            <h3>No contacts yet</h3>
            <p>Add your first contact above to start managing conversations</p>
        </div>
        """, unsafe_allow_html=True)

# PAGE 2: CONVERSATIONS FOR SELECTED CONTACT
elif st.session_state.page == "conversations":
    contact = get_contact(st.session_state.current_contact)
    
    if contact:
        contact_id, name, email, designation, company, notes, created_at = contact
        
        # Navigation
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button("← Back to Contacts"):
                navigate_to("contacts")
        
        st.markdown(f"""
        <div class="section-header">
            💬 Conversations with {name}
            <div style="font-size: 0.9rem; color: #6b7280; font-weight: normal; margin-top: 4px;">
                {designation if designation else 'Contact'} {f'at {company}' if company else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # New conversation section
        with st.expander("🆕 Start New Conversation"):
            with st.form("new_conversation"):
                st.markdown("#### Create a New Conversation Thread")
                conv_title = st.text_input("Conversation Topic", 
                                          placeholder="e.g., Q1 Project Planning, Budget Discussion")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col2:
                    if st.form_submit_button("🚀 Start Conversation", use_container_width=True):
                        if conv_title.strip():
                            conv_id = add_conversation(contact_id, conv_title.strip())
                            st.success(f"✅ Started conversation: {conv_title}")
                            navigate_to("chat", conversation_id=conv_id)
                        else:
                            st.error("Please enter a conversation topic")
        
        # Display conversations
        conversations = get_conversations_for_contact(contact_id)
        
        if conversations:
            st.markdown("#### 📋 Conversation History")
            
            for conv in conversations:
                conv_id, contact_id, title, status, context_summary, created_at, updated_at, message_count, last_message_time = conv
                
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="conversation-card">
                        <div class="conversation-title">💬 {title}</div>
                        <div class="conversation-meta">
                            📊 {message_count or 0} messages • 
                            📅 Last activity: {updated_at[:16] if updated_at else 'No activity'} • 
                            🏷️ {status.title()}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.write("")  # Spacing
                    if st.button("Open Chat", key=f"open_{conv_id}", use_container_width=True):
                        navigate_to("chat", conversation_id=conv_id)
        else:
            st.markdown(f"""
            <div style="text-align: center; padding: 2rem; color: #6b7280;">
                <div style="font-size: 2rem; margin-bottom: 1rem;">🔍</div>
                <h4>No conversations with {name} yet</h4>
                <p>Start a new conversation above to begin tracking your communication</p>
            </div>
            """, unsafe_allow_html=True)

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
        
        # Chat header
        st.markdown(f"""
        <div class="section-header">
            💬 {title}
            <div style="font-size: 0.9rem; color: #6b7280; font-weight: normal; margin-top: 4px;">
                With {contact_name} • {designation if designation else 'Contact'} {f'at {company}' if company else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display messages
        messages = get_messages(st.session_state.current_conversation)
        
        if messages:
            st.markdown("#### Chat Messages")
            
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
        
        st.markdown("---")
        
        # AI Reply section
        st.markdown("#### 🤖 AI Reply Assistant")
        
        with st.form("ai_reply", clear_on_submit=True):
            intent = st.text_input("What do you want to accomplish with your reply?", 
                                  placeholder="e.g., Schedule a meeting, Ask for project update, Decline politely")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.form_submit_button("🎯 Generate AI Reply", use_container_width=True):
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
            st.markdown(f"""
            <div class="ai-reply-box">
                <div class="ai-reply-header">🤖 AI Generated Reply</div>
                <p style="color: #059669; margin-bottom: 16px;">💡 Copy this reply or click 'Use This Reply' to paste it in your message box below.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.code(st.session_state.ai_reply_content, language=None)
            
            col1, col2, col3, col4 = st.columns(4)
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
        
        st.markdown("---")
        
        # Input section
        st.markdown("#### Add Messages")
        
        col1, col2 = st.columns(2)
        
        # Left - Received messages
        with col1:
            st.markdown("**📥 Message from contact**")
            with st.form("add_received", clear_on_submit=True):
                received_text = st.text_area("Paste what they sent:", height=120, 
                                           placeholder=f"Paste {contact_name}'s message here...")
                
                if st.form_submit_button("➕ Add Received Message", use_container_width=True):
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
                                   placeholder="Type what you sent to them...",
                                   key=f"sent_textarea_{st.session_state.current_conversation}")
            
            st.session_state.sent_message_text = sent_text
            
            if st.button("➕ Add Sent Message", key="add_sent_btn", use_container_width=True):
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
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p>🚀 Built with Streamlit & Gemini AI • Deployed on Google Cloud Run</p>
    <p style="font-size: 0.8rem;">💡 <strong>Tip:</strong> Build detailed contact profiles, then manage multiple conversation threads per contact. AI replies use full conversation context for better responses!</p>
</div>
""", unsafe_allow_html=True)
