# 仓库管理系统 (Warehouse Tool)

一个基于 FastAPI 的轻量级仓库管理系统，支持库存管理、产品图片管理和扫码操作。采用分层架构设计，前后端分离，提供 Web UI 和 RESTful API。

## 功能特性

### 核心功能

- **库存管理**：入库、出库、库存查询
- **产品管理**：产品详情查看（库存 + 图片聚合）
- **图片管理**：上传、删除、设置主图
- **扫码操作**：支持 JSON 格式的扫码入库/出库
- **批量处理**：支持批量扫码操作
- **移动端适配**：响应式 Web UI，支持手机浏览器

### 界面预览

系统提供移动端友好的 Web 界面，包含以下页面：

- **首页**：状态概览、快捷操作、最近活动
- **搜索**：产品搜索、扫码加载产品
- **操作**：入库/出库/扫码/批量 四种操作模式
- **图片**：产品图片上传和管理
- **设置**：系统状态、本地缓存管理

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 数据库 | SQLite |
| 文件存储 | 本地文件系统 |
| 前端 | 原生 HTML + CSS + JavaScript |
| 扫码 | Web Barcode Detector API |

## 项目结构

```
warehouse_pj/
├── app.py                  # FastAPI 主应用
├── inventory.py            # 库存核心逻辑（内存实现）
├── sqlite_inventory.py     # 库存 SQLite 持久化
├── image_store.py          # 图片文件存储
├── sqlite_image_store.py   # 图片元数据管理
├── product_ids.py          # 产品 ID 规范化
├── static/                 # 前端静态文件
│   ├── index.html          # 主页面
│   ├── app.js              # 前端逻辑
│   └── styles.css          # 样式
├── tests/                  # 测试目录
│   ├── test_app.py
│   ├── test_inventory.py
│   └── test_sqlite_inventory.py
├── requirements.txt        # 依赖
└── warehouse.db            # SQLite 数据库
```

## API 接口

### 健康检查

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 服务健康状态 |

### 库存管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/items` | GET | 获取库存列表，支持 `?query=` 搜索 |
| `/items/{product_id}` | GET | 获取单个产品库存 |
| `/items/add` | POST | 入库 |
| `/items/remove` | POST | 出库 |

**入库/出库请求体：**
```json
{
  "product_id": "SKU-001",
  "quantity": 10
}
```

### 产品详情

| 接口 | 方法 | 说明 |
|------|------|------|
| `/products/{product_id}` | GET | 获取产品详情（库存 + 图片） |

### 扫码操作

| 接口 | 方法 | 说明 |
|------|------|------|
| `/scan` | POST | 扫码入库/出库 |

**请求体：**
```json
{
  "action": "add",
  "product_id": "SKU-001",
  "quantity": 5,
  "source": "scanner",
  "raw_code": "{\"product_id\":\"SKU-001\",\"quantity\":5}"
}
```

### 图片管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/images` | POST | 上传图片（form-data: product_id, image） |
| `/images/{product_id}` | GET | 获取产品图片列表 |
| `/images/{product_id}/primary` | POST | 设置主图（请求体: `{ "image_id": 1 }`） |
| `/images/{product_id}/{image_id}` | DELETE | 删除图片 |

## 快速开始

### 环境要求

- Python 3.10+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
python -m unittest discover -s tests -v
```

**当前测试覆盖：33 个测试用例**

### 启动服务

```bash
python -m uvicorn app:app --reload
```

或指定端口：

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8001
```

### 访问应用

- Web 界面：http://localhost:8001/
- API 文档：http://localhost:8001/docs

## 使用指南

### 基本流程

1. **添加入库**：在"操作"页面选择"入库"模式，输入产品 ID 和数量
2. **查看库存**：在"搜索"页面查看产品列表和库存
3. **上传图片**：在"图片"页面上传产品图片
4. **扫码操作**：在"操作"页面选择"扫码"模式，使用摄像头扫描二维码

### 扫码格式

系统支持以下 JSON 格式的扫码内容：

```json
{
  "action": "add",
  "product_id": "SKU-001",
  "quantity": 5
}
```

或出库：

```json
{
  "action": "remove",
  "product_id": "SKU-001",
  "quantity": 2
}
```

### 批量操作

在"操作"页面选择"批量"模式，可以粘贴多行 JSON：

```json
[{"action":"add","product_id":"SKU-001","quantity":5},{"action":"remove","product_id":"SKU-002","quantity":2}]
```

或每行一个对象：

```json
{"action":"add","product_id":"SKU-001","quantity":5}
{"action":"remove","product_id":"SKU-002","quantity":2}
```

## 设计特点

- **分层架构**：核心业务逻辑与存储、接口层分离
- **大小写不敏感**：产品 ID 统一转换为大写处理
- **自动主图**：第一个上传的图片自动设为主图
- **主图继承**：删除主图时，最早上传的图片自动提升为主图
- **移动端优先**：UI 设计针对手机浏览器优化

## 待办事项

- [ ] 添加产品删除功能
- [ ] 添加库存导入/导出
- [ ] 添加图片缩略图预览
- [ ] 添加前端自动化测试
- [ ] 添加配置管理（数据库路径、图片目录等）
- [ ] 添加 AI 辅助产品识别
