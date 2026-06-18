# 📊 Smart EDA — Bộ Dữ Liệu Mẫu

Thư mục này chứa tất cả bộ dữ liệu để test và demo pipeline Smart EDA.

```
examples/
├── chinook/          # Cửa hàng nhạc số — 11 bảng, ~15K rows
├── dvd-rental/       # Cho thuê phim (Sakila) — 16 bảng, ~50K rows
├── northwind/        # Thương mại bán sỉ — 8 bảng, ~5K rows
├── olist/            # E-commerce Brazil (schema DBML only, data tải từ Kaggle)
└── sample_datasets/  # Dataset nhỏ để test pipeline (dirty data, multi-table)
    ├── orders_json_dirty/
    ├── school_multi_relations/
    └── students_csv_dirty/
```

---

## Dataset 1: Chinook (`examples/chinook/`)

**Mô tả**: Cửa hàng nhạc số (mô phỏng iTunes)  
**Nguồn**: https://github.com/lerocha/chinook-database  
**Bảng**: 11 bảng, ~15.000 rows  

| Table | Rows | FK |
|-------|------|-----|
| Artist | 275 | — |
| Album | 347 | Artist |
| Track | 3,503 | Album, Genre, MediaType |
| Genre | 25 | — |
| MediaType | 5 | — |
| Playlist | 18 | — |
| PlaylistTrack | 8,715 | Playlist, Track |
| Employee | 8 | Employee (self-ref) |
| Customer | 59 | Employee |
| Invoice | 412 | Customer |
| InvoiceLine | 2,240 | Invoice, Track |

**Schema**: `examples/chinook/chinook-schema.dbml`

**Chạy test**:
```bash
python run_pipeline.py --multi \
  examples/chinook/Artist.csv \
  examples/chinook/Album.csv \
  examples/chinook/Track.csv \
  --schema examples/chinook/chinook-schema.dbml
```

---

## Dataset 2: Northwind (`examples/northwind/`)

**Mô tả**: Công ty thương mại bán sỉ (dữ liệu thực Microsoft, 1994–1996)  
**Nguồn**: https://github.com/uwla/sample_mysql_database  
**Bảng**: 8 bảng, ~5.000 rows  

| Table | Rows | Đặc điểm |
|-------|------|-----------|
| customers | 91 | Có NULL region, fax |
| orders | 830 | Có NULL ShippedDate (chưa giao) |
| products | 77 | Có 8 sản phẩm discontinued |
| employees | 9 | Self-referencing (ReportsTo) |
| suppliers | 29 | — |
| categories | 8 | — |
| shippers | 3 | — |

**Schema**: `examples/northwind/northwind-schema.dbml`

**Chạy test**:
```bash
python run_pipeline.py --multi \
  examples/northwind/customers.csv \
  examples/northwind/orders.csv \
  examples/northwind/products.csv \
  --schema examples/northwind/northwind-schema.dbml
```

---

## Dataset 3: DVD Rental / Sakila (`examples/dvd-rental/`)

**Mô tả**: Chuỗi cho thuê phim (MySQL official sample)  
**Nguồn**: https://github.com/ivanceras/sakila  
**Bảng**: 16 bảng, ~50.000 rows  

| Table | Rows | Đặc điểm |
|-------|------|-----------|
| rental | 16,044 | **`return_date` NULL** khi chưa trả |
| film | 1,000 | `description` text, `rating` categorical |
| inventory | 4,581 | — |
| customer | 599 | `active` boolean |
| film_actor | 5,462 | Many-to-many |

**Schema**: `examples/dvd-rental/sakila-schema.dbml`

---

## Dataset 4: Olist Brazil (`examples/olist/`)

**Mô tả**: E-commerce thực tế từ Brazil — nhiều vấn đề data quality  
**Tải tại**: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce  
**Bảng**: 9 bảng, ~100K rows  
**Vấn đề**: Nhiều NULL, FK violations, text reviews tiếng Bồ Đào Nha

Sau khi tải về, đặt CSV vào `examples/olist/` và chạy:
```bash
python run_pipeline.py --multi examples/olist/*.csv \
  --schema examples/olist/olist-schema.dbml
```

---

## Dataset nhỏ để test pipeline (`examples/sample_datasets/`)

| Dataset | Mô tả |
|---------|-------|
| `students_csv_dirty/` | CSV đơn bảng có dirty data, dùng để test single-table mode |
| `orders_json_dirty/` | JSON có schema mismatch, dùng để test type detection |
| `school_multi_relations/` | 3 bảng có FK inferred (không cần schema DBML) |

```bash
# Test single-table
python run_pipeline.py examples/sample_datasets/students_csv_dirty/students.csv

# Test multi-table không schema
python run_pipeline.py --multi \
  examples/sample_datasets/school_multi_relations/schools.csv \
  examples/sample_datasets/school_multi_relations/classes.csv \
  examples/sample_datasets/school_multi_relations/students.csv
```

---

## Cách chạy nhanh

```bash
# Single-table
python run_pipeline.py examples/chinook/Track.csv

# Multi-table với schema đầy đủ
python run_pipeline.py --multi \
  --schema examples/chinook/chinook-schema.dbml \
  examples/chinook/Album.csv \
  examples/chinook/Artist.csv \
  examples/chinook/Track.csv \
  examples/chinook/Invoice.csv \
  examples/chinook/InvoiceLine.csv
```
