"""
scoring.py — Tính điểm phù hợp giữa job và freelancer (phần CÓ CẤU TRÚC).

Công thức tổng: điểm = Σ (trọng số × mức_khớp mỗi tiêu chí)
Bốn tiêu chí, tổng trọng số = 100:
    - Kỹ năng & portfolio : 40
    - Kinh nghiệm         : 25
    - Ngân sách           : 20
    - Thời gian & múi giờ : 15

Toàn bộ là thuật toán thuần — không gọi AI, không tốn token.
Mỗi hàm con vừa trả về mức_khớp (0..1), vừa trả về dữ liệu để GIẢI THÍCH lý do.
"""

WEIGHTS = {
    "skills": 40,
    "experience": 25,
    "budget": 20,
    "time": 15,
}


def _norm(s: str) -> str:
    """Chuẩn hoá chuỗi để so khớp: bỏ khoảng trắng thừa, viết thường."""
    return s.strip().lower()


def score_skills(job, fl):
    """
    Tiêu chí 1 — Kỹ năng (40).
    Mức khớp = (số kỹ năng yêu cầu mà freelancer có) / (số kỹ năng yêu cầu).
    Lưu ý: đây là so khớp CHÍNH XÁC theo chữ. 'Sketch' KHÔNG khớp 'Figma'
    dù cùng là công cụ thiết kế — đây đúng là điểm yếu của khớp-chuỗi,
    và là chỗ ta sẽ dùng AI chuẩn hoá thuật ngữ ở bước sau.
    """
    required = [_norm(s) for s in job["required_skills"]]
    have = {_norm(s) for s in fl["skills"]}

    matched = [s for s in required if s in have]
    missing = [s for s in required if s not in have]
    ratio = len(matched) / len(required) if required else 0.0

    return ratio, matched, missing


def score_experience(job, fl):
    """
    Tiêu chí 2 — Kinh nghiệm (25).
    Đủ hoặc vượt mức yêu cầu = full điểm. Dưới mức = tính theo tỉ lệ.
    (Đơn giản, dễ giải thích: 'đạt yêu cầu tối thiểu là được full trục này'.)
    """
    req = job["min_experience_years"]
    exp = fl["experience_years"]
    if req <= 0:
        return 1.0
    ratio = min(exp / req, 1.0)
    return ratio


def score_budget(job, fl):
    """
    Tiêu chí 3 — Ngân sách (20).
    Giá đề xuất nằm trong hoặc dưới trần ngân sách = full (rẻ hơn thì tốt cho khách).
    Vượt trần = trừ điểm theo mức độ vượt (trần / giá đề xuất).
    """
    price = fl["proposed_price"]
    bmax = job["budget_max"]
    if price <= bmax:
        return 1.0
    return max(0.0, bmax / price)


def score_time(job, fl):
    """
    Tiêu chí 4 — Thời gian & múi giờ (15).
    Gồm 2 phần:
      - Sẵn sàng (60%): bắt đầu càng sớm so với deadline càng tốt.
      - Múi giờ  (40%): lệch càng ít càng tốt (dung sai ~6 giờ).
    """
    deadline = job["deadline_weeks"]
    avail = fl["available_in_weeks"]
    avail_score = max(0.0, 1 - avail / deadline) if deadline > 0 else 1.0

    diff = abs(job["timezone"] - fl["timezone"])
    tz_score = max(0.0, 1 - diff / 6)

    combined = 0.6 * avail_score + 0.4 * tz_score
    return combined, avail_score, tz_score, diff


def match_score(job, fl):
    """
    Gộp 4 tiêu chí thành điểm cuối + bảng giải thích từng trục.
    Trả về dict: điểm tổng (0..100), điểm từng tiêu chí, và chi tiết để hiển thị.
    """
    skill_ratio, matched_skills, missing_skills = score_skills(job, fl)
    exp_ratio = score_experience(job, fl)
    budget_ratio = score_budget(job, fl)
    time_ratio, avail_score, tz_score, tz_diff = score_time(job, fl)

    points = {
        "skills": skill_ratio * WEIGHTS["skills"],
        "experience": exp_ratio * WEIGHTS["experience"],
        "budget": budget_ratio * WEIGHTS["budget"],
        "time": time_ratio * WEIGHTS["time"],
    }
    total = round(sum(points.values()))

    # Bảng giải thích: mỗi trục kèm đánh giá đạt (✓) / lưu ý (!)
    reasons = []
    reasons.append({
        "tieu_chi": "Kỹ năng",
        "dat": len(missing_skills) == 0,
        "chi_tiet": f"Khớp {len(matched_skills)}/{len(job['required_skills'])} kỹ năng yêu cầu"
                    + (f"; thiếu: {', '.join(missing_skills)}" if missing_skills else ""),
    })
    reasons.append({
        "tieu_chi": "Kinh nghiệm",
        "dat": fl["experience_years"] >= job["min_experience_years"],
        "chi_tiet": f"{fl['experience_years']} năm (yêu cầu {job['min_experience_years']}+)",
    })
    reasons.append({
        "tieu_chi": "Ngân sách",
        "dat": fl["proposed_price"] <= job["budget_max"],
        "chi_tiet": f"Đề xuất {fl['proposed_price']:,}đ "
                    f"(ngân sách {job['budget_min']:,}–{job['budget_max']:,}đ)",
    })
    reasons.append({
        "tieu_chi": "Thời gian & múi giờ",
        "dat": fl["available_in_weeks"] <= job["deadline_weeks"] and tz_diff <= 1,
        "chi_tiet": (f"Bắt đầu sau {fl['available_in_weeks']} tuần "
                     f"(deadline {job['deadline_weeks']} tuần); "
                     f"lệch múi giờ {tz_diff}h"),
    })

    return {
        "id": fl["id"],
        "freelancer": fl["name"],
        "role": fl["role"],
        "total": total,
        "points": {k: round(v, 1) for k, v in points.items()},
        "reasons": reasons,
    }


def rank(job, freelancers):
    """Chấm tất cả freelancer rồi xếp từ cao xuống thấp."""
    results = [match_score(job, fl) for fl in freelancers]
    results.sort(key=lambda r: r["total"], reverse=True)
    return results


if __name__ == "__main__":
    import json

    with open("du-lieu-mau.json", encoding="utf-8") as f:
        data = json.load(f)

    job = data["job"]
    ranked = rank(job, data["freelancers"])

    print(f"JOB: {job['title']}")
    print(f"Yêu cầu: {', '.join(job['required_skills'])} | "
          f"KN {job['min_experience_years']}+ năm | "
          f"NS {job['budget_min']:,}–{job['budget_max']:,}đ | "
          f"deadline {job['deadline_weeks']} tuần\n")
    print("=" * 60)

    for r in ranked:
        print(f"\n{r['total']}%  {r['freelancer']} — {r['role']}")
        p = r["points"]
        print(f"   Kỹ năng {p['skills']}/40 | KN {p['experience']}/25 | "
              f"NS {p['budget']}/20 | TG {p['time']}/15")
        for reason in r["reasons"]:
            mark = "✓" if reason["dat"] else "!"
            print(f"     {mark} {reason['tieu_chi']}: {reason['chi_tiet']}")
