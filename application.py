import os
from flask import Flask, render_template, redirect, url_for, session
from register_login import register_login_bp  # Import the blueprint

application = Flask(__name__)
application.secret_key = os.urandom(24)  # Needed for session management

# Register the blueprint
application.register_blueprint(register_login_bp)

@application.route('/')
def home():
    return render_template('landing_page.html')

@application.route('/register_user')
def register():
    login_clicked = session.pop('login_clicked', False)
    return render_template('register.html', login_clicked=login_clicked)

@application.route('/login_user')
def login():
    session['login_clicked'] = True
    return redirect(url_for('register'))

if __name__ == '__main__':
    application.run(debug=True)
