from ..addons.extensions import db


class Order(db.Model):
    __tablename__ = "orders_table"

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(50), nullable=False)
    farmerid = db.Column(db.String(50), nullable=False)
    orderid = db.Column(db.String(150), nullable=False)
    productid = db.Column(db.String(150), nullable=False)
    productname = db.Column(db.String(150), nullable=False)
    initialprice = db.Column(db.String(150), nullable=False)
    totalprice = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.String(100), nullable=False)
    unittag = db.Column(db.String(150), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Order: {self.id}>"
