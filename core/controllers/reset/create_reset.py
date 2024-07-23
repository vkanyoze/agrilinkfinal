from flask import Blueprint, request, jsonify, make_response
from ...models.buyerModel import Buyers
from ...models.farmerModel import Farmers
from ...models.farmProfileModel import FarmProfile
from ...models.buyerProfileModel import BuyerProfile
from ...addons.functions import jsonifyFormat
from ...addons.extensions import db
from datetime import datetime, timedelta
import pytz


bp_reset = Blueprint("create_reset", __name__)
current_time = datetime.now(pytz.timezone("Africa/Lusaka"))


@bp_reset.route("/delete_account", methods=["POST"])
def delete_account():
    _json = request.json
    _email = _json["email"]

    if _email:
        # Check if otp is already in the database
        is_farmer_email = Farmers.query.filter_by(email=_email).first()

        if is_farmer_email:
            _farmerid = is_farmer_email.id

            # EDIT DETAILS
            is_farmer_email.firstname = "Deleted" + str(current_time)
            is_farmer_email.lastname = "Deleted" + str(current_time)
            is_farmer_email.email = "Deleted" + str(current_time)
            is_farmer_email.mobilenum = "Deleted" + str(current_time)
            is_farmer_email.address = "Deleted" + str(current_time)
            db.session.commit()

            # Check farmer id exist
            is_farmer_profile = FarmProfile.query.filter_by(farm_id=_farmerid).first()

            if is_farmer_profile:
                is_farmer_profile.farm_name = "Deleted" + str(current_time)
                is_farmer_profile.description = "Deleted" + str(current_time)
                is_farmer_profile.farm_address = "Deleted" + str(current_time)
                is_farmer_profile.farm_logo = "Deleted" + str(current_time)
                is_farmer_profile.farm_latitude = "Deleted" + str(current_time)
                is_farmer_profile.farm_longitude = "Deleted" + str(current_time)
                is_farmer_profile.status = "Deleted" + str(current_time)

        # Check if otp is already in the database
        is_buyer_email = Buyers.query.filter_by(email=_email).first()

        if is_buyer_email:
            _buyerid = is_buyer_email.id

            # EDIT DETAILS
            is_buyer_email.firstname = "Deleted" + str(current_time)
            is_buyer_email.lastname = "Deleted" + str(current_time)
            is_buyer_email.email = "Deleted" + str(current_time)
            is_buyer_email.mobilenum = "Deleted" + str(current_time)
            is_buyer_email.address = "Deleted" + str(current_time)
            db.session.commit()

            # Check buyer id exist
            is_buyer_profile = BuyerProfile.query.filter_by(buyer_id=_buyerid).first()

            if is_buyer_profile:
                is_buyer_profile.buyer_address = "Deleted" + str(current_time)
                is_buyer_profile.buyer_image = "Deleted" + str(current_time)
                is_buyer_profile.buyer_latitude = "Deleted" + str(current_time)
                is_buyer_profile.buyer_longitude = "Deleted" + str(current_time)
                is_buyer_profile.status = "Deleted" + str(current_time)

        resp = jsonify(
              {
                "status": 200,
                "isError": "false",
                "message": "Account successfully deleted.",
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
