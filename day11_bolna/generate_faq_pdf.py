"""
Generate Naveen Dental Clinic FAQ as PDF
for uploading to Bolna AI Knowledge Base.
"""
import os

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic_faq.pdf")

FAQ_TEXT = """
NAVEEN ADVANCED DENTAL CLINIC
Frequently Asked Questions

SERVICES
We offer general dentistry, root canal treatment, dental implants, teeth whitening,
orthodontics (braces and aligners), pediatric dentistry, and emergency dental care.

PRICING
- Consultation: Rs. 300
- Root canal treatment: Rs. 4,000 to Rs. 8,000 depending on tooth location
- Teeth cleaning: Rs. 800
- Tooth extraction: Rs. 1,000 to Rs. 2,500
- Dental implants: starting from Rs. 25,000 per tooth
- Teeth whitening: Rs. 3,500

CLINIC HOURS
We are open Monday to Saturday, 9:00 AM to 8:00 PM.
We are closed on Sundays.
Emergency cases are seen on a priority basis even outside regular hours
by calling our emergency line.

APPOINTMENTS
Appointments can be booked via phone call, WhatsApp, or walk-in.
We recommend booking at least one day in advance for non-emergency visits.
Walk-ins are accepted based on availability.

INSURANCE AND PAYMENT
We accept cash, UPI, credit/debit cards, and most major dental insurance plans.
EMI options are available for treatments above Rs. 15,000.

LOCATION
We are located in Vijayawada, Andhra Pradesh, with easy access and parking available.

EMERGENCY CARE
For dental emergencies like severe pain, broken teeth, or knocked-out teeth,
call our emergency line immediately.
We prioritize same-day appointments for emergency cases.

ABOUT ARIA
Aria is the AI receptionist for Naveen Advanced Dental Clinic.
Aria can help you with appointment information, pricing queries,
clinic hours, and general dental inquiries.
For bookings, please call the clinic directly or ask Aria to connect you.
"""

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        fontSize=18, textColor=colors.HexColor('#1a3d5c'),
        alignment=TA_CENTER, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER, spaceAfter=20
    )
    heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#1a3d5c'),
        spaceBefore=14, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=11, leading=18, textColor=colors.HexColor('#333333')
    )

    story = []

    story.append(Paragraph("Naveen Advanced Dental Clinic", title_style))
    story.append(Paragraph("AI Receptionist — Knowledge Base", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a3d5c')))
    story.append(Spacer(1, 16))

    sections = [
        ("SERVICES", [
            "We offer a full range of dental services including:",
            "- General dentistry and check-ups",
            "- Root canal treatment",
            "- Dental implants",
            "- Teeth whitening",
            "- Orthodontics (braces and aligners)",
            "- Pediatric dentistry",
            "- Emergency dental care",
        ]),
        ("PRICING", [
            "- Consultation: Rs. 300",
            "- Root canal treatment: Rs. 4,000 to Rs. 8,000 (depending on tooth location)",
            "- Teeth cleaning: Rs. 800",
            "- Tooth extraction: Rs. 1,000 to Rs. 2,500",
            "- Dental implants: Starting from Rs. 25,000 per tooth",
            "- Teeth whitening: Rs. 3,500",
        ]),
        ("CLINIC HOURS", [
            "Monday to Saturday: 9:00 AM to 8:00 PM",
            "Sunday: Closed",
            "Emergency cases are attended on priority even outside regular hours.",
        ]),
        ("APPOINTMENTS", [
            "Appointments can be booked via phone call, WhatsApp, or walk-in.",
            "We recommend booking at least one day in advance for non-emergency visits.",
            "Walk-ins are accepted based on availability.",
        ]),
        ("INSURANCE AND PAYMENT", [
            "We accept: Cash, UPI, Credit/Debit Cards, and major dental insurance plans.",
            "EMI options are available for treatments above Rs. 15,000.",
        ]),
        ("LOCATION", [
            "Naveen Advanced Dental Clinic",
            "Vijayawada, Andhra Pradesh",
            "Easy access with parking available.",
        ]),
        ("EMERGENCY CARE", [
            "For dental emergencies (severe pain, broken teeth, knocked-out teeth):",
            "Call our emergency line immediately.",
            "We prioritize same-day appointments for all emergency cases.",
        ]),
        ("ABOUT ARIA", [
            "Aria is our AI voice receptionist powered by advanced AI.",
            "Aria can help with: appointment information, pricing queries,",
            "clinic hours, services offered, and general dental inquiries.",
            "For confirmed bookings, please call the clinic directly.",
        ]),
    ]

    for heading, lines in sections:
        story.append(Paragraph(heading, heading_style))
        for line in lines:
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 8))

    doc.build(story)
    print(f"[OK] PDF created: {OUTPUT_PATH}")
    print(f"     Upload this file to Bolna → Knowledge Base → Upload PDF")

except ImportError:
    # Fallback: plain text file if reportlab not installed
    txt_path = OUTPUT_PATH.replace(".pdf", "_for_bolna.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(FAQ_TEXT)
    print(f"[OK] Text file created (reportlab not installed): {txt_path}")
    print(f"     Upload this as plain text to Bolna Knowledge Base → Add URL")
    print(f"     OR install reportlab: pip install reportlab")
