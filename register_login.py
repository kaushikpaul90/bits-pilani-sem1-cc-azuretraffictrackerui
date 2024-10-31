import os
import boto3
from markupsafe import Markup
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask import Flask, Blueprint, request, jsonify, url_for, redirect, flash, render_template, session
from fetch_data import fetch_data_bp  # Import the blueprint

# register_login = Flask(__name__)

# Create a Blueprint
register_login_bp = Blueprint('register_login', __name__)

# Register the blueprint
register_login_bp.register_blueprint(fetch_data_bp)

# Generate random secret and initialize URLSafeTimedSerializer and SNS client
s = URLSafeTimedSerializer(os.urandom(24))
sns_client = boto3.client('sns', region_name=os.getenv('region', 'us-east-1'))

def send_verification_email(token):
    verification_link = url_for('register_login.confirm_email', token=token, _external=True)
    message = f'Please click the following link to confirm your email: {verification_link}'
    response = sns_client.publish(
        TopicArn=os.getenv('sns_topic_arn'),
        Message=message,
        Subject='Confirm Your Email'
    )
    return response

def create_sns_subscription(email):
    response = sns_client.subscribe(
        TopicArn=os.getenv('sns_topic_arn'),
        Protocol='email',
        Endpoint=email,
        ReturnSubscriptionArn=True,
        Attributes={
            'FilterPolicy': '{"email": ["'+email+'"]}'
        }
    )
    return response

def check_subscription_status(email):
    subscriptions = sns_client.list_subscriptions_by_topic(TopicArn=os.getenv('sns_topic_arn'))
    for subscription in subscriptions['Subscriptions']:
        if subscription['Endpoint'] == email and subscription['SubscriptionArn'] not in ['PendingConfirmation', 'Deleted']:
            return True
    return False

@register_login_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'register-email' in request.form:
        email = request.form['register-email']
        if check_subscription_status(email):
            session['email'] = email
            flash(Markup('Mail id already registered.<br/>Proceed to login.'), 'success')
            return redirect(url_for('register'))
            # return redirect(url_for('fetch_data.live_traffic_index'))
        token = s.dumps(email, salt='email-confirm')
        send_verification_email(token)
        create_sns_subscription(email)
        flash('A confirmation email has been sent to your email address.', 'info')
        return redirect(url_for('register'))
    return render_template('register.html')

@register_login_bp.route('/login', methods=['GET', 'POST'])
def login():
    email = request.form['login-email']
    if email == '':
        return render_template('register.html')
    if check_subscription_status(email):
        session['email'] = email
        return redirect(url_for('register_login.fetch_data.live_traffic_index'))
    else:
        flash('Please register/confirm your email address before proceeding.', 'warning')
        return redirect(url_for('register'))

@register_login_bp.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        return '<h1>The token is expired!</h1>'
    
    flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('register'))

@register_login_bp.route('/dashboard')
def dashboard():
    return 'Welcome to your dashboard!'

@register_login_bp.route('/clear_session', methods=['POST'])
def clear_session():
    session.clear()
    return render_template('register.html')

if __name__ == '__main__':
    register_login_bp.run(debug=True)
