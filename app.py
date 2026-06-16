import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask import Flask
from flask_login import LoginManager # type: ignore

from blueprints import main_bp, User
from config import Config

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User(user_id, "გიორგი", "user@pantrypal.ge")

app.register_blueprint(main_bp, name='')

if __name__ == '__main__':
    app.run(debug=True)
