"""
main.py — API backend cho Khớp.

Bọc hàm rank() trong scoring.py thành một endpoint HTTP để frontend gọi.
Chạy:  uvicorn main:app --reload
Mặc định mở ở http://127.0.0.1:8000  (tài liệu tự sinh ở /docs)
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scoring import rank
from roadmap import build_roadmap

app = FastAPI(title="Khớp — API matching")

# Cho phép frontend (mở bằng localhost cổng khác) gọi API.
# Demo nên để "*"; sản phẩm thật thì giới hạn đúng domain của mình.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nạp dữ liệu mẫu một lần lúc khởi động.
DATA = json.loads(Path("du-lieu-mau.json").read_text(encoding="utf-8"))


@app.get("/api/job")
def get_job():
    """Trả về thông tin job đang tuyển (để trang hiển thị phần tóm tắt)."""
    return DATA["job"]


@app.get("/api/match")
def get_match():
    """
    Chấm tất cả freelancer với job và trả về danh sách đã xếp hạng.
    Đây là phần lõi: gọi thẳng thuật toán trong scoring.py.
    """
    job = DATA["job"]
    ranked = rank(job, DATA["freelancers"])
    return {
        "job_title": job["title"],
        "count": len(ranked),
        "results": ranked,
    }


@app.get("/api/roadmap/{freelancer_id}")
def get_roadmap(freelancer_id: str):
    """
    Trả về lộ trình phát triển cho một freelancer (dựa trên khoảng cách điểm).
    Phần này là thuật toán thuần — 0 token.
    """
    job = DATA["job"]
    fl = next((f for f in DATA["freelancers"] if f["id"] == freelancer_id), None)
    if fl is None:
        return {"error": f"Không tìm thấy freelancer id '{freelancer_id}'"}
    return build_roadmap(job, fl)
