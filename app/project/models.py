from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

#   \brief - Model for user accounts.
class User(UserMixin, db.Model):

    __tablename__ = 'flasklogin-users'

    id = db.Column(db.Integer,
                   primary_key=True)
    name = db.Column(db.String(40),
                     nullable=False,
                     unique=False)
    password = db.Column(db.String(200),
                         primary_key=False,
                         unique=False,
                         nullable=False)
    created_on = db.Column(db.DateTime,
                           index=False,
                           unique=False,
                           nullable=True)
    last_login = db.Column(db.DateTime,
                           index=False,
                           unique=False,
                           nullable=True)

#   \brief - Creates the hashed password.
    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')

#   \brief - Checks the hashed password.
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

#   \brief - Returns the user's username.
    def __repr__ (self):
        return self.name
