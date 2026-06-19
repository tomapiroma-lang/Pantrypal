import os
from dotenv import load_dotenv
from flask import Flask, session
from flask_login import LoginManager
from blueprints import main_bp, User
from config import Config

load_dotenv()

app = Flask(
    __name__,
    static_folder='public/static',  # Vercel serves /public/** via its CDN, so this
    static_url_path='/static',      # keeps url_for('static', ...) links unchanged
    template_folder='templates',
)
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
# FIX: Namespace the login view
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    username = session.get('logged_username', 'მომხმარებელი')
    email = session.get('logged_email', 'user@pantrypal.ge')
    return User(user_id, username, email)

app.register_blueprint(main_bp, url_prefix='/')

if __name__ == '__main__':
    app.run(debug=True)