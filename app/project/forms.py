from wtforms import Form, StringField, PasswordField, validators, SubmitField
from wtforms.validators import ValidationError, DataRequired, EqualTo, Length

#   \brief Defines validation functions which will be used.
def digit_chr(form,field):
    if not any(chr.isdigit() for chr in field.data):
        raise ValidationError("Password must contain at least one number.")
def upper_case_chr(form,field):
    if not any(chr.isupper() for chr in field.data):
        raise ValidationError("Password must contain at least one upper case character.")
def lower_case_chr(form,field):
    if not any(chr.islower() for chr in field.data):
        raise ValidationError("Password must contain at least one lower case character.")

#   \brief User login form.
class LoginForm(Form):
    name = StringField('Username', validators=[DataRequired(message=('Enter username.'))])
    password = PasswordField('Password', validators=[DataRequired('Please enter password.')])
    submit = SubmitField('Log In')
    
#   \brief User signup form.
class SignupForm(Form):
    name = StringField('Name',
                        validators=[DataRequired(message=('Enter username.'))])
    password = PasswordField('Password',
                             validators=[DataRequired(message='Please enter a password.'),
                                         Length(min=6, message=('Please select a stronger password.')),
                                         EqualTo('confirm', message='Passwords do not match!'),digit_chr,upper_case_chr,lower_case_chr])
    confirm = PasswordField('Confirm password')
    submit = SubmitField('Register')

#   \brief Change password form.
class ChangePasswordForm(Form):
    old_password = PasswordField('Old password')
    new_password = PasswordField('Password',
                             validators=[DataRequired(message='Please enter a password.'),
                                         Length(min=6, message=('Please select a stronger password.')),
                                         EqualTo('confirm_password', message='New passwords do not match!'),digit_chr,upper_case_chr,lower_case_chr])
    confirm_password = PasswordField('Confirm password')
    submit = SubmitField('Change password')
    
#   \brief Change username form.
class ChangeUsernameForm(Form):
    password = PasswordField('Password', validators=[DataRequired('Please enter password.')])
    new_name = StringField('New username', validators=[DataRequired(message=('Enter new username.'))])
    submit = SubmitField('Change username')
