from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from models import User
from extensions import db 

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=["POST", "GET"]) 
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        timezone = request.form.get("timezone", "UTC")
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('auth.signup'))
            
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password_hash = hashed_pw, timezone = timezone)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now login.')
        return redirect(url_for('auth.login'))
    return render_template('signup.html')

@auth_bp.route("/login", methods=["GET", "POST"]) 
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Login failed. Check your username and password.")
    return render_template('login.html')

@auth_bp.route("/logout") 
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('main.index'))