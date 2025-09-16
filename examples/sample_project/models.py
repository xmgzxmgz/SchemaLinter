"""
示例 Python 项目 - SQLAlchemy 模型定义

这个文件展示了典型的 SQLAlchemy 模型定义，
SchemaLinter 将分析这些模型与数据库模式的关系。
"""

from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    orders = relationship("Order", back_populates="user")
    cart_items = relationship("ShoppingCart", back_populates="user")


class Category(Base):
    """商品分类模型"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # 这个字段在新模式中被重命名了
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    products = relationship("Product", back_populates="category")
    parent = relationship("Category", remote_side=[id])


class Product(Base):
    """商品模型"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  # 长度在新模式中增加了
    description = Column(Text)
    price = Column(DECIMAL(10, 2), nullable=False)  # 精度在新模式中增加了
    stock_quantity = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey('categories.id'))
    sku = Column(String(50), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("ShoppingCart", back_populates="product")


class Order(Base):
    """订单模型"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """订单项模型"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    total_price = Column(DECIMAL(10, 2), nullable=False)
    
    # 关系
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class ShoppingCart(Base):
    """购物车模型 - 这个表在新模式中被重命名为 cart_items"""
    __tablename__ = 'shopping_cart'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")