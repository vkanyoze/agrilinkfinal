from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import aliased
from sqlalchemy import func, and_, select, distinct
from ...models.buyerModel import Buyers
from ...models.farmProfileModel import FarmProfile
from ...models.buyerProfileModel import BuyerProfile
from ...models.ordersModel import Order
from ...models.productsModel import Products
from ...models.paymentModel import Payment
from ...addons.extensions import db
from ...addons.functions import (
    gen_len_code,
    send_sms_use_bulksms,
    jsonifyFormat,
    send_email,
    register_mobile_payment,
    payment_request,
    payment_status,
    sendSMS,
)
from jwt.algorithms import get_default_algorithms
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from datetime import datetime, timedelta
from io import BytesIO
import os
import pytz, requests
import random
import jwt, uuid, json
from decouple import config

bp_payment = Blueprint("create_payment", __name__)

base_url = config("BASE_URL")
current_time = datetime.now(pytz.timezone("Africa/Lusaka"))
project_enviroment = config("ENVIROMENT")


# EXPRESS LOAN REQUEST
@bp_payment.route("/accept_payment", methods=["POST"])
@jwt_required()
def accept_payment():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    _json = request.json
    _orderid = _json["orderid"]
    _amount = _json["amount"]
    _mobile = _json["mobile"]
    _serviceProvider = _json["service_provider"]
    _order = _json["order"]

    _amount = float(_amount)
    app_id = gen_len_code(32, True)
    # Convert _orderid to bytes using utf-8 encoding
    transactionid = uuid.uuid4().hex
    created_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
    payment_method = "mobile_money"
    _email = "Null"
    _payment_result = ""
    amount_to_receive = _amount - (_amount * 0.05)

    # PASSING DATA PAYMENT API
    payment_register_response = register_mobile_payment(
        transactionid,
        str(_orderid),
        _order,
        payment_method,
        _amount,
        _mobile,
        _email,
        _serviceProvider,
    )
    payment_register_str = payment_register_response.decode(
        "utf-8"
    )  # Decode bytes to string
    payment_register_dict = json.loads(payment_register_str)

    # GET THE RESPONSE STATUS
    payment_register_status = payment_register_dict.get("statuscode")

    # INITIALIZE PAYMENTS IN THE DB
    initialize_payment = Payment(
        transaction_id=transactionid,
        order_id=_orderid,
        customer_id=current_user_id,
        payment_amount=_amount,
        currency="ZMW",
        service_fee=0.05,
        amount_merchant_receive=amount_to_receive,
        payment_method=payment_method,
        payment_type=_serviceProvider,
        response_code=payment_register_status,
        status="Processing",
        transaction_referrence=0,
        transaction_date=created_date,
    )
    db.session.add(initialize_payment)
    db.session.commit()

    if payment_register_status == "200":
        """THE BEGINING OF PAYMENT PROCESSING"""
        _payment_result = payment_register_dict.get("data")
        payment_request_response = payment_request(app_id, _payment_result)

        payment_request_str = payment_request_response.decode(
            "utf-8"
        )  # Decode bytes to string
        payment_request_dict = json.loads(
            payment_request_str
        )  # Parse JSON string to dictionary
        payment_request_status = payment_request_dict.get("statuscode")

        """ THE END OF PAYMENT PROCESSING """
        if payment_request_status == "200":
            payment_status_response = payment_status(_payment_result)

            status_data_str = payment_status_response.decode(
                "utf-8"
            )  # Decode bytes to string
            status_data_dict = json.loads(
                status_data_str
            )  # Parse JSON string to dictionary

            status_response_status = status_data_dict.get("statuscode")

            if status_response_status == "200":
                # Check if transaction id is in the database
                payment_row = Payment.query.filter_by(
                    transaction_id=transactionid
                ).first()

                statusdata_resp = status_data_dict.get("data")

                if payment_row:
                    # Update transaction status  in  payments table
                    account_status = Payment.query.filter_by(
                        transaction_id=transactionid
                    ).first()
                    account_status.response_code = status_data_dict.get("statuscode")
                    account_status.status = statusdata_resp.get("transactionstatus")
                    account_status.transaction_referrence = statusdata_resp.get(
                        "reference"
                    )
                    db.session.commit()

                    formatted_amount = f"{_amount:.2f}"
                    _message = (
                        " You have paid ZMW "
                        + str(formatted_amount)
                        + " to Agrilink ref is : "
                        + statusdata_resp.get("reference")
                        + " on "
                        + created_date
                    )
                    sms_resp = sendSMS("+26" + _mobile, "AgriLink", _message)
                    resp = jsonify(
                        {
                            "status": 200,
                            "isError": "false",
                            "message": status_data_dict.get("statusmessage"),
                        }
                    )
                    http_response = jsonifyFormat(resp, 200)
                    return http_response
                else:
                    payment_row = Payment.query.filter_by(
                        transaction_id=transactionid
                    ).first()

                    if payment_row:
                        # Update status
                        account_status = Payment.query.filter_by(
                            transaction_id=transactionid
                        ).first()
                        account_status.response_code = status_data_dict.get(
                            "statuscode"
                        )
                        account_status.status = statusdata_resp.get("transactionstatus")
                        account_status.transaction_referrence = statusdata_resp.get(
                            "reference"
                        )
                        db.session.commit()
                        resp = jsonify(
                            {
                                "status": 400,
                                "isError": "true",
                                "message": status_data_dict.get("statusmessage"),
                            }
                        )
                        http_response = jsonifyFormat(resp, 200)
                        return http_response

                    else:
                        resp = jsonify(
                            {
                                "status": 400,
                                "isError": "true",
                                "message": "Transation not found",
                            }
                        )
                        http_response = jsonifyFormat(resp, 200)
                        return http_response

            else:
                resp = jsonify(
                    {
                        "status": payment_request_dict.get("statuscode"),
                        "isError": "true",
                        "message": payment_request_dict.get("statusmessage"),
                    }
                )
                http_response = jsonifyFormat(resp, 200)
                return http_response

        else:
            resp = jsonify(
                {
                    "status": 400,
                    "isError": "true",
                    "message": payment_register_dict.get("statusmessage"),
                }
            )
            http_response = jsonifyFormat(resp, 200)
            return http_response


@bp_payment.route("/record_order", methods=["POST"])
@jwt_required()
def record_order():
    # Access the JWT payload
    current_user_id = get_jwt_identity()
    try:
        data = request.get_json()

        # Iterate through the received data and save it in the database
        for order_data in data["orders_details"]:
            farmerid = ""

            productresp = Products.query.filter_by(id=order_data["productId"]).first()

            if productresp:
                farmerid = productresp.farmer_id
            else:
                farmerid = None

            new_order = Order(
                userid=current_user_id,
                orderid=data["orderID"],
                farmerid=farmerid,
                productid=order_data["productId"],
                productname=order_data["productName"],
                initialprice=order_data["initialPrice"],
                totalprice=order_data["productPrice"],
                quantity=order_data["quantity"],
                unittag=order_data["unitTag"],
                order_date=datetime.utcnow(),
            )
            db.session.add(new_order)

        db.session.commit()
        resp = jsonify(
            {
                "status": 201,
                "isError": "false",
                "message": "Order saved successfully",
            }
        )
        http_response = jsonifyFormat(resp, 200)
        return http_response

    except Exception as e:
        db.session.rollback()
        error_message = "Failed to save orders: " + str(e)
        resp = jsonify(
            {
                "status": 500,
                "isError": "true",
                "message": error_message,
            }
        )
        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_payment.route("/show_buyers_transactions", methods=["POST"])
@jwt_required()
def show_buyers_transactions():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    # Query the database to get payments for the specific userid
    is_payment = Payment.query.filter_by(customer_id=current_user_id).all()

    if is_payment:
        # Convert the products to a list of dictionaries
        payments_list = [
            {
                "id": pay.transaction_id,
                "order_id": pay.order_id,
                "customer_id": pay.customer_id,
                "payment_amount": pay.payment_amount,
                "status": pay.status,
                "transaction_referrence": pay.transaction_referrence,
                "transaction_date": pay.transaction_date,
            }
            for pay in is_payment
        ]

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Payments found",
                "payments": [payments_list],
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
                "message": "Payments not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_payment.route("/show_buyers_orders", methods=["GET"])
@jwt_required()
def show_buyers_orders():
    # Access the JWT payload
    current_user_id = get_jwt_identity()
    current_user_id_str = str(current_user_id)

    # Query to get orders for the current user, grouped by orderid and userid
    is_order = (
        db.session.query(
            Order.orderid,
            Order.productname,
            Order.quantity,
            Order.totalprice,
            Payment.payment_amount,
            Payment.status,
        )
        .join(Payment, Payment.order_id == Order.orderid)
        .filter(
            and_(
                Payment.customer_id == current_user_id_str,
                Order.userid == current_user_id_str,
            )
        )
        .all()
    )

    if is_order:
        # Convert the products to a list of dictionaries
        orders_list = [
            {
                "orderid": ord.orderid,
                "productname": ord.productname,
                "quantity": ord.quantity,
                "totalPrice": ord.totalprice,
                "status": ord.status,
            }
            for ord in is_order
        ]

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Orders found",
                "orders": [orders_list],
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
                "message": "Orders not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_payment.route("/show_farmers_orders", methods=["GET"])
@jwt_required()
def show_farmers_orders():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    # Query to get orders for the current user, grouped by orderid and userid
    is_order = (
        db.session.query(
            Order.orderid,
            Order.farmerid,
            Order.productname,
            Order.quantity,
            Order.totalprice,
            Order.order_date,
            Order.userid,
        )
        .filter_by(farmerid=str(current_user_id))
        .all()
    )

    if is_order:
        # Convert the products to a list of dictionaries
        orders_list = [
            {
                "farmerid": ord.farmerid,
                "orderid": ord.orderid,
                "productname": ord.productname,
                "quantity": ord.quantity,
                "buyer": ord.userid,
                "totalPrice": ord.totalprice,
                "order_date": ord.order_date,
            }
            for ord in is_order
        ]

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Orders found",
                "orders": [orders_list],
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
                "message": "Orders not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_payment.route("/show_transactions", methods=["GET"])
@jwt_required()
def show_transactions():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    # Step 1: Get all order IDs for the current user
    order_ids = (
        db.session.query(Order.orderid).filter_by(farmerid=str(current_user_id)).all()
    )

    # Extract the order IDs from the result
    order_ids = [order_id[0] for order_id in order_ids]

    payment_details = (
        db.session.query(
            Payment.transaction_id,
            Payment.order_id,
            Payment.payment_amount,
            Payment.service_fee,
            Payment.amount_merchant_receive,
            Payment.transaction_referrence,
            Payment.transaction_date,
        )
        .filter(Payment.order_id.in_(order_ids))
        .all()
    )

    if payment_details:
        # Convert the products to a list of dictionaries
        transaction_list = [
            {
                "transaction_id": pays.transaction_id,
                "order_id": pays.order_id,
                "payment_amount": pays.payment_amount,
                "service_fee": pays.service_fee,
                "amount_merchant_receive": pays.amount_merchant_receive,
                "transaction_referrence": pays.transaction_referrence,
                "transaction_date": pays.transaction_date,
            }
            for pays in payment_details
        ]

        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Transaction(s) found",
                "transactions": [transaction_list],
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
                "message": "Transaction(s) not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_payment.route("/show_order_location", methods=["POST"])
@jwt_required()
def show_order_location():
    # Access the JWT payload
    current_user_id = get_jwt_identity()

    order_ids = (
        db.session.query(func.min(Order.orderid).label("orderid"))
        .filter_by(farmerid=str(current_user_id))
        .group_by(Order.orderid)
        .all()
    )

    # Extract the order IDs from the result
    order_ids = [order_id.orderid for order_id in order_ids]

    print(order_ids)

    orders_data = (
        db.session.query(
            func.min(Order.orderid).label("orderid"),
            Order.farmerid.label("farmerid"),
            Order.userid.label("userid"),
            FarmProfile.farm_latitude,
            FarmProfile.farm_longitude,
        )
        .filter(Order.orderid.in_(order_ids))
        .group_by(Order.farmerid, Order.userid, FarmProfile.farm_id)
        .all()
    )

    # Accessing elements using integer indices
    buyer_ids = [order_data[2] for order_data in orders_data]

    buyer_details = (
        db.session.query(
            Buyers.id,
            Buyers.firstname,
            Buyers.lastname,
            Buyers.address,
            BuyerProfile.buyer_latitude.label("latitude"),
            BuyerProfile.buyer_longitude.label("longitude"),
        )
        .join(BuyerProfile, BuyerProfile.buyer_id == Buyers.id)
        .filter(Buyers.id.in_(buyer_ids))
        .all()
    )

    buyers_list = [
        {
            "buyer_id": buyer.id,
            "buyer_firstname": buyer.firstname,
            "buyer_lastname": buyer.lastname,
            "buyer_address": buyer.address,
            "buyer_latitude": buyer.latitude,
            "buyer_longitude": buyer.longitude,
        }
        for buyer in buyer_details
    ]

    orders_data = [
        {
            "orderid": order_data[0],  # Assuming "orderid" is the first element
            "farmerid": order_data[1],  # Assuming "farmerid" is the second element
            "buyerid": order_data[2],
            "farmer_latitude": order_data[3],
            "farmer_longitude": order_data[4],
        }
        for order_data in orders_data
    ]

    if orders_data:
        resp = jsonify(
            {
                "status": 200,
                "isError": "false",
                "message": "Order(s) Location found",
                "orders_details": [orders_data],
                "buyer_details": [buyers_list],
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
                "message": "Order(s) Location not Found",
            }
        )

        http_response = jsonifyFormat(resp, 200)
        return http_response


@bp_payment.route("/generate_invoice")
def generate_invoice():
    # Create a PDF document
    pdf_buffer = generate_pdf()

    # Create a response with the PDF content
    response = make_response(pdf_buffer)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=invoice.pdf"

    return response


def generate_pdf():
    # Create a buffer for the PDF
    buffer = BytesIO()

    # Create a PDF document
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # Company Logo
    script_directory = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_directory, "logo.png")

    pdf.drawInlineImage(logo_path, 50, A4[1] - 100, width=100, height=100)

    # Invoice Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(350, A4[1] - 40, "Invoice")

    # Today's Date
    pdf.setFont("Helvetica", 12)
    pdf.drawString(350, A4[1] - 60, "Invoice Date: 2024-01-05")

    # Reference
    reference_text = "Reference: Your_Reference_Here"
    reference_width = pdf.stringWidth(reference_text, "Helvetica", 12)
    pdf.drawString(A4[0] - 65 - reference_width, A4[1] - 80, reference_text)

    # Billing Data
    billing_data_text = "Billing Data: Billing_Data_Here"
    billing_data_width = pdf.stringWidth(billing_data_text, "Helvetica", 12)
    pdf.drawString(A4[0] - 85 - billing_data_width, A4[1] - 100, billing_data_text)

    # Our Information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, A4[1] - 150, "Our Information:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, A4[1] - 170, "Name: AgriLink Innovations")
    pdf.drawString(50, A4[1] - 185, "Address: Your Company Address")
    pdf.drawString(50, A4[1] - 200, "Address: Your Company Address")
    pdf.drawString(50, A4[1] - 215, "Phone: Your Company Phone")

    # Billing To
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(250, A4[1] - 150, "Billing To:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(250, A4[1] - 170, "Name: Customer Name")
    pdf.drawString(250, A4[1] - 185, "Address: Customer Address")
    pdf.drawString(250, A4[1] - 200, "Address: Your Company Address")
    pdf.drawString(250, A4[1] - 215, "Phone: Customer Phone")

    # Skip 3 rows
    pdf.drawString(50, A4[1] - 240, " " * 500)

    # Table Headers
    pdf.drawString(50, A4[1] - 250, "Product")
    pdf.drawString(190, A4[1] - 250, "Quantity")
    pdf.drawString(320, A4[1] - 250, "Price")
    pdf.drawString(465, A4[1] - 250, "Total")

    # Table Data
    data = [["Sample Product", 2, 50.00, 100.00], ["Sample Product", 4, 20.00, 10.00]]
    table = Table(data, colWidths=[80, 150, 100, 200])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]
        )
    )

    table.wrapOn(pdf, A4[0] - 50, A4[1] - 300)
    table.drawOn(pdf, 50, A4[1] - 300)

    # Save the PDF to the buffer
    pdf.save()

    # Move the buffer position to the beginning
    buffer.seek(0)

    return buffer.getvalue()
