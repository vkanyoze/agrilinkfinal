from ..addons.extensions import db
from datetime import datetime


class Payment(db.Model):
    __tablename__ = "payments_table"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), nullable=False, unique=True)
    order_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, nullable=False)
    payment_amount = db.Column(db.String(55), nullable=False)
    currency = db.Column(db.String(155), nullable=False)
    service_fee = db.Column(db.String(100))
    amount_merchant_receive = db.Column(db.String(100))
    payment_method = db.Column(db.String(55), nullable=False)
    payment_type = db.Column(db.String(55), nullable=False)
    response_code = db.Column(db.String(155), nullable=False)
    status = db.Column(db.String(15), nullable=False)
    transaction_referrence = db.Column(db.String(155), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Payment: {self.id}>"
