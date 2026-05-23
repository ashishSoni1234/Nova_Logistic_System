from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from database import Base


class SupplyChainData(Base):
    __tablename__ = "supply_chain_data"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(100), nullable=True, index=True)
    order_date = Column(String(50), nullable=True)
    ship_date = Column(String(50), nullable=True)
    customer_name = Column(String(255), nullable=True)
    customer_segment = Column(String(100), nullable=True)
    product_name = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    market = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    order_status = Column(String(50), nullable=True)
    shipping_mode = Column(String(100), nullable=True)
    sales = Column(Float, nullable=True)
    order_quantity = Column(Integer, nullable=True)
    profit = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)
    late_delivery_risk = Column(Integer, nullable=True)
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
