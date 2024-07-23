from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import and_
from ...models.farmerModel import Farmers
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

bp_farmers = Blueprint("create_farmers", __name__, template_folder="templates")

base_url = config("BASE_URL")
current_time = datetime.now(pytz.timezone("Africa/Lusaka"))
project_enviroment = config("ENVIROMENT")


# STATUS ENDPOINT
@bp_farmers.route("/check_status", methods=["GET"])
def check_status():
    # Get the current UTC time
    current_utc_time = datetime.utcnow()

    # Convert the UTC time to a string in a readable format
    formatted_time = current_utc_time.strftime("%Y-%m-%d %H:%M:%S")

    # Return the response as a string
    return "AgriLink Buyers is running " + formatted_time


# REGISTRATION ENDPOINT
@bp_farmers.route("/register", methods=["POST"])
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
            is_mobile = Farmers.query.filter_by(mobilenum=_phonenumber).first()

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
                is_email = Farmers.query.filter_by(email=_email).first()

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

                    new_user = Farmers(
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
@bp_farmers.route("/email_verification", methods=["POST"])
def email_verification():
    # GETTING VALUES FROM CLIENT
    _json = request.json

    # parameter signature is specified
    _email = _json["email"]
    _otp = _json["otp"]

    # Check if email is already in the database
    is_email = Farmers.query.filter_by(email=_email).first()

    if is_email:
        is_otp = Farmers.query.filter_by(email_verification_code=_otp).first()

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
@bp_farmers.route("/resend_email", methods=["POST"])
def resend_email():
    _json = request.json

    _email = _json["email"]

    # Checking if values has been passed from the client
    if _email:
        # Check if email is found in the database
        is_email = Farmers.query.filter_by(email=_email).first()

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

                update_code = Farmers.query.filter_by(email=_email).first()

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
@bp_farmers.route("/send_otp", methods=["POST"])
def send_otp():
    _json = request.json

    _email = _json["email"]

    # Checking if values has been passed from the client
    if _email:
        # Check if header_value is already in the database
        is_user_mobile = Farmers.query.filter_by(email=_email).first()

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
@bp_farmers.route("/resend_otp", methods=["POST"])
def resend_otp():
    _json = request.json

    _mobile = _json["mobile"]

    # Checking if values has been passed from the client
    if _mobile:
        # Check if header_value is already in the database
        is_user_mobile = Farmers.query.filter_by(mobilenum=_mobile).first()

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
@bp_farmers.route("/phone_verification", methods=["POST"])
def phone_verification():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _mobile = _json["mobile"]
    _otp = _json["otp"]

    if _mobile and _otp:
        # Check if mobile is already in the database
        is_user_mobile = Farmers.query.filter_by(mobilenum=_mobile).first()

        if is_user_mobile:
            # Check if otp is already in the database
            is_user_otp = Farmers.query.filter_by(mobile_verification_code=_otp).first()

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
@bp_farmers.route("/login", methods=["POST"])
def login():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]
    _password = _json["password"]

    if _email and _password:
        # CHECK IF DETAILS EXIST IN FARMERS TABLE
        user = Farmers.query.filter_by(email=_email).first()

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
@bp_farmers.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    # Getting old access token
    identity = get_jwt_identity()

    if identity:
        # Check if user exists
        is_user = Farmers.query.filter_by(id=identity).first()

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
@bp_farmers.route("/forgot_password", methods=["POST"])
def forgot_password():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]

    if _email:
        # Check if user exists
        is_user = Farmers.query.filter_by(email=_email).first()

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
@bp_farmers.route("/verifyotp_forgot_password", methods=["POST"])
def verifyotp_forgot_password():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]
    _otp = _json["otp"]

    if _email and _otp:
        # Check if user exists
        is_user = Farmers.query.filter_by(reset_code=_otp, email=_email).first()

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
@bp_farmers.route("/new_password", methods=["POST"])
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
            is_user = Farmers.query.filter_by(email=_email).first()

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


@bp_farmers.route("/create_profile", methods=["POST"])
@jwt_required()
def create_profile():
    # Access the JWT payload
    _user_id = get_jwt_identity()

    _json = request.json

    _farm_name = _json["farm_name"]
    _description = _json["description"]
    _farm_address = _json["farm_address"]
    _farm_logo = _json["farm_logo"]

    if _user_id and _farm_name and _description and _farm_address and _farm_logo:
        coordinates = get_coordinates(_farm_address)

        _longitude = ""
        _latitude = ""

        if coordinates:
            _latitude, _longitude = coordinates

        else:
            _latitude, _longitude = 0, 0

        logo = saveimgtofile(_farm_logo)
        datecreated = datetime.utcnow()

        farmer_profile = FarmProfile(
            farm_id=_user_id,
            farm_name=_farm_name,
            description=_description,
            farm_address=_farm_address,
            farm_logo=logo,
            farm_latitude=_longitude,
            farm_longitude=_latitude,
            status="Active",
            create_timestamp=datecreated,
            update_timestamp=datecreated,
        )
        db.session.add(farmer_profile)
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


@bp_farmers.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    # Check if user is registered
    is_user_present = Farmers.query.filter_by(id=current_user_id).first()

    if is_user_present:
        _id = is_user_present.id
        _firstname = is_user_present.firstname
        _lastname = is_user_present.lastname
        _mobile = is_user_present.mobilenum
        _email = is_user_present.email

        # Check if user is registered
        is_user_profile = FarmProfile.query.filter_by(farm_id=current_user_id).first()

        if is_user_profile:
            _farm_name = is_user_profile.farm_name
            _description = is_user_profile.description
            _farm_address = is_user_profile.farm_address
            _farm_logo = is_user_profile.farm_logo
            _farm_latitude = is_user_profile.farm_latitude
            _farm_longitude = is_user_profile.farm_longitude

            # Construct the response
            profile_data = {
                "_firstname": _firstname,
                "_lastname": _lastname,
                "_mobile": _mobile,
                "_email": _email,
                "_farm_name": _farm_name,
                "_description": _description,
                "_farm_address": _farm_address,
                "_farm_logo": _farm_logo,
                "_farm_latitude": _farm_latitude,
                "_farm_longitude": _farm_longitude,
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


@bp_farmers.route("/create_products", methods=["POST"])
@jwt_required()
def create_products():
    # Access the JWT payload
    _farmer_id = get_jwt_identity()

    _json = request.json

    _product_name = _json["product_name"]
    _product_description = _json["description"]
    _product_weight = _json["product_weight"]
    _product_quantity = _json["product_quantity"]
    _product_price = _json["product_price"]
    _product_image = _json["product_image"]

    if (
        _farmer_id
        and _product_name
        and _product_description
        and _product_weight
        and _product_quantity
        and _product_price
        and _product_image
    ):
        product_img = saveimgtofile(_product_image)
        datecreated = datetime.utcnow()

        addProducts = Products(
            farmer_id=_farmer_id,
            product_name=_product_name,
            product_description=_product_description,
            product_weight=_product_weight,
            product_quantity=_product_quantity,
            product_price=_product_price,
            product_image=product_img,
            create_timestamp=datecreated,
            update_timestamp=datecreated,
        )
        db.session.add(addProducts)
        db.session.commit()

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Product created successfully",
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


@bp_farmers.route("/show_products", methods=["GET"])
@jwt_required()
def show_products():
    # Access the JWT payload
    farmer_id = get_jwt_identity()

    # Query the database to get products for the specific farmer_id
    products = Products.query.filter_by(farmer_id=farmer_id).all()

    if products:
        # Convert the products to a list of dictionaries
        products_list = [
            {
                "id": product.id,
                "farmer_id": product.farmer_id,
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

    # If Profile Not Present
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

