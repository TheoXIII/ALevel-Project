import os
from flask import redirect, render_template, flash, Blueprint, request, session, url_for
from flask_login import login_required, logout_user, current_user, login_user
from flask import current_app as app
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import LoginForm, SignupForm
from .models import db, User
from . import login_manager
from .routes import create_defaults, flash_form_errors, basic_load

#Blueprint configuration.
auth_bp = Blueprint('auth_bp', __name__ ,
                    template_folder='templates',
                    static_folder='static')

#   \brief - User sign-up page.
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup_page():
    #Redirect user to dashboard if they are logged in
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.dashboard'))
    signup_form = SignupForm(request.form)

    #POST: Sign user in
    if request.method == 'POST':
        if signup_form.validate():
            #Get form fields
            name = request.form.get('name')
            password = request.form.get('password')
            existing_user = User.query.filter_by(name=name).first()
            if existing_user is None:
                user = User(name=name,
                            password=generate_password_hash(password, method='sha256'))
                db.session.add(user)
                db.session.commit()
                login_user(user)
                create_defaults()
                basic_load()
                return redirect(url_for('main_bp.dashboard'))
            flash('A user already exists with that username.')
            return redirect(url_for('auth_bp.signup_page'))
        flash_form_errors(signup_form) #Flash validation errors if validation fails.
    #GET: Load signup page
    return render_template('/signup.html',
                           title='Create an account',
                           form=SignupForm(),
                           template='signup-page',
                           body="Sign up for a user account.")

#   \brief - User login page.
@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    #Redirect user to dashboard if they are logged in
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.dashboard'))
    login_form = LoginForm(request.form)
    #Create user and redirect them to the dashboard.
    if request.method == 'POST':
        if login_form.validate():
            #Get form fields
            name = request.form.get('name')
            password = request.form.get('password')
            #Validate login attempt
            user = User.query.filter_by(name=name).first()
            if user:
                if user.check_password(password=password):
                    login_user(user)
                    basic_load()
                    next = request.args.get('next')
                    return redirect(next or url_for('main_bp.dashboard'))
        flash('Invalid username/password combination')
        return redirect(url_for('auth_bp.login_page'))
    #GET: Load login page
    return render_template('login.html',
                           form=LoginForm(),
                           title='Log in',
                           template='login-page',
                           body="Log in with your user account.")

#   \brief - Logs out user.
@auth_bp.route('/logout')
@login_required
def logout_page():
    logout_user()
    return redirect(url_for('main_bp.home'))

#   \brief - Checks if the user is logged in.
@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None

#   \brief - Redirects users who are not logged in to the login page.
@login_manager.unauthorized_handler
def unauthorized():
    flash('You must be logged in to view that page.')
    return redirect(url_for('auth_bp.login_page'))
