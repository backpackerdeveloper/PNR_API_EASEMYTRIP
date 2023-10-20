import subprocess
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from base64 import b64encode
from flask import Flask, request, jsonify
import time
import sys
import json  # Import json module to access the loads function

from requests import post

app = Flask(__name__)

REQUIRED_PACKAGES = ['cryptography', 'requests']

# Check if the required packages are installed
for package in REQUIRED_PACKAGES:
    try:
        __import__(package)
    except ImportError:
        # Package is not installed, so attempt to install it
        subprocess.check_call(['pip', 'install', package])

def encrypt_pnr(pnr):
    """Encrypts the PNR number using AES CBC encryption with PKCS7 padding.

    Args:
        pnr (str): The PNR number to encrypt.

    Returns:
        str: The base64-encoded encrypted PNR.

    """
    data = bytes(pnr, 'utf-8')
    backend = default_backend()
    padder = padding.PKCS7(128).padder()

    data = padder.update(data) + padder.finalize()
    key = b'8080808080808080'
    iv = b'8080808080808080'
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    ct = encryptor.update(data) + encryptor.finalize()
    enc_pnr = b64encode(ct)
    return enc_pnr.decode('utf-8')

def create_pnr_data_json(json_data):
    """Creates a JSON object with the PNR status information.

    Args:
        json_data (dict): JSON data containing the PNR status information.

    Returns:
        dict: JSON object with the PNR status information.

    Raises:
        KeyError: If the required keys are missing in the JSON data.

    """
    pnr_details = {}
    try:
        boarding_station = json_data["BrdPointName"]
        destination_station = json_data["DestStnName"]
        quota = json_data["quota"]
        class_name = json_data["className"]
        train_number = json_data["trainNumber"]
        train_name = json_data["trainName"]
        date_of_journey = json_data["dateOfJourney"]

        pnr_details["boarding_station"] = boarding_station
        pnr_details["destination_station"] = destination_station
        pnr_details["quota"] = quota
        pnr_details["class_name"] = class_name
        pnr_details["train_number"] = train_number
        pnr_details["train_name"] = train_name
        pnr_details["date_of_journey"] = date_of_journey

        passenger_list = []
        for passenger in json_data["passengerList"]:
            passenger_data = {}
            passenger_serial_number = passenger["passengerSerialNumber"]
            current_status = passenger["currentStatus"]
            current_coach_id = passenger["currentCoachId"]
            current_berth_no = passenger["currentBerthNo"]

            passenger_data["passenger_serial_number"] = passenger_serial_number
            passenger_data["current_status"] = current_status
            passenger_data["current_coach_id"] = current_coach_id
            passenger_data["current_berth_no"] = current_berth_no

            passenger_list.append(passenger_data)

        pnr_details["passenger_list"] = passenger_list
    except KeyError as e:
        raise KeyError("Invalid JSON data format. Missing key: " + str(e))

    return pnr_details

@app.route('/check_pnr', methods=['POST'])
def check_pnr():
    try:
        input_data = request.get_json()
        pnr = input_data.get('pnr')

        if pnr is None or len(pnr) != 10:
            return jsonify({"error": "Invalid PNR format"}), 400

        encrypted_pnr = encrypt_pnr(pnr)

        json_data = {
            'pnrNumber': encrypted_pnr,
        }

        response = post('https://railways.easemytrip.com/Train/PnrchkStatus', json=json_data, verify=True)
        response.raise_for_status()
        json_data = json.loads(response.content)  # Explicitly use json.loads

        # Output PNR data in JSON format
        json_output = create_pnr_data_json(json_data)
        return jsonify(json_output)

    except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
        return jsonify({"error": f"An error occurred while connecting to the API: {str(e)}"}), 500
    except ValueError as e:
        return jsonify({"error": "Invalid response from the API. Response cannot be parsed as JSON."}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
