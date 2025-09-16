-- 目标数据库模式示例
-- 这是电商系统的升级版数据库结构，包含了一些变更

-- 用户表 (添加了新字段)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    phone VARCHAR(20),  -- 新增字段
    date_of_birth DATE,  -- 新增字段
    is_active BOOLEAN DEFAULT true,  -- 新增字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 商品分类表 (重命名了字段)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,  -- 从 name 重命名为 category_name
    description TEXT,
    parent_id INTEGER REFERENCES categories(id),
    is_active BOOLEAN DEFAULT true,  -- 新增字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 商品表 (修改了字段类型和添加新字段)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,  -- 长度从 200 增加到 255
    description TEXT,
    price DECIMAL(12, 2) NOT NULL,  -- 精度从 (10,2) 增加到 (12,2)
    stock_quantity INTEGER DEFAULT 0,
    category_id INTEGER REFERENCES categories(id),
    sku VARCHAR(50) UNIQUE,
    weight DECIMAL(8, 3),  -- 新增字段
    dimensions VARCHAR(50),  -- 新增字段
    is_digital BOOLEAN DEFAULT false,  -- 新增字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 订单表 (添加了新字段)
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total_amount DECIMAL(12, 2) NOT NULL,  -- 精度增加
    shipping_cost DECIMAL(8, 2) DEFAULT 0,  -- 新增字段
    tax_amount DECIMAL(8, 2) DEFAULT 0,  -- 新增字段
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,  -- 新增字段
    billing_address TEXT,  -- 新增字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 订单项表 (字段类型变更)
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,  -- 精度增加
    total_price DECIMAL(12, 2) NOT NULL,  -- 精度增加
    discount_amount DECIMAL(8, 2) DEFAULT 0  -- 新增字段
);

-- 购物车表被重命名为 cart_items
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 新增字段
);

-- 新增的表：用户地址表
CREATE TABLE user_addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    address_type VARCHAR(20) NOT NULL,  -- 'shipping' 或 'billing'
    street_address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50) NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 新增的表：商品评论表
CREATE TABLE product_reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    user_id INTEGER REFERENCES users(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200),
    comment TEXT,
    is_verified_purchase BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引 (一些新增，一些删除)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);  -- 新增索引
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_weight ON products(weight);  -- 新增索引
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_cart_items_user ON cart_items(user_id);  -- 对应重命名的表
CREATE INDEX idx_user_addresses_user ON user_addresses(user_id);  -- 新增索引
CREATE INDEX idx_product_reviews_product ON product_reviews(product_id);  -- 新增索引
CREATE INDEX idx_product_reviews_user ON product_reviews(user_id);  -- 新增索引

-- 注意：shopping_cart 表的索引 idx_shopping_cart_user 被删除了，因为表被重命名