from flask import Flask
import os
from model import db, Item

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def update_sale_columns():
    try:
        # Update all items where for_sale is NULL
        db.session.query(Item).filter(Item.for_sale.is_(None)).update(
            {Item.for_sale: False}, synchronize_session=False
        )
        
        # Update all items where sale_price is NULL
        db.session.query(Item).filter(Item.sale_price.is_(None)).update(
            {Item.sale_price: 0}, synchronize_session=False
        )
        
        db.session.commit()
        print("Successfully updated sale columns for all items")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating sale columns: {str(e)}")

if __name__ == "__main__":
    with app.app_context():
        update_sale_columns()