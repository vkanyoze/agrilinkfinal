from ..addons.extensions import db
from datetime import datetime


class Inputs(db.Model):
    """Inputs model"""

    __tablename__ = "farm_inputs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    product_description = db.Column(db.String(150), nullable=False)
    product_weight = db.Column(db.String(150), nullable=False)
    product_quantity = db.Column(db.String(150), nullable=False)
    product_price = db.Column(db.String(150), nullable=False)
    product_image = db.Column(db.String(250), nullable=False)
    create_timestamp = db.Column(db.DateTime, nullable=False)
    update_timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Inputs {self.id}>"
