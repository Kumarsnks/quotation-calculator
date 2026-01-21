import base64
import textwrap
import time
import streamlit as st
from io import BytesIO
from xhtml2pdf import pisa
import os
from datetime import datetime
import math
from jinja2 import Environment, FileSystemLoader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USD_INR_RATE = 91.01

template_env = Environment(
    loader=FileSystemLoader(os.path.join(os.getcwd(), "templates"))
)
internal_template = template_env.get_template("internal_report.html")
client_template = template_env.get_template("client_report.html")


logo_path = os.path.join(BASE_DIR, "templates", "ormae_logo.png")
generated_on = datetime.now().strftime("%d %b %Y, %I:%M %p")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem !important;   /* default is ~6rem */
        }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns([2, 2, 1])

with col2:
    st.image(logo_path, width=200)


def add_milestone():
    st.session_state.milestones.append(
        {"name": f"Milestone {len(st.session_state.milestones) + 1}", "desc": "", "pct": 0.0}
    )


# Download PDF button
def generate_pdf_from_html(template_html: str):
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        src=template_html,
        dest=pdf_buffer,
        encoding="UTF-8"
    )

    if pisa_status.err:
        return None

    pdf_buffer.seek(0)
    return pdf_buffer


# ------------------ PAGE CONFIG ------------------
st.set_page_config(layout="wide")

# ------------------ STYLES ------------------
st.markdown("""
<style>
.section-divider {
    width: 100%;
    height: 5px;
    background: linear-gradient(
        to right,
        #d1d5db,
        #9ca3af,
        #d1d5db
    );
    border-radius: 10px;
    margin: 15px 0;
}

.big-total {
    font-size: 52px;
    font-weight: 700;
    color: #6aa84f;
}
.breakdown {
    display: flex;
    justify-content: space-around;
    margin-top: 1.5rem;
    font-weight: 600;
}
.breakdown div {
    text-align: center;
}
.estimate-text {
    margin-top: 1.8rem;
    font-size: 16px;
    font-weight: 600;
    color: #555;
}

}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; font-size:60px; margin-top:-40px;'>Quotation Calculator</h1>", unsafe_allow_html=True)

# ================== PROJECT DETAILS ==================
st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:left; font-size:30px;'> 📌 Project Details</h1>", unsafe_allow_html=True)

p1, p2 = st.columns([2, 1])
p1.markdown(
    "<div style='margin-bottom:0px; font-size:14px;'>"
    "Project Name <span style='color:red;'>*</span>"
    "</div>",
    unsafe_allow_html=True
)

p2.markdown(
    "<div style='margin-bottom:0px; font-size:14px;'>Client Type</div>",
    unsafe_allow_html=True
)

project_name = p1.text_input("Project Name", label_visibility="collapsed")
client_type = p2.selectbox(
    "Client Type",
    ["IND", "USA"],
    label_visibility="collapsed"
)

currency_symbol = "₹" if client_type == "IND" else "$"
if client_type == "IND":
    margin_divisor = 0.7
    conversion_rate = 1
else:
    margin_divisor = 0.5
    conversion_rate = 1 / USD_INR_RATE

project_description = st.text_area("Project Description", height=100)

# ================== ROLE MASTER ==================
ROLES = {
    "Data Engineer": {"comp": 1200000},
    "Senior Data Engineer": {"comp": 2000000},
    "Lead Data Engineer": {"comp": 2600000},
    "Software Developer": {"comp": 1200000},
    "Senior Software Developer": {"comp": 2000000},
    "Lead Software Developer": {"comp": 2600000},
    "Frontend Developer": {"comp": 1200000},
    "Senior Frontend Developer": {"comp": 2000000},
    "Lead Frontend Developer": {"comp": 2600000},
    "DevOps Engineer": {"comp": 2000000},
    "Data Scientist": {"comp": 1200000},
    "OR Scientist": {"comp": 1200000},
    "Project Manager": {"comp": 2600000}
}

# ================== SESSION STATE ==================
if "rows" not in st.session_state:
    st.session_state.rows = [0]

# ================== QUOTATION CARD ==================
st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

controls, spacer = st.columns([2, 9])

with controls:
    c1, c2 = st.columns(2)

    with c1:
        overhead_factor = st.number_input(
            "Overhead Factor",
            min_value=1.0,
            max_value=2.0,
            value=1.4,
            step=0.1,
            format="%.1f"
        )

    with c2:
        margin_factor_pct = st.selectbox(
            "Margin %",
            options=[10, 20, 30, 40, 50],
            index=2
        )

margin_factor = 1 - margin_factor_pct / 100

st.markdown(
    "<h1 style='text-align:left; font-size:30px;'> 🧮 Team Structure</h1>",
    unsafe_allow_html=True
)


# =========================== ROLES ====================================

headers = [
    "Role <span style='color:red;'>*</span>",
    "Count <span style='color:red;'>*</span>",
    "Hours <span style='color:red;'>*</span>",
    "Compensation",
    "Emp Cost / Hr",
    "Overhead / Hr",
    "Margin / Hr",
    "Total Hours",
    "Internal Cost",
    "Internal Cost + Overhead",
    "Margin"
]

cols = st.columns([2, 1, 0.8, 1, 1, 1, 1, 1, 1, 1, 1, 0.4])

for col, header in zip(cols, headers):
    col.markdown(f"**{header}**", unsafe_allow_html=True)

total_internal = 0
total_final = 0
total_margin = 0
total_duration = 0
total_resource = 0
remove_rows = []

for idx in range(len(st.session_state.rows)):
    c = st.columns([2, 1, 0.8, 1, 1, 1, 1, 1, 1, 1, 1, 0.4])

    selected_roles = [
        st.session_state.get(f"role_{i}")
        for i in range(len(st.session_state.rows))
        if i != idx
    ]
    available_roles = [""] + [r for r in ROLES if r not in selected_roles]

    role = c[0].selectbox("Role", available_roles, key=f"role_{idx}", label_visibility="collapsed")
    count = c[1].number_input("Count", min_value=0, step=1, key=f"count_{idx}", label_visibility="collapsed")
    hours = c[2].number_input("Hours", min_value=0, step=1, key=f"hours_{idx}", label_visibility="collapsed")

    if role:
        comp = ROLES[role]["comp"] * conversion_rate
    else:
        comp = emp = overhead = 0

    emp = comp / 2080
    overhead = emp * overhead_factor
    margin = overhead / margin_divisor
    total_hours = count * hours
    internal_cost = total_hours * emp
    final_amount = total_hours * overhead
    margin_amount = final_amount / margin_factor

    c[3].text(f"{currency_symbol}{comp:,.0f}")
    c[4].text(f"{currency_symbol}{emp:,.0f}")
    c[5].text(f"{currency_symbol}{overhead:,.0f}")
    c[6].text(f"{currency_symbol}{margin:,.0f}")
    c[7].text(f"{total_hours:,}")
    c[8].text(f"{currency_symbol}{internal_cost:,.0f}")
    c[9].text(f"{currency_symbol}{final_amount:,.0f}")
    c[10].text(f"{currency_symbol}{margin_amount:,.0f}")

    with c[11]:
        st.markdown("""
        <style>
        button[kind="secondary"] {
            margin: 0 !important;
            padding: 0px !important;
            background: transparent !important;
            border: none !important;
            font-size: 15px !important;
        }

        button[kind="secondary"]:hover {
            transform: scale(1.2);
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("🗑️", key=f"remove_{idx}"):
            remove_rows.append(idx)

    total_internal += internal_cost
    total_final += final_amount
    total_margin += margin_amount
    total_duration += total_hours
    total_resource += count

if remove_rows:
    for r in sorted(remove_rows, reverse=True):
        st.session_state.rows.pop(r)
    st.rerun()

# Get list of roles already selected
selected_roles = [st.session_state.get(f"role_{i}") for i in range(len(st.session_state.rows))]
available_roles = [r for r in ROLES if r not in selected_roles]

# Disable Add Role button if no roles left
disable_add_role = len(available_roles) == 0

st.button("➕ Add Role", on_click=lambda: st.session_state.rows.append(len(st.session_state.rows)),
          disabled=disable_add_role)


# =========================== DISCOUNT ===========================

disc_col, spacer = st.columns([1, 11])

with disc_col:
    discount_pct = st.number_input(
        "Discount %",
        min_value=0,
        max_value=100,
        step=5,
    )

discount_amount = total_margin * discount_pct / 100
final_after_discount = total_margin - discount_amount

# =============================== TOTAL AMOUNT TABLE =====================================
st.markdown(
    f"""
    <table style="
        width:40%;
        border-collapse:collapse;
        margin-top:14px;
        font-size:16px;
    ">
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Total Resource Count</td>
            <td style="padding:6px 8px; text-align:right;">
                {total_resource:,.0f}
            </td>
        </tr>
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Total Project Duration</td>
            <td style="padding:6px 8px; text-align:right;">
                {total_duration:,.0f} Hrs
            </td>
        </tr>
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Total Internal Cost</td>
            <td style="padding:6px 8px; text-align:right;">
                {currency_symbol}{total_internal:,.0f}
            </td>
        </tr>
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Total Internal Cost + Total Overhead</td>
            <td style="padding:6px 8px; text-align:right;">
                {currency_symbol}{total_final:,.0f}
            </td>
        </tr>
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Total Margin Cost</td>
            <td style="padding:6px 8px; text-align:right;">
                {currency_symbol}{total_margin:,.0f}
            </td>
        </tr>
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Offered Discount</td>
            <td style="padding:6px 8px; text-align:right;">
                {discount_pct:,}%
            </td>
        </tr>
        <tr>
            <td style="padding:6px 8px; font-weight:600;">Discounted Amount</td>
            <td style="padding:6px 8px; text-align:right;">
                {currency_symbol}{discount_amount:,.0f}
            </td>
        </tr>
        <tr>
            <td style="
                padding:10px 8px;
                font-weight:700;
                font-size:20px;
                border-top:2px solid #333;
            ">
                Total Project Amount
            </td>
            <td style="
                padding:10px 8px;
                text-align:right;
                font-size:26px;
                font-weight:800;
                color:#16a34a;
                border-top:2px solid #333;
            ">
                {currency_symbol}{final_after_discount:,.0f}
            </td>
        </tr>
    </table>
    """,
    unsafe_allow_html=True
)

st.markdown("</div>", unsafe_allow_html=True)

# =========================== MILESTONE ======================================================

if final_after_discount > 0 and not st.session_state.show_milestone:
    # Smaller button on the left
    btn_col_left, btn_col_right = st.columns([1, 10])  # Left column smaller, right column takes rest

    with btn_col_left:
        if st.button("Create Milestones", type="primary", use_container_width=False):
            st.session_state.show_milestone = True
            if not st.session_state.get("milestones"):
                st.session_state.milestones = [{"name": "Milestone 1", "desc": "", "pct": 0.0}]
            st.rerun()

if "show_milestone" not in st.session_state:
    st.session_state.show_milestone = False

if "milestones" not in st.session_state:
    st.session_state.milestones = [
        {"name": "Milestone 1", "desc": "", "pct": 0.0}
    ]

if st.session_state.show_milestone and final_after_discount > 0:

    h1, h2 = st.columns([1, 3])

    with h1:
        st.markdown("### 💎 Milestone Breakdown")

    total_placeholder = h2.empty()

    total_pct = 0
    success_placeholder = st.empty()

    for i, m in enumerate(st.session_state.milestones):
        c1, c2, c3, c4, c5 = st.columns([3, 4, 1, 2, 0.6])

        with c1:
            m["name"] = st.text_input(
                "Milestone Name",
                m["name"],
                key=f"ms_name_{i}"
            )
        with c2:
            m["desc"] = st.text_input(
                "Description",
                value="",
                placeholder="",
                key=f"ms_desc_{i}"
            )

        with c3:
            m["pct"] = st.number_input(
                "Percentage %",
                min_value=0,
                max_value=100,
                step=5,
                key=f"ms_pct_{i}"
            )

        with c4:
            amount = final_after_discount * m["pct"] / 100
            st.markdown(
                f"""
                <div style="font-weight:600; padding-top:28px; color:#16a34a;">
                    {currency_symbol}{amount:,.0f}
                </div>
                """,
                unsafe_allow_html=True
            )

        with c5:
            st.markdown("<div style='padding-top:22px;'>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"remove_ms_{i}"):
                if len(st.session_state.milestones) > 1:
                    # Remove only this milestone
                    st.session_state.milestones.pop(i)
                else:
                    # Last milestone → clear all
                    st.session_state.milestones = []
                    st.session_state.show_milestone = False
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        total_pct += m["pct"]

    color = "#16a34a" if total_pct == 100 else "#dc2626"

    # ➕ Add milestone
    if total_pct < 100:
        col_btn, col_total = st.columns([3, 1.5])

        with col_btn:
            st.button("➕ Add Milestone", on_click=add_milestone)

        with col_total:
            st.markdown(
                f"""
                    <div style="
                        text-align:left;
                        font-weight:700;
                        font-size:22px;
                        color:{color};
                        padding-top:10px;
                    ">
                        Total Allocated: {total_pct:.0f}%
                    </div>
                    """,
                unsafe_allow_html=True
            )
    # Success if 100%
    if total_pct == 100:
        success_placeholder.success("✅ Milestones allocated successfully")

    elif total_pct > 100:
        st.warning("⚠️ Total milestone percentage cannot exceed 100%")

# =================================== Data for PDF ==========================================================

# Prepare roles data
HOURS_PER_DAY = 8
roles_data = []
total_project_hours = 0
total_manpower = 0

for idx in range(len(st.session_state.rows)):
    role = st.session_state.get(f"role_{idx}")
    if role:
        count = st.session_state.get(f"count_{idx}", 0)
        hours = st.session_state.get(f"hours_{idx}", 0)

        comp = ROLES[role]["comp"] * conversion_rate
        emp = comp / 2080
        overhead = emp * overhead_factor
        margin_rate = overhead / margin_divisor
        total_hours = count * hours
        internal_cost = total_hours * emp
        final_amount = total_hours * overhead
        margin_amount = final_amount / margin_factor

        role_total_hours = count * hours
        total_project_hours += role_total_hours
        total_manpower += count

        roles_data.append({
            "Role": role,
            "Count": count,
            "Hours": hours,
            "Margin": margin_rate,
            "Margin_Amount": margin_amount
        })

total_project_days = math.ceil(total_project_hours / HOURS_PER_DAY)


# Prepare milestone data
milestone_data = []
if st.session_state.show_milestone and st.session_state.milestones:
    rounded_project_total = int(round(final_after_discount))
    percentages = [m["pct"] for m in st.session_state.milestones]
    milestone_count = len(percentages)
    milestone_amounts = []

    # Handle rounding
    running_total = 0
    for i, pct in enumerate(percentages):
        if i < milestone_count - 1:
            amt = round(rounded_project_total * pct / 100)
            milestone_amounts.append(amt)
            running_total += amt
        else:
            milestone_amounts.append(rounded_project_total - running_total)

    for i, m in enumerate(st.session_state.milestones):
        milestone_data.append({
            "Name": m["name"],
            "Description": m["desc"],
            "Percentage": m["pct"],
            "Amount": milestone_amounts[i]
        })

# =========================== UPLOAD DOCUMENTS ===========================
st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
st.markdown("### 📎 Upload Documents")

# ---------- Initialize session state ----------
if "user_doc" not in st.session_state:
    st.session_state.user_doc = None

if "functional_doc" not in st.session_state:
    st.session_state.functional_doc = None


st.markdown("**User Requirement Document**")
u1, u2 = st.columns([3, 4])

with u1:
    user_doc = st.file_uploader(
        "User Requirement Document",
        type=["pdf", "doc", "docx"],
        key="user_doc_uploader",
        label_visibility="collapsed"
    )
    if user_doc:
        st.session_state.user_doc = user_doc

# with u2:
st.markdown("**Functional Requirement Document**")

col1, col2 = st.columns([3, 4])   # adjust ratio to control width

with col1:
    functional_doc = st.file_uploader(
        "Functional Requirement Document",
        type=["pdf", "doc", "docx"],
        key="functional_doc_uploader",
        label_visibility="collapsed"
    )
    if functional_doc:
        st.session_state.user_doc = functional_doc

st.markdown("</div>", unsafe_allow_html=True)

# =========================== VALIDATION ===========================
has_project_name = bool(project_name.strip())

has_valid_role = any(
    st.session_state.get(f"role_{i}")
    for i in range(len(st.session_state.rows))
)

milestones_valid = (
        not st.session_state.show_milestone
        or sum(m["pct"] for m in st.session_state.milestones) == 100
)

can_download = (
        has_project_name
        and has_valid_role
        and total_project_hours > 0
        and milestones_valid
)

if can_download:
    rendered_html = internal_template.render(
        generated_on=generated_on,
        logo_path=logo_path,
        project_name=project_name,
        project_description=project_description,
        total_project_hours=total_project_hours,
        total_project_days=total_project_days,
        total_internal=total_internal,
        total_final=total_final,
        total_margin=total_margin,
        discount_pct=discount_pct,
        discount_amount=discount_amount,
        final_after_discount=final_after_discount,
        total_manpower=total_manpower,
        roles_data=roles_data,
        milestone_data=milestone_data,
        currency_symbol=currency_symbol,
        user_doc=st.session_state.user_doc,
        functional_doc=st.session_state.functional_doc
    )

    internal_buffer = generate_pdf_from_html(rendered_html)

    # ---------- CLIENT REPORT ----------
    client_html = client_template.render(
        logo_path=logo_path,
        project_name=project_name,
        project_description=project_description,
        total_project_hours=total_project_hours,
        total_project_days=total_project_days,
        total_margin=total_margin,
        discount_pct=discount_pct,
        final_after_discount=final_after_discount,
        total_manpower=total_manpower,
        roles_data=roles_data,
        milestone_data=milestone_data,
        currency_symbol=currency_symbol,
        user_doc=st.session_state.user_doc,
        functional_doc=st.session_state.functional_doc
    )

    client_buffer = generate_pdf_from_html(client_html)

    if internal_buffer and client_buffer:
        internal_pdf_base64 = base64.b64encode(internal_buffer.getvalue()).decode('utf-8')
        client_pdf_base64 = base64.b64encode(client_buffer.getvalue()).decode('utf-8')

        st.markdown(
            f"""
                <div style="display:flex; justify-content:left; margin-top:10px;">
                    <a href="data:application/pdf;base64,{internal_pdf_base64}" 
                       download="{project_name} Internal Quotation.pdf"
                       style="
                           text-decoration:none;
                           border:2px solid #2563eb;
                           background:#2563eb;
                           color:white;
                           padding:8px 20px;
                           border-radius:8px;
                           font-size:16px;
                           font-weight:600;
                           cursor:pointer;
                       ">
                        📄 Generate Internal Report
                    </a>
                </div>
                """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
                <div style="display:flex; justify-content:left; margin-top:10px;">
                    <a href="data:application/pdf;base64,{client_pdf_base64}" 
                       download="{project_name} Client Quotation.pdf"
                       style="
                           text-decoration:none;
                           border:2px solid #2563eb;
                           background:#2563eb;
                           color:white;
                           padding:8px 20px;
                           border-radius:8px;
                           font-size:16px;
                           font-weight:600;
                           cursor:pointer;
                       ">
                        📄 Generate Client Report
                    </a>
                </div>
                """,
            unsafe_allow_html=True
        )

st.markdown(
    "<div style='margin-top:40px; font-size:13px; color:#555;'>"
    "<span style='color:red;'>*</span> indicates required fields"
    "</div>",
    unsafe_allow_html=True
)
