from web3 import Web3
import json
import logging
import clamd

web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
web3.eth.defaultAccount = web3.eth.accounts[0]

abi_path = r'C:\Users\vinay\doc_verification\build\contracts\DocumentVerification.json'
try:
    with open(abi_path) as f:
        contract_data = json.load(f)
        contract_abi = contract_data['abi']
        contract_address = '0xF987cC655DB25533bF954d78bf27e25d849326Bc'
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

def hash_document(file):
    return Web3.keccak(file.read()).hex()

def is_malware(file):
    file.seek(0)              # Reset the file pointer to the beginning of the file
    clamd_host = '127.0.0.1'
    clamd_port = 3310
    cd = clamd.ClamdNetworkSocket(clamd_host, clamd_port)  # Create a connection to the ClamAV daemon
    result = cd.instream(file)  # Scan the file
    return result['stream'][0] == 'FOUND' # Check if malware was found
