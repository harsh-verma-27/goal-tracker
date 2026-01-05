# 🎯 GoalTracker V1

**A full-stack, timezone-aware goal management application built with Flask and PostgreSQL.**

🔴 **Live Demo:** https://goal-tracker-vyik.onrender.com/

---

## 📖 About
GoalTracker is a CRUD (Create, Read, Update, Delete) web application designed to help users manage tasks and deadlines effectively. This application also handles **Timezone Awareness**—converting local user time (IST) to UTC for storage and back again for display, ensuring deadlines are accurate regardless of server location.

It is currently deployed on **Render** using a production-grade **PostgreSQL** database.

## ✨ Key Features
* **🔐 Secure Authentication:** Complete User Signup, Login, and Logout system with hashed passwords.
* **🌍 Timezone Intelligence:** Automatically captures user input in local time, converts to UTC for the database, and renders back to IST for the user.
* **📊 Dynamic Dashboard:** Filter goals by Category, Status (Pending, In Progress, Completed), or Search by title.
* **🗑️ Recycle Bin:** "Soft delete" functionality allows users to move items to Trash, Restore them, or Delete them permanently.
* **📱 Responsive Design:** Built with Bootstrap 5 to work seamlessly on mobile and desktop.
* **☁️ Cloud Native:** Configured to auto-detect environment (Local vs. Cloud) and switch database connections automatically.

## 🛠️ Tech Stack
* **Backend:** Python 3, Flask
* **Database:** PostgreSQL (Production), SQLite (Dev fallback), SQLAlchemy ORM
* **Frontend:** HTML5, Jinja2, Bootstrap 5
* **Deployment:** Render, Gunicorn
* **Utilities:** `pytz` (Timezones), `Werkzeug` (Security)

---

## 🚀 How to Run Locally
If you want to run this project on your own machine:

1.  **Clone the repository**
    ```bash
    git clone https://github.com/harsh-verma-27/goal-tracker
    cd goal-tracker
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables**
    Create a `.env` file in the root directory and add:
    ```ini
    SECRET_KEY=your_secret_key
    DB_PASSWORD=your_local_db_password
    # Optional: FLASK_DEBUG=True
    ```

5.  **Run the App**
    ```bash
    python app.py
    ```
    Open `http://127.0.0.1:5000` in your browser.

---

**Author:** Harsh Verma