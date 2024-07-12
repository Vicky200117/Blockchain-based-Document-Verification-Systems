from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from web3 import Web3
import clamd
from cryptography.fernet import Fernet
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Connect to Ganache
web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
web3.eth.defaultAccount = web3.eth.accounts[0]

# Load the ABI
abi_path = r'C:\Users\vinay\doc_verification\build\contracts\DocumentVerification.json'
try:
    with open(abi_path) as f:
        contract_data = json.load(f)
        contract_abi = contract_data['abi']
        contract_address = '0x2038fA52b0bd6D1Ce6906dD087533fC84a56950c'
except FileNotFoundError:
    logging.error(f"ABI file not found at path: {abi_path}")
    exit(1)
except json.JSONDecodeError:
    logging.error(f"Error decoding JSON from the ABI file: {abi_path}")
    exit(1)
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}")
    exit(1)

contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Generate and set encryption key
key = Fernet.generate_key()
cipher_suite = Fernet(key)
app.config['ENCRYPTION_KEY'] = key

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # Adding role field
    sensitive_data = db.Column(db.String(500), nullable=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_hash = db.Column(db.String(300), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    user = db.relationship('User', backref=db.backref('documents', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(300), nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload')
@login_required
def upload_page():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return send_from_directory('.', 'upload.html')

@app.route('/verify')
@login_required
def verify_page():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    return send_from_directory('.', 'verify.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    email = data['email']
    password = data['password']
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400
    password_hash = generate_password_hash(password)
    role = 'admin' if email == 'admin@gmail.com' and not User.query.filter_by(role='admin').first() else 'user'
    new_user = User(username=username, email=email, password_hash=password_hash, role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({'message': 'Logged in'})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_document():
    files = request.files.getlist('file')
    response = []
    for file in files:
        document_hash = hash_document(file)
        if is_malware(file):
            return jsonify({'message': f'Malware detected in file: {file.filename}'}), 400

        exists = contract.functions.verifyDocument(document_hash).call()
        if exists:
            return jsonify({'message': f'Document {file.filename} already exists'}), 400

        tx_hash = contract.functions.uploadDocument(document_hash).transact({
            'from': web3.eth.defaultAccount
        })
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        new_document = Document(user_id=current_user.id, document_hash=document_hash, filename=file.filename)
        db.session.add(new_document)
        db.session.commit()

        response.append({'filename': file.filename, 'id': new_document.id})

    return jsonify({'message': 'Documents uploaded successfully', 'documents': response})


@app.route('/revoke', methods=['POST'])
@login_required
def revoke_document():
    data = request.get_json()
    document_id = data.get('id')

    if not document_id:
        return jsonify({'message': 'Document ID not provided'}), 400

    document = Document.query.filter_by(id=document_id, user_id=current_user.id).first()
    if not document:
        return jsonify({'message': 'Document not found or access denied'}), 404

    tx_hash = contract.functions.revokeDocument(document.document_hash).transact({
        'from': web3.eth.defaultAccount
    })
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    db.session.delete(document)
    db.session.commit()

    return jsonify({'message': 'Document revoked successfully', 'transaction_hash': receipt.transactionHash.hex()})

@app.route('/files', methods=['GET'])
@login_required
def get_files():
    documents = Document.query.filter_by(user_id=current_user.id).all()
    response = [{'id': doc.id, 'filename': doc.filename} for doc in documents]
    return jsonify({'documents': response})

@app.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    notifications = Notification.query.all()
    return jsonify({'notifications': [n.message for n in notifications]})

@app.route('/admin/users', methods=['GET'])
@login_required
def admin_users():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    users = User.query.all()
    return jsonify({'users': [{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in users]})

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    user = User.query.get(user_id)
    if user:
        documents = Document.query.filter_by(user_id=user_id).all()
        for doc in documents:
            try:
                tx_hash = contract.functions.revokeDocument(doc.document_hash).transact({
                    'from': web3.eth.defaultAccount
                })
                web3.eth.wait_for_transaction_receipt(tx_hash)
                db.session.delete(doc)
            except Exception as e:
                logging.error(f"Error deleting document {doc.filename} for user {user.username}: {e}")
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User and associated documents deleted'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/admin/documents', methods=['GET'])
@login_required
def get_admin_documents():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    documents = Document.query.all()
    response = []
    for document in documents:
        user = User.query.get(document.user_id)
        response.append({
            'id': document.id,
            'filename': document.filename,
            'username': user.username if user else 'Unknown'
        })
    return jsonify({'documents': response})

@app.route('/admin/documents/<int:document_id>/verify', methods=['POST'])
@login_required
def verify_document_admin(document_id):
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    document = Document.query.get(document_id)
    if not document:
        return jsonify({'message': 'Document not found'}), 404
    try:
        exists = contract.functions.verifyDocument(document.document_hash).call()
        if exists:
            return jsonify({'message': 'Document already verified'})
        tx_hash = contract.functions.uploadDocument(document.document_hash).transact({
            'from': web3.eth.defaultAccount
        })
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({'message': 'Document verified', 'transaction_hash': receipt.transactionHash.hex()})
    except Exception as e:
        logging.error(f"Error verifying document: {e}")
        return jsonify({'message': 'Verification failed'}), 500

@app.route('/admin/documents/<int:document_id>/delete', methods=['DELETE'])
@login_required
def delete_document_admin(document_id):
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    document = Document.query.get(document_id)
    if not document:
        return jsonify({'message': 'Document not found or access denied'}), 404
    try:
        tx_hash = contract.functions.revokeDocument(document.document_hash).transact({
            'from': web3.eth.defaultAccount
        })
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        db.session.delete(document)
        db.session.commit()
        return jsonify({'message': 'Document deleted', 'transaction_hash': receipt.transactionHash.hex()})
    except Exception as e:
        logging.error(f"Error deleting document: {e}")
        return jsonify({'message': 'Deletion failed'}), 500

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    return send_from_directory('.', 'admin_dashboard.html')

def hash_document(file):
    return Web3.keccak(file.read()).hex()

def is_malware(file):
    file.seek(0)
    clamd_host = '127.0.0.1'
    clamd_port = 3310
    cd = clamd.ClamdNetworkSocket(clamd_host, clamd_port)
    result = cd.instream(file)
    return result['stream'][0] == 'FOUND'

if __name__ == '__main__':
    app.run(debug=True, ssl_context=('C:\\Users\\vinay\\Downloads\\nginx-1.26.1\\nginx-selfsigned.crt', 'C:\\Users\\vinay\\Downloads\\nginx-1.26.1\\nginx-selfsigned.key'))
