from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, User, Goal, Category
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_remembered, current_user, login_required
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from urllib.parse import quote_plus
import pytz

load_dotenv()

database_url = os.getenv('DATABASE_URL')

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        print("Warning: No DB_PASSWORD set for local dev.")
    else:
        encoded_password = quote_plus(db_password)
        database_url = f'postgresql://postgres:{encoded_password}@localhost/goal_tracker'

app=Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    print("Database created successfully!")

@app.route('/') #home/index page
def index():
    return render_template('index.html')

@app.route('/signup', methods=["POST", "GET"]) #singup page
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('signup'))
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password_hash = hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now login.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route("/login", methods=["GET", "POST"]) #login page
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect(url_for("dashboard"))
        else:
            flash("Login failed. Check your username and password.")
    return render_template('login.html')

@app.route("/logout") #logout function
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('index'))

@app.template_filter('to_ist')
def to_ist_filter(dt):
    if dt is None:
        return ""
    india_tz = pytz.timezone('Asia/Kolkata')
    local_dt = dt.astimezone(india_tz)
    return local_dt.strftime('%Y-%m-%d %I:%M %p')

@app.template_filter('to_ist_form')
def to_ist_form_filter(dt):
    if dt is None:
        return ""
    india_tz = pytz.timezone('Asia/Kolkata')
    local_dt = dt.astimezone(india_tz)
    return local_dt.strftime('%Y-%m-%dT%H:%M')

@app.route("/dashboard", methods=["GET", "POST"]) #dashboard page
@login_required
def dashboard():
    if request.method == "POST":
        goal_title = request.form.get("goal_title")
        description = request.form.get("description")
        deadline_raw = request.form.get("deadline")
        category_id = request.form.get("category_id")
        deadline = None
        if deadline_raw:
            naive_dt = datetime.strptime(deadline_raw, "%Y-%m-%dT%H:%M")
            india_tz = pytz.timezone('Asia/Kolkata')
            aware_dt = india_tz.localize(naive_dt)
            deadline = aware_dt
        if category_id and category_id!="":
            category_id = int(category_id)
        else:
            category_id = None
        new_goal = Goal(title=goal_title, description=description, owner=current_user, deadline=deadline, category_id=category_id)
        db.session.add(new_goal)
        db.session.commit()
        flash('Goal added!')
        return redirect(url_for('dashboard'))
    
    query = Goal.query.filter_by(user_id=current_user.id, is_deleted=False)

    selected_category = request.args.get("category_id")
    if selected_category and selected_category!="":
        query = query.filter_by(category_id=int(selected_category))

    selected_status = request.args.get("status")
    if selected_status == "overdue":
        now_utc = datetime.now(timezone.utc)
        query = query.filter(Goal.deadline < now_utc, Goal.status != 'completed', Goal.status != 'archived')
    elif selected_status and selected_status != "":
        query = query.filter_by(status=selected_status)
    else:
        query = query.filter(Goal.status != 'archived')
    
    search_query = request.args.get("q")
    if search_query:
        query = query.filter(Goal.title.contains(search_query))
    
    sort_by = request.args.get('sort_by', 'deadline_asc')
    if sort_by == 'deadline_desc':
        query = query.order_by(Goal.deadline.desc().nulls_last())
    elif sort_by == 'created_desc':
        query = query.order_by(Goal.date_created.desc())
    elif sort_by == 'created_asc':
        query = query.order_by(Goal.date_created.asc())
    elif sort_by == 'title_asc':
        query = query.order_by(Goal.title.asc())
    else:
        query = query.order_by(Goal.deadline.asc().nulls_last())

    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    user_goals = pagination.items
    user_categories = Category.query.filter_by(user_id = current_user.id).all()
    return render_template('dashboard.html', 
                           goals=user_goals,
                           pagination=pagination,
                           now=datetime.now(timezone.utc), 
                           categories=user_categories,
                           selected_category=int(selected_category) if selected_category else None,
                           selected_status=selected_status, 
                           search_query=search_query,
                           sort_by=sort_by)

@app.route("/create_category", methods=["POST"]) #function to create a new category
@login_required
def create_category():
    category_name = request.form.get("category_name")
    if category_name:
        exists = Category.query.filter_by(name=category_name, user_id=current_user.id).first()
        if not exists:
            new_category = Category(name=category_name, owner=current_user)
            db.session.add(new_category)
            db.session.commit()
            flash("Category added!")
        else:
            flash("Category already exists!")
    return redirect(url_for("dashboard"))


@app.route("/delete/<int:goal_id>") #delete function
@login_required
def delete_goal(goal_id):
    goal_to_delete = Goal.query.get_or_404(goal_id)
    if goal_to_delete.owner != current_user:
        flash("Invalid Goal ID!")
        return redirect(url_for("dashboard"))
    goal_to_delete.is_deleted = True
    db.session.commit()
    flash("Goal moved to Trash.")
    return redirect(url_for("dashboard"))

@app.route("/advance_status/<int:goal_id>") #function to modify the current status of a task
@login_required
def advance_status(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner != current_user:
        return redirect(url_for("dashboard"))
    if goal.status == "pending":
        goal.status = "in_progress"
        goal.start_time = datetime.now(timezone.utc)
    elif goal.status == "in_progress":
        goal.status = "completed"
        goal.end_time = datetime.now(timezone.utc)
    elif goal.status == "completed":
        goal.status = "archived"
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/reset_status/<int:goal_id>") #function for "pausing" a task in progress
@login_required
def reset_status(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner != current_user:
        return redirect(url_for("dashboard"))
    if goal.status == "in_progress":
        goal.status = "pending"
        goal.start_time = None
        db.session.commit()
        flash("Goal paused.")
    return redirect(url_for("dashboard"))
    
@app.route("/trash") #function to get trash page
@login_required
def trash():
    query = Goal.query.filter_by(user_id=current_user.id, is_deleted=True)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    deleted_goals = pagination.items
    return render_template('trash.html', goals=deleted_goals, pagination=pagination)

@app.route("/restore/<int:goal_id>") #restoring a temporarily deleted goal
@login_required
def restore_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner == current_user:
        goal.is_deleted = False
        db.session.commit()
        flash("Goal restored!")
    return redirect(url_for("trash"))

@app.route("/permanent_delete/<int:goal_id>")  #perma deleting a goal
@login_required
def permanent_delete(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner == current_user:
        db.session.delete(goal)
        db.session.commit()
        flash("Goal deleted!")
    return redirect(url_for("trash"))

@app.route("/empty_trash")  #perma deleting all goals in trash
@login_required
def empty_trash():
    trash_goals = Goal.query.filter_by(user_id=current_user.id, is_deleted=True).all()
    if trash_goals:
        for goal in trash_goals:
            db.session.delete(goal)
        db.session.commit()
        flash("Trash emptied permanently!")
    else:
        flash("Trash is already empty.")
    return redirect(url_for("trash"))

@app.route("/edit/<int:goal_id>", methods=["GET", "POST"])  #editing a goal
@login_required
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)

    if goal.owner != current_user:
        flash("Invalid Goal!")
        return redirect(url_for("dashboard"))

    categories = Category.query.filter_by(user_id = current_user.id).all()

    if request.method == 'POST':
        goal.title = request.form.get("goal_title")
        goal.description = request.form.get("description")
        deadline_raw = request.form.get("deadline")
        if deadline_raw:
            naive_dt = datetime.strptime(deadline_raw, "%Y-%m-%dT%H:%M")
            india_tz = pytz.timezone('Asia/Kolkata')
            goal.deadline = india_tz.localize(naive_dt)
        else:
            goal.deadline = None
        
        category_id = request.form.get("category_id")
        if category_id and category_id!="":
            goal.category_id = int(category_id)
        else:
            goal.category_id = None
        
        db.session.commit()
        flash("Goal Updated!")
        return redirect(url_for("dashboard"))
    return render_template("edit_goal.html", goal=goal, categories=categories)

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode)