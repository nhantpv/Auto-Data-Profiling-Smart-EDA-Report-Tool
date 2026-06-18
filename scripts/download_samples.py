"""
Download and prepare 3 sample multi-table datasets for Smart EDA testing.
Datasets:
  1. Chinook   - digital media store (11 tables, ~15K rows)
  2. Northwind - wholesale trading  (13 tables, ~5K rows)
  3. DVD Rental - video rental store (15 tables, ~50K rows) — replaces Olist

Run: python download_samples.py
"""

import os
import sqlite3
import csv
import urllib.request
import urllib.error
import zipfile
import io
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXAMPLES_DIR = BASE_DIR / "examples"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def download(url: str, dest: Path, label: str = ""):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  [skip] {dest.name} already exists")
        return
    print(f"  Downloading {label or dest.name} ...", flush=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0 SmartEDA-test-downloader/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  ✓ Saved {dest.name} ({len(data):,} bytes)")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        raise


def write_dbml(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"  ✓ Created {path.name}")


# ─── 1. CHINOOK ───────────────────────────────────────────────────────────────

CHINOOK_SQLITE_URL = (
    "https://github.com/lerocha/chinook-database/raw/master/"
    "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
)

CHINOOK_DBML = """
// Chinook Database — Digital Media Store
// Source: https://github.com/lerocha/chinook-database

Table Artist {
  ArtistId integer [pk, increment]
  Name varchar(120)
}

Table Album {
  AlbumId integer [pk, increment]
  Title varchar(160) [not null]
  ArtistId integer [not null, ref: > Artist.ArtistId]
}

Table MediaType {
  MediaTypeId integer [pk, increment]
  Name varchar(120)
}

Table Genre {
  GenreId integer [pk, increment]
  Name varchar(120)
}

Table Track {
  TrackId integer [pk, increment]
  Name varchar(200) [not null]
  AlbumId integer [ref: > Album.AlbumId]
  MediaTypeId integer [not null, ref: > MediaType.MediaTypeId]
  GenreId integer [ref: > Genre.GenreId]
  Composer varchar(220)
  Milliseconds integer [not null]
  Bytes integer
  UnitPrice decimal(10,2) [not null]
}

Table Playlist {
  PlaylistId integer [pk, increment]
  Name varchar(120)
}

Table PlaylistTrack {
  PlaylistId integer [pk, ref: > Playlist.PlaylistId]
  TrackId integer [pk, ref: > Track.TrackId]

  indexes {
    (PlaylistId, TrackId) [pk]
  }
}

Table Employee {
  EmployeeId integer [pk, increment]
  LastName varchar(20) [not null]
  FirstName varchar(20) [not null]
  Title varchar(30)
  ReportsTo integer [ref: > Employee.EmployeeId]
  BirthDate datetime
  HireDate datetime
  Address varchar(70)
  City varchar(40)
  State varchar(40)
  Country varchar(40)
  PostalCode varchar(10)
  Phone varchar(24)
  Fax varchar(24)
  Email varchar(60)
}

Table Customer {
  CustomerId integer [pk, increment]
  FirstName varchar(40) [not null]
  LastName varchar(20) [not null]
  Company varchar(80)
  Address varchar(70)
  City varchar(40)
  State varchar(40)
  Country varchar(40)
  PostalCode varchar(10)
  Phone varchar(24)
  Fax varchar(24)
  Email varchar(60) [not null]
  SupportRepId integer [ref: > Employee.EmployeeId]
}

Table Invoice {
  InvoiceId integer [pk, increment]
  CustomerId integer [not null, ref: > Customer.CustomerId]
  InvoiceDate datetime [not null]
  BillingAddress varchar(70)
  BillingCity varchar(40)
  BillingState varchar(40)
  BillingCountry varchar(40)
  BillingPostalCode varchar(10)
  Total decimal(10,2) [not null]
}

Table InvoiceLine {
  InvoiceLineId integer [pk, increment]
  InvoiceId integer [not null, ref: > Invoice.InvoiceId]
  TrackId integer [not null, ref: > Track.TrackId]
  UnitPrice decimal(10,2) [not null]
  Quantity integer [not null]
}
"""


def setup_chinook():
    print("\n=== Chinook Database ===")
    out_dir = EXAMPLES_DIR / "chinook"
    out_dir.mkdir(parents=True, exist_ok=True)

    sqlite_path = out_dir / "Chinook_Sqlite.sqlite"
    download(CHINOOK_SQLITE_URL, sqlite_path, "Chinook SQLite")

    print("  Exporting tables to CSV...")
    conn = sqlite3.connect(sqlite_path)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]

    for table in tables:
        csv_path = out_dir / f"{table}.csv"
        if csv_path.exists():
            print(f"  [skip] {table}.csv")
            continue
        rows = conn.execute(f"SELECT * FROM [{table}]").fetchall()
        col_names = [d[0] for d in conn.execute(f"SELECT * FROM [{table}] LIMIT 0").description]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(col_names)
            w.writerows(rows)
        print(f"  ✓ {table}.csv ({len(rows):,} rows)")
    conn.close()

    write_dbml(out_dir / "chinook-schema.dbml", CHINOOK_DBML)
    print(f"  Tables: {', '.join(tables)}")


# ─── 2. NORTHWIND ─────────────────────────────────────────────────────────────

NORTHWIND_BASE = "https://raw.githubusercontent.com/uwla/sample_mysql_database/master/csv/"
NORTHWIND_TABLES = [
    "categories", "customers", "employees", "employee_territories",
    "order_details", "orders", "products", "regions",
    "shippers", "suppliers", "territories",
]

NORTHWIND_DBML = """
// Northwind Database — Wholesale Trading Company
// Source: https://github.com/uwla/sample_mysql_database

Table categories {
  CategoryID integer [pk]
  CategoryName varchar(15) [not null]
  Description text
  Picture blob
}

Table suppliers {
  SupplierID integer [pk]
  CompanyName varchar(40) [not null]
  ContactName varchar(30)
  ContactTitle varchar(30)
  Address varchar(60)
  City varchar(15)
  Region varchar(15)
  PostalCode varchar(10)
  Country varchar(15)
  Phone varchar(24)
  Fax varchar(24)
  HomePage text
}

Table products {
  ProductID integer [pk]
  ProductName varchar(40) [not null]
  SupplierID integer [ref: > suppliers.SupplierID]
  CategoryID integer [ref: > categories.CategoryID]
  QuantityPerUnit varchar(20)
  UnitPrice decimal(10,4)
  UnitsInStock smallint
  UnitsOnOrder smallint
  ReorderLevel smallint
  Discontinued integer [not null]
}

Table regions {
  RegionID integer [pk]
  RegionDescription varchar(50) [not null]
}

Table territories {
  TerritoryID varchar(20) [pk]
  TerritoryDescription varchar(50) [not null]
  RegionID integer [not null, ref: > regions.RegionID]
}

Table employees {
  EmployeeID integer [pk]
  LastName varchar(20) [not null]
  FirstName varchar(10) [not null]
  Title varchar(30)
  TitleOfCourtesy varchar(25)
  BirthDate datetime
  HireDate datetime
  Address varchar(60)
  City varchar(15)
  Region varchar(15)
  PostalCode varchar(10)
  Country varchar(15)
  HomePhone varchar(24)
  Extension varchar(4)
  Photo blob
  Notes text
  ReportsTo integer [ref: > employees.EmployeeID]
  PhotoPath varchar(255)
}

Table employee_territories {
  EmployeeID integer [pk, ref: > employees.EmployeeID]
  TerritoryID varchar(20) [pk, ref: > territories.TerritoryID]

  indexes {
    (EmployeeID, TerritoryID) [pk]
  }
}

Table shippers {
  ShipperID integer [pk]
  CompanyName varchar(40) [not null]
  Phone varchar(24)
}

Table customers {
  CustomerID varchar(5) [pk]
  CompanyName varchar(40) [not null]
  ContactName varchar(30)
  ContactTitle varchar(30)
  Address varchar(60)
  City varchar(15)
  Region varchar(15)
  PostalCode varchar(10)
  Country varchar(15)
  Phone varchar(24)
  Fax varchar(24)
}

Table orders {
  OrderID integer [pk]
  CustomerID varchar(5) [ref: > customers.CustomerID]
  EmployeeID integer [ref: > employees.EmployeeID]
  OrderDate datetime
  RequiredDate datetime
  ShippedDate datetime
  ShipVia integer [ref: > shippers.ShipperID]
  Freight decimal(10,4)
  ShipName varchar(40)
  ShipAddress varchar(60)
  ShipCity varchar(15)
  ShipRegion varchar(15)
  ShipPostalCode varchar(10)
  ShipCountry varchar(15)
}

Table order_details {
  OrderID integer [pk, ref: > orders.OrderID]
  ProductID integer [pk, ref: > products.ProductID]
  UnitPrice decimal(10,4) [not null]
  Quantity smallint [not null]
  Discount real [not null]

  indexes {
    (OrderID, ProductID) [pk]
  }
}
"""


def setup_northwind():
    print("\n=== Northwind Database ===")
    out_dir = EXAMPLES_DIR / "northwind"
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for table in NORTHWIND_TABLES:
        csv_path = out_dir / f"{table}.csv"
        url = NORTHWIND_BASE + table + ".csv"
        try:
            download(url, csv_path, table)
        except Exception:
            failed.append(table)

    if failed:
        print(f"  ⚠ Failed tables: {failed}")

    write_dbml(out_dir / "northwind-schema.dbml", NORTHWIND_DBML)


# ─── 3. DVD RENTAL (thay thế Olist) ───────────────────────────────────────────

# Sử dụng Sakila/DVD Rental từ MySQL sample DB - có CSV sẵn trên GitHub
DVD_BASE = "https://raw.githubusercontent.com/ivanceras/sakila/master/csv-sakila-db/"
DVD_TABLES = [
    "actor", "address", "category", "city", "country", "customer",
    "film", "film_actor", "film_category", "film_text",
    "inventory", "language", "payment", "rental", "staff", "store",
]

DVD_DBML = """
// Sakila/DVD Rental Database — Video Rental Store
// Source: https://github.com/ivanceras/sakila
// 16 tables, ~50K rows, nhiều NULL values thực tế (rental dates, return dates)

Table country {
  country_id smallint [pk, increment]
  country varchar(50) [not null]
  last_update timestamp [not null]
}

Table city {
  city_id smallint [pk, increment]
  city varchar(50) [not null]
  country_id smallint [not null, ref: > country.country_id]
  last_update timestamp [not null]
}

Table address {
  address_id smallint [pk, increment]
  address varchar(50) [not null]
  address2 varchar(50)
  district varchar(20) [not null]
  city_id smallint [not null, ref: > city.city_id]
  postal_code varchar(10)
  phone varchar(20) [not null]
  last_update timestamp [not null]
}

Table language {
  language_id tinyint [pk, increment]
  name char(20) [not null]
  last_update timestamp [not null]
}

Table category {
  category_id tinyint [pk, increment]
  name varchar(25) [not null]
  last_update timestamp [not null]
}

Table actor {
  actor_id smallint [pk, increment]
  first_name varchar(45) [not null]
  last_name varchar(45) [not null]
  last_update timestamp [not null]
}

Table film {
  film_id smallint [pk, increment]
  title varchar(255) [not null]
  description text
  release_year year
  language_id tinyint [not null, ref: > language.language_id]
  original_language_id tinyint [ref: > language.language_id]
  rental_duration tinyint [not null]
  rental_rate decimal(4,2) [not null]
  length smallint
  replacement_cost decimal(5,2) [not null]
  rating enum
  special_features set
  last_update timestamp [not null]
}

Table film_actor {
  actor_id smallint [pk, ref: > actor.actor_id]
  film_id smallint [pk, ref: > film.film_id]
  last_update timestamp [not null]

  indexes {
    (actor_id, film_id) [pk]
  }
}

Table film_category {
  film_id smallint [pk, ref: > film.film_id]
  category_id tinyint [pk, ref: > category.category_id]
  last_update timestamp [not null]

  indexes {
    (film_id, category_id) [pk]
  }
}

Table film_text {
  film_id smallint [pk]
  title varchar(255) [not null]
  description text
}

Table store {
  store_id tinyint [pk, increment]
  manager_staff_id tinyint [not null]
  address_id smallint [not null, ref: > address.address_id]
  last_update timestamp [not null]
}

Table staff {
  staff_id tinyint [pk, increment]
  first_name varchar(45) [not null]
  last_name varchar(45) [not null]
  address_id smallint [not null, ref: > address.address_id]
  picture blob
  email varchar(50)
  store_id tinyint [not null, ref: > store.store_id]
  active boolean [not null]
  username varchar(16) [not null]
  password varchar(40)
  last_update timestamp [not null]
}

Table customer {
  customer_id smallint [pk, increment]
  store_id tinyint [not null, ref: > store.store_id]
  first_name varchar(45) [not null]
  last_name varchar(45) [not null]
  email varchar(50)
  address_id smallint [not null, ref: > address.address_id]
  active boolean [not null]
  create_date datetime [not null]
  last_update timestamp
}

Table inventory {
  inventory_id mediumint [pk, increment]
  film_id smallint [not null, ref: > film.film_id]
  store_id tinyint [not null, ref: > store.store_id]
  last_update timestamp [not null]
}

Table rental {
  rental_id integer [pk, increment]
  rental_date datetime [not null]
  inventory_id mediumint [not null, ref: > inventory.inventory_id]
  customer_id smallint [not null, ref: > customer.customer_id]
  return_date datetime
  staff_id tinyint [not null, ref: > staff.staff_id]
  last_update timestamp [not null]
}

Table payment {
  payment_id smallint [pk, increment]
  customer_id smallint [not null, ref: > customer.customer_id]
  staff_id tinyint [not null, ref: > staff.staff_id]
  rental_id integer [ref: > rental.rental_id]
  amount decimal(5,2) [not null]
  payment_date datetime [not null]
  last_update timestamp
}
"""


def setup_dvd_rental():
    print("\n=== Sakila/DVD Rental Database ===")
    out_dir = EXAMPLES_DIR / "dvd-rental"
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for table in DVD_TABLES:
        csv_path = out_dir / f"{table}.csv"
        url = DVD_BASE + table + ".csv"
        try:
            download(url, csv_path, table)
        except Exception:
            failed.append(table)

    if failed:
        print(f"  ⚠ Failed tables: {failed}")

    write_dbml(out_dir / "sakila-schema.dbml", DVD_DBML)


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 55)
    print("DONE — Dataset Summary")
    print("=" * 55)
    datasets = {
        "chinook":    "Chinook (digital music store)",
        "northwind":  "Northwind (wholesale trading)",
        "dvd-rental": "Sakila/DVD Rental (video store)",
    }
    for folder, name in datasets.items():
        d = EXAMPLES_DIR / folder
        if not d.exists():
            continue
        csvs = list(d.glob("*.csv"))
        dbml = list(d.glob("*.dbml"))
        print(f"\n  {name}")
        print(f"    📁 {d}")
        print(f"    CSV tables : {len(csvs)} ({', '.join(f.stem for f in csvs[:5])}{'...' if len(csvs) > 5 else ''})")
        print(f"    DBML schema: {'✅ ' + dbml[0].name if dbml else '❌ missing'}")


if __name__ == "__main__":
    print("Smart EDA — Test Dataset Downloader")
    print("=" * 55)
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    setup_chinook()
    setup_northwind()
    setup_dvd_rental()
    print_summary()
