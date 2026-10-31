import json
from pathlib import Path
import fitz  # PyMuPDF


# Question templates with signature anchor substrings to find exact page programmatically
QUESTION_DEFINITIONS = [
    # Northwind_Labs_Employee_Handbook.pdf
    {
        "id": 1,
        "question": "How many days of paid vacation do new employees receive per year?",
        "expected_answer": "New employees receive 18 days of paid vacation per year, accrued at 1.5 days per month.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "accrue 18 days of paid vacation",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 2,
        "question": "How long is the initial probationary period for new hires at Northwind Labs?",
        "expected_answer": "The initial probationary period is 90 calendar days.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "initial 90-calendar-day probationary period",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 3,
        "question": "What are the core collaboration hours when employees must be online?",
        "expected_answer": "Core collaborative hours are from 10:00 AM to 4:00 PM EST, Monday through Friday.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "10:00 AM to 4:00 PM EST",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 4,
        "question": "How many days per week are hybrid employees permitted to work remotely?",
        "expected_answer": "Eligible hybrid employees may work remotely up to 2 days per week (typically Tuesdays and Thursdays).",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "work remotely up to 2 days per week",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 5,
        "question": "What is the minimum internet speed required for remote workers?",
        "expected_answer": "Remote employees must have an internet connection with a minimum download speed of 50 Mbps.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "minimum download speed of 50 Mbps",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 6,
        "question": "How many unused vacation days can be rolled over to the next calendar year?",
        "expected_answer": "A maximum of 5 unused vacation days may be rolled over into the following year.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "maximum of 5 unused vacation days",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 7,
        "question": "How many paid sick days do full-time employees receive annually?",
        "expected_answer": "Full-time employees receive 10 paid sick days per year, credited upfront on January 1.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "10 paid sick days per year",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 8,
        "question": "When is a doctor's note required for consecutive sick leave absences?",
        "expected_answer": "A doctor's note from a licensed healthcare provider is required for consecutive sick absences exceeding 3 business days.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "exceeding 3 business days require",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 9,
        "question": "How many weeks of paid parental leave do primary caregivers receive?",
        "expected_answer": "Primary caregivers receive 12 weeks of fully paid parental leave (after 6 months of service).",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "12 weeks of fully paid parental leave",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 10,
        "question": "How many days of paid bereavement leave are provided for immediate family members?",
        "expected_answer": "Up to 5 consecutive paid business days for immediate family members.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "up to 5 consecutive paid business days for the death of an immediate",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 11,
        "question": "How much paid leave does Northwind Labs provide for jury duty?",
        "expected_answer": "Up to 2 weeks (10 business days) of fully paid leave for jury duty service.",
        "source_filename": "Northwind_Labs_Employee_Handbook.pdf",
        "anchor": "up to 2 weeks (10 business days) of fully paid leave",
        "split": "test",
        "is_answerable": True,
    },

    # Northwind_Labs_Benefits_Guide.pdf
    {
        "id": 12,
        "question": "What is the individual deductible under the Premier PPO medical plan?",
        "expected_answer": "The individual annual in-network deductible is $500 ($1,000 for families).",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "individual annual in-network deductible is $500",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 13,
        "question": "How much does the company contribute annually to an individual HSA under the HDHP?",
        "expected_answer": "Northwind Labs contributes $750 per year for individual coverage ($1,500 for families) in quarterly installments.",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "contributes $750 per year to an individual Health Savings Account",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 14,
        "question": "What percentage does Northwind Labs match on employee 401(k) contributions?",
        "expected_answer": "Northwind Labs matches 100% of employee contributions up to 5% of eligible base salary.",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "100% employer match on employee contributions up to 5%",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 15,
        "question": "What is the vesting schedule for employer 401(k) matching contributions?",
        "expected_answer": "Employer matching contributions feature 100% immediate vesting from day one of employment.",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "100% immediate vesting from day one",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 16,
        "question": "What is the monthly reimbursement amount for the wellness and fitness stipend?",
        "expected_answer": "$75 per month (up to a $900 annual maximum).",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "wellness reimbursement stipend of $75 per month",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 17,
        "question": "What is the annual reimbursement limit for tuition and professional learning?",
        "expected_answer": "Up to $5,250 per calendar year for pre-approved courses with a grade of B or higher.",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "$5,250 per calendar year in tuition",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 18,
        "question": "How many free counseling sessions are provided through Lyra Health EAP?",
        "expected_answer": "Up to 6 confidential, fully covered mental health counseling sessions per issue per calendar year.",
        "source_filename": "Northwind_Labs_Benefits_Guide.pdf",
        "anchor": "up to 6 confidential, fully covered mental health counseling",
        "split": "test",
        "is_answerable": True,
    },

    # Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf
    {
        "id": 19,
        "question": "What is the maximum allowed value for gifts received from vendors or clients?",
        "expected_answer": "Gifts cannot exceed $50 in estimated value. Gifts between $25 and $50 must be reported.",
        "source_filename": "Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf",
        "anchor": "exceed $50 in estimated fair market value",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 20,
        "question": "What are the corporate requirements for employee password length and complexity?",
        "expected_answer": "Minimum 14 characters including uppercase, lowercase, numbers, and symbols; rotated every 90 days.",
        "source_filename": "Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf",
        "anchor": "minimum length of 14 characters",
        "split": "dev",
        "is_answerable": True,
    },
    {
        "id": 21,
        "question": "Within how many minutes of inactivity must corporate laptops automatically lock?",
        "expected_answer": "Laptops auto-lock after 5 minutes of inactivity.",
        "source_filename": "Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf",
        "anchor": "after 5 minutes of inactivity",
        "split": "test",
        "is_answerable": True,
    },
    {
        "id": 22,
        "question": "Within how many hours must a suspected security incident or breach be reported?",
        "expected_answer": "Within 2 hours of discovery to security@northwindlabs.com or emergency hotline ext. 4357.",
        "source_filename": "Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf",
        "anchor": "within a strict maximum window of 2 hours",
        "split": "test",
        "is_answerable": True,
    },

    # 8 UNANSWERABLE QUESTIONS (Expected Behavior = Fallback)
    {
        "id": 23,
        "question": "What is Northwind Labs' stock ticker symbol on NASDAQ?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "dev",
        "is_answerable": False,
    },
    {
        "id": 24,
        "question": "Can employees bring pet dogs into the office on Casual Fridays?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "test",
        "is_answerable": False,
    },
    {
        "id": 25,
        "question": "What is the corporate reimbursement policy for business class international flights?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "test",
        "is_answerable": False,
    },
    {
        "id": 26,
        "question": "Does Northwind Labs offer a relocation assistance package for moving to the Tokyo office?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "test",
        "is_answerable": False,
    },
    {
        "id": 27,
        "question": "What is the personal mobile phone number of the Chief Executive Officer?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "dev",
        "is_answerable": False,
    },
    {
        "id": 28,
        "question": "How much corporate discount do employees get when buying Apple MacBooks through the company store?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "test",
        "is_answerable": False,
    },
    {
        "id": 29,
        "question": "Does Northwind Labs provide free catered lunch on Wednesdays?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "test",
        "is_answerable": False,
    },
    {
        "id": 30,
        "question": "Can a new employee who has been with the company for only 2 months take paid parental leave?",
        "expected_answer": "I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly.",
        "source_filename": None,
        "source_page": None,
        "split": "test",
        "is_answerable": False,
    },
]


def find_page_for_anchor(pdf_path: Path, anchor: str) -> int:
    """Finds the 1-indexed page number containing the anchor text in the PDF."""
    doc = fitz.open(str(pdf_path))
    anchor_clean = anchor.lower().replace("\n", " ")
    for page_idx in range(len(doc)):
        page_text = doc[page_idx].get_text("text").lower().replace("\n", " ")
        if anchor_clean in page_text:
            doc.close()
            return page_idx + 1
    doc.close()
    raise ValueError(f"Anchor '{anchor}' not found in {pdf_path}")


def generate_questions_json():
    # Resolve paths relative to this file so it works from any working directory
    project_root = Path(__file__).resolve().parent.parent
    sample_dir = project_root / "sample_docs"
    eval_dir = project_root / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)

    final_questions = []

    for q in QUESTION_DEFINITIONS:
        q_copy = dict(q)
        if q_copy["is_answerable"]:
            filename = q_copy["source_filename"]
            pdf_path = sample_dir / filename
            anchor = q_copy.pop("anchor")
            page_num = find_page_for_anchor(pdf_path, anchor)
            q_copy["source_page"] = page_num
        else:
            q_copy.pop("anchor", None)

        final_questions.append(q_copy)

    out_file = eval_dir / "questions.json"
    out_file.write_text(json.dumps(final_questions, indent=2), encoding="utf-8")
    print(f"Generated {len(final_questions)} evaluation questions with verified page ground truth at: {out_file}")

    dev_count = sum(1 for q in final_questions if q["split"] == "dev")
    test_count = sum(1 for q in final_questions if q["split"] == "test")
    print(f"  - Dev Split: {dev_count} questions (used for threshold/chunking tuning)")
    print(f"  - Test Split: {test_count} questions (held-out out-of-sample evaluation)")


if __name__ == "__main__":
    generate_questions_json()
