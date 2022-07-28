from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session
from flask_admin import Admin, BaseView, expose


db = SQLAlchemy()
login_manager = LoginManager()
sess = Session()


#   \brief - Construct the core application.
def create_app():
    app = Flask( __name__ , instance_relative_config=False)
    #Application configuration
    app.config.from_object('config.Config')

    #Initialize plugins
    db.init_app(app)
    login_manager.init_app(app)
    sess.init_app(app)

    with app.app_context():
        #Import parts of the application
        from . import routes
        from . import auth
        from .admin_views import SupportView, SupportList
        from .models import User
        app.register_blueprint(routes.main_bp)
        app.register_blueprint(auth.auth_bp)
        admin = Admin(app)
        #Initialize global database
        db.create_all()
        
        #Add admin views
        admin.add_view(SupportList(name='View all queries'))
        users = User.query.all()
        for user in users:
            admin.add_view(SupportView(name=user.name, endpoint=str(user.id), category='Support users'))

        return app
