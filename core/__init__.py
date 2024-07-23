from flask import Flask, request, jsonify
import urllib.parse
import logging
from core.addons.extensions import db, jwt
from core.addons.functions import jsonifyFormat
from decouple import config
from flask_cors import CORS
from datetime import datetime, timedelta


# BLUEPRINTS CALL
from .controllers.buyers.create_buyers import bp_buyers
from .controllers.farmers.create_farmers import bp_farmers
from .controllers.payments.create_payments import bp_payment
from .controllers.admin.create_admin import bp_admin
from .controllers.reset.create_reset import bp_reset


def create_app():
    app = Flask(__name__)
    CORS(app)

    db_enviroment = config("ENVIROMENT")
    db_password = config("DB_PASS")

    if db_enviroment == "Development":
        encoded = urllib.parse.quote_plus(db_password)
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            "postgresql://agriadmin:" + encoded + "@138.197.231.118/agrilink_db"
        )
    else:
        encoded = urllib.parse.quote_plus(db_password)
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            "postgresql://agriadmin:" + encoded + "@138.197.231.118/agrilink_db"
        )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    db.init_app(app)

    @app.errorhandler(429)
    def too_many_request(error):
        resp = jsonify(
            {
                "status": 429,
                "isError": "true",
                "message": "Too many requests. Please try again later.",
            }
        )
        http_response = jsonifyFormat(resp, 200)
        return http_response

    @app.errorhandler(405)
    def method_not_allowed(error):
        resp = jsonify(
            {
                "status": 405,
                "isError": "true",
                "message": "The method is not allowed for this request",
            }
        )
        http_response = jsonifyFormat(resp, 200)
        return http_response

    @jwt.expired_token_loader
    def my_expired_token_callback(jwt_header, jwt_data):
        resp = jsonify({"status": 401, "isError": True, "message": "Token has expired"})
        return resp

    # JWT configs
    app.secret_key = config("SECRET_KEY")
    app.config["JWT_TOKEN_LOCATION"] = ["headers", "query_string"]
    app.config["JWT_BLACKLIST_ENABLED"] = True
    app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=120)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_ALGORITHM"] = "HS256"

    # BLUEPRINTS IMPLEMENTATION
    app.register_blueprint(bp_buyers, url_prefix="/agrilinkapi/buyers")
    app.register_blueprint(bp_farmers, url_prefix="/agrilinkapi/farmers")
    app.register_blueprint(bp_payment, url_prefix="/agrilinkapi/payment")
    app.register_blueprint(bp_admin, url_prefix="/agrilinkapi/admin")
    app.register_blueprint(bp_reset, url_prefix="/agrilinkapi/reset")

    jwt.init_app(app)
    return app
