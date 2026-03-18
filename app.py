import streamlit as st
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os

# --- 1. FONT SYSTEM ---
def get_arial_bold():
    paths = [
        "C:/Windows/Fonts/arialbd.ttf", 
        "/Library/Fonts/Arial Bold.ttf", 
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    ]
    for path in paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("Arial-Bold", path))
            return "Arial-Bold"
    return "Helvetica-Bold"

# --- 2. VALIDATION LOGIC ---
def validate_row(row):
    """Checks Col C for required u15a/u25a sizing codes."""
    code = str(row.iloc[2]).lower().strip()
    if "u15a" in code or "u25a" in code:
        return "✅ Ready"
    return "❌ Error: Missing Size Code"

# --- 3. ARTWORK GENERATOR (24" Wide with 0.25" Radius) ---
def generate_production_pdf(df):
    buffer = io.BytesIO()
    page_w, page_h = 24 * inch, 36 * inch 
    margin, gap = 0.5 * inch, 0.25 * inch
    corner_radius = 0.25 * inch
    font_name = get_arial_bold()
    
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))
    curr_x, curr_y = margin, page_h - margin
    
    ready_df = df[df['Status'] == "✅ Ready"]
    
    for _, row in ready_df.iterrows():
        try:
            qty = int(row.iloc[0])        # Col A: QTY
            text = str(row.iloc[1])[:15]  # Col B: Inscription
            code = str(row.iloc[2]).lower() # Col C: Part Number (Size Logic)
            
            # Sizing from Code
            if "u25a" in code:
                label_h, font_size = 2.5 * inch, 144 # 2" text
            else:
                label_h, font_size = 1.5 * inch, 72  # 1" text

            # Width Rule: 0.5" + (1.5" * Chars)
            label_w = (0.5 + (1.5 * len(text))) * inch

            for _ in range(qty):
                if curr_x + label_w > (page_w - margin):
                    curr_x = margin
                    curr_y -= (label_h + gap)
                
                if curr_y - label_h < margin:
                    c.showPage()
                    curr_x, curr_y = margin, page_h - margin
                
                draw_y = curr_y - label_h

                # Draw Label with 0.25" Rounded Corners
                # 1. Background Fill (Yellow)
                c.setFillColorRGB(1, 1, 0)
                c.roundRect(curr_x, draw_y, label_w, label_h, corner_radius, stroke=0, fill=1)
                
                # 2. 1pt Black Border
                c.setStrokeColorRGB(0, 0, 0)
                c.setLineWidth(1)
                c.roundRect(curr_x, draw_y, label_w, label_h, corner_radius, stroke=1, fill=0)
                
                # 3. Centered Arial Bold Text
                c.setFillColorRGB(0, 0, 0)
                c.setFont(font_name, font_size)
                text_x = curr_x + (label_w / 2)
                text_y = draw_y + (label_h / 2) - (font_size / 4)
                c.drawCentredString(text_x, text_y, text)

                curr_x += (label_w + gap)
            
            # Reset Row for next Excel entry
            curr_x = margin
            curr_y -= (label_h + gap)
        except: continue
            
    c.save()
    buffer.seek(0)
    return buffer

# --- 4. CHECKLIST GENERATOR ---
def generate_checklist_pdf(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=40, bottomMargin=40)
    elements = []
    data = [["DONE", "QTY", "INSCRIPTION", "PART NUMBER"]]
    ready_df = df[df['Status'] == "✅ Ready"]
    for _, row in ready_df.iterrows():
        data.append(["[  ]", str(row.iloc[0]), str(row.iloc[1]), str(row.iloc[2])])

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ])

    table = Table(data, colWidths=[0.7*inch, 0.7*inch, 4.3*inch, 1.8*inch], repeatRows=1)
    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- 5. STREAMLIT UI ---
st.set_page_config(page_title="Production Suite", layout="wide")
st.title("🏭 Production Label & Checklist Suite")

file = st.file_uploader("Upload Excel File", type=['xlsx', 'xls'])

if file:
    if 'df' not in st.session_state:
        df = pd.read_excel(file)
        df.insert(0, 'Status', df.apply(validate_row, axis=1))
        st.session_state.df = df

    st.subheader("1. Verify and Edit Data")
    edited = st.data_editor(st.session_state.df, use_container_width=True, hide_index=True)
    
    # Live Re-Validation
    edited['Status'] = edited.iloc[:, 1:].apply(validate_row, axis=1)
    st.session_state.df = edited

    st.subheader("2. Production Downloads")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate 24\" Artwork PDF"):
            art = generate_production_pdf(edited)
            st.download_button("📥 Download Artwork", art, "label_artwork.pdf")
    with c2:
        if st.button("Generate 8.5\" Checklist PDF"):
            chk = generate_checklist_pdf(edited.iloc[:, 1:])
            st.download_button("📥 Download Checklist", chk, "checklist.pdf")