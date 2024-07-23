from ..addons.extensions import db
from datetime import datetime


class CompanyProfile(db.Model):
    """Company Profile Model"""

    __tablename__ = "company_profile"

    company_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(150), nullable=False)
    company_address = db.Column(db.String(150), nullable=False)
    company_logo = db.Column(db.String(150), nullable=False)
    company_latitude = db.Column(db.String(50), nullable=False)
    company_longitude = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(15), nullable=False)
    create_timestamp = db.Column(db.DateTime, nullable=False)
    update_timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<CompanyProfile {self.id}>"
