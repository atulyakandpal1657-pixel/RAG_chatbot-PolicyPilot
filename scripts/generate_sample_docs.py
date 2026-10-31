import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_header_footer(canvas, doc, doc_title: str):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#4A5568"))
    # Header
    canvas.drawString(54, 750, f"NORTHWIND LABS  |  {doc_title.upper()}")
    canvas.setStrokeColor(colors.HexColor("#CBD5E0"))
    canvas.setLineWidth(0.5)
    canvas.line(54, 742, 558, 742)

    # Footer
    page_num = canvas.getPageNumber()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(54, 36, "CONFIDENTIAL  -  FOR INTERNAL EMPLOYEES ONLY")
    canvas.drawRightString(558, 36, f"Page {page_num}")
    canvas.line(54, 48, 558, 48)
    canvas.restoreState()


def build_employee_handbook(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2C5282"),
        spaceAfter=8,
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("Northwind Labs Employee Handbook", title_style))
    story.append(Paragraph("Version 4.2  |  Effective January 1, 2026", callout_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Welcome & Workplace Principles", h2_style))
    story.append(
        Paragraph(
            "Welcome to Northwind Labs! We are committed to fostering a collaborative, ethical, and inclusive environment. "
            "Employment at Northwind Labs is at-will, meaning either you or Northwind Labs may terminate the employment relationship at any time, "
            "with or without cause or prior notice. All workplace decisions adhere to equal employment opportunity principles.",
            body_style,
        )
    )

    story.append(Paragraph("2. Onboarding & 90-Day Probationary Period", h2_style))
    story.append(
        Paragraph(
            "All new hires undergo an initial 90-calendar-day probationary period. During this period, performance and cultural fit "
            "are reviewed at 30, 60, and 90-day intervals with your manager. Satisfactory completion of the 90-day probationary period "
            "confirms regular full-time status and activates full eligibility for tuition assistance.",
            body_style,
        )
    )

    story.append(Paragraph("3. Working Hours & Core Collaboration Hours", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs maintains standard 40-hour workweeks for full-time employees. All full-time employees are required to be "
            "accessible and available during core collaborative hours from 10:00 AM to 4:00 PM EST, Monday through Friday. "
            "Flexible start times between 7:30 AM and 10:00 AM EST are permitted with prior team manager approval.",
            body_style,
        )
    )

    # Page Break to Page 2
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("Northwind Labs Employee Handbook", title_style))
    story.append(Paragraph("4. Remote Work & Hybrid Telecommuting Policy", h2_style))
    story.append(
        Paragraph(
            "Employees in eligible hybrid roles may work remotely up to 2 days per week, coordinated directly with their department lead "
            "(customarily scheduled on Tuesdays and Thursdays). Remote employees must maintain a dedicated private workspace and an "
            "internet connection with a verified minimum download speed of 50 Mbps. Company laptops must remain within the continental "
            "United States unless formal international travel clearance has been authorized by IT and HR.",
            body_style,
        )
    )

    story.append(Paragraph("5. Paid Time Off (PTO) & Vacation Accrual", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs values work-life balance and provides generous paid vacation for full-time staff. "
            "New employees accrue 18 days of paid vacation per year, calculated at a rate of 1.5 days per month of active service. "
            "Annual vacation accrual increases to 22 days per year upon completing 3 years of continuous service, and 25 days per year "
            "after 5 years. Vacation requests exceeding 3 consecutive days must be submitted through BambooHR at least 2 weeks in advance. "
            "A maximum of 5 unused vacation days may be rolled over into the subsequent calendar year; any excess unused days expire on December 31.",
            body_style,
        )
    )

    story.append(Paragraph("6. Company Paid Holidays", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs observes 11 paid company holidays each calendar year, including New Year's Day, Martin Luther King Jr. Day, "
            "Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving Day, the day following Thanksgiving, Christmas Eve, "
            "Christmas Day, and one floating cultural holiday of employee choice.",
            body_style,
        )
    )

    # Page Break to Page 3
    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("Northwind Labs Employee Handbook", title_style))
    story.append(Paragraph("7. Paid Sick Leave Policy", h2_style))
    story.append(
        Paragraph(
            "All full-time employees receive 10 paid sick days per year, credited upfront on January 1 of each calendar year. "
            "Sick leave may be utilized for personal physical or mental illness, medical appointments, or to care for an immediate family member. "
            "Unused sick days do not roll over from year to year and are not paid out upon separation of employment. "
            "Consecutive sick leave absences exceeding 3 business days require documentation from a licensed healthcare provider.",
            body_style,
        )
    )

    story.append(Paragraph("8. Parental Leave Policy", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs provides 12 weeks of fully paid parental leave for primary caregivers following the birth, adoption, or foster placement "
            "of a child. Secondary caregivers are entitled to 6 weeks of fully paid parental leave. "
            "To qualify, employees must have completed a minimum of 6 months of continuous full-time service prior to the qualifying event. "
            "Parental leave must be taken within the first 12 months of the child's arrival and may be taken continuously or in two separate blocks.",
            body_style,
        )
    )

    story.append(Paragraph("9. Medical & Family Leave (FMLA)", h2_style))
    story.append(
        Paragraph(
            "Employees with at least 12 months of service who have worked at least 1,250 hours during the previous 12 months are eligible for "
            "up to 12 weeks of unpaid, job-protected leave under the Family and Medical Leave Act (FMLA) for qualifying family and medical emergencies.",
            body_style,
        )
    )

    # Page Break to Page 4
    story.append(PageBreak())

    # ================= PAGE 4 =================
    story.append(Paragraph("Northwind Labs Employee Handbook", title_style))
    story.append(Paragraph("10. Bereavement Leave", h2_style))
    story.append(
        Paragraph(
            "Employees are eligible for up to 5 consecutive paid business days for the death of an immediate family member (spouse, domestic partner, "
            "child, parent, or sibling). Up to 3 consecutive paid business days are granted for the death of extended family members (grandparent, grandchild, "
            "aunt, uncle, or cousin). Additional unpaid leave may be granted upon request to HR.",
            body_style,
        )
    )

    story.append(Paragraph("11. Jury Duty & Civic Obligations", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs provides up to 2 weeks (10 business days) of fully paid leave for employees summoned to jury duty service. "
            "Employees must provide a copy of the official court summons to HR within 48 hours of receipt. "
            "Employees are also granted up to 2 hours of paid time off to vote in local, state, or federal elections if polls are not open "
            "for 2 consecutive hours outside their normal work shift.",
            body_style,
        )
    )

    story.append(Paragraph("12. Voluntary Resignation & Notice Period", h2_style))
    story.append(
        Paragraph(
            "To ensure continuity of operations, non-exempt hourly employees are requested to provide a minimum of 2 weeks written notice "
            "prior to resignation. Exempt professional, managerial, and executive employees are expected to provide 4 weeks written notice. "
            "Final paychecks, including accrued unused vacation pay (subject to rollover limits), are disbursed in accordance with state statutory requirements.",
            body_style,
        )
    )

    doc.build(
        story,
        onFirstPage=lambda c, d: create_header_footer(c, d, "Employee Handbook"),
        onLaterPages=lambda c, d: create_header_footer(c, d, "Employee Handbook"),
    )


def build_benefits_guide(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2C5282"),
        spaceAfter=8,
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("Northwind Labs Benefits Guide", title_style))
    story.append(Paragraph("Plan Year 2026  |  Total Rewards & Health Overview", callout_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Health & Medical Coverage Plans", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs provides comprehensive medical coverage through BlueCross BlueShield with two plan options: "
            "the Premier PPO Plan and the High Deductible Health Plan (HDHP) with HSA. Northwind Labs covers 85% of monthly employee premiums "
            "and 75% of dependent premiums across both plans.",
            body_style,
        )
    )

    story.append(Paragraph("2. Premier PPO Medical Plan", h2_style))
    story.append(
        Paragraph(
            "Under the Premier PPO Plan, the individual annual in-network deductible is $500, and the family deductible is $1,000. "
            "In-network primary care office visits require a $25 copay, specialist visits require a $40 copay, and urgent care visits require a $50 copay. "
            "Generic prescription drugs carry a $10 copay, preferred brand names carry a $30 copay, and specialty medications carry a $60 copay. "
            "Annual out-of-pocket maximums are capped at $3,000 for individual coverage and $6,000 for family coverage.",
            body_style,
        )
    )

    story.append(Paragraph("3. High Deductible Health Plan (HDHP) & HSA Contribution", h2_style))
    story.append(
        Paragraph(
            "The HDHP features an annual in-network deductible of $1,500 for individuals and $3,000 for families. "
            "To support participants, Northwind Labs contributes $750 per year to an individual Health Savings Account (HSA) and $1,500 per year "
            "for family coverage, deposited in equal quarterly installments on the first payroll of each calendar quarter. "
            "HSA funds roll over indefinitely and are 100% owned by the employee.",
            body_style,
        )
    )

    # Page Break to Page 2
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("Northwind Labs Benefits Guide", title_style))
    story.append(Paragraph("4. Dental Insurance via Delta Dental", h2_style))
    story.append(
        Paragraph(
            "Dental benefits are administered through Delta Dental PPO. Preventive care (cleanings, cleanings every 6 months, routine x-rays) "
            "is covered at 100% with no deductible. Basic restorative procedures (cavity fillings, extractions) are covered at 80% after a $50 deductible. "
            "Major services (crowns, bridges, dentures) are covered at 50%. The annual maximum dental benefit is $2,000 per insured member. "
            "Orthodontic treatment is covered at 50% with a separate lifetime maximum benefit of $1,500 for dependent children under age 19.",
            body_style,
        )
    )

    story.append(Paragraph("5. Vision Insurance via VSP", h2_style))
    story.append(
        Paragraph(
            "Vision care is insured through VSP Choice. Annual eye exams are covered in full after a $10 copay. "
            "Prescription eyeglass lenses are covered after a $25 materials copay. Northwind members receive an annual $200 frame allowance, "
            "plus a 20% discount on any frame costs exceeding $200. Elective contact lenses receive a $200 annual allowance in lieu of eyeglass lenses.",
            body_style,
        )
    )

    story.append(Paragraph("6. Life and Disability Insurance", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs provides basic life insurance and Accidental Death & Dismemberment (AD&D) equal to 2x annual base salary at no cost "
            "to the employee, up to a maximum benefit of $500,000. Short-term disability insurance replaces 60% of weekly pre-disability base salary "
            "up to $2,000/week for up to 26 weeks, starting on the 8th day of disability. Long-term disability replaces 60% of monthly salary up to $10,000/month "
            "after a 180-day elimination period.",
            body_style,
        )
    )

    # Page Break to Page 3
    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("Northwind Labs Benefits Guide", title_style))
    story.append(Paragraph("7. 401(k) Retirement Savings & Employer Matching", h2_style))
    story.append(
        Paragraph(
            "Our 401(k) retirement plan is administered through Fidelity Investments. Northwind Labs offers a 100% employer match on employee "
            "contributions up to 5% of eligible annual base salary. For instance, if you contribute 5% of your salary, Northwind matches another 5%, "
            "effectively doubling your savings. Employees may contribute on a pre-tax traditional 401(k) basis or after-tax Roth basis. "
            "Crucially, employer matching contributions feature 100% immediate vesting from day one of employment—there is no vesting schedule.",
            body_style,
        )
    )

    story.append(Paragraph("8. Wellness & Fitness Monthly Stipend", h2_style))
    story.append(
        Paragraph(
            "To support holistic health, Northwind Labs provides a taxable wellness reimbursement stipend of $75 per month ($900 annual maximum). "
            "Eligible expenses include commercial gym memberships, fitness studio classes (e.g., yoga, pilates, crossfit), sports league registration fees, "
            "personal athletic equipment, and digital mindfulness app subscriptions (such as Headspace or Calm). "
            "Reimbursement receipts must be submitted via Expensify by the 20th of each calendar month.",
            body_style,
        )
    )

    story.append(Paragraph("9. Flexible Spending Accounts (FSA)", h2_style))
    story.append(
        Paragraph(
            "Employees not enrolled in the HDHP/HSA plan may participate in a Healthcare Flexible Spending Account (FSA) up to the IRS annual limit ($3,200). "
            "A Dependent Care FSA is also available up to $5,000 per household annually for qualifying child care or elder care expenses.",
            body_style,
        )
    )

    # Page Break to Page 4
    story.append(PageBreak())

    # ================= PAGE 4 =================
    story.append(Paragraph("Northwind Labs Benefits Guide", title_style))
    story.append(Paragraph("10. Tuition & Professional Learning Reimbursement", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs invests actively in team skill development, offering up to $5,250 per calendar year in tuition and educational reimbursement. "
            "Eligible expenses include undergraduate and graduate courses at accredited academic institutions, professional technical certifications "
            "(e.g., AWS, Azure, PMP, CISSP), and approved industry conference admissions. "
            "To qualify for reimbursement, coursework must be pre-approved by your manager and HR prior to enrollment, and you must achieve a grade of 'B' "
            "or better (or 'Pass' in pass/fail grading).",
            body_style,
        )
    )

    story.append(Paragraph("11. Commuter & Transit Assistance", h2_style))
    story.append(
        Paragraph(
            "Employees may elect pre-tax payroll deductions up to $150 per month for qualified public transit passes, train fares, vanpools, and workplace parking. "
            "In addition, employees who regularly bicycle to work are eligible for an annual $100 bicycle tune-up and maintenance reimbursement credit.",
            body_style,
        )
    )

    story.append(Paragraph("12. Employee Assistance Program (EAP) via Lyra Health", h2_style))
    story.append(
        Paragraph(
            "Emotional well-being support is available 24 hours a day, 365 days a year through Lyra Health. "
            "Employees and their immediate household members are entitled to up to 6 confidential, fully covered mental health counseling sessions "
            "per issue per calendar year, accessible via in-person visits or secure video consultations.",
            body_style,
        )
    )

    doc.build(
        story,
        onFirstPage=lambda c, d: create_header_footer(c, d, "Benefits Guide"),
        onLaterPages=lambda c, d: create_header_footer(c, d, "Benefits Guide"),
    )


def build_code_of_conduct_and_it_security(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2C5282"),
        spaceAfter=8,
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("Northwind Labs Code of Conduct & IT Security", title_style))
    story.append(Paragraph("Revision 3.1  |  Compliance & Information Assurance", callout_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Standards of Ethical Business Conduct", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs operates on foundational pillars of honesty, legal compliance, and unwavering ethical standards. "
            "Employees must strictly avoid any activities or relationships that present a conflict between personal interests and company duties. "
            "Secondary employment, outside consulting, or commercial board seats require prior written disclosure and formal authorization from "
            "the Chief Legal Officer.",
            body_style,
        )
    )

    story.append(Paragraph("2. Gifts, Hospitality, and Entertainment Policy", h2_style))
    story.append(
        Paragraph(
            "Employees are strictly prohibited from accepting personal gifts, entertainment, or meals from vendors, clients, or competitors "
            "that exceed $50 in estimated fair market value. Any business gift or meal valued between $25 and $50 must be reported and logged "
            "in the Northwind Compliance Portal within 5 business days of receipt. "
            "Cash, gift cards, prepaid debit cards, or cryptocurrency gifts of any value are unconditionally prohibited under all circumstances.",
            body_style,
        )
    )

    story.append(Paragraph("3. Equal Treatment & Anti-Harassment Standards", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs enforces zero tolerance for discrimination, harassment, or bullying based on race, sex, age, religion, disability, "
            "gender identity, or sexual orientation. Every employee is expected to treat coworkers, clients, and partners with dignity and professional respect.",
            body_style,
        )
    )

    # Page Break to Page 2
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("Northwind Labs Code of Conduct & IT Security", title_style))
    story.append(Paragraph("4. Whistleblower Protection & Non-Retaliation Policy", h2_style))
    story.append(
        Paragraph(
            "Northwind Labs fosters an open reporting culture. Employees who report suspected financial fraud, safety hazards, unlawful acts, "
            "or code of conduct violations in good faith are protected from any form of retaliation, demotion, termination, or harassment. "
            "Reports may be submitted 24/7 on a completely anonymous basis via the Northwind Ethics Hotline at 1-800-555-NWND (1-800-555-6963) "
            "or through our secure web portal at ethics.northwindlabs.com. Any manager found engaging in retaliation will face immediate termination.",
            body_style,
        )
    )

    story.append(Paragraph("5. Confidentiality & Intellectual Property", h2_style))
    story.append(
        Paragraph(
            "All proprietary research, source code, algorithm models, product blueprints, customer datasets, and strategic roadmaps developed at "
            "Northwind Labs represent exclusive company property. Proprietary information must never be copied, transferred to personal accounts, "
            "or uploaded to third-party public AI services. Non-disclosure obligations persist indefinitely following departure from the company.",
            body_style,
        )
    )

    story.append(Paragraph("6. Social Media & Public Communications", h2_style))
    story.append(
        Paragraph(
            "Only designated corporate communications spokespersons are authorized to speak to the media or post official announcements on behalf of "
            "Northwind Labs. Personal social media commentary regarding company business must include the explicit disclaimer: 'Opinions expressed are solely my own.'",
            body_style,
        )
    )

    # Page Break to Page 3
    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("Northwind Labs Code of Conduct & IT Security", title_style))
    story.append(Paragraph("7. Password & Authentication Security Standards", h2_style))
    story.append(
        Paragraph(
            "All employee domain and application credentials must adhere to strict corporate security requirements: "
            "Passwords must contain a minimum length of 14 characters, combining uppercase letters, lowercase letters, numbers, and at least one special symbol. "
            "Passwords must be rotated every 90 days and cannot be reused within 10 password change cycles. "
            "Multi-Factor Authentication (MFA) is strictly mandatory for all systems using Okta Verify push notifications or hardware FIDO2 keys (YubiKey). "
            "SMS/text-based 2FA is explicitly banned due to SIM-swap vulnerabilities.",
            body_style,
        )
    )

    story.append(Paragraph("8. Clean Desk & Physical Workplace Security", h2_style))
    story.append(
        Paragraph(
            "Employees must manually lock their computer workstations (Windows Key + L or Command + Control + Q) whenever leaving their desk. "
            "All corporate laptops are enforced with automatic screensaver locks requiring password reentry after 5 minutes of inactivity. "
            "Under our clean desk policy, all sensitive hardcopy documents, whiteboard notes, removable media, and security keycards must be locked "
            "in desk drawers or filing cabinets prior to departing the office at the end of each workday.",
            body_style,
        )
    )

    story.append(Paragraph("9. Wireless Network Security", h2_style))
    story.append(
        Paragraph(
            "While traveling or working remotely, connecting company laptops to public, unsecured Wi-Fi networks (e.g., airports, coffee shops, hotels) "
            "without an active Northwind GlobalProtect VPN session is strictly forbidden.",
            body_style,
        )
    )

    # Page Break to Page 4
    story.append(PageBreak())

    # ================= PAGE 4 =================
    story.append(Paragraph("Northwind Labs Code of Conduct & IT Security", title_style))
    story.append(Paragraph("10. Security Incident Reporting & Response", h2_style))
    story.append(
        Paragraph(
            "Rapid incident response is vital to preserving organizational cyber defense. Any employee who discovers or suspects a security breach, "
            "compromised password, phishing click, malware infection, unauthorized data access, or lost/stolen hardware device must report it "
            "immediately to the IT Security Operations Center (SOC). "
            "Reports must be sent to security@northwindlabs.com or reported via telephone to the Emergency Security Hotline (ext. 4357 / HELP) "
            "within a strict maximum window of 2 hours from discovery. Failure to report a known compromise within 2 hours is grounds for disciplinary action.",
            body_style,
        )
    )

    story.append(Paragraph("11. Device Management & Removable Media Policy", h2_style))
    story.append(
        Paragraph(
            "All company-issued laptops are managed via centralized endpoint detection and response (EDR) software. "
            "The use of external USB flash drives, unapproved external hard drives, and SD memory cards is disabled by default on all company workstations. "
            "If external storage is required for business purposes, an encrypted company-issued drive must be requested through IT Helpdesk.",
            body_style,
        )
    )

    story.append(Paragraph("12. Mobile Device & BYOD Rules", h2_style))
    story.append(
        Paragraph(
            "Employees accessing company email, Slack, or corporate networks on personal mobile devices must enroll their device in Microsoft Intune "
            "Mobile Device Management (MDM). Enrolled devices must enforce biometric or PIN lock and allow remote company data wipe upon loss or termination. "
            "Jailbroken or rooted smartphones are strictly barred from accessing company systems.",
            body_style,
        )
    )

    doc.build(
        story,
        onFirstPage=lambda c, d: create_header_footer(c, d, "Code of Conduct & IT Security"),
        onLaterPages=lambda c, d: create_header_footer(c, d, "Code of Conduct & IT Security"),
    )


def generate_all_sample_docs():
    # Resolve output directory relative to this file, not the caller's CWD
    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "sample_docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    handbook_path = output_dir / "Northwind_Labs_Employee_Handbook.pdf"
    benefits_path = output_dir / "Northwind_Labs_Benefits_Guide.pdf"
    conduct_path = output_dir / "Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf"

    print("Generating Northwind Labs Employee Handbook...")
    build_employee_handbook(handbook_path)
    print(f"Generated: {handbook_path}")

    print("Generating Northwind Labs Benefits Guide...")
    build_benefits_guide(benefits_path)
    print(f"Generated: {benefits_path}")

    print("Generating Northwind Labs Code of Conduct & IT Security...")
    build_code_of_conduct_and_it_security(conduct_path)
    print(f"Generated: {conduct_path}")


if __name__ == "__main__":
    generate_all_sample_docs()
