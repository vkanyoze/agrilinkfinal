from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import aliased
from sqlalchemy import func
from ...models.companyProfileModel import CompanyProfile
from ...models.adminUserModel import AdminUsers
from ...models.inputsModel import Inputs
from ...addons.extensions import db
from ...addons.functions import (
    gen_len_code,
    send_sms_use_bulksms,
    jsonifyFormat,
    send_email,
    get_coordinates,
    saveimgtofile,
)
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
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

bp_admin = Blueprint("create_admin", __name__, template_folder="templates")

base_url = config("ADMIN_BASE_URL")
current_time = datetime.now(pytz.timezone("Africa/Lusaka"))
project_enviroment = config("ENVIROMENT")


# STATUS ENDPOINT
@bp_admin.route("/check_status", methods=["GET"])
def check_status():
    # Get the current UTC time
    current_utc_time = datetime.utcnow()

    # Convert the UTC time to a string in a readable format
    formatted_time = current_utc_time.strftime("%Y-%m-%d %H:%M:%S")

    # Return the response as a string
    return "AgriLink Admin is running " + formatted_time


# REGISTRATION ENDPOINT
@bp_admin.route("/register", methods=["POST"])
def register():
    _json = request.json

    _firstname = _json["firstname"]
    _lastname = _json["lastname"]
    _email = _json["email"]
    _phonenumber = _json["phonenumber"]
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
            is_mobile = AdminUsers.query.filter_by(phonenum=_phonenumber).first()

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
                is_email = AdminUsers.query.filter_by(email=_email).first()

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

                    datecreated = datetime.utcnow()

                    new_user = AdminUsers(
                        admin_id=_userid,
                        firstname=_firstname,
                        lastname=_lastname,
                        email=_email,
                        phonenum=_phonenumber,
                        password=_hashed_password,
                        reset_code=0,
                        create_timestamp=datecreated,
                        update_timestamp=datecreated,
                    )
                    db.session.add(new_user)
                    db.session.commit()

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


# FUNCTION TO LOGIN
@bp_admin.route("/login", methods=["POST"])
def login():
    # GETTING VALUES FROM CLIENT
    _json = request.json
    _email = _json["email"]
    _password = _json["password"]

    if _email and _password:
        # CHECK IF DETAILS EXIST IN FARMERS TABLE
        user = AdminUsers.query.filter_by(email=_email).first()

        if user:
            # GETTING ID AND PASSWORD FROM DB
            _id = user.admin_id
            userpassword = user.password

            # CHECKING PASSWORD
            if check_password_hash(userpassword, _password):
                # CREATE ACCESS AND REFRESH TOKEN
                refresh = create_refresh_token(identity=_id)
                access = create_access_token(identity=_id)

                # CREATE EXPIRATION DATE AND TIME
                exp_access_timestamp = datetime.now() + timedelta(minutes=60)
                exp_refresh_timestamp = datetime.now() + timedelta(days=30)

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
@bp_admin.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    # Getting old access token
    identity = get_jwt_identity()

    if identity:
        # Check if user exists
        is_user = AdminUsers.query.filter_by(admin_id=identity).first()

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


@bp_admin.route("/company_profile", methods=["POST"])
@jwt_required()
def company_profile():
    # Access the JWT payload
    _adminid = get_jwt_identity()

    _json = request.json

    _companyname = _json["companyname"]
    _description = _json["description"]
    _companyaddress = _json["companyaddress"]
    _companylogo = _json["companylogo"]

    if _adminid and _companyname and _description and _companyaddress and _companylogo:
        coordinates = get_coordinates(_companyaddress)

        _longitude = ""
        _latitude = ""

        if coordinates:
            _latitude, _longitude = coordinates

        else:
            _latitude, _longitude = 0, 0

        logo = saveimgtofile(_companylogo)
        datecreated = datetime.utcnow()
        company_code = gen_len_code(9, True)

        companyprofile = CompanyProfile(
            company_id=company_code,
            admin_id=_adminid,
            company_name=_companyname,
            description=_description,
            company_address=_companyaddress,
            company_logo=logo,
            company_latitude=_latitude,
            company_longitude=_longitude,
            status="Active",
            create_timestamp=datecreated,
            update_timestamp=datecreated,
        )
        db.session.add(companyprofile)
        db.session.commit()

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Company Profile created successfully",
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


@bp_admin.route("/list_companies", methods=["GET"])
def list_farmers():
    company_profiles = CompanyProfile.query.all()

    if company_profiles:
        # Convert the farm profiles to a list of dictionaries
        company_profiles_list = []
        for profile in company_profiles:
            company_profiles_list.append(
                {
                    "company_id": profile.company_id,
                    "company_name": profile.company_name,
                    "description": profile.description,
                    "company_address": profile.company_address,
                    "company_logo": profile.company_logo,
                }
            )

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Farms found",
                "farms": [company_profiles_list],
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


@bp_admin.route("/create_products", methods=["POST"])
def create_products():
    # Access the JWT payload

    _json = request.json

    _company_id = _json["companyid"]
    _product_name = _json["product_name"]
    _product_description = _json["description"]
    _product_weight = _json["product_weight"]
    _product_quantity = _json["product_quantity"]
    _product_price = _json["product_price"]
    _product_image = _json["product_image"]

    if (
        _product_name
        and _product_description
        and _product_weight
        and _product_quantity
        and _product_price
        and _product_image
    ):
        product_img = saveimgtofile(_product_image)
        datecreated = datetime.utcnow()

        addInputs = Inputs(
            company_id=_company_id,
            product_name=_product_name,
            product_description=_product_description,
            product_weight=_product_weight,
            product_quantity=_product_quantity,
            product_price=_product_price,
            product_image=product_img,
            create_timestamp=datecreated,
            update_timestamp=datecreated,
        )
        db.session.add(addInputs)
        db.session.commit()

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Input created successfully",
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


@bp_admin.route("/show_inputs", methods=["POST"])
def show_inputs():
    _json = request.json

    _company_id = _json["companyid"]

    # Query the database to get products for the specific farmer_id
    products = Inputs.query.filter_by(company_id=_company_id).all()

    if products:
        # Convert the products to a list of dictionaries
        products_list = [
            {
                "id": product.id,
                "company_id": product.company_id,
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
