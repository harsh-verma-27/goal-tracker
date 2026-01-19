from flask import Flask
from extensions import db, login_manager, csrf
from models import User
import os
from dotenv import load_dotenv
import pytz
from flask_login import current_user
from routes.auth import auth_bp
from routes.main import main_bp
from routes.api import api_bp

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # 1. Config
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    if not database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)

    # 3. Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # 4. Template Filters
    @app.template_filter('to_local_time')
    def to_local_time_filter(dt):
        if dt is None: return ""
        user_tz = pytz.timezone(current_user.timezone)
        local_dt = dt.astimezone(user_tz)
        return local_dt.strftime('%Y-%m-%d %I:%M %p')

    @app.template_filter('to_local_time_form')
    def to_local_time_form_filter(dt):
        if dt is None: return ""
        user_tz = pytz.timezone(current_user.timezone)
        local_dt = dt.astimezone(user_tz)
        return local_dt.strftime('%Y-%m-%dT%H:%M')
    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode)