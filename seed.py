import random
from datetime import datetime, timedelta, timezone
from app import create_app
from extensions import db
from models import User, Goal, Category
from werkzeug.security import generate_password_hash

# 1. Setup
app = create_app()

# 2. Sample Data
CATEGORIES = ['Work', 'Health', 'Learning', 'Personal', 'Chores']
VERBS = ['Write', 'Fix', 'Study', 'Clean', 'Buy', 'Call', 'Deploy', 'Review', 'Plan', 'Exercise']
NOUNS = ['Report', 'Bug', 'Python Script', 'Room', 'Groceries', 'Mom', 'Server', 'Q3 Strategy', 'Week', 'Cardio']

def get_random_date():
    # Generates a date between 30 days ago and 30 days in future
    start = datetime.now(timezone.utc) - timedelta(days=30)
    end = datetime.now(timezone.utc) + timedelta(days=30)
    return start + (end - start) * random.random()

def seed_database():
    with app.app_context():
        print("🌱 Seeding Database (Clean Version)...")
        
        # Drop all tables and recreate to ensure schema is perfect
        db.drop_all()
        db.create_all()

        # 3. Create User
        print("Creating 'testuser' (Password: password)...")
        user = User(
            username='testuser',
            password_hash=generate_password_hash('password', method='pbkdf2:sha256'),
            timezone='UTC'
        )
        db.session.add(user)
        db.session.commit()

        # 4. Create Categories
        cat_objects = []
        for name in CATEGORIES:
            cat = Category(name=name, owner=user)
            db.session.add(cat)
            cat_objects.append(cat)
        db.session.commit()
        
        cat_objects = Category.query.filter_by(user_id=user.id).all()

        # 5. Generate 50 Goals
        print("Generating 50 goals...")
        for i in range(50):

            title = f"{random.choice(VERBS)} {random.choice(NOUNS)}"
            category = random.choice(cat_objects)
            deadline = get_random_date()
            
            now = datetime.now(timezone.utc)
            
            if deadline > now:
                status = random.choice(['pending', 'pending', 'pending', 'in_progress'])
                end_time = None
            else:
                status = random.choice(['completed', 'completed', 'pending'])
                if status == 'completed':
                    end_time = deadline - timedelta(hours=random.randint(1, 48))
                else:
                    end_time = None

            goal = Goal(
                title=title,
                description=f"Auto-generated goal #{i+1}",
                deadline=deadline,
                user_id=user.id,
                category_id=category.id,
                status=status,
                end_time=end_time
            )

            db.session.add(goal)

        db.session.commit()
        print("✅ Success! Database reset with clean schema.")
        print("👉 Login with: testuser / password")

if __name__ == "__main__":
    seed_database()