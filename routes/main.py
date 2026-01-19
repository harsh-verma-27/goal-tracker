from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Goal, Category, RecurringPattern
from extensions import db
from datetime import datetime, timezone, timedelta
from utils import check_recurring_goals
import pytz

main_bp = Blueprint('main', __name__)

@main_bp.route('/') 
def index():
    return render_template('index.html')

@main_bp.route("/dashboard", methods=["GET", "POST"]) 
@login_required
def dashboard():
    check_recurring_goals(current_user)
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status")
    search_query = request.args.get("q")
    sort_by = request.args.get('sort_by', 'deadline_asc')
    page = request.args.get('page', 1, type=int)

    pagination = Goal.get_filtered(
        user_id=current_user.id,
        category_id=category_id,
        status=status,
        search_query=search_query,
        sort_by=sort_by,
        page=page,
        per_page=5
    )

    user_goals = pagination.items
    user_categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('dashboard.html', 
                           goals=user_goals,
                           pagination=pagination,
                           now=datetime.now(timezone.utc), 
                           categories=user_categories,
                           selected_category=category_id,
                           selected_status=status, 
                           search_query=search_query,
                           sort_by=sort_by)

@main_bp.route("/analytics")
@login_required
def analytics():
    return render_template('analytics.html')

@main_bp.route("/create_category", methods=["POST"]) 
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
    return redirect(url_for("main.dashboard"))

@main_bp.route("/edit/<int:goal_id>", methods=["GET", "POST"]) 
@login_required
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner != current_user:
        flash("Invalid Goal!")
        return redirect(url_for("main.dashboard"))
    
    categories = Category.query.filter_by(user_id = current_user.id).all()

    if request.method == 'POST':
        new_title = request.form.get("goal_title")
        new_description = request.form.get("description")
        category_id = request.form.get("category_id")
        update_mode = request.form.get("update_mode", "this")

        goal.title = new_title
        goal.description = new_description
        
        if category_id and category_id != "":
            goal.category_id = int(category_id)
        else:
            goal.category_id = None
            
        deadline_raw = request.form.get("deadline")
        if deadline_raw:
            naive_dt = datetime.strptime(deadline_raw, "%Y-%m-%dT%H:%M")
            user_tz = pytz.timezone(current_user.timezone)
            aware_dt = user_tz.localize(naive_dt)
            user_now = datetime.now(timezone.utc).astimezone(user_tz)
            if aware_dt.date() < user_now.date():
                 flash("Deadline cannot be in a past day!", "danger")
                 return render_template("edit_goal.html", goal=goal, categories=categories)
            
            goal.deadline = aware_dt
        else:
            goal.deadline = None

        # If user wants to update future goals, update the Pattern (Factory)
        if update_mode == 'future' and goal.pattern_id:
            pattern = RecurringPattern.query.get(goal.pattern_id)
            if pattern:
                pattern.title = new_title
                pattern.description = new_description
                pattern.category_id = goal.category_id
                
                # If the user changed the time on this goal, update the Anchor Time
                if goal.deadline:
                    pattern.anchor_date = goal.deadline

        db.session.commit()
        flash("Goal Updated!")
        return redirect(url_for("main.dashboard"))
        
    return render_template("edit_goal.html", goal=goal, categories=categories)