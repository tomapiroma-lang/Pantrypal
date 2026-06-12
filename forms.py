from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    email = StringField(
        'ელ-ფოსტა', 
        validators=[
            DataRequired(message="ელ-ფოსტის შეყვანა აუცილებელია"), 
            Email(message="გთხოვთ შეიყვანოთ ვალიდური ელ-ფოსტა")
        ]
    )
    password = PasswordField(
        'პაროლი', 
        validators=[DataRequired(message="პაროლის შეყვანა აუცილებელია")]
    )
    remember = BooleanField('დამიმახსოვრე')
    submit = SubmitField('შესვლა')

class RegisterForm(FlaskForm):
    username = StringField(
        'მომხმარებლის სახელი', 
        validators=[
            DataRequired(message="მომხმარებლის სახელის შეყვანა აუცილებელია"),
            Length(min=3, max=20, message="სახელი უნდა იყოს 3-დან 20 სიმბოლომდე")
        ]
    )
    email = StringField(
        'ელ-ფოსტა', 
        validators=[
            DataRequired(message="ელ-ფოსტის შეყვანა აუცილებელია"), 
            Email(message="გთხოვთ შეიყვანოთ ვალიდური ელ-ფოსტა")
        ]
    )
    password = PasswordField(
        'პაროლი', 
        validators=[
            DataRequired(message="პაროლის შეყვანა აუცილებელია"),
            Length(min=8, message="პაროლი უნდა შედგებოდეს მინიმუმ 8 სიმბოლოსგან")
        ]
    )
    confirm_password = PasswordField(
        'პაროლის დადასტურება', 
        validators=[
            DataRequired(message="გთხოვთ გაიმეოროთ პაროლი"), 
            EqualTo('password', message='პაროლები არ ემთხვევა')
        ]
    )
    agree = BooleanField(
        'ვეთანხმები კონფიდენციალურობის პოლიტიკას', 
        validators=[DataRequired(message="წესებზე დათანხმება აუცილებელია")]
    )
    submit = SubmitField('რეგისტრაცია')