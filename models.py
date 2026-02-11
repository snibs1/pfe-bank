from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class Simulation(db.Model):
    
    __tablename__ = 'simulations'
    
    
    id = db.Column(db.Integer, primary_key=True)
    
    
    client_name = db.Column(db.String(100), nullable=False)
    cin = db.Column(db.String(20))       
    phone = db.Column(db.String(20))     
    
    
    annual_income = db.Column(db.Float)  
    credit_score = db.Column(db.Integer) 
    loan_amount = db.Column(db.Float)    
    loan_term = db.Column(db.Integer)    
    interest_rate = db.Column(db.Float)  
    
    
    risk_score = db.Column(db.Float, nullable=False) 
    status = db.Column(db.String(20), nullable=False) 
    
    
    date_added = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Client {self.client_name}>'