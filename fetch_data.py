import os
import json
import boto3
import logging
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from flask import Flask, Blueprint, request, jsonify, url_for, redirect, flash, render_template, session
import register_login

# # Initialize Flask application
# application = Flask(__name__)

# Create a Blueprint
fetch_data_bp = Blueprint('fetch_data', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Get environment variables
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
api_gateway_url = os.getenv('api_gateway_url')
x_api_key = os.getenv('x_api_key')
region = os.getenv('region', 'us-east-1')  # Default to 'us-east-1' if not set

# Initialize SNS client
sns_client = boto3.client('sns', region_name=os.getenv('region', 'us-east-1'))

def check_subscription_status(email):
    subscriptions = sns_client.list_subscriptions_by_topic(TopicArn=os.getenv('sns_topic_arn'))
    for subscription in subscriptions['Subscriptions']:
        if subscription['Endpoint'] == email and subscription['SubscriptionArn'] not in ['PendingConfirmation', 'Deleted']:
            return True
    return False

# @fetch_data_bp.route('/')
@fetch_data_bp.route('/live-traffic')
def live_traffic_index():
    # email = request.args.get('email')
    email = session.get('email', 'NA')
    if check_subscription_status(email):
        return render_template('index.html', email=email)
    else:
        flash('Mail id is not registered.<br>Please register to access Live Traffic Alerts...', 'warning')
        return redirect(url_for('fetch_data.live_traffic_index', email=email))

@fetch_data_bp.route('/get-api-key', methods=['GET'])
def get_api_key():
    api_access_key = os.getenv('api_access_key')
    return jsonify({'api_access_key': api_access_key})

@fetch_data_bp.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    from_location = data['from_location']
    to_location = data['to_location']
    email = data['email']

    # Prepare the payload for the API Gateway
    payload = {
        'from': from_location,
        'to': to_location,
        'email': email
    }

    # Create the AWS request
    aws_request = AWSRequest(method='POST', url=api_gateway_url, data=json.dumps(payload), headers={'x-api-key': x_api_key})
    credentials = Credentials(aws_access_key_id, aws_secret_access_key)
    SigV4Auth(credentials, 'execute-api', region).add_auth(aws_request)

    # Convert the AWSRequest to a requests.Request
    prepared_request = requests.Request(
        method=aws_request.method,
        url=aws_request.url,
        headers=dict(aws_request.headers.items()),
        data=aws_request.body
    ).prepare()

    # Make the API Gateway request
    session = requests.Session()
    response = session.send(prepared_request)

    # Parse the response from the API Gateway
    response_payload = response.json()
    
    # Log the response payload
    logging.info(f'Response Payload: {response_payload}')
    
    if response_payload['statusCode'] == 500:
        printable_response = 'We are sorry, but Azure Maps is currently unable to serve requests for all locations. Our system is still learning...'
    else:
        printable_response = response_payload['body'].strip('"')

    return json.dumps({'result': printable_response})

@fetch_data_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('register_login.login'))

if __name__ == '__main__':
    fetch_data_bp.debug = True
    fetch_data_bp.run()
