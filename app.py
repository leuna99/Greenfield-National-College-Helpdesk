from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import os
import webbrowser

from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# ENVIRONMENT / OPENAI
# =========================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "greenfield_national_college_secret_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "helpdesk.db")


# =========================================================
# DATABASE
# =========================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = get_db()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # ADMINS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # FAQS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # CHATS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # TICKETS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            reply TEXT,
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # DEFAULT ADMIN
    # Username: admin
    # Password: admin123
    # -----------------------------------------------------

    admin = cursor.execute(
        "SELECT * FROM admins WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:

        cursor.execute("""
            INSERT INTO admins (username, password)
            VALUES (?, ?)
        """, (
            "admin",
            generate_password_hash("admin123")
        ))

    # -----------------------------------------------------
    # DEFAULT FAQS
    # -----------------------------------------------------

    faq_count = cursor.execute(
        "SELECT COUNT(*) AS total FROM faqs"
    ).fetchone()["total"]

    if faq_count == 0:

        faq_data = [

            (
                "What is the fee of BCA?",
                "The BCA fee is Rs. 50,000 per semester. There are 8 semesters, making the total fee Rs. 400,000."
            ),

            (
                "What is the total BCA fee?",
                "The total BCA fee is Rs. 400,000 for 8 semesters."
            ),

            (
                "How long is BCA?",
                "BCA is a 4-year undergraduate program consisting of 8 semesters."
            ),

            (
                "How many semesters are there in BCA?",
                "BCA consists of 8 semesters."
            ),

            (
                "How long is one semester?",
                "Each semester is approximately 6 months."
            ),

            (
                "Where is Greenfield National College?",
                "Greenfield National College is located at Bafal, Chetan Marga, Kathmandu, Nepal."
            ),

            (
                "What does BCA stand for?",
                "BCA stands for Bachelor of Computer Applications."
            ),

            (
                "How can I create a ticket?",
                "Login to the Student Helpdesk and open the Helpdesk section to create a support ticket."
            ),

            (
                "How can I check my ticket?",
                "Login to the Student Helpdesk and open the Helpdesk section to view your submitted tickets."
            ),

            (
                "What is the attendance information?",
                "Students should maintain regular attendance according to college and university requirements."
            ),

            (
                "Where can I find exam information?",
                "Please check official college or university notices for examination schedules."
            )

        ]

        cursor.executemany("""
            INSERT INTO faqs (question, answer)
            VALUES (?, ?)
        """, faq_data)

    connection.commit()
    connection.close()


# =========================================================
# LOGIN DECORATORS
# =========================================================

def student_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash("Please login first.")

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "admin_id" not in session:

            flash("Admin login required.")

            return redirect(
                url_for("admin_login")
            )

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# AI CHATBOT
# =========================================================

def chatbot_answer(question):

    question = question.strip()

    if not question:
        return "Please type a question."

    if client is None:

        return (
            "⚠️ AI is not configured yet. "
            "Please check your OPENAI_API_KEY in the .env file."
        )

    college_information = """

You are the Greenfield National College AI Student Assistant.

You help students with:

- College questions
- BCA subjects
- Programming
- Computer science
- Mathematics
- Assignments
- General knowledge
- Technology
- Current information
- Everyday questions

COLLEGE INFORMATION

College:
Greenfield National College

Location:
Bafal, Chetan Marga, Kathmandu, Nepal

BCA:

- Duration: 4 years
- 8 semesters
- Approximately 6 months per semester
- Fee: Rs. 50,000 per semester
- Total fee: Rs. 400,000

IMPORTANT RULES

1. Answer naturally and clearly.
2. Do not invent college information.
3. If the student asks for current information, use web search.
4. Use trustworthy sources for current information.
5. If you are uncertain, say so.
6. Explain difficult topics in simple language.
7. Help students learn instead of simply giving confusing answers.
8. For programming questions, provide examples when useful.
9. You can answer general questions even when they are not related to Greenfield National College.
10. When asked who you are, say that you are the Greenfield National College AI Student Assistant.

"""

    try:

        response = client.responses.create(

            model=OPENAI_MODEL,

            instructions=college_information,

            tools=[
                {
                    "type": "web_search",
                    "search_context_size": "low"
                }
            ],

            input=question
        )

        answer = response.output_text

        if not answer:

            return "Sorry, I could not generate an answer."

        return answer

    except Exception as e:

        print("OpenAI API Error:", e)

        return (
            "⚠️ Sorry, I could not connect to the AI service.\n\n"
            "Please check your API key, API billing, and internet connection."
        )


# =========================================================
# HOME
# =========================================================

@app.route("/")
@app.route("/home")
def home():

    return render_template(
        "index.html"
    )


@app.route("/index")
def index():

    return redirect(
        url_for("home")
    )


# =========================================================
# SYLLABUS
# =========================================================

@app.route("/syllabus")
def syllabus():

    return render_template(
        "syllabus.html"
    )


# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash("Please fill in all fields.")

            return redirect(
                url_for("login")
            )

        connection = get_db()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()

        # -------------------------------------------------
        # NEW STUDENT
        # -------------------------------------------------

        if user is None:

            cursor = connection.execute("""
                INSERT INTO users
                (name, email, password)
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                generate_password_hash(password)
            ))

            connection.commit()

            user_id = cursor.lastrowid

        # -------------------------------------------------
        # EXISTING STUDENT
        # -------------------------------------------------

        else:

            if not check_password_hash(
                user["password"],
                password
            ):

                connection.close()

                flash(
                    "Incorrect email or password."
                )

                return redirect(
                    url_for("login")
                )

            user_id = user["id"]

            name = user["name"]

        connection.close()

        session["user_id"] = user_id
        session["user_name"] = name

        flash(
            "Welcome to Greenfield National College! 🎓"
        )

        return redirect(
            url_for("chat")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# STUDENT LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop("user_id", None)
    session.pop("user_name", None)

    flash(
        "You have been logged out."
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# CHATBOT PAGE
# =========================================================

@app.route("/chat", methods=["GET", "POST"])
@student_required
def chat():

    current = None

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip()

        if question:

            answer = chatbot_answer(
                question
            )

            connection = get_db()

            connection.execute("""
                INSERT INTO chats
                (user_id, question, answer)
                VALUES (?, ?, ?)
            """, (
                session["user_id"],
                question,
                answer
            ))

            connection.commit()
            connection.close()

            current = {
                "question": question,
                "answer": answer
            }

    # IMPORTANT:
    # Old chat history is NOT loaded.
    # Every new opening starts with the welcome message.

    return render_template(
        "chat.html",
        current=current
    )


# =========================================================
# STUDENT TICKETS
# =========================================================

@app.route("/tickets", methods=["GET", "POST"])
@student_required
def tickets():

    if request.method == "POST":

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not subject or not description:

            flash(
                "Please fill in all ticket fields."
            )

            return redirect(
                url_for("tickets")
            )

        connection = get_db()

        connection.execute("""
            INSERT INTO tickets
            (user_id, subject, description, status)
            VALUES (?, ?, ?, 'Open')
        """, (
            session["user_id"],
            subject,
            description
        ))

        connection.commit()
        connection.close()

        flash(
            "Your helpdesk ticket has been submitted. 🎫"
        )

        return redirect(
            url_for("tickets")
        )

    connection = get_db()

    student_tickets = connection.execute("""
        SELECT *
        FROM tickets
        WHERE user_id = ?
        ORDER BY id DESC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    return render_template(
        "tickets.html",
        tickets=student_tickets
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db()

        admin = connection.execute("""
            SELECT *
            FROM admins
            WHERE username = ?
        """, (
            username,
        )).fetchone()

        connection.close()

        if admin and check_password_hash(
            admin["password"],
            password
        ):

            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]

            flash(
                "Admin login successful."
            )

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid admin username or password."
        )

    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    connection = get_db()

    students = connection.execute(
        "SELECT COUNT(*) AS total FROM users"
    ).fetchone()["total"]

    tickets_total = connection.execute(
        "SELECT COUNT(*) AS total FROM tickets"
    ).fetchone()["total"]

    open_tickets = connection.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'Open'
    """).fetchone()["total"]

    closed_tickets = connection.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'Closed'
    """).fetchone()["total"]

    chats = connection.execute(
        "SELECT COUNT(*) AS total FROM chats"
    ).fetchone()["total"]

    faqs_count = connection.execute(
        "SELECT COUNT(*) AS total FROM faqs"
    ).fetchone()["total"]

    ticket_data = connection.execute("""
        SELECT
            tickets.*,
            users.name,
            users.email
        FROM tickets
        JOIN users
        ON tickets.user_id = users.id
        ORDER BY tickets.id DESC
    """).fetchall()

    connection.close()

    stats = {

        "students": students,

        "tickets": tickets_total,

        "open_tickets": open_tickets,

        "closed_tickets": closed_tickets,

        "chats": chats,

        "faqs": faqs_count
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        tickets=ticket_data
    )


# =========================================================
# ADMIN UPDATE TICKET
# =========================================================

@app.route(
    "/admin/ticket/<int:ticket_id>",
    methods=["POST"]
)
@admin_required
def admin_update_ticket(ticket_id):

    reply = request.form.get(
        "reply",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "Open"
    )

    if status not in [
        "Open",
        "Closed"
    ]:

        status = "Open"

    connection = get_db()

    connection.execute("""
        UPDATE tickets
        SET reply = ?,
            status = ?
        WHERE id = ?
    """, (
        reply,
        status,
        ticket_id
    ))

    connection.commit()
    connection.close()

    flash(
        "Ticket updated successfully."
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN FAQ MANAGEMENT
# =========================================================

@app.route(
    "/admin/faqs",
    methods=["GET", "POST"]
)
@admin_required
def admin_faqs():

    connection = get_db()

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip()

        answer = request.form.get(
            "answer",
            ""
        ).strip()

        if question and answer:

            connection.execute("""
                INSERT INTO faqs
                (question, answer)
                VALUES (?, ?)
            """, (
                question,
                answer
            ))

            connection.commit()

            flash(
                "FAQ added successfully."
            )

        else:

            flash(
                "Please fill in both fields."
            )

    faqs = connection.execute("""
        SELECT *
        FROM faqs
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "faqs.html",
        faqs=faqs
    )


# =========================================================
# DELETE FAQ
# =========================================================

@app.route(
    "/admin/faqs/delete/<int:faq_id>",
    methods=["POST"]
)
@admin_required
def delete_faq(faq_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM faqs WHERE id = ?",
        (faq_id,)
    )

    connection.commit()
    connection.close()

    flash(
        "FAQ deleted successfully."
    )

    return redirect(
        url_for("admin_faqs")
    )


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/admin/analytics")
@admin_required
def analytics():

    connection = get_db()

    data = {

        "students": connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()["total"],

        "chats": connection.execute(
            "SELECT COUNT(*) AS total FROM chats"
        ).fetchone()["total"],

        "tickets": connection.execute(
            "SELECT COUNT(*) AS total FROM tickets"
        ).fetchone()["total"],

        "open": connection.execute("""
            SELECT COUNT(*) AS total
            FROM tickets
            WHERE status = 'Open'
        """).fetchone()["total"],

        "closed": connection.execute("""
            SELECT COUNT(*) AS total
            FROM tickets
            WHERE status = 'Closed'
        """).fetchone()["total"],

        "faqs": connection.execute(
            "SELECT COUNT(*) AS total FROM faqs"
        ).fetchone()["total"]
    }

    connection.close()

    return render_template(
        "analytics.html",
        analytics=data
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_username", None)

    flash(
        "Admin logged out."
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    webbrowser.open(
        "http://127.0.0.1:5000/"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )