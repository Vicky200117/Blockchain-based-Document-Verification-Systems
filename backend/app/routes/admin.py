from flask import Blueprint, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from app.models import User, Document, Notification
from app import db
from app.utils.blockchain import contract, web3

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@login_required
def admin_users():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    users = User.query.all()
    return jsonify({'users': [{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in users]})

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
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
                db.session.rollback()
                return jsonify({'message': f"Error deleting document {doc.filename} for user {user.username}: {e}"}), 500
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User and associated documents deleted'})
    return jsonify({'message': 'User not found'}), 404

@admin_bp.route('/documents', methods=['GET'])
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

@admin_bp.route('/documents/<int:document_id>/verify', methods=['POST'])
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
        return jsonify({'message': 'Verification failed', 'error': str(e)}), 500

@admin_bp.route('/documents/<int:document_id>/delete', methods=['DELETE'])
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
        db.session.rollback()
        return jsonify({'message': 'Deletion failed', 'error': str(e)}), 500

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403
    return send_from_directory('templates', 'admin_dashboard.html')
