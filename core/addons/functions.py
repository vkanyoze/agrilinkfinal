import secrets, string, requests, re, io, base64
import json
import ssl
import smtplib
import uuid, random
from PIL import Image
from flask import make_response, jsonify
from decouple import config
from email.message import EmailMessage
import cloudinary
import cloudinary.uploader
import cloudinary.api

sms_username = config("SMS_USER")
sms_password = config("SMS_PASS")
api_key = config("SMS_KEY")
OPENCAGE_API_KEY = config("OPENCAGE_API_KEY")

email_smtp = config("SMTP_HOST")
email_sender = config("EMAIL_USER")
email_password = config("EMAIL_PASS")

sam_app_key = config("SAM_APP_KEY")
sam_auth_key = config("SAM_AUTH_KEY")
sam_currency = config("SAM_CURRENCY")


cloudinary.config(
    cloud_name=config("CLOUD_NAME"),
    api_key=config("CLOUD_API_KEY"),
    api_secret=config("CLOUD_API_SECRET"),
)


def verify_nrc(nrc_number):
    nrc_pattern = re.compile(r"^[0-9]{6}/[0-9]{2}/[0-9]{1}$")

    is_pattern_valid = "None"

    if nrc_pattern.match(nrc_number):
        is_pattern_valid = "Valid NRC number"
    else:
        is_pattern_valid = "Invalid NRC number"

    return is_pattern_valid


# FUNCTION TO CONVERT MOBILE NUMBER TO 9 DIDGITS
def convert_phone_number(phone):
    # Check if phone contains international values +260 or 260
    if phone.find("+260") != -1:
        newphone = str.replace(phone, "+260", "")
    elif phone.find("260") != -1:
        newphone = str.replace(phone, "260", "")
    elif phone.find("0") != -1:
        newphone = str.replace(phone, "0", "")

    # actual pattern which only change this line
    num = re.sub(r"(?<!\S)(\d{3})-", r"(\1) ", newphone)
    return num


# CONVERT RESPONSE TO JSON
def jsonifyFormat(responsedata, code):
    # Set the HTTP status code
    status_code = code

    # Create the response with the desired HTTP status code
    response = make_response(responsedata, status_code)

    # Set the Content-Type header to application/json
    response.headers["Content-Type"] = "application/json"

    return response


# FUNCTION TO GENERATE DIGIT CODE
def gen_len_code(length, num_only):
    code = None

    if num_only:
        digits = string.digits
        code = "".join(secrets.choice(digits) for i in range(length))
    else:
        # alphabet = string.ascii_letters + string.digits
        alphabet = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(alphabet) for i in range(length))

    return code


# FUNCTION TO SEND SMS USING ROUTESMS API
def send_sms_use_bulksms(mobile_number, msg):
    if len(mobile_number) == 9:
        mobile_number = "0" + mobile_number

    # sending get request and saving the response as response object
    resp = requests.post(
        "https://api.rmlconnect.net:8443/bulksms/bulksms?username="
        + sms_username
        + "&password="
        + sms_password
        + "&type=0&dlr=1&destination=+26"
        + mobile_number
        + "&source=AgriLink&message="
        + msg
    )

    return resp.text.encode("utf8")


def generate_domain_name():
    letters = string.ascii_lowercase
    random_name = "".join(random.choice(letters) for _ in range(10))
    random_extension = random.choice([".com", ".net", ".org"])
    domain_name = random_name + random_extension
    return domain_name


# FUNCTION TO SEND WHATSAPP USING TEXTME API
def send_watext(mobile_number, msg):
    if len(mobile_number) == 9:
        mobile_number = "0" + mobile_number

        # sending get request and saving the response as response object
        resp = requests.post(
            "https://api.textmebot.com/send.php?recipient=+26"
            + mobile_number
            + "&apikey=qCfwZoQBKxvg&text="
            + msg
            + "&json=yes"
        )

        return resp.text.encode("utf8")


# FUNCTION TO SEND EMAIL USING SMTP
def send_email(sendto, heading, msg):
    sender = email_sender
    em = EmailMessage()
    em["From"] = sender
    em["To"] = sendto
    em["Subject"] = heading
    em.add_header("Content-Type", "text/html")
    em.set_payload(msg)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(email_smtp, 465, context=context) as smtp:
        smtp.login(sender, email_password)
        smtp.sendmail(email_sender, sendto, em.as_string().encode("utf-8"))

        return msg


# FUNCTION TO SEND EMAILS
def send_mg_email(sendto, heading, msg):
    email_resp = requests.post(
        "https://api.mailgun.net/v3/mg.kuuzapay.com/messages",
        auth=("api", config("MAIL_GUN_API_TOKEN")),
        data={
            "from": "KuuzaPay <noreply@mg.kuuzapay.com>",
            "to": sendto,
            "subject": heading,
            "html": msg,
        },
    )
    return email_resp


def saveimgtofile(userimage):
    # Decode base64 string to bytes
    image = base64.b64decode(str(userimage))

    # Generate a unique filename using UUID
    my_id = uuid.uuid4().hex
    fileName = my_id

    # Path to save the uncompressed image
    uncompressedImagePath = "upload/" + fileName + "_uncompressed.png"

    # Save the uncompressed image
    img = Image.open(io.BytesIO(image))
    img.save(uncompressedImagePath, "png")

    # Compress the image
    compressedImagePath = "upload/" + fileName + "_compressed.png"
    img.save(compressedImagePath, quality=85)  # Adjust quality as needed

    # Upload the compressed image to cloudinary
    result = cloudinary.uploader.upload(compressedImagePath, public_id=fileName)

    # Return the URL of the compressed image
    return result["url"]


def get_coordinates(address):
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "key": OPENCAGE_API_KEY,
        "q": address,
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data and data["results"]:
        location = data["results"][0]["geometry"]
        return location["lat"], location["lng"]
    else:
        return None


# SEND SMS USING ZAMTEL
def sendSMS(mobile_no, sender_id, message):
    if len(mobile_no) == 9:
        mobile_number = "260" + mobile_no
    elif len(mobile_no) == 10:
        mobile_number = "26" + mobile_no
    else:
        mobile_number = mobile_no

    # Set up the API endpoint
    api_url = f"https://bulksms.zamtel.co.zm/api/v2.1/action/send/api_key/{api_key}/contacts/{mobile_number}/senderId/{sender_id}/message/{message}"

    try:
        # Make the POST request using the requests library
        response = requests.post(api_url)

        # Check if the request was successful (HTTP status code 200)
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "SMS sent successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to send SMS"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# FUNCTION TO REGISTER PAYMENT ON SAMPAY API FORM MOBILE PAYMENTS
def register_mobile_payment(
    request_id,
    order_id,
    order_details,
    payment_method,
    amount,
    phone,
    email,
    service_type,
):
    if len(phone) == 9:
        phone = "0" + phone

    dictionary = {
        "app_key": sam_app_key,
        "auth_key": sam_auth_key,
        "key_type": "business",
        "request_id": request_id,
        "order_id": order_id,
        "order_details": order_details,
        "method": payment_method,
        "amount": amount,
        "currency": sam_currency,
        "chargetype": "cc",
        "account": "+26" + phone,
        "holder_mail": email,
        "service": service_type,
        "etps": "no",
        "tpsa": "null",
    }
    jsonString = json.dumps(dictionary, indent=4)

    url = "https://samafricaonline.com/sam_pay/public/ra_register"
    payload = jsonString
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text.encode("utf8")


# FUNCTION TO SEND A PAYMENT REQUEST TO THE CLIENT
def payment_request(request_id, token):
    dictionary = {
        "app_key": sam_app_key,
        "auth_key": sam_auth_key,
        "key_type": "business",
        "request_id": request_id,
        "method": "mobile_money",
        "token": token,
    }
    jsonString = json.dumps(dictionary, indent=4)

    url = "https://samafricaonline.com/sam_pay/public/ra_mmpayrequest"

    payload = jsonString
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text.encode("utf8")


# FUNCTION TO CHECK PAYMENT STATUS
def payment_status(token):
    dictionary = {
        "app_key": sam_app_key,
        "auth_key": sam_auth_key,
        "key_type": "business",
        "token": token,
    }
    jsonString = json.dumps(dictionary, indent=4)

    url = "https://samafricaonline.com/sam_pay/public/ra_check"

    payload = jsonString
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text.encode("utf8")
