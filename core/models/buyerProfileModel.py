from ..addons.extensions import db
from datetime import datetime


class BuyerProfile(db.Model):
    """Buyer Profile model"""

    __tablename__ = "buyer_profile"

    buyer_id = db.Column(db.Integer, primary_key=True)
    buyer_address = db.Column(db.String(150), nullable=False)
    buyer_image = db.Column(db.String(150), nullable=False)
    buyer_latitude = db.Column(db.String(150), nullable=False)
    buyer_longitude = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(15), nullable=False)
    create_timestamp = db.Column(db.DateTime, nullable=False)
    update_timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<BuyerProfile {self.farm_id}>"
