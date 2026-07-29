"""
roadmap.py — Lộ trình phát triển cho freelancer điểm thấp.

Ý tưởng: hàm tính điểm đã biết freelancer mất điểm ở đâu và mất bao nhiêu.
Lộ trình = xếp các khoảng cách đó theo "sửa được thì lợi nhất", kèm điểm dự kiến.
Đây là phần THUẬT TOÁN (0 token). Lời khuyên tự nhiên bằng AI sẽ là lớp phủ sau.
"""

from scoring import WEIGHTS, match_score, score_skills


# Ngưỡng: dưới mức này thì mới đề xuất lộ trình cải thiện.
LOW_SCORE_THRESHOLD = 75


def build_roadmap(job, fl):
    """
    Trả về lộ trình cho một freelancer: các mục cần cải thiện,
    xếp theo mức điểm có thể lấy lại (cao xuống thấp), kèm điểm dự kiến.
    """
    result = match_score(job, fl)
    points = result["points"]

    # Khoảng cách mỗi tiêu chí = điểm tối đa - điểm hiện có.
    gaps = []

    # --- Kỹ năng ---
    skill_ratio, matched, missing = score_skills(job, fl)
    skill_gap = WEIGHTS["skills"] - points["skills"]
    if missing:
        gaps.append({
            "tieu_chi": "Kỹ năng",
            "diem_co_the_lay_lai": round(skill_gap, 1),
            "hanh_dong": f"Bổ sung kỹ năng: {', '.join(missing)}",
            "loai": "skills",
        })

    # --- Kinh nghiệm ---
    if fl["experience_years"] < job["min_experience_years"]:
        exp_gap = WEIGHTS["experience"] - points["experience"]
        thieu = job["min_experience_years"] - fl["experience_years"]
        gaps.append({
            "tieu_chi": "Kinh nghiệm",
            "diem_co_the_lay_lai": round(exp_gap, 1),
            "hanh_dong": f"Tích lũy thêm ~{thieu} năm kinh nghiệm liên quan "
                         f"(hoặc thêm dự án vào portfolio) để đạt mức {job['min_experience_years']}+ năm",
            "loai": "experience",
        })

    # --- Ngân sách ---
    if fl["proposed_price"] > job["budget_max"]:
        budget_gap = WEIGHTS["budget"] - points["budget"]
        gaps.append({
            "tieu_chi": "Ngân sách",
            "diem_co_the_lay_lai": round(budget_gap, 1),
            "hanh_dong": f"Cân nhắc điều chỉnh giá đề xuất xuống trong khoảng "
                         f"{job['budget_min']:,}–{job['budget_max']:,}đ",
            "loai": "budget",
        })

    # --- Thời gian & múi giờ ---
    time_gap = WEIGHTS["time"] - points["time"]
    if time_gap >= 1:  # chỉ đề xuất nếu mất đáng kể
        note = []
        if fl["available_in_weeks"] > 0:
            note.append("bắt đầu sớm hơn nếu có thể")
        if abs(job["timezone"] - fl["timezone"]) > 0:
            note.append("sắp xếp giờ làm chồng lấp nhiều hơn với khách")
        if note:
            gaps.append({
                "tieu_chi": "Thời gian & múi giờ",
                "diem_co_the_lay_lai": round(time_gap, 1),
                "hanh_dong": "Cải thiện lịch: " + ", ".join(note),
                "loai": "time",
            })

    # Xếp theo điểm lấy lại được — sửa cái lợi nhất trước.
    gaps.sort(key=lambda g: g["diem_co_the_lay_lai"], reverse=True)

    # Điểm dự kiến nếu sửa hết các mục kỹ năng + kinh nghiệm (2 đòn bẩy chính,
    # là những thứ freelancer chủ động cải thiện được qua học tập).
    diem_hien_tai = result["total"]
    diem_neu_sua_ky_nang = diem_hien_tai
    for g in gaps:
        if g["loai"] in ("skills", "experience"):
            diem_neu_sua_ky_nang += g["diem_co_the_lay_lai"]
    diem_du_kien = round(min(diem_neu_sua_ky_nang, 100))

    return {
        "freelancer": fl["name"],
        "diem_hien_tai": diem_hien_tai,
        "diem_du_kien": diem_du_kien,
        "can_lo_trinh": diem_hien_tai < LOW_SCORE_THRESHOLD,
        "cac_buoc": gaps,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    data = json.loads(Path("du-lieu-mau.json").read_text(encoding="utf-8"))
    job = data["job"]

    for fl in data["freelancers"]:
        rm = build_roadmap(job, fl)
        flag = "  ← cần lộ trình" if rm["can_lo_trinh"] else ""
        print(f"\n{rm['freelancer']} — hiện {rm['diem_hien_tai']}%{flag}")
        if rm["can_lo_trinh"]:
            print(f"  Nếu cải thiện kỹ năng/kinh nghiệm: {rm['diem_hien_tai']}% → {rm['diem_du_kien']}%")
            for i, b in enumerate(rm["cac_buoc"], 1):
                print(f"  {i}. [+{b['diem_co_the_lay_lai']}đ] {b['hanh_dong']}")
        else:
            print("  Điểm đã cao, không cần lộ trình cải thiện.")
