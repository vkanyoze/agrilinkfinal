from ..addons.extensions import db
from datetime import datetime


class AdminUsers(db.Model):
    """Admin Users model"""

    __tablename__ = "admin_table"

    admin_id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), index=True, nullable=False)
    phonenum = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(200))
    reset_code = db.Column(db.String(50))
    status = db.Column(db.String(50))
    create_timestamp = db.Column(db.DateTime, nullable=False)
    update_timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<SystemUsers {self.adminid}>"
