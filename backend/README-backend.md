# Khớp — Backend matching

Backend tính điểm phù hợp giữa job và freelancer bằng **thuật toán thuần** (không gọi AI).

## Có gì trong này

- `scoring.py` — thuật toán tính điểm (công thức trọng số 40/25/20/15).
- `main.py` — API FastAPI bọc thuật toán thành 2 endpoint.
- `du-lieu-mau.json` — 1 job + 4 freelancer mẫu.
- `requirements.txt` — thư viện cần cài.

## Chạy

Đặt cả 4 file trên vào cùng một thư mục (ví dụ `backend/`), rồi:

```bash
# 1. Cài thư viện (nên tạo virtualenv trước)
pip install -r requirements.txt

# 2. Khởi động server
uvicorn main:app --reload
```

Server mở ở `http://127.0.0.1:8000`.

## Thử

- `http://127.0.0.1:8000/docs` — giao diện test API tự sinh, bấm "Try it out" chạy thử ngay.
- `http://127.0.0.1:8000/api/job` — thông tin job.
- `http://127.0.0.1:8000/api/match` — danh sách freelancer đã xếp hạng + giải thích.

## Ghi chú kiến trúc

- Toàn bộ matching là phép toán trọng số, chạy 0 token — đây là phần chạy nhiều nhất.
- Trọng số 40/25/20/15 khớp đúng công thức đã công bố ở trang chủ.
- Con số % và bảng "vì sao khớp" đều do thuật toán sinh ra, không hardcode.
