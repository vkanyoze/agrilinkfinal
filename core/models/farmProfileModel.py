from ..addons.extensions import db
from datetime import datetime


class FarmProfile(db.Model):
    """Farm Profile model"""

    __tablename__ = "farm_profile"

    farm_id = db.Column(db.Integer, primary_key=True)
    farm_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(150), nullable=False)
    farm_address = db.Column(db.String(150), nullable=False)
    farm_logo = db.Column(db.String(150), nullable=False)
    farm_latitude = db.Column(db.String(150), nullable=False)
    farm_longitude = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(15), nullable=False)
    create_timestamp = db.Column(db.DateTime, nullable=False)
    update_timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<FarmProfile {self.farm_id}>"
