from datetime import datetime, timezone, timedelta
from models import RecurringPattern, Goal
from extensions import db

def check_recurring_goals(user):
    """
    Checks the user's RecurringPatterns (The Rules).
    If the last generated goal for a pattern is in the past, creates new ones.
    """
    
    # 1. Find all active patterns (factories)
    patterns = RecurringPattern.query.filter_by(
        user_id=user.id, 
        is_active=True
    ).all()

    now_utc = datetime.now(timezone.utc)
    changes_made = False

    for pattern in patterns:
        # 2. Find the LATEST goal created by this pattern to track the SEQUENCE
        last_goal = Goal.query.filter_by(pattern_id=pattern.id)\
            .order_by(Goal.deadline.desc()).first()
            
        if not last_goal:
            # If no goals exist (e.g. user deleted them all), restart from the anchor date
            current_deadline_date = pattern.anchor_date
        else:
            current_deadline_date = last_goal.deadline

        if not current_deadline_date: 
            continue

        # 3. Get the "Anchor Time" from the Pattern
        anchor_time = pattern.anchor_date.timetz()

        # 4. Catch-Up Loop
        while current_deadline_date < (now_utc - timedelta(hours=12)):
            
            if pattern.frequency == 'daily':
                current_deadline_date += timedelta(days=1)
            elif pattern.frequency == 'weekly':
                current_deadline_date += timedelta(weeks=1)
            elif pattern.frequency == 'monthly':
                current_deadline_date += timedelta(days=30)

            if current_deadline_date > (now_utc + timedelta(days=1)):
                break

            new_dt_combined = datetime.combine(current_deadline_date.date(), anchor_time)

            # Create the Product (The Task)
            new_goal = Goal(
                title=pattern.title,
                description=pattern.description,
                user_id=user.id,
                category_id=pattern.category_id,
                deadline=new_dt_combined,
                pattern_id=pattern.id,
                status='pending'
            )
            db.session.add(new_goal)
            changes_made = True

    if changes_made:
        db.session.commit()