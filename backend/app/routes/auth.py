from flask import Blueprint, request, jsonify, redirect, url_for, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
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

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({'message': 'Logged in'})
    return jsonify({'message': 'Invalid credentials'}), 401

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.index'))

@auth_bp.route('/')
def index():
    return send_from_directory('templates', 'index.html')
