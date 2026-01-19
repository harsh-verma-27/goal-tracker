from flask import Blueprint, jsonify, request, url_for
from flask_login import login_required, current_user
from models import Goal, RecurringPattern, Category
from extensions import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, case, and_, func, text
import os
from google import genai

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/goals', methods=['GET'])
@login_required
def get_goals():
    query = Goal.query.filter_by(user_id=current_user.id)

    # 1. Date Filter
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Goal.deadline) == target_date)
        except ValueError:
            pass 

    # 2. Status Filter
    status = request.args.get('status')
    if status == 'overdue':
        now_utc = datetime.now(timezone.utc)
        query = query.filter(Goal.deadline < now_utc, Goal.status != 'completed')
    elif status:
        query = query.filter_by(status=status)

    # 3. Category Filter
    category_id = request.args.get('category_id')
    if category_id:
        query = query.filter_by(category_id=category_id)

    # 4. Search Filter
    search_query = request.args.get('q')
    if search_query:
        query = query.filter(
            or_(
                Goal.title.ilike(f'%{search_query}%'),
                Goal.description.ilike(f'%{search_query}%')
            )
        )

    # 5. Sorting (THE NEW 4-TIER LOGIC)
    sort_by = request.args.get('sort_by', 'date_asc')
    now_utc = datetime.now(timezone.utc)

    # Define the "Priority Score" (Lower number = Higher Priority)
    status_priority = case(
        (Goal.status == 'in_progress', 0),                             # Tier 0: In Progress
        (and_(Goal.status == 'pending', Goal.deadline < now_utc), 1),  # Tier 1: Overdue
        (Goal.status == 'pending', 2),                                 # Tier 2: Normal Pending
        (Goal.status == 'completed', 3),                               # Tier 3: Completed
        else_=2 
    )

    if sort_by == 'date_desc':
        # Sort by Priority Tier First, THEN by Date
        query = query.order_by(status_priority, Goal.deadline.desc().nulls_last())
    elif sort_by == 'created_desc':
        query = query.order_by(status_priority, Goal.date_created.desc())
    else:
        query = query.order_by(status_priority, Goal.deadline.asc().nulls_last())

    goals = query.all()
    
    # 6. Serialization
    results = []
    
    for goal in goals:
        computed_status = goal.status
        if goal.deadline and goal.deadline < now_utc and goal.status == 'pending':
            computed_status = 'overdue'

        # Colors for Dots
        dot_color = '#3788d8'
        if computed_status == 'completed': dot_color = '#198754'
        if computed_status == 'overdue': dot_color = '#dc3545'
        if computed_status == 'in_progress': dot_color = '#ffc107'

        results.append({
            'id': goal.id,
            'title': goal.title,
            'description': goal.description,
            'status': computed_status,
            'deadline_pretty': goal.deadline.strftime('%Y-%m-%d %I:%M %p') if goal.deadline else "No Deadline",
            'category': goal.category.name if goal.category else None,
            'is_recurring': bool(goal.pattern_id),
            'urls': {'edit': url_for('main.edit_goal', goal_id=goal.id)},
            'start': goal.deadline.isoformat() if goal.deadline else None,
            'color': dot_color,
            'display': 'list-item' 
        })

    return jsonify(results)

@api_bp.route('/api/goals/create', methods=['POST'])
@login_required
def create_goal_api():
    data = request.get_json()
    
    title = data.get('title')
    deadline_str = data.get('deadline')
    frequency = data.get('frequency', 'none')
    description = data.get('description')
    category_id = data.get('category_id')

    if category_id == "": category_id = None
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

    # Create Pattern (Logic borrowed from main.py)
    pattern = None
    if frequency != 'none' and deadline:
        pattern = RecurringPattern(
            title=title,
            description=description,
            frequency=frequency,
            user_id=current_user.id,
            anchor_date=deadline,
            category_id=category_id
        )
        db.session.add(pattern)
        db.session.flush() 

    # Create Goal
    new_goal = Goal(
        title=title,
        description=description,
        deadline=deadline,
        user_id=current_user.id,
        pattern_id=pattern.id if pattern else None,
        category_id=category_id
    )
    
    db.session.add(new_goal)
    db.session.commit()
    
    return jsonify({'success': True, 'id': new_goal.id})

@api_bp.route('/api/categories/create', methods=['POST'])
@login_required
def create_category_api():
    data = request.get_json()
    raw_name = data.get('name', '')
    
    name = raw_name.strip().title()
    
    if not name:
        return jsonify({'error': 'Name required'}), 400
        
    # 2. Check duplicates
    exists = Category.query.filter_by(name=name, user_id=current_user.id).first()
    if exists:
        # If it exists, just return the existing one 
        return jsonify({
            'success': True, 
            'category': {'id': exists.id, 'name': exists.name}
        })
        
    new_cat = Category(name=name, owner=current_user)
    db.session.add(new_cat)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'category': {'id': new_cat.id, 'name': new_cat.name}
    })

@api_bp.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    user_id = current_user.id
    
    # 1. KPIs
    total = Goal.query.filter_by(user_id=user_id).count()
    completed = Goal.query.filter_by(user_id=user_id, status='completed').count()
    win_rate = round((completed / total * 100), 1) if total > 0 else 0

    # 2. PIE CHART (Categories)
    cat_stats = db.session.query(Category.name, func.count(Goal.id))\
        .join(Goal, Goal.category_id == Category.id)\
        .filter(Goal.user_id == user_id)\
        .group_by(Category.name).all()
    
    pie_labels = [r[0] for r in cat_stats]
    pie_data = [r[1] for r in cat_stats]
    
    # Add "General" for uncategorized
    uncategorized = Goal.query.filter_by(user_id=user_id, category_id=None).count()
    if uncategorized > 0:
        pie_labels.append("General")
        pie_data.append(uncategorized)

    status_stats = db.session.query(Goal.status, func.count(Goal.id))\
        .filter(Goal.user_id == user_id)\
        .group_by(Goal.status).all()
    
    status_labels = [r[0].replace('_', ' ').title() for r in status_stats] # "in_progress" -> "In Progress"
    status_data = [r[1] for r in status_stats]

    # 3. BAR CHART (Last 7 Days Activity)
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=6)
    
    recent_activity = db.session.query(func.date(Goal.end_time), func.count(Goal.id))\
        .filter(Goal.user_id == user_id, Goal.status == 'completed', Goal.end_time >= seven_days_ago)\
        .group_by(func.date(Goal.end_time)).all()
    
    # Map results to days (fill zeros)
    activity_map = {str(r[0]): r[1] for r in recent_activity}
    bar_labels = []
    bar_data = []
    
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        bar_labels.append(day.strftime('%a')) # Mon, Tue...
        bar_data.append(activity_map.get(str(day), 0))

    return jsonify({
        'kpi': {'total': total, 'completed': completed, 'win_rate': win_rate},
        'pie_category': {'labels': pie_labels, 'data': pie_data},
        'pie_status': {'labels': status_labels, 'data': status_data},
        'bar': {'labels': bar_labels, 'data': bar_data}
    })

# ---------------------------------------------------------
#  CATEGORY MANAGEMENT
# ---------------------------------------------------------

@api_bp.route('/api/categories', methods=['GET'])
@login_required
def get_categories_api():
    user_cats = Category.query.filter_by(user_id=current_user.id).all()
    results = []
    
    for cat in user_cats:
        # Count active goals using this category
        count = Goal.query.filter_by(
            category_id=cat.id
        ).count()
        
        results.append({
            'id': cat.id,
            'name': cat.name,
            'count': count
        })
    
    return jsonify(results)

@api_bp.route('/api/categories/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category_api(cat_id):

    category = Category.query.get_or_404(cat_id)
    if category.owner != current_user:
        return jsonify({'error': 'Unauthorized'}), 403

    # 1. Uncategorize Goals (The "Safety" Logic)
    goals = Goal.query.filter_by(category_id=cat_id).all()
    for goal in goals:
        goal.category_id = None
        
    # 2. Uncategorize Patterns (Recurring Rules)
    patterns = RecurringPattern.query.filter_by(category_id=cat_id).all()
    for pattern in patterns:
        pattern.category_id = None

    # 3. Delete the Category
    db.session.delete(category)
    db.session.commit()
    
    return jsonify({'success': True})

# ---------------------------------------------------------
#  STATUS UPDATES (Start, Pause, Finish)
# ---------------------------------------------------------

@api_bp.route("/api/advance/<int:goal_id>", methods=["POST"])
@login_required
def advance_status_api(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    now = datetime.now(timezone.utc)
    
    # 1. PENDING -> IN PROGRESS
    if goal.status == "pending" or goal.status == "overdue":
        goal.status = "in_progress"
        
    # 2. IN PROGRESS -> COMPLETED
    elif goal.status == "in_progress":
        goal.status = "completed"
        goal.end_time = now
        
        # RECURRING LOGIC
        if goal.pattern_id:
            pattern = RecurringPattern.query.get(goal.pattern_id)
            if pattern:
                next_deadline = goal.deadline
                if pattern.frequency == 'daily':
                    next_deadline += timedelta(days=1)
                elif pattern.frequency == 'weekly':
                    next_deadline += timedelta(weeks=1)
                elif pattern.frequency == 'monthly':
                    next_deadline += timedelta(days=30)
                
                new_goal = Goal(
                    title=pattern.title,
                    description=goal.description,
                    deadline=next_deadline,
                    user_id=current_user.id,
                    pattern_id=pattern.id,
                    category_id=goal.category_id
                )
                db.session.add(new_goal)

    db.session.commit()
    return jsonify({'success': True})

# ---------------------------------------------------------
#  DELETION & TRASH MANAGEMENT
# ---------------------------------------------------------

@api_bp.route("/api/delete/<int:goal_id>", methods=["POST"])
@login_required
def delete_goal_api(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner != current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'success': True, 'id': goal.id})

# ---------------------------------------------------------
#  AI CHAT ENDPOINT
# ---------------------------------------------------------

@api_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_with_ai():
    data = request.get_json()
    goal_id = data.get('goal_id')
    user_message = data.get('message')
    
    if not goal_id or not user_message:
        return jsonify({'error': 'Missing data'}), 400

    # 1. Fetch Goal Context
    goal = Goal.query.get_or_404(goal_id)
    if goal.owner != current_user:
        return jsonify({'error': 'Unauthorized'}), 403

    # 2. Configure New Client
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'error': 'Server missing API Key'}), 500
    
    try:
        # Initialize the new Client
        client = genai.Client(api_key=api_key)

        # 3. Construct Prompt (Enhanced with Time Awareness)
        from datetime import datetime
        now = datetime.now()
        time_context = f"Current Date: {now.strftime('%Y-%m-%d')}"

        system_instruction = f"""
        You are a smart and helpful Productivity Coach.
        {time_context}
        
        The user is asking for help with this goal:
        - Title: "{goal.title}"
        - Description: "{goal.description or 'None'}"
        - Deadline: {goal.deadline or 'None'}
        - Status: {goal.status}
        
        INSTRUCTIONS:
        1. Be clear and practical.
        2. Use your own reasoning with no preset length limit.
        3. Respond only as long as needed to fully and clearly address everything the user asked.
        4. Be direct and to the point—no filler.
        5. Clarify all parts of the request and add only minimal extra help that genuinely improves usefulness.
        """

        full_prompt = f"{system_instruction}\n\nUser: {user_message}"

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt
        )
        
        return jsonify({'reply': response.text})

    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({'error': 'AI connection failed. Check server logs.'}), 500

    