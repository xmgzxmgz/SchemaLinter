"""
示例 Python 项目 - 原生 SQL 查询

这个文件展示了典型的原生 SQL 查询，
SchemaLinter 将分析这些查询中的表名和列名引用。
"""

import sqlite3
from typing import List, Dict, Any


class UserService:
    """用户服务类"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """根据邮箱获取用户信息"""
        query = """
        SELECT id, username, email, first_name, last_name, created_at
        FROM users 
        WHERE email = ?
        """
        cursor = self.db.execute(query, (email,))
        return cursor.fetchone()
    
    def get_user_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有订单"""
        query = """
        SELECT o.id, o.total_amount, o.status, o.created_at,
               COUNT(oi.id) as item_count
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.user_id = ?
        GROUP BY o.id, o.total_amount, o.status, o.created_at
        ORDER BY o.created_at DESC
        """
        cursor = self.db.execute(query, (user_id,))
        return cursor.fetchall()
    
    def update_user_info(self, user_id: int, first_name: str, last_name: str):
        """更新用户信息"""
        query = """
        UPDATE users 
        SET first_name = ?, last_name = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        self.db.execute(query, (first_name, last_name, user_id))
        self.db.commit()


class ProductService:
    """商品服务类"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_products_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """根据分类获取商品列表"""
        query = """
        SELECT p.id, p.name, p.description, p.price, p.stock_quantity, p.sku,
               c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.category_id = ?
        ORDER BY p.name
        """
        cursor = self.db.execute(query, (category_id,))
        return cursor.fetchall()
    
    def search_products(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索商品"""
        query = """
        SELECT p.id, p.name, p.description, p.price, p.stock_quantity,
               c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.name LIKE ? OR p.description LIKE ?
        ORDER BY p.name
        """
        search_term = f"%{keyword}%"
        cursor = self.db.execute(query, (search_term, search_term))
        return cursor.fetchall()
    
    def update_product_price(self, product_id: int, new_price: float):
        """更新商品价格"""
        query = """
        UPDATE products 
        SET price = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        self.db.execute(query, (new_price, product_id))
        self.db.commit()


class OrderService:
    """订单服务类"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create_order(self, user_id: int, items: List[Dict[str, Any]]) -> int:
        """创建新订单"""
        # 创建订单
        order_query = """
        INSERT INTO orders (user_id, total_amount, status, created_at)
        VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
        """
        
        total_amount = sum(item['quantity'] * item['unit_price'] for item in items)
        cursor = self.db.execute(order_query, (user_id, total_amount))
        order_id = cursor.lastrowid
        
        # 添加订单项
        item_query = """
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price)
        VALUES (?, ?, ?, ?, ?)
        """
        
        for item in items:
            total_price = item['quantity'] * item['unit_price']
            self.db.execute(item_query, (
                order_id, 
                item['product_id'], 
                item['quantity'], 
                item['unit_price'], 
                total_price
            ))
        
        self.db.commit()
        return order_id
    
    def get_order_details(self, order_id: int) -> Dict[str, Any]:
        """获取订单详情"""
        order_query = """
        SELECT o.id, o.user_id, o.total_amount, o.status, o.created_at,
               u.username, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = ?
        """
        
        items_query = """
        SELECT oi.id, oi.quantity, oi.unit_price, oi.total_price,
               p.name as product_name, p.sku
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """
        
        order_cursor = self.db.execute(order_query, (order_id,))
        order = order_cursor.fetchone()
        
        items_cursor = self.db.execute(items_query, (order_id,))
        items = items_cursor.fetchall()
        
        return {
            'order': order,
            'items': items
        }


class CartService:
    """购物车服务类"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def add_to_cart(self, user_id: int, product_id: int, quantity: int):
        """添加商品到购物车"""
        # 检查是否已存在
        check_query = """
        SELECT id, quantity FROM shopping_cart 
        WHERE user_id = ? AND product_id = ?
        """
        cursor = self.db.execute(check_query, (user_id, product_id))
        existing = cursor.fetchone()
        
        if existing:
            # 更新数量
            update_query = """
            UPDATE shopping_cart 
            SET quantity = quantity + ?
            WHERE id = ?
            """
            self.db.execute(update_query, (quantity, existing['id']))
        else:
            # 新增记录
            insert_query = """
            INSERT INTO shopping_cart (user_id, product_id, quantity, added_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """
            self.db.execute(insert_query, (user_id, product_id, quantity))
        
        self.db.commit()
    
    def get_cart_items(self, user_id: int) -> List[Dict[str, Any]]:
        """获取购物车商品"""
        query = """
        SELECT sc.id, sc.quantity, sc.added_at,
               p.id as product_id, p.name, p.price, p.stock_quantity
        FROM shopping_cart sc
        JOIN products p ON sc.product_id = p.id
        WHERE sc.user_id = ?
        ORDER BY sc.added_at DESC
        """
        cursor = self.db.execute(query, (user_id,))
        return cursor.fetchall()
    
    def clear_cart(self, user_id: int):
        """清空购物车"""
        query = "DELETE FROM shopping_cart WHERE user_id = ?"
        self.db.execute(query, (user_id,))
        self.db.commit()


class ReportService:
    """报表服务类"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_sales_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """获取销售汇总"""
        query = """
        SELECT 
            COUNT(DISTINCT o.id) as total_orders,
            SUM(o.total_amount) as total_revenue,
            COUNT(DISTINCT o.user_id) as unique_customers,
            AVG(o.total_amount) as avg_order_value
        FROM orders o
        WHERE o.created_at BETWEEN ? AND ?
        AND o.status != 'cancelled'
        """
        cursor = self.db.execute(query, (start_date, end_date))
        return cursor.fetchone()
    
    def get_top_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热销商品"""
        query = """
        SELECT 
            p.id, p.name, p.sku,
            SUM(oi.quantity) as total_sold,
            SUM(oi.total_price) as total_revenue
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'cancelled'
        GROUP BY p.id, p.name, p.sku
        ORDER BY total_sold DESC
        LIMIT ?
        """
        cursor = self.db.execute(query, (limit,))
        return cursor.fetchall()