SET NAMES utf8mb4;
-- 企业后台管理系统 数据库初始化脚本（MySQL 8.0）
CREATE DATABASE IF NOT EXISTS admin_panel CHARACTER SET utf8mb4;
USE admin_panel;

-- 用户表
CREATE TABLE IF NOT EXISTS sys_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  phone VARCHAR(20) DEFAULT '',
  status TINYINT DEFAULT 1,
  is_deleted TINYINT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 角色表
CREATE TABLE IF NOT EXISTS sys_role (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) UNIQUE NOT NULL,
  code VARCHAR(64) DEFAULT '',
  `desc` VARCHAR(255) DEFAULT '',
  status TINYINT DEFAULT 1,
  is_deleted TINYINT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 用户角色中间表
CREATE TABLE IF NOT EXISTS sys_user_role (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  KEY idx_user (user_id),
  KEY idx_role (role_id)
);

-- 菜单表（M目录 / C页面 / F按钮）
CREATE TABLE IF NOT EXISTS sys_menu (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parent_id BIGINT DEFAULT 0,
  name VARCHAR(64) NOT NULL,
  menu_type VARCHAR(1) DEFAULT 'C',
  path VARCHAR(128) DEFAULT '',
  component VARCHAR(128) DEFAULT '',
  perms VARCHAR(128) DEFAULT '',
  icon VARCHAR(64) DEFAULT '',
  sort INT DEFAULT 0,
  visible TINYINT DEFAULT 1,
  is_deleted TINYINT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 角色菜单中间表
CREATE TABLE IF NOT EXISTS sys_role_menu (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  role_id BIGINT NOT NULL,
  menu_id BIGINT NOT NULL,
  KEY idx_role (role_id)
);

-- 字典类型表
CREATE TABLE IF NOT EXISTS sys_dict_type (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dict_type VARCHAR(64) UNIQUE NOT NULL,
  name VARCHAR(64) NOT NULL,
  status TINYINT DEFAULT 1,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 字典项表
CREATE TABLE IF NOT EXISTS sys_dict_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dict_type VARCHAR(64) NOT NULL,
  label VARCHAR(64) NOT NULL,
  value VARCHAR(64) NOT NULL,
  sort INT DEFAULT 0,
  status TINYINT DEFAULT 1,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_type (dict_type)
);

-- 操作日志表（只读）
CREATE TABLE IF NOT EXISTS sys_oper_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NULL,
  username VARCHAR(64) DEFAULT '',
  module VARCHAR(64) DEFAULT '',
  action VARCHAR(32) DEFAULT '',
  method VARCHAR(8) DEFAULT '',
  path VARCHAR(255) DEFAULT '',
  ip VARCHAR(64) DEFAULT '',
  params TEXT,
  result VARCHAR(16) DEFAULT '成功',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_created (created_at)
);

-- 业务数据表（扩展演示）
CREATE TABLE IF NOT EXISTS biz_data (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  category VARCHAR(64) DEFAULT '',
  price INT DEFAULT 0,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 文件表
CREATE TABLE IF NOT EXISTS sys_file (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  filename VARCHAR(255) NOT NULL,
  filepath VARCHAR(512) NOT NULL,
  size BIGINT DEFAULT 0,
  uploader VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============ 种子数据 ============
INSERT IGNORE INTO sys_role(id, name, code, `desc`) VALUES
(1, 'super_admin', 'SUPER_ADMIN', '超级管理员'),
(2, 'admin', 'ADMIN', '普通管理员'),
(3, 'operator', 'OPERATOR', '普通操作员');

INSERT IGNORE INTO sys_menu(id, parent_id, name, menu_type, path, icon, sort, perms) VALUES
(1, 0, '用户管理', 'C', '/users', 'User', 1, 'system:user:list'),
(2, 0, '角色管理', 'C', '/roles', 'Avatar', 2, 'system:role:list'),
(3, 0, '菜单管理', 'C', '/menus', 'Menu', 3, 'system:menu:list'),
(4, 0, '数据字典', 'C', '/dicts', 'Collection', 4, 'system:dict:list'),
(5, 0, '操作日志', 'C', '/logs', 'Document', 5, 'system:log:list'),
(6, 0, '个人中心', 'C', '/profile', 'UserFilled', 6, 'profile:view'),
(7, 0, '业务数据', 'C', '/biz', 'Goods', 7, 'biz:list'),
(8, 0, '文件管理', 'C', '/files', 'Folder', 8, 'file:list'),
(11, 1, '新增用户', 'F', '', '', 1, 'system:user:add'),
(12, 1, '编辑用户', 'F', '', '', 2, 'system:user:edit'),
(13, 1, '删除用户', 'F', '', '', 3, 'system:user:remove'),
(14, 1, '重置密码', 'F', '', '', 4, 'system:user:reset'),
(21, 2, '新增角色', 'F', '', '', 1, 'system:role:add'),
(22, 2, '编辑角色', 'F', '', '', 2, 'system:role:edit'),
(23, 2, '删除角色', 'F', '', '', 3, 'system:role:remove'),
(24, 2, '分配权限', 'F', '', '', 4, 'system:role:assign'),
(31, 3, '新增菜单', 'F', '', '', 1, 'system:menu:add'),
(32, 3, '编辑菜单', 'F', '', '', 2, 'system:menu:edit'),
(33, 3, '删除菜单', 'F', '', '', 3, 'system:menu:remove'),
(41, 4, '新增字典', 'F', '', '', 1, 'system:dict:add'),
(42, 4, '编辑字典', 'F', '', '', 2, 'system:dict:edit'),
(43, 4, '删除字典', 'F', '', '', 3, 'system:dict:remove');

-- admin 角色拥有全部菜单
INSERT IGNORE INTO sys_role_menu(role_id, menu_id) SELECT 2, id FROM sys_menu;

-- admin / 123456 （bcrypt）
INSERT IGNORE INTO sys_user(id, username, password_hash, nickname, phone, status) VALUES
(1, 'admin', '$2b$12$uU9BRrhB.cf/TJrON2GiHuLicPQx8vNxzFdmpRMnbGLlbU/r3C5ce', '超级管理员', '13800000000', 1);
INSERT IGNORE INTO sys_user_role(user_id, role_id) VALUES (1, 1);

INSERT IGNORE INTO sys_dict_type(dict_type, name, remark) VALUES
('user_status', '用户状态', '系统内置'),
('menu_type', '菜单类型', '系统内置'),
('yes_no', '是否', '系统内置');
INSERT IGNORE INTO sys_dict_item(dict_type, label, value, sort) VALUES
('user_status', '启用', '1', 1), ('user_status', '禁用', '0', 2),
('menu_type', '目录', 'M', 1), ('menu_type', '页面', 'C', 2), ('menu_type', '按钮', 'F', 3),
('yes_no', '是', '1', 1), ('yes_no', '否', '0', 2);
