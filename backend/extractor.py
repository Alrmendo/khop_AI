"""
extractor.py — TẦNG 1 (song ngữ Việt/Anh, thuật toán thuần, 0 token).

Đọc mô tả job dạng tự do → bóc ra dữ liệu có cấu trúc + chấm độ tin cậy.
Nếu tin cậy thấp → needs_ai=True để Tầng 2 (Gemini) xử lý.

Nguyên tắc song ngữ: chạy CẢ mẫu tiếng Việt lẫn tiếng Anh, cái nào khớp thì lấy —
không cần đoán ngôn ngữ trước ("triệu" và "$" không đụng nhau).
Cấu trúc để dễ cắm thêm ngôn ngữ khác sau này.
"""

import re


# ---------------------------------------------------------------------------
# TỪ ĐIỂN KỸ NĂNG — tên chuẩn -> biến thể (trộn Việt + Anh).
# Giữ gọn, thực dụng; phần đuôi dài để Tầng 2 AI gánh cho cả hai ngôn ngữ.
# ---------------------------------------------------------------------------
SKILL_DICT = {
    "Figma":         ["figma", "figjam"],
    "Sketch":        ["sketch"],
    "Adobe XD":      ["adobe xd", "adobexd"],
    "UI Design":     ["ui design", "ui/ux", "ux/ui", "ui-ux", "user interface",
                      "thiết kế giao diện", "thiết kế ui", "giao diện người dùng"],
    "E-commerce":    ["e-commerce", "ecommerce", "online store", "shopping site",
                      "thương mại điện tử", "web bán hàng", "website bán hàng",
                      "bán hàng online", "sàn thương mại", "trang bán hàng"],
    "Prototyping":   ["prototyping", "prototype", "tạo mẫu", "dựng mẫu"],
    "Design System": ["design system", "hệ thống thiết kế"],
    "Web Design":    ["web design", "website design", "thiết kế web", "thiết kế website"],
    "HTML/CSS":      ["html/css", "html", "css"],
    "User Research": ["user research", "nghiên cứu người dùng", "phỏng vấn người dùng"],
    "Illustration":  ["illustration", "minh hoạ", "minh họa", "vẽ minh hoạ"],
}

SHORT_ALIASES = {"ui", "ux", "css", "html", "xd"}


def _detect_lang(text: str) -> str:
    """Nhận diện ngôn ngữ đơn giản: có dấu tiếng Việt => 'vi', ngược lại 'en'.
    Chỉ để BÁO CÁO; việc bóc số vẫn thử cả hai bộ mẫu."""
    if re.search(r"[ăâđêôơưáàảãạấầẩẫậéèẻẽẹíìỉĩịóòỏõọúùủũụ]", text.lower()):
        return "vi"
    return "en"


def _find_budget(text: str):
    """
    Trả về (min, max, currency). Thử cả VNĐ và USD.
    VN: '15-25 triệu', '20 triệu', '20tr'  -> VND
    EN: '$2000', '$2000-$3000', '2000-3000 usd', '$2k' -> USD
    """
    low = text.lower().replace(",", "")

    # --- Tiếng Việt (VND) ---
    m = re.search(r"(\d+)\s*(?:-|–|đến|tới)\s*(\d+)\s*(?:triệu|tr\b)", low)
    if m:
        return int(m.group(1)) * 1_000_000, int(m.group(2)) * 1_000_000, "VND"
    m = re.search(r"(\d+)\s*(?:triệu|tr\b)", low)
    if m:
        v = int(m.group(1)) * 1_000_000
        return v, v, "VND"

    # --- Tiếng Anh (USD) ---
    def _usd(tok):  # '2k' -> 2000 ; '2000' -> 2000
        tok = tok.strip()
        if tok.endswith("k"):
            return int(float(tok[:-1]) * 1000)
        return int(float(tok))

    m = re.search(r"\$?\s*(\d+(?:\.\d+)?k?)\s*(?:-|–|to)\s*\$?\s*(\d+(?:\.\d+)?k?)\s*(?:usd)?", low)
    if m and ("$" in low or "usd" in low or "k" in (m.group(1) + m.group(2))):
        return _usd(m.group(1)), _usd(m.group(2)), "USD"
    m = re.search(r"\$\s*(\d+(?:\.\d+)?k?)", low)
    if m:
        v = _usd(m.group(1))
        return v, v, "USD"
    m = re.search(r"(\d+(?:\.\d+)?k?)\s*usd", low)
    if m:
        v = _usd(m.group(1))
        return v, v, "USD"

    return None, None, None


def _find_experience(text: str):
    """Số năm KN tối thiểu. VN: '3 năm', '3+ năm'. EN: '3 years', '3 yrs'."""
    low = text.lower()
    m = re.search(r"(\d+)\s*\+?\s*(?:năm|years?|yrs?)", low)
    if m:
        return int(m.group(1))
    return None


def _find_deadline(text: str):
    """Thời hạn quy về TUẦN. VN: 'tuần','tháng'. EN: 'week(s)','month(s)'."""
    low = text.lower()
    m = re.search(r"(\d+)\s*(?:tuần|weeks?)", low)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(?:tháng|months?)", low)
    if m:
        return int(m.group(1)) * 4
    return None


def _find_skills(text: str):
    low = text.lower()
    found = []
    for canonical, aliases in SKILL_DICT.items():
        for alias in aliases:
            if alias in SHORT_ALIASES:
                if re.search(rf"\b{re.escape(alias)}\b", low):
                    found.append(canonical)
                    break
            elif alias in low:
                found.append(canonical)
                break
    return found


def extract_job(text: str):
    """Trích toàn bộ + chấm độ tin cậy + cờ needs_ai."""
    lang = _detect_lang(text)
    skills = _find_skills(text)
    exp = _find_experience(text)
    bmin, bmax, currency = _find_budget(text)
    deadline = _find_deadline(text)

    missing = []
    if not skills:
        missing.append("required_skills")
    if bmin is None:
        missing.append("budget")
    if exp is None:
        missing.append("min_experience_years")
    if deadline is None:
        missing.append("deadline_weeks")

    needs_ai = ("required_skills" in missing) or ("budget" in missing)
    confidence = round(1 - len(missing) / 4, 2)

    return {
        "lang": lang,
        "extracted": {
            "required_skills": skills,
            "min_experience_years": exp,
            "budget_min": bmin,
            "budget_max": bmax,
            "currency": currency,
            "deadline_weeks": deadline,
        },
        "missing": missing,
        "confidence": confidence,
        "needs_ai": needs_ai,
        "source": "tier1_algorithm",
    }


if __name__ == "__main__":
    tests = [
        "Cần thiết kế lại giao diện web bán hàng, thành thạo Figma. "
        "Ngân sách 15-25 triệu, thời hạn 3 tuần, ít nhất 3 năm kinh nghiệm.",
        "Tuyển bạn làm UI/UX cho sàn thương mại điện tử, biết Sketch càng tốt. "
        "Ngân sách khoảng 20 triệu, làm trong 1 tháng.",
        "Cần người làm web đẹp đẹp, giá tốt, xong sớm nha.",
        "Looking for a UI designer skilled in Figma for our e-commerce site. "
        "Budget $2000-$3000, timeline 3 weeks, at least 3 years experience.",
        "Need a web design freelancer, HTML/CSS. Budget $2k, 2 months, 2 years experience.",
        "Want someone to make our site look nice, good price, asap.",
    ]

    for i, t in enumerate(tests, 1):
        r = extract_job(t)
        e = r["extracted"]
        print(f"\n[{i}] ({r['lang']}) \"{t[:52]}...\"")
        print(f"    Ky nang: {e['required_skills']}")
        print(f"    KN: {e['min_experience_years']} | "
              f"NS: {e['budget_min']}-{e['budget_max']} {e['currency'] or ''} | "
              f"Deadline: {e['deadline_weeks']} tuan")
        print(f"    Tin cay: {r['confidence']} | "
              f"{'-> CAN AI (Tang 2)' if r['needs_ai'] else '-> DU (Tang 1)'}")
