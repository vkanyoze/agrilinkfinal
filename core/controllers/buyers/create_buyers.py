from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import and_
import math
from ...models.buyerModel import Buyers
from ...models.buyerProfileModel import BuyerProfile
from ...models.farmProfileModel import FarmProfile
from ...models.productsModel import Products
from ...addons.extensions import db
from ...addons.functions import (
    gen_len_code,
    send_sms_use_bulksms,
    jsonifyFormat,
    send_email,
    saveimgtofile,
    get_coordinates,
    sendSMS,
)
from jwt.algorithms import get_default_algorithms
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from datetime import datetime, timedelta
import pytz
import random
import jwt
from decouple import config

bp_buyers = Blueprint("create_buyers", __name__, template_folder="templates")

base_url = config("BASE_URL")
current_time = datetime.now(pytz.timezone("Africa/Lusaka"))
project_enviroment = config("ENVIROMENT")


# STATUS ENDPOINT
@bp_buyers.route("/check_status", methods=["GET"])
def check_status():
    # Get the current UTC time
    current_utc_time = datetime.utcnow()

    # Convert the UTC time to a string in a readable format
    formatted_time = current_utc_time.strftime("%Y-%m-%d %H:%M:%S")

    # Return the response as a string
    return "AgriLink Buyers is running " + formatted_time


# REGISTRATION ENDPOINT
@bp_buyers.route("/register", methods=["POST"])
def register():
    _json = request.json

    _firstname = _json["firstname"]
    _lastname = _json["lastname"]
    _email = _json["email"]
    _phonenumber = _json["phonenumber"]
    _address = _json["address"]
    _password = _json["password"]
    _confirm_password = _json["confirmpassword"]

    # GET CLIENT IP
    client_ip = request.remote_addr

    # Checking if values has been passed from the client
    if (
        _firstname
        and _lastname
        and _email
        and _phonenumber
        and _address
        and _password
        and _confirm_password
    ):
        # password validation
        if len(_password) < 8:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Password must be more than 8 Characters",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        elif _password != _confirm_password:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Your passwords do not match",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        else:
            # Check if phone number is already in the database
            is_mobile = Buyers.query.filter_by(mobilenum=_phonenumber).first()

            if is_mobile:
                resp = jsonify(
                    {
                        "status": 400,
                        "isError": "true",
                        "message": "Phone number already used to registered an account. Use a different number",
                    }
                )
                http_response = jsonifyFormat(resp, 200)
                return http_response

            else:
                # Check if email is already in the database
                is_email = Buyers.query.filter_by(email=_email).first()

                if is_email:
                    resp = jsonify(
                        {
                            "status": 400,
                            "isError": "true",
                            "message": "Email already used to registered an account. Use a different number",
                        }
                    )
                    http_response = jsonifyFormat(resp, 200)
                    return http_response

                else:
                    _hashed_password = generate_password_hash(_password)
                    _userid = "".join(
                        [str(random.randint(0, 999)).zfill(3) for _ in range(2)]
                    )
                    verification_code = gen_len_code(6, True)
                    is_verified = "Not Verified"
                    datecreated = datetime.utcnow()

                    new_user = Buyers(
                        id=_userid,
                        firstname=_firstname,
                        lastname=_lastname,
                        email=_email,
                        password=_hashed_password,
                        mobilenum=_phonenumber,
                        address=_address,
                        is_email_verified=is_verified,
                        is_mobile_verified=is_verified,
                        email_verification_code=verification_code,
                        mobile_verification_code=verification_code,
                        reset_code=0,
                        datecreated=datecreated,
                        lastmodified=datecreated,
                    )
                    db.session.add(new_user)
                    db.session.commit()

                    # SEND AN EMAIL
                    subject = "Confirm your Agrilink account "
                    body = render_template(
                        "index_registration.html", otp=verification_code
                    )

                    # Sending Email
                    sent = send_email(_email, subject, body)

                    resp = jsonify(
                        {
                            "status": 200,
                            "isError": "false",
                            "message": "Account successfully created.",
                        }
                    )

                    http_response = jsonifyFormat(resp, 200)
                    return http_response

    # If the keys are not passed
    else:
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# EMAIL ADDRESS VERIFICATION ENDPOINT
@bp_buyers.route("/email_verification", methods=["POST"])
def email_verification():
    # GETTING VALUES FROM CLIENT
    _json = request.json

    # parameter signature is specified
    _email = _json["email"]
    _otp = _json["otp"]

    # Check if email is already in the database
    is_email = Buyers.query.filter_by(email=_email).first()

    if is_email:
        is_otp = Buyers.query.filter_by(email_verification_code=_otp).first()

        if is_otp:
            # Update the email status
            is_email.is_email_verified = "Verified"
            db.session.commit()

            resp = jsonify(
                {
                    "status": 200,
                    "isError": "false",
                    "message": "Email is verified successfully",
                }
            )
            return resp

        else:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "OTP not found",
                }
            )
        return resp

    else:
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "Error with the email verification",
            }
        )
        return resp


# RESEND VERIFICATION EMAIL
@bp_buyers.route("/resend_email", methods=["POST"])
def resend_email():
    _json = request.json

    _email = _json["email"]

    # Checking if values has been passed from the client
    if _email:
        # Check if email is found in the database
        is_email = Buyers.query.filter_by(email=_email).first()

        if is_email:
            is_verified = is_email.is_email_verified

            if is_verified == "Verified":
                resp = jsonify(
                    {
                        "status": 400,
                        "isError": "true",
                        "message": "Email is already verified",
                    }
                )
                http_response = jsonifyFormat(resp, 200)
                return http_response

            else:
                verification_code = gen_len_code(6, True)

                update_code = Buyers.query.filter_by(email=_email).first()

                if update_code:
                    update_code.email_verification_code = verification_code
                    db.session.commit()

                    # SEND AN EMAIL
                    subject = "Confirm your Agrilink account "
                    body = render_template(
                        "index_registration.html", otp=verification_code
                    )

                    # Sending Email
                    sent = send_email(_email, subject, body)
                    resp = jsonify(
                        {
                            "status": 200,
                            "isError": "false",
                            "message": "Link resend successfully.",
                        }
                    )

                    http_response = jsonifyFormat(resp, 200)
                    return http_response
        else:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Please enter missing value",
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response


# SEND OTP TO MOBILE NUMBER FOR VERIFICATION
@bp_buyers.route("/send_otp", methods=["POST"])
def send_otp():
    _json = request.json

    _email = _json["email"]

    # Checking if values has been passed from the client
    if _email:
        # Check if header_value is already in the database
        is_user_mobile = Buyers.query.filter_by(email=_email).first()

        if is_user_mobile:
            # Generate OTP
            otp_code = gen_len_code(6, True)

            message = (
                "Your one time password to activate your AgriLink account is : "
                + otp_code
            )

            # Send otp code
            sresponse = send_sms_use_bulksms(is_user_mobile.mobilenum, message)

            # Update the code
            is_user_mobile.mobile_verification_code = otp_code
            db.session.commit()

            resp = (
                jsonify(
                    {
                        "status": 200,
                        "isError": "false",
                        "message": "OTP sent successfully",
                    }
                ),
                200,
            )
            return resp

        else:
            # MOBILE DOES NOT EXIST
            resp = jsonify(
                {"status": 400, "isError": "true", "message": "Account does not exist"}
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# RESEND OTP TO MOBILE NUMBER FOR VERIFICATION
@bp_buyers.route("/resend_otp", methods=["POST"])
def resend_otp():
    _json = request.json
    _mobile = _json["mobile"]

    # Checking if values has been passed from the client
    if _mobile:
        # Check if header_value is already in the database
        is_user_mobile = Buyers.query.filter_by(mobilenum=_mobile).first()

        if is_user_mobile:
            # Generate OTP
            otp_code = gen_len_code(6, True)

            message = (
                "Your one time password to activate your AgriLink account is : "
                + otp_code
            )

            # Send otp code
            zresponse = sendSMS(is_user_mobile.mobilenum, "AgriLink", message)

            # Update the code
            is_user_mobile.mobile_verification_code = otp_code
            db.session.commit()

            resp = (
                jsonify(
                    {
                        "status": 200,
                        "isError": "false",
                        "message": "OTP sent successfully",
                    }
                ),
                200,
            )
            return resp

        else:
            # MOBILE DOES NOT EXIST
            resp = jsonify(
                {"status": 400, "isError": "true", "message": "Account does not exist"}
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# MOBILE NUMBER VERIFICATION ENDPOINT
@bp_buyers.route("/phone_verification", methods=["POST"])
def phone_verification():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _mobile = _json["mobile"]
    _otp = _json["otp"]

    if _mobile and _otp:
        # Check if mobile is already in the database
        is_user_mobile = Buyers.query.filter_by(mobilenum=_mobile).first()

        if is_user_mobile:
            # Check if otp is already in the database
            is_user_otp = Buyers.query.filter_by(mobile_verification_code=_otp).first()

            if is_user_otp:
                is_user_mobile.is_mobile_verified = "Verified"
                db.session.commit()

                resp = jsonify(
                    {
                        "status": 200,
                        "isError": "false",
                        "message": "Mobile is verified successfully",
                    }
                )
                http_response = jsonifyFormat(resp, 200)
                return http_response

            else:
                resp = jsonify(
                    {
                        "status": 400,
                        "isError": "true",
                        "message": "Error verifying using this OTP",
                    }
                )
                http_response = jsonifyFormat(resp, 200)
                return http_response

        else:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Error with the mobile verification",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response
    else:
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )
        http_response = jsonifyFormat(resp, 200)
        return http_response


# FUNCTION TO LOGIN
@bp_buyers.route("/login", methods=["POST"])
def login():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]
    _password = _json["password"]

    if _email and _password:
        # CHECK IF DETAILS EXIST IN FARMERS TABLE
        user = Buyers.query.filter_by(email=_email).first()

        if user:
            # GETTING ID AND PASSWORD FROM DB
            _id = user.id
            userpassword = user.password
            confirm_email_verified = user.is_email_verified
            confirm_mobile_verified = user.is_mobile_verified

            # CHECKING PASSWORD
            if check_password_hash(userpassword, _password):
                # CREATE ACCESS AND REFRESH TOKEN
                refresh = create_refresh_token(identity=_id)
                access = create_access_token(identity=_id)

                # CREATE EXPIRATION DATE AND TIME
                exp_access_timestamp = datetime.now() + timedelta(minutes=60)
                exp_refresh_timestamp = datetime.now() + timedelta(days=30)

                if confirm_email_verified == "Verified":
                    if confirm_mobile_verified == "Verified":
                        # RESPONSE WHEN THE ATHENTICATION IS WORKING
                        resp = jsonify(
                            {
                                "status": 200,
                                "isError": "false",
                                "message": "User Successfully authenticated.",
                                "access": access,
                                "access_exp": exp_access_timestamp,
                                "refresh": refresh,
                                "refresh_exp": exp_refresh_timestamp,
                            }
                        )

                        http_response = jsonifyFormat(resp, 200)
                        return http_response

                    else:
                        # RESPONSE MOBILE NOT VERIFIED
                        resp = jsonify(
                            {
                                "status": 400,
                                "isError": "true",
                                "message": "Mobile number not verified",
                                "access": access,
                                "access_exp": exp_access_timestamp,
                                "refresh": refresh,
                                "refresh_exp": exp_refresh_timestamp,
                            }
                        )

                        http_response = jsonifyFormat(resp, 200)
                        return http_response
                else:
                    # RESPONSE MOBILE NOT VERIFIED
                    resp = jsonify(
                        {
                            "status": 400,
                            "isError": "true",
                            "message": "Email address not verified",
                            "access": access,
                            "access_exp": exp_access_timestamp,
                            "refresh": refresh,
                            "refresh_exp": exp_refresh_timestamp,
                        }
                    )

                    http_response = jsonifyFormat(resp, 200)
                    return http_response

            else:
                # RESPONSE WHEN THE PASSWORD IS WRONG
                resp = jsonify(
                    {
                        "status": 400,
                        "isError": "true",
                        "message": "Invalid  password please check and try again",
                    }
                )

                http_response = jsonifyFormat(resp, 200)
                return http_response

        else:
            # RESPONSE WHEN THE MOBILE IS WRONG
            resp = jsonify(
                {
                    "status": 401,
                    "isError": "true",
                    "message": "Invalid email please check and try again",
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# refresh tokens to access this route.
@bp_buyers.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    # Getting old access token
    identity = get_jwt_identity()

    if identity:
        # Check if user exists
        is_user = Buyers.query.filter_by(id=identity).first()

        if is_user:
            # Create an access and refresh token
            access_token = create_access_token(identity=identity)
            refresh_token = create_refresh_token(identity=identity)

            # Set Expiration time for access and refresh token
            exp_access_timestamp = datetime.now() + timedelta(minutes=90)
            exp_refresh_timestamp = datetime.now() + timedelta(hours=24)

            # RESPONSE WHEN THE ATHENTICATION IS WORKING
            resp = jsonify(
                {
                    "status": 200,
                    "refresh": refresh_token,
                    "access": access_token,
                    "access_exp": exp_access_timestamp,
                    "refresh_exp": exp_refresh_timestamp,
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# FORGOT PASSWORD ENDPOINT
@bp_buyers.route("/forgot_password", methods=["POST"])
def forgot_password():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]

    if _email:
        # Check if user exists
        is_user = Buyers.query.filter_by(email=_email).first()

        if is_user:
            # Generate OTP
            otp_code = gen_len_code(6, True)

            message = (
                "Your one time password to reset your AgriLink account is : " + otp_code
            )

            # Send otp code
            zresponse = sendSMS(is_user.mobilenum, "AgriLink", message)

            # SEND AN EMAIL
            subject = "Reset your Agrilink account "
            body = render_template("reset.html", otp=otp_code)

            # Sending Email
            sent = send_email(_email, subject, body)

            # Update the code
            is_user.reset_code = otp_code
            db.session.commit()

            resp = jsonify(
                {
                    "status": 200,
                    "isError": "false",
                    "message": "OTP successfully send",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        else:
            # RESPONSE WHEN USER IS NOT FOUND
            resp = jsonify(
                {"status": 400, "isError": "true", "message": "User does not exist"}
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# FORGOT PASSWORD ENDPOINT
@bp_buyers.route("/verifyotp_forgot_password", methods=["POST"])
def verifyotp_forgot_password():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]
    _otp = _json["otp"]

    if _email and _otp:
        # Check if user exists
        is_user = Buyers.query.filter_by(reset_code=_otp, email=_email).first()

        if is_user:
            resp = jsonify(
                {
                    "status": 200,
                    "isError": "false",
                    "message": "OTP verified successfully ",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        else:
            # RESPONSE WHEN USER IS NOT FOUND
            resp = jsonify({"status": 400, "isError": "true", "message": "Wrong OTP"})

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


# NEW PASSWORD ENDPOINT
@bp_buyers.route("/new_password", methods=["POST"])
def new_password():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]
    _password = _json["password"]
    _confirmpassword = _json["confirmpassword"]

    if _password and _confirmpassword:
        # password validation
        if len(_password) < 8:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Password must be more than 8 Characters",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        elif _password != _confirmpassword:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Your passwords do not match",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        else:
            # Check if user exists
            is_user = Buyers.query.filter_by(email=_email).first()

            if is_user:
                _hashed_password = generate_password_hash(_password)

                # UPDATE PASSWORD
                is_user.password = _hashed_password
                db.session.commit()

                resp = jsonify(
                    {
                        "status": 200,
                        "isError": "false",
                        "message": "Password changed  successfully",
                    }
                )
                http_response = jsonifyFormat(resp, 200)
                return http_response

            else:
                # RESPONSE WHEN USER IS NOT FOUND
                resp = jsonify(
                    {"status": 400, "isError": "true", "message": "User does not exist"}
                )

                http_response = jsonifyFormat(resp, 200)
                return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth's radius in kilometers

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c  # Distance in kilometers

    return distance


def paginate_results(farms, page_size, page_number):
    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size
    return farms[start_index:end_index]


@bp_buyers.route("/farmer_list", methods=["POST"])
def farmer_list():
    _json = request.json
    _latitude = _json["latitude"]
    _longitude = _json["longitude"]

    if _latitude and _longitude:
        # Retrieve farm data from the database
        farms = FarmProfile.query.all()

        if farms:
            # Calculate distances and sort farms based on distance
            farms.sort(
                key=lambda farm: haversine(
                    _latitude,
                    _longitude,
                    float(farm.farm_latitude),
                    float(farm.farm_longitude),
                )
            )

            # Pagination parameters from query parameters
            page_size = int(request.args.get("page_size", 2))
            page_number = int(request.args.get("page_number", 1))

            # Get paginated results
            paginated_farms = paginate_results(farms, page_size, page_number)

            # Prepare response with distance
            response = {
                "farms": [
                    {
                        "id": farm.farm_id,
                        "name": farm.farm_name,
                        "description": farm.description,
                        "address": farm.farm_address,
                        "logo": farm.farm_logo,
                        "distance_km": haversine(
                            _latitude,
                            _longitude,
                            float(farm.farm_latitude),
                            float(farm.farm_longitude),
                        ),
                    }
                    for farm in paginated_farms
                ]
            }

            resp = jsonify(
                {
                    "status": 200,
                    "isError": "false",
                    "message": "Farms found",
                    "paginated": response,
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

        else:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Farms not found",
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_buyers.route("/create_profile", methods=["POST"])
@jwt_required()
def create_profile():
    # Access the JWT payload
    _user_id = get_jwt_identity()

    _json = request.json

    _buyer_address = _json["buyer_address"]
    _buyer_image = _json["buyer_image"]

    if _user_id and _buyer_address and _buyer_image:
        coordinates = get_coordinates(_buyer_address)

        _longitude = ""
        _latitude = ""

        if coordinates:
            _latitude, _longitude = coordinates
        else:
            _latitude, _longitude = 0, 0

        logo = saveimgtofile(_buyer_image)
        datecreated = datetime.utcnow()

        buyer_profile = BuyerProfile(
            buyer_id=_user_id,
            buyer_address=_buyer_address,
            buyer_image=logo,
            buyer_latitude=_longitude,
            buyer_longitude=_latitude,
            status="Active",
            create_timestamp=datecreated,
            update_timestamp=datecreated,
        )
        db.session.add(buyer_profile)
        db.session.commit()

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Profile created successfully",
            }
        )
        http_response = jsonifyFormat(resp, 200)
        return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_buyers.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    # Check if user is registered
    is_user_present = Buyers.query.filter_by(id=current_user_id).first()

    if is_user_present:
        _id = is_user_present.id
        _firstname = is_user_present.firstname
        _lastname = is_user_present.lastname

        # Check if user is registered
        is_user_profile = BuyerProfile.query.filter_by(buyer_id=current_user_id).first()

        if is_user_profile:
            _buyer_address = is_user_profile.buyer_address
            _buyer_image = is_user_profile.buyer_image
            _buyer_latitude = is_user_profile.buyer_latitude
            _buyer_longitude = is_user_profile.buyer_longitude

            # Construct the response
            profile_data = {
                "_firstname": _firstname,
                "_lastname": _lastname,
                "_buyer_address": _buyer_address,
                "_buyer_image": _buyer_image,
                "_buyer_latitude": _buyer_latitude,
                "_buyer_longitude": _buyer_longitude,
            }

            resp = jsonify(
                {
                    "status": 200,
                    "isError": "false",
                    "message": "Profile found",
                    "profile": [profile_data],
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

        # If Profile Not Present
        else:
            _firstname = is_user_present.firstname
            _lastname = is_user_present.lastname
            _mobile = is_user_present.mobilenum
            _email = is_user_present.email
            _address = is_user_present.address

            # Construct the response
            profile_data = {
                "_firstname": _firstname,
                "_lastname": _lastname,
                "_email": _email,
                "_mobile": _mobile,
                "_address": _address,
            }

            # RESPONSE WHEN SOME DETAILS ARE MISSING
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Profile not Found",
                    "profile": [profile_data],
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If User Not Present
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "User not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_buyers.route("/list_farmers", methods=["GET"])
def list_farmers():
    farm_profiles = FarmProfile.query.all()

    if farm_profiles:
        # Convert the farm profiles to a list of dictionaries
        farm_profiles_list = []
        for profile in farm_profiles:
            farm_profiles_list.append(
                {
                    "farm_id": profile.farm_id,
                    "farm_name": profile.farm_name,
                    "description": profile.description,
                    "farm_address": profile.farm_address,
                    "farm_logo": profile.farm_logo,
                }
            )

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Farms found",
                "farms": [farm_profiles_list],
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response

    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "Farms not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_buyers.route("/list_products", methods=["POST"])
def list_products():
    _json = request.json
    _farmID = _json["farmid"]

    if _farmID:
        # Query the database to get products for the specific farmer_id
        products = Products.query.filter_by(farmer_id=_farmID).all()

        if products:
            # Convert the products to a list of dictionaries
            products_list = [
                {
                    "id": product.id,
                    "product_name": product.product_name,
                    "product_description": product.product_description,
                    "product_weight": product.product_weight,
                    "product_quantity": product.product_quantity,
                    "product_price": product.product_price,
                    "product_image": product.product_image,
                }
                for product in products
            ]

            resp = jsonify(
                {
                    "status": 200,
                    "isError": "false",
                    "message": "Products found",
                    "products": [products_list],
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

        else:
            # RESPONSE WHEN SOME DETAILS ARE MISSING
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": "Products not Found",
                }
            )

            http_response = jsonifyFormat(resp, 200)
            return http_response

    # If the keys are not passed
    else:
        # RESPONSE WHEN SOME DETAILS ARE MISSING
        resp = jsonify(
            {
                "status": 400,
                "isError": "true",
                "message": "One or more key values are missing, please enter missing values",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response
