"""
tier2_ai.py — TẦNG 2 (lưới an toàn bằng Gemini) + luồng chuẩn hoá hoàn chỉnh.

Luồng: process_job(text)
    1. Chạy Tầng 1 (thuật toán). Nếu đủ tin cậy → trả luôn, 0 token.
    2. Nếu Tầng 1 báo cần AI → gọi Gemini bóc giúp.
    3. Nếu Gemini cũng thất bại (lỗi/hết quota/JSON sai/vẫn thiếu) →
       trả trạng thái 'needs_more_info': đề nghị người đăng bổ sung, KHÔNG bịa dữ liệu.

Key đọc từ biến môi trường GEMINI_API_KEY (nạp từ file .env). Không hardcode.
"""

import os
import re
import json

from extractor import extract_job

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # nếu chưa cài python-dotenv, vẫn đọc được env hệ thống

API_KEY = os.getenv("GEMINI_API_KEY")

# Model free-tier nhanh, rẻ. Tên model có thể đổi theo thời gian —
# nếu gặp lỗi "model not found", đổi dòng này theo model hiện có trong AI Studio.
MODEL = "gemini-flash-latest"

EMPTY = {
    "required_skills": [],
    "min_experience_years": None,
    "budget_min": None,
    "budget_max": None,
    "currency": None,
    "deadline_weeks": None,
}


def _needs_more_info(reason, partial=None, still_missing=None):
    """Trả về khi cả Tầng 1 lẫn Tầng 2 đều không đủ dữ liệu."""
    return {
        "status": "needs_more_info",
        "reason": reason,
        "still_missing": still_missing or [],
        "extracted": partial or dict(EMPTY),
        "source": "fallback",
    }


def _build_prompt(text: str) -> str:
    """Prompt ép Gemini trả về ĐÚNG JSON theo schema của Tầng 1."""
    return f"""Bạn là bộ trích xuất thông tin tuyển dụng. Đọc mô tả công việc dưới đây
và trả về CHỈ một object JSON, không thêm chữ nào khác, không dùng dấu ``` .

Schema (thiếu trường nào thì để null, riêng required_skills để mảng rỗng []):
{{
  "required_skills": ["..."],       // tên kỹ năng, ví dụ: Figma, UI Design, E-commerce
  "min_experience_years": 3,        // số năm kinh nghiệm tối thiểu, hoặc null
  "budget_min": 15000000,           // số, không kèm đơn vị, hoặc null
  "budget_max": 25000000,           // số, hoặc null
  "currency": "VND",                // "VND" hoặc "USD", hoặc null
  "deadline_weeks": 3               // quy về số tuần, hoặc null
}}

Nếu mô tả mơ hồ, hãy SUY LUẬN kỹ năng khả dĩ từ ngữ cảnh (ví dụ "web bán hàng đẹp"
gợi ý: Web Design, UI Design, E-commerce). Nhưng KHÔNG bịa số ngân sách/thời gian nếu
mô tả không nêu — để null.

Mô tả công việc:
\"\"\"{text}\"\"\"
"""


def _parse_json(raw: str):
    """Bóc JSON từ phản hồi AI, chịu được trường hợp có dấu ``` bao quanh."""
    if not raw:
        return None
    s = raw.strip()
    # bỏ hàng rào markdown nếu có
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    # lấy đoạn từ { đầu tiên tới } cuối
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        s = m.group(0)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def extract_with_ai(text: str):
    """Gọi Gemini bóc thông tin. Trả về dict chuẩn hoặc needs_more_info."""
    if not API_KEY:
        return _needs_more_info("Chưa cấu hình GEMINI_API_KEY trong .env")

    try:
        from google import genai
        client = genai.Client(api_key=API_KEY)
        resp = client.models.generate_content(
            model=MODEL,
            contents=_build_prompt(text),
        )
        raw = resp.text
    except Exception as e:
        # mạng lỗi, hết quota, sai model... đều rơi vào đây
        return _needs_more_info(f"Không gọi được AI ({type(e).__name__})")

    data = _parse_json(raw)
    if data is None:
        return _needs_more_info("AI trả về không đúng định dạng JSON")

    # Chuẩn hoá về đúng schema, điền mặc định cho trường thiếu
    extracted = dict(EMPTY)
    for k in EMPTY:
        if k in data and data[k] is not None:
            extracted[k] = data[k]

    # Ngay cả sau AI, nếu vẫn thiếu trường quan trọng thì đề nghị bổ sung
    still_missing = []
    if not extracted["required_skills"]:
        still_missing.append("kỹ năng yêu cầu")
    if extracted["budget_min"] is None:
        still_missing.append("ngân sách")
    if still_missing:
        return _needs_more_info(
            "Mô tả quá mơ hồ, cần bổ sung thông tin",
            partial=extracted,
            still_missing=still_missing,
        )

    return {
        "status": "ok",
        "extracted": extracted,
        "source": "tier2_ai",
    }


def process_job(text: str):
    """
    Luồng hoàn chỉnh: Tầng 1 → (nếu cần) Tầng 2 → (nếu vẫn fail) needs_more_info.
    Đây là hàm mà backend sẽ gọi.
    """
    t1 = extract_job(text)

    if not t1["needs_ai"]:
        return {
            "status": "ok",
            "extracted": t1["extracted"],
            "source": "tier1_algorithm",
            "confidence": t1["confidence"],
        }

    # Tầng 1 bó tay → nhờ Tầng 2
    return extract_with_ai(text)


if __name__ == "__main__":
    samples = [
        "Cần thiết kế web bán hàng, thành thạo Figma, ngân sách 15-25 triệu, 3 tuần, 3 năm.",  # Tầng 1
        "Cần người làm web đẹp đẹp, giá tốt, xong sớm nha.",                                    # Tầng 2
    ]
    for s in samples:
        r = process_job(s)
        print(f"\n\"{s[:50]}...\"")
        print(f"  source : {r['source']}")
        print(f"  status : {r['status']}")
        if r["status"] == "ok":
            print(f"  data   : {r['extracted']}")
        else:
            print(f"  reason : {r['reason']}")
            print(f"  thiếu  : {r.get('still_missing')}")
