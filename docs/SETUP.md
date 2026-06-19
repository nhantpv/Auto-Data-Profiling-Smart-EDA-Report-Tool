# Hướng dẫn Cài đặt Môi trường (Setup Guide)

Tài liệu này hướng dẫn chi tiết từng bước để cài đặt môi trường phát triển và chạy hệ thống **Smart EDA**, hỗ trợ mọi nền tảng Windows, macOS, hoặc Linux.

---

## Yêu cầu Hệ thống tối thiểu

| Thành phần | Phiên bản yêu cầu | Ghi chú |
|-----------|------------------|---------|
| Python | **>= 3.11** | Bắt buộc. Dự án sử dụng cú pháp type hints mới của Python 3.11. |
| pip | 23+ | Cần thiết để giải quyết Dependency hiện đại. |
| Git | Bất kỳ | Để tải source code về máy. |
| RAM | Tối thiểu 4 GB | Nếu phân tích tập dữ liệu lớn hàng triệu dòng, khuyến nghị 8GB+. (Dù đã có cơ chế Sampling nhưng Pandas vẫn cần nhiều bộ nhớ lúc đọc). |
| Ổ đĩa | 2 GB trống | Dành cho Virtual Environment và các thư viện khoa học dữ liệu. |

---

## Bước 1: Tải mã nguồn (Clone Repository)

Mở Terminal (hoặc Command Prompt/PowerShell) và chạy:

```bash
git clone <repo-url>
cd Auto-Data-Profiling-Smart-EDA-Report-Tool
```

---

## Bước 2: Thiết lập Không gian Ảo (Virtual Environment)

Luôn sử dụng Virtual Environment (Môi trường ảo) để tránh xung đột thư viện với các dự án Python khác trên máy của bạn.

### Trên Linux / macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Trên Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Trên Windows (Command Prompt)

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

> **Dấu hiệu thành công:** Khi bạn thấy chữ `(.venv)` xuất hiện ở đầu dòng lệnh Terminal. Nếu Windows báo lỗi "Execution of scripts is disabled", hãy chạy PowerShell với quyền Admin và gõ lệnh: `Set-ExecutionPolicy Unrestricted -Force`.

---

## Bước 3: Cài đặt Thư viện (Dependencies)

Source code sử dụng cơ chế `pyproject.toml` hiện đại thay cho `requirements.txt`.

Chạy lệnh sau để cài đặt toàn bộ hệ thống ở chế độ **Editable Mode** (Mọi thay đổi code của bạn sẽ có tác dụng ngay lập tức mà không cần cài lại):

```bash
pip install -e .
```

*Nếu bạn muốn chạy test, hãy cài đặt thêm pytest độc lập:*
```bash
pip install pytest httpx
```

### Danh sách các Thư viện Cốt lõi (`pyproject.toml`)

| Thư viện | Vai trò |
|---------|---------|
| `pandas >= 2.0` | Động cơ xử lý dữ liệu chính (DataFrame Engine). |
| `pydantic >= 2.0` | Validator và định nghĩa cấu trúc JSON (Layer 3 Ontology). |
| `ydata-profiling >= 4.0` | Dùng để quét số liệu thống kê tĩnh (Profiling Layer 1). |
| `pyod >= 1.0` | Động cơ dò quét bất thường (Ensemble Anomaly Engine L2a). |
| `pydbml >= 1.0` & `simple-ddl-parser` | Parse cấu trúc file Lược đồ quan hệ (DBML & SQL Schema Engine L2b). |
| `pyampute >= 0.0.3` | Hỗ trợ phân tích cơ chế dữ liệu Rỗng (Missingness L2.5). |
| `matplotlib` & `seaborn` | Bộ đôi thư viện sinh biểu đồ trực quan (Visualizer Layer 3.5). |
| `fastapi` & `uvicorn` | Dựng Web API Server (Layer 5). |
| `openpyxl` & `pyarrow` | Động cơ đọc định dạng Excel và Parquet. |

---

## Bước 4: Thiết lập Biến Môi trường (Environment Variables)

Hệ thống cung cấp một file `.env.example`. Hãy nhân bản nó ra thành `.env`:

### Linux / macOS
```bash
cp .env.example .env
```

### Windows
```cmd
copy .env.example .env
```

Mở file `.env` lên và cấu hình theo nhu cầu:

```env
# Chế độ khởi chạy LLM.
# Nếu bạn không có tài khoản OpenAI API, giữ nguyên là 'deterministic'.
SMART_EDA_L4_PROVIDER=deterministic

# API Key cho tính năng Agent viết báo cáo (Chỉ điền nếu có)
OPENAI_API_KEY=sk-...

# Tối đa dung lượng file upload qua giao diện Web
SMART_EDA_MAX_UPLOAD_MB=100
```

> **Bảo mật:** Không bao giờ đưa file `.env` lên Github.

---

## Bước 5: Kiểm tra cài đặt

Sau khi cài xong, hãy chạy bộ Unit Test của hệ thống để đảm bảo mọi thứ trơn tru:

```bash
pytest tests/ -q
```

---

## Khởi động Ứng dụng

Bạn có 2 cách để khởi chạy Smart EDA:

### 1. Chạy thông qua Giao diện Web (Khuyến nghị)

Giao diện Web cung cấp luồng chạy dễ nhìn, có Real-time Progress Bar:

```bash
uvicorn src.webapp.app:app --host 127.0.0.1 --port 8000 --reload
# Hoặc chạy script có sẵn
python run_ui.py
```
Sau đó mở trình duyệt tại: **http://127.0.0.1:8000**

### 2. Chạy thông qua Command Line Interface (Dành cho Developer/Data Engineer)

Thích hợp khi bạn muốn tự động hóa luồng phân tích (Automation Script):

```bash
python run_pipeline.py duong_dan/toi/file_data.csv thu_muc_output
```

Tất cả báo cáo (HTML, JSON, Hình ảnh) sẽ được xuất thẳng ra `thu_muc_output`.

---

## Gỡ lỗi cài đặt (Troubleshooting)

### 1. `ModuleNotFoundError: No module named 'src'` hoặc `smart_eda`
**Nguyên nhân:** Bạn chưa cài đặt package hoặc quên cờ `-e`.
**Cách sửa:** Chạy lại `pip install -e .` ở thư mục gốc của project.

### 2. Báo lỗi khi cài đặt `ydata-profiling` trên Windows
**Nguyên nhân:** Thiếu Build Tools của C++.
**Cách sửa:** Tải Microsoft C++ Build Tools và cài đặt gói "Desktop development with C++", sau đó chạy lệnh cài pip lại.

### 3. Không tìm thấy lệnh `pytest` hoặc `uvicorn`
**Nguyên nhân:** Virtual Environment của bạn chưa được Activate.
**Cách sửa:** Hãy gõ lại lệnh `.venv\Scripts\activate` (Windows) hoặc `source .venv/bin/activate` (Mac/Linux).
