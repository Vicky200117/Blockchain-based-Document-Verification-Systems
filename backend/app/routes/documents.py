from flask import Blueprint, request, jsonify, redirect, url_for, send_from_directory
from flask_login import login_required, current_user
from app.models import Document
from app import db
from app.utils.blockchain import hash_document, is_malware, contract, web3

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/upload')
@login_required
def upload_page():
    if current_user.role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    return send_from_directory('templates', 'upload.html')

@documents_bp.route('/upload', methods=['POST'])
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

@documents_bp.route('/revoke', methods=['POST'])
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

@documents_bp.route('/files', methods=['GET'])
@login_required
def get_files():
    documents = Document.query.filter_by(user_id=current_user.id).all()
    response = [{'id': doc.id, 'filename': doc.filename} for doc in documents]
    return jsonify({'documents': response})
