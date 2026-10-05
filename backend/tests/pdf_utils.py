"""Builds small but valid text PDFs for tests (no extra dependency needed)."""


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list[str], lines_per_page: int = 48) -> bytes:
    """One Helvetica text line per entry; long inputs flow onto extra pages."""
    pages = [lines[i:i + lines_per_page] for i in range(0, max(len(lines), 1), lines_per_page)] or [[]]
    objects: list[bytes] = []

    def add(body: str | bytes) -> int:
        objects.append(body.encode("latin-1") if isinstance(body, str) else body)
        return len(objects)

    catalog = add("")  # placeholders, filled in below
    pages_obj = add("")
    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    for page_lines in pages:
        content = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
        content += [f"({_escape(line)}) Tj T*" for line in page_lines]
        content.append("ET")
        stream = "\n".join(content).encode("latin-1", errors="replace")
        content_id = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_ids.append(add(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 595 842] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font} 0 R >> >> >>"
        ))
    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objects[pages_obj - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, catalog, xref)
    return bytes(out)


# ---------- sample resumes used across the tests ----------
FULL_RESUME = [
    "ASHA PATIL",
    "asha.patil@example.com | +91 98765 43210 | linkedin.com/in/ashapatil | github.com/ashapatil",
    "",
    "SUMMARY",
    "Second year computer science student interested in data analysis and machine learning.",
    "Looking for an internship where I can apply my skills in Python and SQL to real business problems.",
    "",
    "EDUCATION",
    "B.Tech in Computer Science and Engineering",
    "ABC Institute of Technology, Pune",
    "2024 - 2028    CGPA: 8.4",
    "HSC (12th) - Science, XYZ Junior College, 2024, 88.5%",
    "",
    "SKILLS",
    "Languages: Python, SQL, C, Java",
    "Data: Pandas, NumPy, Scikit-learn, Statistics, Excel",
    "Tools: Git, Linux",
    "",
    "PROJECTS",
    "Placement Predictor",
    "- Built a model in Python using Scikit-learn and Pandas to predict placement outcomes.",
    "- Improved accuracy from 71% to 84% by tuning features on a dataset of 1200 students.",
    "- Presented the findings to faculty and documented the full workflow in a shared report.",
    "Student Portal",
    "- Developed a web portal with Flask and MySQL used by 150 students.",
    "- Designed REST APIs and wrote unit tests covering the login and marks modules.",
    "- Collaborated with a team of 4 and managed tasks using Git branches and pull requests.",
    "Campus Bus Tracker",
    "- Created a mobile friendly page that shows live bus timings for 3 college routes.",
    "- Optimized database queries and reduced page load time by 40%.",
    "",
    "EXPERIENCE",
    "Data Intern - Acme Analytics            Jun 2025 - Aug 2025",
    "- Analysed sales data with SQL and Excel and created 5 weekly dashboards.",
    "- Cleaned and merged data from 3 sources using Python and reported trends to the manager.",
    "- Automated a monthly report, saving about 6 hours of manual work every month.",
    "",
    "CERTIFICATIONS",
    "- Google Data Analytics Certificate",
    "- Python for Everybody (Coursera)",
]

MISSING_SECTIONS_RESUME = [
    "Ravi Kumar",
    "ravi.kumar@example.com",
    "",
    "EDUCATION",
    "B.E. Mechanical Engineering, DEF College of Engineering, 2022 - 2026",
    "I am a hard working student who likes to learn new things and work with teams on many different tasks.",
    "I have good communication and I am interested in getting a job in a good company where I can grow.",
    "I have done many things in college and I am looking forward to starting my career in industry soon.",
]
