from ..addons.extensions import db
from datetime import datetime


class Farmers(db.Model):
    """Farmers model"""

    __tablename__ = "farmers_table"

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), index=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    mobilenum = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(50), nullable=False)
    is_email_verified = db.Column(db.String(50), nullable=False)
    is_mobile_verified = db.Column(db.String(50), nullable=False)
    email_verification_code = db.Column(db.String(50))
    mobile_verification_code = db.Column(db.String(50))
    reset_code = db.Column(db.String(50))
    datecreated = db.Column(db.DateTime, nullable=False)
    lastmodified = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Farmers {self.id}>"
