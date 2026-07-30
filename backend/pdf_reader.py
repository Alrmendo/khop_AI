"""
pdf_reader.py — Đọc CV dạng PDF (text) và bóc kỹ năng + kinh nghiệm.

Nguyên tắc: pdfplumber CHỈ lo lấy chữ ra khỏi PDF. Phần "hiểu" (bóc kỹ năng,
kinh nghiệm) tái dùng đúng bộ trích xuất đã có trong extractor.py — không viết lại.

Giới hạn đã biết: chỉ đọc được PDF text (xuất từ Word/Canva...).
PDF scan (ảnh) cần OCR (Tesseract) — để phase sau.
"""

import io

import pdfplumber

from extractor import _find_skills, _find_experience


def extract_text_from_pdf(path: str) -> str:
    """Bóc toàn bộ text từ file PDF (theo đường dẫn). Rỗng nếu là PDF scan."""
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages).strip()


def extract_text_from_bytes(data: bytes) -> str:
    """Bóc text từ PDF dạng bytes (dùng khi nhận file upload qua API)."""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages).strip()


def _parse_text(text: str):
    """Bóc kỹ năng + kinh nghiệm từ text đã có (dùng chung cho path & bytes)."""
    if not text:
        return {
            "status": "needs_more_info",
            "reason": "Không đọc được chữ — có thể là PDF scan, cần OCR.",
            "extracted": {"skills": [], "experience_years": None},
            "source": "pdf_reader",
        }
    skills = _find_skills(text)
    exp = _find_experience(text)

    # --- Cổng tin cậy ---
    # Không đủ nếu: (a) không thấy kỹ năng nào, HOẶC
    # (b) text dài (CV thật) nhưng bóc được quá ít kỹ năng so với độ dài —
    #     dấu hiệu từ điển không phủ domain của CV này → nhờ Tầng 2 (Gemini).
    # Ngưỡng: cứ ~800 ký tự nên có ít nhất 1 kỹ năng; CV 5000 ký tự mà <6 kỹ năng
    # thì đáng ngờ (như CV Business Analyst lọt lưới trước đây).
    expected_min = max(1, len(text) // 800)
    low_density = len(skills) < expected_min
    needs_ai = (len(skills) == 0) or low_density

    reason = None
    if needs_ai and skills:
        reason = (f"Bóc được {len(skills)} kỹ năng nhưng CV dài {len(text)} ký tự "
                  f"— nghi ngờ từ điển chưa phủ hết, nên chuyển AI đọc kỹ hơn.")

    return {
        "status": "ok" if not needs_ai else "needs_ai",
        "extracted": {"skills": skills, "experience_years": exp},
        "needs_ai": needs_ai,
        "low_confidence_reason": reason,
        "raw_text_preview": text[:200],
        "source": "tier1_algorithm",
    }


def parse_resume(path: str):
    """CV.pdf (đường dẫn) -> kỹ năng + kinh nghiệm."""
    return _parse_text(extract_text_from_pdf(path))


def parse_resume_bytes(data: bytes):
    """CV.pdf (bytes từ upload) -> kỹ năng + kinh nghiệm."""
    return _parse_text(extract_text_from_bytes(data))


if __name__ == "__main__":
    import json
    r = parse_resume("cv_mau.pdf")
    print("KẾT QUẢ ĐỌC CV:")
    print(f"  source : {r['source']}")
    print(f"  status : {r['status']}")
    print(f"  kỹ năng: {r['extracted']['skills']}")
    print(f"  kinh nghiệm: {r['extracted']['experience_years']} năm")
    print(f"\n  (Trích text thô bóc được:)")
    print(f"  {r.get('raw_text_preview', '')[:150]}...")
