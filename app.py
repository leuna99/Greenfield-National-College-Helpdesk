from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import os
import webbrowser
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


# =========================================================
# MACHINE LEARNING CHATBOT
# =========================================================

ML_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "ml_model",
    "chatbot_model.pkl"
)

ml_model = joblib.load(ML_MODEL_PATH)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "greenfield_national_college_secret_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "helpdesk.db"
)


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
    #
    # Username: admin
    # Password: admin123
    # -----------------------------------------------------

    admin = cursor.execute(
        "SELECT * FROM admins WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:

        cursor.execute("""
            INSERT INTO admins
            (username, password)
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
            INSERT INTO faqs
            (question, answer)
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
# MACHINE LEARNING CHATBOT
# =========================================================

def chatbot_answer(question):

    question = question.strip()

    if not question:

        return "Please type a question."

    try:

        # Predict intent using trained ML model
        intent = ml_model.predict([question])[0]

        responses = {
                      "bca_fee":
                        "The BCA fee is Rs. 50,000 per semester.",

                        "bca_duration":
                        "The BCA program is 4 years and consists of 8 semesters.",

                        "bca_subjects":
                        "The BCA program includes subjects related to programming, databases, networking, mathematics, web development and other computer application topics.",

                        "semester_info":
                        "Each semester is approximately 6 months long.",

                        "admin_support":
                        "For administrative assistance, you can create a helpdesk ticket through the system.",

                        "ticket_help":
                         "You can create a helpdesk ticket from the Helpdesk Tickets section.",

                         "login_help":
                        "Use the student login page to access the system. New students can register automatically using their email.",

                        "chatbot_info":
                         "I am the Student Helpdesk Chatbot. I can answer questions about BCA, academic information, programming and student support.",

                        "greeting":
                        "Hello! 👋 How can I help you today?",

                        "thanks":
                        "You're welcome! 😊",

                         "programming":
                        "I can help with programming, computer science and technology-related questions.",

                        "how_are_you":
                         "I'm fine, thank you! 😊 And you?",

                         "semester_1_subjects":
                         "TU BCA Semester I subjects are:\n"
                          "1. BCA 101 - Computer Fundamentals and Applications\n"
                          "2. BCA 102 - Programming in C\n"
                          "3. BCA 103 - Digital Logic\n"
                         "4. BCA 104 - Mathematics-I\n"
                         "5. BCA 105 - Professional Communication and Ethics\n"
                          "6. BCA 106 - Hardware Workshop",

                        "semester_2_subjects":
                        "TU BCA Semester II subjects are:\n"
                        "1. BCA 151 - Discrete Structure\n"
                        "2. BCA 152 - Microprocessor and Computer Architecture\n"
                        "3. BCA 153 - OOP in Java\n"
                        "4. BCA 154 - Mathematics-II\n"
                        "5. BCA 155 - UX/UI Design\n"
                        "6. BCA 156 - Principles of Management",

                        "semester_3_subjects":
                        "TU BCA Semester III subjects are:\n"
                        "1. BCA 201 - Data Structure and Algorithms\n"
                        "2. BCA 202 - Database Management System\n"
                        "3. BCA 203 - Web Technology-I\n"
                        "4. BCA 204 - System Analysis and Design\n"
                        "5. BCA 205 - Probability and Statistics\n"
                        "6. BCA 206 - Applied Economics",

                        "semester_4_subjects":
                        "TU BCA Semester IV subjects are:\n"
                        "1. BCA 251 - Operating Systems\n"
                        "2. BCA 252 - Software Engineering\n"
                        "3. BCA 253 - Numerical Methods\n"
                        "4. BCA 254 - Python Programming\n"
                        "5. BCA 255 - Web Technology-II\n"
                        "6. BCA 256 - Project-I",

                        "semester_5_subjects":
                        "TU BCA Semester V subjects are:\n"
                        "1. BCA 301 - Computer Network\n"
                        "2. BCA 302 - Artificial Intelligence\n"
                        "3. BCA 303 - Advance Java Programming\n"
                        "4. BCA 304 - MIS and e-Business\n"
                        "5. BCA 305 - Society and Technology\n"
                        "6. BCA 306 - Project-II",

                        "semester_6_subjects":
                        "TU BCA Semester VI subjects are:\n"
                        "1. BCA 351 - Computer Graphics and Animation\n"
                        "2. BCA 352 - Mobile Programming\n"
                        "3. BCA 353 - Cryptography and Network Security\n"
                        "4. BCA 354 - Technical Writing\n"
                        "5. BCA 355 - Distributed System\n"
                        "6. BCA 356 - Project-III",

                        "semester_7_subjects":
                        "TU BCA Semester VII subjects are:\n"
                        "1. BCA 401 - Cyber Security and Ethical Hacking\n"
                        "2. BCA 402 - Software Project Management\n"
                        "3. BCA 403 - Financial Accounting\n"
                        "4. BCA 404 - Project-IV\n"
                        "5. BCA 405 - Elective-I\n"
                        "6. BCA 406 - Elective-II",

                        "semester_8_subjects":
                        "TU BCA Semester VIII subjects are:\n"
                        "1. BCA 451 - Cloud Computing\n"
                        "2. BCA 452 - Internship\n"
                        "3. BCA 453 - Elective-III\n"
                        "4. BCA 454 - Elective-IV",

                        "all_bca_subjects":
                        "TU BCA is an 8-semester program. "
                        "You can ask me about the subjects of any semester from Semester I to Semester VIII."
                     }
        answer = responses.get(
            intent,
            "Sorry, I don't have an answer for that question yet."
        )

        print("Question:", question)
        print("Predicted Intent:", intent)
        print("Answer:", answer)

        return answer

    except Exception as e:

        print("ML Chatbot Error:", e)

        return (
            "Sorry, I could not process your question."
        )

# =========================================================
# TICKET CLUSTERING
# =========================================================

def get_ticket_clusters():

    connection = get_db()

    tickets = connection.execute("""
        SELECT id, subject, description
        FROM tickets
        WHERE description IS NOT NULL
        AND TRIM(description) != ''
    """).fetchall()

    connection.close()

    # -----------------------------------------------------
    # NOT ENOUGH TICKETS
    # -----------------------------------------------------

    if len(tickets) < 2:

        return {
            "total_tickets": len(tickets),
            "number_of_clusters": 0,
            "clusters": [],
            "largest_cluster": None
        }

    # -----------------------------------------------------
    # CREATE DATAFRAME
    # -----------------------------------------------------

    tickets_df = pd.DataFrame(
        [dict(ticket) for ticket in tickets]
    )

    tickets_df["text"] = (
        tickets_df["subject"].fillna("") + " " +
        tickets_df["description"].fillna("")
    )

    # -----------------------------------------------------
    # TF-IDF
    # -----------------------------------------------------

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2)
    )

    X = vectorizer.fit_transform(
        tickets_df["text"]
    )

    total_tickets = len(tickets_df)

    # -----------------------------------------------------
    # FIND DISTINCT TICKET PATTERNS
    # -----------------------------------------------------

    unique_vectors = np.unique(
        X.toarray(),
        axis=0
    ).shape[0]

    # -----------------------------------------------------
    # IF ALL TICKETS ARE IDENTICAL
    # -----------------------------------------------------

    if unique_vectors < 2:

        common_subject = (
            tickets_df["subject"]
            .value_counts()
            .index[0]
        )

        largest_cluster = {
            "cluster_number": 1,
            "count": total_tickets,
            "subject": common_subject
        }

        return {
            "total_tickets": total_tickets,
            "number_of_clusters": 1,
            "clusters": [largest_cluster],
            "largest_cluster": largest_cluster
        }

    # -----------------------------------------------------
    # AUTOMATICALLY DETERMINE MAXIMUM K
    # -----------------------------------------------------

    max_k = min(
        10,
        total_tickets,
        unique_vectors
    )

    # -----------------------------------------------------
    # AUTOMATIC CLUSTER SELECTION
    # -----------------------------------------------------

    if max_k == 2:

        best_k = 2

    else:

        inertias = []

        for k in range(2, max_k + 1):

            model = KMeans(
                n_clusters=k,
                random_state=42,
                n_init=10
            )

            model.fit(X)

            inertias.append(
                model.inertia_
            )

        # -------------------------------------------------
        # CALCULATE IMPROVEMENTS
        # -------------------------------------------------

        improvements = []

        for i in range(1, len(inertias)):

            improvement = (
                inertias[i - 1] -
                inertias[i]
            )

            improvements.append(
                improvement
            )

        # -------------------------------------------------
        # SELECT ELBOW
        # -------------------------------------------------

        if len(improvements) == 1:

            best_k = 2

        else:

            ratios = []

            for i in range(1, len(improvements)):

                previous = improvements[i - 1]
                current = improvements[i]

                if previous == 0:

                    ratio = 1

                else:

                    ratio = current / previous

                ratios.append(ratio)

            best_index = ratios.index(
                min(ratios)
            ) + 1

            best_k = best_index + 2

        # -------------------------------------------------
        # FINAL SAFETY CHECK
        # -------------------------------------------------

        best_k = min(
            best_k,
            unique_vectors,
            total_tickets
        )

    # -----------------------------------------------------
    # PERFORM K-MEANS
    # -----------------------------------------------------

    kmeans = KMeans(
        n_clusters=best_k,
        random_state=42,
        n_init=10
    )

    tickets_df["cluster"] = kmeans.fit_predict(X)

    # -----------------------------------------------------
    # CREATE CLUSTER RESULTS
    # -----------------------------------------------------

    cluster_counts = (
        tickets_df["cluster"]
        .value_counts()
        .sort_values(
            ascending=False
        )
    )

    clusters = []

    for cluster_number in cluster_counts.index:

        cluster_tickets = tickets_df[
            tickets_df["cluster"] == cluster_number
        ]

        count = len(cluster_tickets)

        # Most common subject in this cluster
        common_subject = (
            cluster_tickets["subject"]
            .value_counts()
            .index[0]
        )

        clusters.append({
            "cluster_number": cluster_number + 1,
            "count": count,
            "subject": common_subject
        })

    # -----------------------------------------------------
    # SORT LARGEST GROUP FIRST
    # -----------------------------------------------------

    clusters.sort(
        key=lambda item: item["count"],
        reverse=True
    )

    # -----------------------------------------------------
    # MOST REPORTED ISSUE
    # -----------------------------------------------------

    largest_cluster = (
        clusters[0]
        if clusters
        else None
    )

    # -----------------------------------------------------
    # RETURN RESULTS TO DASHBOARD
    # -----------------------------------------------------

    return {
        "total_tickets": total_tickets,
        "number_of_clusters": best_k,
        "clusters": clusters,
        "largest_cluster": largest_cluster
    }

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

            flash(
                "Please fill in all fields."
            )

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

        # Store student information in session
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

    session.pop(
        "user_id",
        None
    )

    session.pop(
        "user_name",
        None
    )

    flash(
        "You have been logged out."
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# STUDENT CHATBOT
# =========================================================

@app.route(
    "/chat",
    methods=["GET", "POST"]
)
@student_required
def chat():

    question = None

    answer = None

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip()

        if question:

            # Get answer from ML model
            answer = chatbot_answer(
                question
            )

            # Save chat to database
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

    # IMPORTANT:
    # We do NOT load previous chats here.
    # Every new opening of /chat starts with
    # the welcome message only.

    return render_template(
        "chat.html",
        question=question,
        answer=answer
    )


# =========================================================
# STUDENT TICKETS
# =========================================================

@app.route(
    "/tickets",
    methods=["GET", "POST"]
)
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

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
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
    cluster_data = get_ticket_clusters()

    stats = {

        "students":
            students,

        "tickets":
            tickets_total,

        "open_tickets":
            open_tickets,

        "closed_tickets":
            closed_tickets,

        "chats":
            chats,

        "faqs":
            faqs_count

    }

    return render_template(
    "admin_dashboard.html",
    stats=stats,
    tickets=ticket_data,
    cluster_data=cluster_data
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

        "students":
            connection.execute(
                "SELECT COUNT(*) AS total FROM users"
            ).fetchone()["total"],

        "chats":
            connection.execute(
                "SELECT COUNT(*) AS total FROM chats"
            ).fetchone()["total"],

        "tickets":
            connection.execute(
                "SELECT COUNT(*) AS total FROM tickets"
            ).fetchone()["total"],

        "open":
            connection.execute("""
                SELECT COUNT(*) AS total
                FROM tickets
                WHERE status = 'Open'
            """).fetchone()["total"],

        "closed":
            connection.execute("""
                SELECT COUNT(*) AS total
                FROM tickets
                WHERE status = 'Closed'
            """).fetchone()["total"],

        "faqs":
            connection.execute(
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

    session.pop(
        "admin_id",
        None
    )

    session.pop(
        "admin_username",
        None
    )

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