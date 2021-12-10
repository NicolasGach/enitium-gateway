# app.py
import werkzeug.exceptions as ex
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

@app.route('/callapi/', methods=['GET'])
def respond():
    response = {}
    response['callresponse'] = 'ok'
    return jsonify(response)

# A welcome message to test our server
@app.route('/')
def index():
    response = {}
    response['callresponse'] = 'ok home'
    return jsonify(response)

@app.errorhandler(403)
def access_forbidden(e):
    return '<p>Access forbidden</p>' 

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)