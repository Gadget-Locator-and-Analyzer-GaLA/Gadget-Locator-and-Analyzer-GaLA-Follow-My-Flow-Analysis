from flask import Flask, Blueprint, request, Response
import hashlib 
from app import db

phase3_api = Blueprint('phase3', __name__)

@phase3_api.route('/', methods=['GET'])
def phase3():
    return "This is route for phase 3."


@phase3_api.route('/undefined_value', methods=['POST'])
def add_undefined_value():
    required_fields = ['phase', 'start_key', 'site', 'key', 'func_name', 'js', 'row', 'col', 'func']
    starting_keys = ["RTO", "RAP0", "RAP1", "JRGDP", "OGPWII", "GPWFAC"]

    # check if the request is in json format
    if not request.json:
        return Response('Data not in json format', status=400)
    # get the request body
    request_body = request.get_json()
    # check if the request body contains all the required fields
    for field in required_fields:
        if field not in request_body:
            return Response('Missing field: ' + field, status=400)
    # check if the phase is 3
    if request_body['phase'] != "3":
        return Response('Phase is not 3', status=400)
    # check if the start_key is valid
    if request_body['start_key'] not in starting_keys:
        return Response('Invalid start key', status=400)

    # hash the func using sha256
    # the hash algorithm should match the one in the V8's runtime-object.cc
    sha256_hash = hashlib.sha256()
    sha256_hash.update(request_body["func"].encode('ascii'))
    hash_func = sha256_hash.hexdigest()

    msg = ""

    # add log to undef_prop_dataset
    code_hash_obj = db["phase3"]["undef_prop_dataset"].find_one({"_id": hash_func})
    if (code_hash_obj):
        if (request_body["key"] in code_hash_obj["key_value_dict"]):
            msg += "Key already exists in undef_prop_dataset (Key is " + request_body["key"] + ", Code hash is " + hash_func + "). \n"
        else:
            code_hash_obj["key_value_dict"][request_body["key"]] = request_body["row"] + ", " + request_body["col"]
            db["phase3"]["undef_prop_dataset"].update_one({"_id": hash_func}, {"$set": {"key_value_dict": code_hash_obj["key_value_dict"]}})
    else:
        db["phase3"]["undef_prop_dataset"].insert_one({
            "_id": hash_func,
            "key_value_dict": {
                request_body["key"]: request_body["row"] + ", " + request_body["col"]
            }
        })
    
    # add log to phase_info
    site_obj = db["phase3"]["phase_info"].find_one({"_id": request_body["site"]})
    if (site_obj):
        if (hash_func in site_obj["code_hash_dict"]):
            if (request_body["key"] in site_obj["code_hash_dict"][hash_func]):
                msg += "Key already exists in phase_info (Key is " + request_body["key"] + ", Code hash is " + hash_func + "Site is " + request_body["site"] + "). \n"
            else:
                site_obj["code_hash_dict"][hash_func][request_body["key"]] = [
                    request_body["row"] + ", " + request_body["col"],
                    request_body["js"],
                    request_body["func_name"],
                    request_body["func"]
                ]
                db["phase3"]["phase_info"].update_one({"_id": request_body["site"]}, {"$set": {"code_hash_dict": site_obj["code_hash_dict"]}})
        else:
            site_obj["code_hash_dict"][hash_func] = {
                request_body["key"]: [
                    request_body["row"] + ", " + request_body["col"],
                    request_body["js"],
                    request_body["func_name"],
                    request_body["func"]
                ]
            }
            db["phase3"]["phase_info"].update_one({"_id": request_body["site"]}, {"$set": {"code_hash_dict": site_obj["code_hash_dict"]}})
    else: 
        db["phase3"]["phase_info"].insert_one({
            "_id": request_body["site"],
            "code_hash_dict": {
                hash_func: {
                    request_body["key"]: [
                        request_body["row"] + ", " + request_body["col"],
                        request_body["js"],
                        request_body["func_name"],
                        request_body["func"]
                    ]
                }
            }
        })
    
    # check if the undefined value is new (not in phase 1 info)
    phase1_obj = db["phase1"]["phase_info"].find_one({"_id": request_body["site"]})
    if phase1_obj and phase1_obj["code_hash_dict"].get(hash_func) and phase1_obj["code_hash_dict"][hash_func].get(request_body["key"]):
        msg += "Found in phase 1 info. \n"
    else:
        # add log to new_undefined_value
        undefined_value_obj = db["phase3"]["new_undefined_value"].find_one({"_id": request_body["site"]})
        if undefined_value_obj:
            if hash_func in undefined_value_obj["code_hash_dict"]:
                if request_body["key"] in undefined_value_obj["code_hash_dict"][hash_func]:
                    msg += "Found in phase 1 info. \n"
                else:
                    undefined_value_obj["code_hash_dict"][hash_func][request_body["key"]] = request_body["value"]
                    db["phase3"]["new_undefined_value"].update_one({"_id": request_body["site"]}, {"$set": {"code_hash_dict": undefined_value_obj["code_hash_dict"]}})
            else:
                undefined_value_obj["code_hash_dict"][hash_func] = {
                    request_body["key"]: request_body["value"]
                }
                db["phase3"]["new_undefined_value"].update_one({"_id": request_body["site"]}, {"$set": {"code_hash_dict": undefined_value_obj["code_hash_dict"]}})
    return msg

@phase3_api.route('/payload', methods=['POST'])
def add_payload():
    required_fields = ['phase', 'site', 'code_hash', 'key', 'value', 'row', 'col', 'sink_type']

    # check if the request is in json format
    if not request.json:
        return Response('Data not in json format', status=400)
    # get the request body
    request_body = request.get_json()
    # check if the request body contains all the required fields
    for field in required_fields:
        if field not in request_body:
            return Response('Missing field: ' + field, status=400)
    # check if the phase is 1
    if request_body['phase'] != "3":
        return Response('Phase is not 3', status=400)
    
    msg = ""

    # add payload
    site_obj = db["phase3"]["payload"].find_one({"_id": request_body["site"]})
    if (site_obj):
        if (request_body["code_hash"] in site_obj["code_hash_dict"]):
            if (request_body["key"] in site_obj["code_hash_dict"][request_body["code_hash"]]):
                msg += "Key already exists in payload (Key is " + request_body["key"] + ", Code hash is " + request_body["code_hash"] + ", Site is " + request_body["site"] + "). \n"
            else:
                site_obj["code_hash_dict"][request_body["code_hash"]][request_body["key"]] = {
                    "value": request_body["value"],
                    "row": request_body["row"],
                    "col": request_body["col"],
                    "sink_type": request_body["sink_type"]
                }
                db["phase3"]["payload"].update_one({"_id": request_body["site"]}, {"$set": {"code_hash_dict": site_obj["code_hash_dict"]}})
        else:
            site_obj["code_hash_dict"][request_body["code_hash"]] = {
                request_body["key"]: {
                    "value": request_body["value"],
                    "row": request_body["row"],
                    "col": request_body["col"],
                    "sink_type": request_body["sink_type"]
                }
            }
            db["phase3"]["payload"].update_one({"_id": request_body["site"]}, {"$set": {"code_hash_dict": site_obj["code_hash_dict"]}})
    else:
        db["phase3"]["payload"].insert_one({
            "_id": request_body["site"],
            "code_hash_dict": {
                request_body["code_hash"]: {
                    request_body["key"]: {
                        "value": request_body["value"],
                        "row": request_body["row"],
                        "col": request_body["col"],
                        "sink_type": request_body["sink_type"]
                    }
                }
            }
        })
    
    return msg


@phase3_api.route('/phase_info', methods=['GET'])
def get_phase_info():
    site = request.args.get('site')
    if (site):
        site_obj = db["phase3"]["phase_info"].find_one({"_id": site})
        if (site_obj):
            return site_obj
        else:
            return "Site not found"
    else:
        return "Missing site"

@phase3_api.route('/undef_prop_dataset', methods=['GET'])
def get_undef_prop_dataset():
    code_hash = request.args.get('code_hash')
    if (code_hash):
        code_hash_obj = db["phase3"]["undef_prop_dataset"].find_one({"_id": code_hash})
        if (code_hash_obj):
            return code_hash_obj
        else:
            return "Code hash not found"
    else:
        return "Missing code hash"
    
@phase3_api.route('/new_undefined_value', methods=['GET'])
def get_new_undefined_value():
    site = request.args.get('site')
    if (site):
        undefined_value_obj = db["phase3"]["new_undefined_value"].find_one({"_id": site})
        if (undefined_value_obj):
            return undefined_value_obj
        else:
            return "Site not found"
    else:
        return "Missing site"

@phase3_api.route('/payload', methods=['GET'])
def get_payload():
    site = request.args.get('site')
    if (site):
        payload_obj = db["phase3"]["payload"].find_one({"_id": site})
        if (payload_obj):
            return payload_obj
        else:
            return "Site not found"
    else:
        return "Missing site"