from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    timezone = db.Column(db.String(50), default='UTC')
    goals = db.relationship('Goal', backref='owner', lazy=True)
    categories = db.relationship('Category', backref='owner', lazy=True)
    patterns = db.relationship('RecurringPattern', backref='owner', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    goals = db.relationship('Goal', backref='category', lazy=True)
    patterns = db.relationship('RecurringPattern', backref='category', lazy=True)

class RecurringPattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    frequency = db.Column(db.String(20), nullable=False) # 'daily', 'weekly', 'monthly'
    # This acts as the 'Start Date' and the 'Anchor Time'
    anchor_date = db.Column(db.DateTime(timezone=True), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True) 
    # Link to all the child goals created by this pattern
    goals = db.relationship('Goal', backref='pattern', lazy=True)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default = "pending")
    date_created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deadline = db.Column(db.DateTime(timezone=True))
    start_time = db.Column(db.DateTime(timezone=True))
    end_time = db.Column(db.DateTime(timezone=True))
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    pattern_id = db.Column(db.Integer, db.ForeignKey('recurring_pattern.id'), nullable=True)

    @classmethod
    def get_filtered(cls, user_id, category_id=None, status=None, search_query=None, sort_by='deadline_asc', page=1, per_page=5):
        query = cls.query.filter_by(user_id=user_id)
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if status == "overdue":
            now_utc = datetime.now(timezone.utc)
            query = query.filter(cls.deadline < now_utc, cls.status != 'completed', cls.status != 'archived')
        elif status:
            query = query.filter_by(status=status)
        else:
            query = query.filter(cls.status != 'archived')

        if search_query:
            query = query.filter(cls.title.contains(search_query))

        if sort_by == 'deadline_desc':
            query = query.order_by(cls.deadline.desc().nulls_last())
        elif sort_by == 'created_desc':
            query = query.order_by(cls.date_created.desc())
        elif sort_by == 'created_asc':
            query = query.order_by(cls.date_created.asc())
        elif sort_by == 'title_asc':
            query = query.order_by(cls.title.asc())
        else:
            query = query.order_by(cls.deadline.asc().nulls_last())

        query = query.options(joinedload(cls.category))

        return query.paginate(page=page, per_page=per_page, error_out=False)