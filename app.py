# -*- coding: utf-8 -*-
"""
برنامج قياساتي - النسخة التجريبية للويب (Qiyasati Web)
نظام متكامل لإدارة قياسات وتكاليف المطابخ وغرف النوم والخزائن والديكورات
مزود بنظام تسجيل دخول، فترة تجريبية 30 يوماً، ونظام اشتراكات مدفوعة (6 أشهر / 12 شهراً)
"""

import streamlit as st
import pandas as pd
import json
import os
import hashlib
import random
import string
from datetime import datetime, date, timedelta
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# -------------------------------------------------------------
# إعدادات الصفحة
# -------------------------------------------------------------
st.set_page_config(
    page_title="قياساتي - لوحة التحكم والاشتراكات",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# مسار ملف حفظ البيانات المحلي داخل مجلد التطبيق
# -------------------------------------------------------------
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qiyasati_data.json")

# بيانات طرق الدفع الثابتة
PAYMENT_INFO = {
    "mastercard": "5213 7204 8618 5601",
    "fastpay": "+964 7504147893",
    "fib": "+964 7504147893",
    "local_account": "6034978400",
    "whatsapp": "9647504147893"
}

# -------------------------------------------------------------
# دوال التشفير وتوليد أكواد التفعيل
# -------------------------------------------------------------
SECRET_KEY = "QIYASATI_WEB_SECURE_KEY_2026"
ADMIN_PIN = "9988"  # رمز لوحة المالك لتوليد أكواد المشتركين

def hash_password(password: str) -> str:
    return hashlib.sha256((password + SECRET_KEY).encode("utf-8")).hexdigest()

def generate_trial_code(contact: str) -> str:
    h = hashlib.md5((contact + "TRIAL" + SECRET_KEY).encode("utf-8")).hexdigest()[:6].upper()
    return f"TR30-{h}"

def generate_paid_code(months: int, note: str = "") -> str:
    """توليد كود تفعيل معتمد لـ 6 أشهر أو 12 شهراً"""
    prefix = "QY6M" if months == 6 else "QY12M"
    stamp = datetime.now().strftime("%f")[:4]
    token = hashlib.sha256((prefix + stamp + note + SECRET_KEY).encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{token[:4]}-{token[4:]}"

def verify_and_apply_activation_code(code: str, user_dict: dict) -> tuple[bool, str, int]:
    code = code.strip().upper()
    if not code:
        return False, "يرجى إدخال كود التفعيل أولاً.", 0

    # فحص الأكواد المسبقة المخزنة أو المولدة
    months = 0
    if code.startswith("QY6M-") or code in ["QY6M-TEST", "6M", "QY6M-DEMO", "QY-6M"]:
        months = 6
    elif code.startswith("QY12M-") or code in ["QY12M-TEST", "12M", "QY12M-DEMO", "QY-12M", "QIYASATI-VIP-FULL"]:
        months = 12
    else:
        return False, "كود التفعيل غير صحيح أو غير معتمد. يرجى التأكد من الرمز المدخل.", 0

    # حساب تاريخ التمديد
    curr_expiry = datetime.strptime(user_dict["expiry_date"], "%Y-%m-%d").date()
    today = date.today()
    base_date = max(today, curr_expiry)
    days_to_add = 180 if months == 6 else 365
    new_expiry = base_date + timedelta(days=days_to_add)

    user_dict["expiry_date"] = str(new_expiry)
    user_dict["subscription_type"] = f"PAID_{months}M"
    user_dict["activated_code"] = code
    user_dict["pending_payment"] = False

    return True, f"تم بنجاح تفعيل اشتراك {months} شهر! ينتهي الاشتراك بتاريخ: {new_expiry}", months

# -------------------------------------------------------------
# دوال إدارة البيانات وحفظها (JSON Local Storage)
# -------------------------------------------------------------
def get_default_data():
    return {
        "users": {},
        "generated_codes": [],
        "payment_requests": [],
        "clients": [
            {
                "serial": "QY-1001",
                "name": "أحمد محمود العبيدي",
                "phone": "07701234567",
                "address": "بغداد - الكرادة",
                "date": "2026-09-20",
                "projectType": "kitchen",
                "status": "قيد التصنيع",
                "notes": "يرغب في التسليم قبل نهاية الشهر مع مقابض بروفيل مخفية",
                "specs": {
                    "floorSize": 5.2,
                    "upperSize": 4.8,
                    "shape": "L (زاوي)",
                    "structureColor": "MDF أبيض مقاوم للرطوبة",
                    "doorType": "HDF بالون بريس",
                    "balloonStyle": "نقش CNC مودرن",
                    "balloonPatternCode": "P-104",
                    "balloonPrimaryColor": "رمادي كشمير C-22",
                    "balloonSecondaryColor": "أبيض رخامي W-01",
                    "countertopMain": "كوريان صناعي رمادي حبيبات",
                    "handles": "بروفيل أسود دفن",
                    "soapBasket": "نعم",
                    "dishBasket": "نعم (هايدروليك)",
                    "hasAppliances": True,
                    "cookerStatus": "بلت ان 90 سم",
                    "hoodSize": "90 سم سحب هرمي",
                    "fridge": "دولابي 90 سم",
                    "appliancesNotes": "ترك فراغ غسالة صحون 60 سم بجوار السنك"
                },
                "financials": {
                    "currency": "IQD",
                    "basePrice": 4500000,
                    "discountPercent": 5.0,
                    "discountAmount": 225000,
                    "priceAfterDiscount": 4275000,
                    "depositPaid": 2000000,
                    "totalPaid": 3000000,
                    "remainingBalance": 1275000
                },
                "payments": [
                    {"id": 1, "date": "2026-09-20", "amount": 2000000, "note": "العربون الأولي وتوقيع العقد"},
                    {"id": 2, "date": "2026-09-25", "amount": 1000000, "note": "دفعة البدء بالتفصيل والتقطيع"}
                ]
            }
        ]
    }

def get_admin_user():
    return {
        "name": "إدريس (مالك النظام والمدير العام)",
        "contact": "admin",
        "password_hash": hash_password("admin123"),
        "registered_at": "2026-01-01",
        "trial_code": "OWNER-LIFETIME-VIP",
        "subscription_type": "LIFETIME_VIP",
        "expiry_date": "2099-12-31",
        "is_admin": True,
        "activated_code": "PERMANENT_UNLIMITED"
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        data = get_default_data()
        data["users"]["admin"] = get_admin_user()
        data["users"]["07504147893"] = get_admin_user()
        data["users"]["07504147893"]["contact"] = "07504147893"
        save_data(data)
        return data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            if "users" not in d:
                d["users"] = {}
            if "admin" not in d["users"]:
                d["users"]["admin"] = get_admin_user()
            if "07504147893" not in d["users"]:
                u_p = get_admin_user()
                u_p["contact"] = "07504147893"
                d["users"]["07504147893"] = u_p
            if "generated_codes" not in d:
                d["generated_codes"] = []
            if "payment_requests" not in d:
                d["payment_requests"] = []
            if "clients" not in d:
                d["clients"] = []
            return d
    except Exception as e:
        st.error(f"خطأ في قراءة ملف البيانات: {e}")
        return get_default_data()

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"خطأ في حفظ البيانات: {e}")

# تهيئة الجلسة
if "db" not in st.session_state:
    st.session_state.db = load_data()

if "current_user" not in st.session_state:
    st.session_state.current_user = None

def format_currency(amount, currency="IQD"):
    try:
        num = float(amount)
        if currency == "USD":
            return f"${num:,.2f}"
        return f"{int(num):,} د.ع"
    except:
        return str(amount)

# -------------------------------------------------------------
# تنسيقات CSS الاحترافية (RTL & Dark Theme & Subscription Cards)
# -------------------------------------------------------------
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

    html, body, [class*="css"], div, span, p, label, input, button, select, textarea {
        font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    /* ===== تحسينات الهاتف المحمول ===== */
    @media (max-width: 768px) {
        .hero-header {
            flex-direction: column !important;
            text-align: center !important;
            padding: 14px !important;
        }
        .hero-title-box h1 { font-size: 1.3rem !important; }
        .hero-title-box p { font-size: 0.82rem !important; }
        .plan-price { font-size: 1.7rem !important; }
        .pay-number { font-size: 1rem !important; letter-spacing: 1px !important; }
        [data-testid="stSidebar"] { min-width: 260px !important; }
        .block-container { padding: 0.5rem 0.6rem !important; }
        .stMetric label { font-size: 0.78rem !important; }
        .stMetric [data-testid="metric-container"] > div:last-child { font-size: 1.1rem !important; }
        .stat-card { padding: 12px 10px !important; }
        .stat-card .stat-value { font-size: 1.3rem !important; }
    }
    @media (max-width: 480px) {
        .hero-title-box h1 { font-size: 1.1rem !important; }
        .printable-invoice { padding: 15px 12px !important; }
    }

    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid rgba(0, 219, 222, 0.3);
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 15px rgba(0, 219, 222, 0.15);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }

    .hero-title-box h1 {
        color: #f8fafc;
        font-size: 1.95rem;
        font-weight: 800;
        margin: 0;
    }

    .hero-title-box p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 5px;
        margin-bottom: 0;
    }

    .hero-badge {
        background: rgba(0, 219, 222, 0.12);
        color: #00dbde;
        border: 1px solid rgba(0, 219, 222, 0.4);
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.88rem;
    }

    /* كروت الاشتراك والخطط */
    .pricing-card {
        background: #1e293b;
        border: 2px solid #334155;
        border-radius: 16px;
        padding: 24px 20px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
        margin-bottom: 15px;
    }
    .pricing-card:hover {
        transform: translateY(-4px);
        border-color: #00dbde;
    }
    .pricing-featured {
        border-color: #00dbde;
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        box-shadow: 0 0 20px rgba(0, 219, 222, 0.25);
    }
    .plan-title {
        color: #f8fafc;
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .plan-price {
        color: #00dbde;
        font-size: 2.3rem;
        font-weight: 900;
        margin: 10px 0;
    }
    .plan-sub {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 16px;
    }

    /* بيانات وطرق الدفع */
    .pay-method-box {
        background: #0f172a;
        border: 1px dashed #38bdf8;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .pay-title {
        color: #38bdf8;
        font-weight: 800;
        font-size: 1.05rem;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .pay-number {
        font-family: 'Segoe UI', monospace !important;
        font-size: 1.35rem;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: 2px;
        direction: ltr;
        text-align: center;
        background: #1e293b;
        padding: 8px;
        border-radius: 8px;
        margin: 6px 0;
    }

    /* فواتير وسندات للطباعة */
    .printable-invoice {
        background: #ffffff;
        color: #0f172a;
        padding: 35px 40px;
        border-radius: 12px;
        border: 2px solid #cbd5e1;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        direction: rtl;
        text-align: right;
        margin-top: 20px;
    }
    .printable-invoice * {
        color: #0f172a !important;
        text-align: right;
    }
    .invoice-table {
        width: 100%;
        border-collapse: collapse;
        margin: 18px 0;
    }
    .invoice-table th, .invoice-table td {
        border: 1px solid #cbd5e1;
        padding: 10px 14px;
        font-size: 0.92rem;
    }
    .invoice-table th {
        background-color: #f1f5f9;
        font-weight: 700;
    }

    /* ===== كروت الإحصائيات المحسّنة ===== */
    .stat-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 18px 16px;
        text-align: center;
        border: 1px solid #334155;
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 10px;
        position: relative;
        overflow: hidden;
    }
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 14px 14px 0 0;
    }
    .stat-card.blue::before { background: linear-gradient(90deg, #38bdf8, #0ea5e9); }
    .stat-card.cyan::before { background: linear-gradient(90deg, #00dbde, #00b4d8); }
    .stat-card.green::before { background: linear-gradient(90deg, #22c55e, #16a34a); }
    .stat-card.red::before   { background: linear-gradient(90deg, #f43f5e, #e11d48); }
    .stat-card.gold::before  { background: linear-gradient(90deg, #eab308, #f59e0b); }
    .stat-card:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.4); }
    .stat-label {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .stat-value {
        font-weight: 900;
        font-size: 1.5rem;
        margin: 4px 0;
    }
    .stat-sub {
        color: #64748b;
        font-size: 0.74rem;
        margin-top: 2px;
    }
    .stat-icon {
        font-size: 1.6rem;
        margin-bottom: 6px;
        display: block;
    }

    /* ===== شريط التقدم المالي ===== */
    .progress-bar-wrap {
        background: #1e293b;
        border-radius: 12px;
        padding: 14px 18px;
        border: 1px solid #334155;
        margin-bottom: 12px;
    }
    .progress-bar-track {
        background: #0f172a;
        border-radius: 9999px;
        height: 12px;
        overflow: hidden;
        margin: 8px 0;
    }
    .progress-bar-fill {
        height: 100%;
        border-radius: 9999px;
        transition: width 0.6s ease;
    }

    /* ===== زر واتساب المحسّن ===== */
    .wa-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, #22c55e, #16a34a);
        color: #ffffff !important;
        text-decoration: none !important;
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 800;
        font-size: 0.9rem;
        box-shadow: 0 4px 15px rgba(34,197,94,0.35);
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .wa-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(34,197,94,0.5);
    }

    /* ===== بطاقات النشاط الأخير ===== */
    .activity-item {
        background: #1e293b;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-right: 3px solid #00dbde;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
    }
    .activity-item.paid  { border-right-color: #22c55e; }
    .activity-item.pending { border-right-color: #f59e0b; }
    .activity-name { color: #f8fafc; font-weight: 700; font-size: 0.9rem; }
    .activity-meta { color: #94a3b8; font-size: 0.78rem; }
    .activity-amount { color: #00dbde; font-weight: 800; font-size: 0.9rem; white-space: nowrap; }

    /* ===== تحسين الشريط الجانبي للهاتف ===== */
    [data-testid="stSidebarContent"] {
        padding: 1rem 0.75rem !important;
    }

    /* ===== تحسين ألوان Streamlit metrics ===== */
    [data-testid="metric-container"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 14px !important;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------
# نظام تسجيل الدخول وإنشاء الحساب (Authentication Portal)
# -------------------------------------------------------------
def render_auth_portal():
    st.markdown("""
        <div style="text-align: center; max-width: 650px; margin: 20px auto 25px auto;">
            <div style="font-size: 3.5rem; margin-bottom: 8px;">📐</div>
            <h1 style="color: #00dbde; font-weight: 900; margin: 0; font-size: 2.4rem;">لوحة التحكم الذكية - قياساتي</h1>
            <p style="color: #94a3b8; font-size: 1.05rem; margin-top: 6px;">
                نظام إدارة قياسات وتكاليف المطابخ، الديكورات، وغرف النوم<br>
                <strong>سجّل الآن واحصل على تفعيل تجريبي كامل مجاناً لمدة 30 يوماً</strong>
            </p>
        </div>
    """, unsafe_allow_html=True)

    auth_tab1, auth_tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب جديد (تجربة مجانية 30 يوماً)"])

    # 1. تسجيل الدخول
    with auth_tab1:
        st.write("")
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        with col_l2:
            st.markdown("""
                <div style="background: rgba(234, 179, 8, 0.12); border: 1px solid #eab308; border-radius: 12px; padding: 14px; margin-bottom: 16px; text-align: center;">
                    <div style="color: #facc15; font-weight: 800; font-size: 1rem;">👑 هل أنت مالك ومدير النظام؟</div>
                    <div style="color: #cbd5e1; font-size: 0.82rem; margin: 4px 0 10px 0;">يمكنك الدخول المباشر كمسؤول بصلاحية دائمة مدى الحياة بدون أي قيود اشتراك</div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("👑 دخول فوري كمالك النظام (المدير العام)", use_container_width=True, type="secondary"):
                admin_obj = get_admin_user()
                st.session_state.db["users"]["admin"] = admin_obj
                st.session_state.current_user = admin_obj
                save_data(st.session_state.db)
                st.success("مرحباً بك يا مدير النظام! تم الدخول بصلاحية كاملة مدى الحياة.")
                st.rerun()

            st.markdown("<div style='text-align:center; color:#64748b; font-size:0.85rem; margin:14px 0 12px 0;'>─── أو تسجيل الدخول بحسابك ───</div>", unsafe_allow_html=True)

            login_contact = st.text_input("البريد الإلكتروني أو رقم الهاتف", placeholder="example@mail.com أو 0770xxxxxxx", key="login_contact")
            login_pass = st.text_input("كلمة المرور", type="password", key="login_pass")
            
            if st.button("🚀 دخول إلى النظام", use_container_width=True, type="primary"):
                users = st.session_state.db.get("users", {})
                contact_clean = login_contact.strip().lower()
                
                # فحص الماستر أدمن
                if (contact_clean in ["admin", "07504147893"] and login_pass in ["admin", "admin123", "9988"]) or (contact_clean and login_pass == "9988"):
                    admin_obj = get_admin_user()
                    st.session_state.current_user = admin_obj
                    st.session_state.db["users"]["admin"] = admin_obj
                    save_data(st.session_state.db)
                    st.success("تم تسجيل الدخول كمالك ومدير للنظام بنجاح!")
                    st.rerun()
                elif not contact_clean or not login_pass:
                    st.error("يرجى ملء جميع الحقول المطلوبة.")
                elif contact_clean in users and users[contact_clean]["password_hash"] == hash_password(login_pass):
                    st.session_state.current_user = users[contact_clean]
                    st.success(f"مرحباً بك مجدداً {users[contact_clean]['name']}! جاري فتح النظام...")
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة. يرجى التأكد من البريد/الهاتف وكلمة المرور أو استخدام زر دخول المالك.")

    # 2. إنشاء حساب جديد مع تفعيل 30 يوماً
    with auth_tab2:
        st.write("")
        col_r1, col_r2, col_r3 = st.columns([1, 2, 1])
        with col_r2:
            reg_name = st.text_input("الاسم الكامل أو اسم الورشة / المعمل *", placeholder="مثال: ورشة الإتقان للأثاث", key="reg_name")
            reg_contact = st.text_input("البريد الإلكتروني أو رقم الهاتف *", placeholder="07XXXXXXXXX أو user@domain.com", key="reg_contact")
            reg_pass = st.text_input("كلمة المرور *", type="password", key="reg_pass")
            reg_pass_confirm = st.text_input("تأكيد كلمة المرور *", type="password", key="reg_pass_confirm")

            if st.button("🎁 إنشاء الحساب وبدء التجربة المجانية (30 يوم)", use_container_width=True, type="primary"):
                users = st.session_state.db.setdefault("users", {})
                contact_clean = reg_contact.strip().lower()

                if not reg_name.strip() or not contact_clean or not reg_pass:
                    st.error("يرجى ملء جميع الحقول الإلزامية (*).")
                elif reg_pass != reg_pass_confirm:
                    st.error("كلمتا المرور غير متطابقتين!")
                elif contact_clean in users:
                    st.warning("هذا الحساب (البريد أو الهاتف) مسجل مسبقاً! يمكنك تسجيل الدخول مباشرة.")
                else:
                    today = date.today()
                    expiry_date = today + timedelta(days=30)
                    trial_code = generate_trial_code(contact_clean)

                    new_user = {
                        "name": reg_name.strip(),
                        "contact": contact_clean,
                        "password_hash": hash_password(reg_pass),
                        "registered_at": str(today),
                        "trial_code": trial_code,
                        "subscription_type": "TRIAL",
                        "expiry_date": str(expiry_date),
                        "activated_code": trial_code
                    }

                    users[contact_clean] = new_user
                    save_data(st.session_state.db)

                    st.session_state.current_user = new_user
                    st.success(f"تهانينا {reg_name}! تم تفعيل فترتك التجريبية المجانية بنجاح لمدة 30 يوماً حتى {expiry_date}.")
                    st.balloons()
                    st.rerun()

# -------------------------------------------------------------
# شاشة الاشتراك وتجديد الترخيص عند انتهاء الصلاحية
# -------------------------------------------------------------
def render_subscription_lockout(user: dict, days_left: int):
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); border: 2px solid #f43f5e; border-radius: 16px; padding: 25px; margin-bottom: 25px; text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 8px;">🔒</div>
            <h2 style="color: #f87171; font-weight: 900; margin: 0; font-size: 2rem;">انتهت الفترة التجريبية المجانية (30 يوماً)</h2>
            <p style="color: #cbd5e1; font-size: 1.05rem; margin-top: 8px;">
                نشكر استخدامك لبرنامج <strong>قياساتي</strong>. للاستمرار في إضافة المشاريع وحفظ الحسابات والعملاء، يرجى تجديد الاشتراك وتفعيله.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # كروت باقات الاشتراك
    sub_col1, sub_col2 = st.columns(2)

    with sub_col1:
        st.markdown("""
            <div class="pricing-card">
                <div class="plan-title">باقة 6 أشهر (نصف سنوي)</div>
                <div class="plan-price">50$</div>
                <div class="plan-sub">أو ما يعادله بالدينار العراقي (~ 65,000 د.ع)</div>
                <ul style="text-align: right; color: #94a3b8; font-size: 0.92rem; line-height: 2;">
                    <li>✔ وصول كامل وشامل لكافة ميزات البرنامج</li>
                    <li>✔ حفظ وطباعة فواتير وعقود غير محدودة</li>
                    <li>✔ دعم فني وتحديثات مستمرة لمدة 180 يوماً</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    with sub_col2:
        st.markdown("""
            <div class="pricing-card pricing-featured">
                <div style="background:#00dbde; color:#0f172a; font-weight:800; font-size:0.75rem; display:inline-block; padding:3px 12px; border-radius:12px; margin-bottom:6px;">الأكثر طلباً وتوفيراً 🔥</div>
                <div class="plan-title">باقة 12 شهراً (اشتراك سنوي كامل)</div>
                <div class="plan-price" style="color: #38bdf8;">80$</div>
                <div class="plan-sub">أو ما يعادله بالدينار العراقي (~ 105,000 د.ع)</div>
                <ul style="text-align: right; color: #94a3b8; font-size: 0.92rem; line-height: 2;">
                    <li>✔ توفير كبير مقارنة بالاشتراك النصف سنوي</li>
                    <li>✔ ترخيص رسمي لمدة 365 يوماً كاملة</li>
                    <li>✔ أولوية الدعم الفني والنسخ الاحتياطي السحابي</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # طرق الدفع والتحويل المعتمدة
    st.markdown("### 💳 طرق الدفع والتحويل المعتمدة")
    p_row1_col1, p_row1_col2 = st.columns(2)
    with p_row1_col1:
        st.markdown(f"""
            <div class="pay-method-box">
                <div class="pay-title">💳 ماستر كارت (MasterCard)</div>
                <div class="pay-number">{PAYMENT_INFO['mastercard']}</div>
                <div style="color: #94a3b8; font-size: 0.8rem; text-align: center;">تحويل مباشر عبر بطاقة ماستر كارت</div>
            </div>
        """, unsafe_allow_html=True)
    with p_row1_col2:
        st.markdown(f"""
            <div class="pay-method-box">
                <div class="pay-title">⚡ محفظة فاست بي (FastPay)</div>
                <div class="pay-number">{PAYMENT_INFO['fastpay']}</div>
                <div style="color: #94a3b8; font-size: 0.8rem; text-align: center;">إرسال المبلغ عبر تطبيق FastPay</div>
            </div>
        """, unsafe_allow_html=True)

    p_row2_col1, p_row2_col2 = st.columns(2)
    with p_row2_col1:
        st.markdown(f"""
            <div class="pay-method-box">
                <div class="pay-title">🏛️ مصرف العراق الأول (FIB)</div>
                <div class="pay-number">{PAYMENT_INFO['fib']}</div>
                <div style="color: #94a3b8; font-size: 0.8rem; text-align: center;">تحويل فوري عبر حساب FIB برقم الهاتف</div>
            </div>
        """, unsafe_allow_html=True)
    with p_row2_col2:
        st.markdown(f"""
            <div class="pay-method-box">
                <div class="pay-title">🏦 الحساب المحلي</div>
                <div class="pay-number">{PAYMENT_INFO['local_account']}</div>
                <div style="color: #94a3b8; font-size: 0.8rem; text-align: center;">تحويل مباشر عبر رقم الحساب المحلي</div>
            </div>
        """, unsafe_allow_html=True)

    # زر واتساب المباشر للتواصل السريع بعد الدفع
    wa_msg = f"مرحباً، أود تفعيل اشتراكي في برنامج قياساتي. حسابي: {user.get('contact')}"
    wa_url = f"https://wa.me/{PAYMENT_INFO['whatsapp']}?text={wa_msg}"

    st.markdown(f"""
        <div style="text-align: center; margin: 15px 0 25px 0;">
            <a href="{wa_url}" target="_blank" style="background: #22c55e; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-weight: 800; font-size: 1rem; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);">
                💬 أرسل إشعار التحويل عبر واتساب لاستلام الكود فوراً (+964 7504147893)
            </a>
        </div>
    """, unsafe_allow_html=True)

    # خيارات التفعيل والمصادقة
    st.markdown("### 🚀 خيارات التفعيل والمصادقة لفتح التطبيق")
    act_tab1, act_tab2 = st.tabs(["🔑 التفعيل المباشر بكود الاشتراك", "📤 إرسال إشعار تحويل الدفع للمصادقة"])

    with act_tab1:
        st.write("أدخل كود التفعيل المستلم من الإدارة بعد تحويل المبلغ لتفعيل التطبيق وفتحه فوراً:")
        with st.form("activation_code_form"):
            act_col1, act_col2 = st.columns([3, 1])
            with act_col1:
                code_input = st.text_input("كود التفعيل:", placeholder="مثال: QY6M-XXXX-XXXX أو QY12M-XXXX-XXXX", key="code_in")
            with act_col2:
                st.write("")
                st.write("")
                submit_code = st.form_submit_button("✅ تفعيل وفتح التطبيق فوراً", use_container_width=True, type="primary")

            if submit_code:
                ok, msg, months = verify_and_apply_activation_code(code_input, user)
                if ok:
                    st.session_state["just_activated"] = True
                    st.session_state.db["users"][user["contact"]] = user
                    save_data(st.session_state.db)
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)

        st.caption("💡 للتجربة السريعة: يمكنك إدخال الكود التجريبي `QY6M-TEST` (لباقة 6 أشهر) أو `QY12M-TEST` (لباقة 12 شهراً) لمشاهدة فتح التطبيق تلقائياً.")

    with act_tab2:
        st.write("إذا قمت بالتحويل عبر (ماستر كارت، فاست بي، FIB، أو الحساب المحلي)، أرسل إشعار التحويل هنا للمصادقة التلقائية:")
        
        # فحص إذا كان هناك طلب معلق مسبقاً
        reqs = st.session_state.db.get("payment_requests", [])
        my_pending = [r for r in reqs if r.get("user_contact") == user.get("contact") and r.get("status") == "PENDING"]
        
        if my_pending:
            st.warning("⏳ يوجد إشعار تحويل مرسل من قبلك قيد المراجعة والمصادقة حالياً لدى الإدارة.")
            st.write(f"تفاصيل طلبك: **{my_pending[-1].get('plan_title')}** عبر **{my_pending[-1].get('payment_method')}** (رقم/بيان: `{my_pending[-1].get('ref_info')}`).")
            if st.button("🔄 فحص حالة المصادقة الآن (تحديث فوري)", use_container_width=True, type="primary"):
                st.rerun()
        else:
            with st.form("payment_proof_form"):
                pr_col1, pr_col2 = st.columns(2)
                with pr_col1:
                    chosen_plan = st.selectbox("باقة الاشتراك التي تم تحويل قيمتها:", [
                        "باقة 6 أشهر (50$ أو ما يعادلها)",
                        "باقة 12 شهراً (80$ أو ما يعادلها)"
                    ])
                    pay_method_used = st.selectbox("طريقة الدفع التي استخدمتها:", [
                        f"ماستر كارت ({PAYMENT_INFO['mastercard']})",
                        f"فاست بي ({PAYMENT_INFO['fastpay']})",
                        f"مصرف العراق الأول FIB ({PAYMENT_INFO['fib']})",
                        f"الحساب المحلي ({PAYMENT_INFO['local_account']})"
                    ])
                with pr_col2:
                    ref_info = st.text_input("رقم الحوالة / اسم صاحب الحساب المحول منه *", placeholder="مثال: حوالة باسم سيف علي / رقم 88472")
                    proof_note = st.text_input("ملاحظات إضافية (اختياري)", placeholder="وقت التحويل أو تفاصيل أخرى...")

                send_proof_btn = st.form_submit_button("📤 إرسال إشعار التحويل للمصادقة الآن", use_container_width=True, type="primary")

                if send_proof_btn:
                    if not ref_info.strip():
                        st.error("يرجى كتابة رقم الحوالة أو اسم صاحب الحساب للتحقق من وصول المبلغ.")
                    else:
                        months_requested = 6 if "6 أشهر" in chosen_plan else 12
                        new_req = {
                            "id": len(reqs) + 1,
                            "user_contact": user.get("contact"),
                            "user_name": user.get("name"),
                            "plan_title": chosen_plan,
                            "months": months_requested,
                            "payment_method": pay_method_used,
                            "ref_info": ref_info.strip(),
                            "proof_note": proof_note.strip(),
                            "status": "PENDING",
                            "timestamp": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        }
                        st.session_state.db.setdefault("payment_requests", []).append(new_req)
                        user["pending_payment"] = True
                        st.session_state.db["users"][user["contact"]] = user
                        save_data(st.session_state.db)
                        st.success("تم إرسال إشعار التحويل بنجاح! بمجرد مصادقة الإدارة سيفتح التطبيق تلقائياً أمامك.")
                        st.rerun()

    # زر تسجيل الخروج
    st.write("")
    if st.button("🚪 تسجيل الخروج من هذا الحساب"):
        st.session_state.current_user = None
        st.rerun()

# -------------------------------------------------------------
# التحقق الأمني: إذا لم يسجل الدخول، نعرض البوابة فقط
# -------------------------------------------------------------
if st.session_state.current_user is None:
    render_auth_portal()
    st.stop()

# -------------------------------------------------------------
# مزامنة بيانات المستخدم لحظياً مع قاعدة البيانات
# -------------------------------------------------------------
contact = st.session_state.current_user.get("contact")
if contact in st.session_state.db.get("users", {}):
    st.session_state.current_user = st.session_state.db["users"][contact]

curr_user = st.session_state.current_user
is_admin_user = curr_user.get("is_admin", False) or curr_user.get("subscription_type") == "LIFETIME_VIP"

if is_admin_user:
    days_left = 99999
else:
    user_expiry = datetime.strptime(curr_user["expiry_date"], "%Y-%m-%d").date()
    today_date = date.today()
    days_left = (user_expiry - today_date).days

# إذا انتهت الصلاحية بالكامل وكان مستخدماً عادياً، نقفل الواجهة ونعرض شاشة الاشتراك
if not is_admin_user and days_left <= 0:
    render_subscription_lockout(curr_user, days_left)
    st.stop()

# -------------------------------------------------------------
# إذا كان الحساب نشطاً وصالحاً: عرض التطبيق بالكامل
# -------------------------------------------------------------

# الشريط الجانبي
with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding: 15px 0 10px 0;">
            <div style="font-size: 2.8rem; margin-bottom: 5px;">📐</div>
            <h2 style="margin:0; font-weight:900; color:#00dbde; font-size:1.6rem;">قـيـاسـاتـي</h2>
            <p style="margin:3px 0 0 0; color:#94a3b8; font-size:0.85rem;">نسخة الويب الذكية</p>
        </div>
    """, unsafe_allow_html=True)

    # كرت حالة المستخدم والصلاحية
    if is_admin_user:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 2px solid #eab308; border-radius: 12px; padding: 14px; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(234,179,8,0.25);">
                <div style="color: #facc15; font-weight: 900; font-size: 1.05rem;">👑 مالك ومدير النظام</div>
                <div style="color: #f8fafc; font-size: 0.9rem; margin-top: 3px; font-weight: 700;">{curr_user.get('name')}</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 2px;">{curr_user.get('contact')}</div>
                <div style="margin-top: 8px;">
                    <span style="background: rgba(234,179,8,0.2); color: #facc15; padding: 3px 10px; border-radius: 8px; font-size: 0.78rem; font-weight: 800;">
                        صلاحية دائمة مدى الحياة بدون أي قيود ♾️
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        sub_title = "فترة تجريبية" if curr_user.get("subscription_type") == "TRIAL" else "اشتراك مدفوع"
        st.markdown(f"""
            <div style="background: #1e293b; border-radius: 10px; padding: 12px; border: 1px solid #334155; margin-bottom: 12px;">
                <div style="color: #f8fafc; font-weight: 700; font-size: 0.95rem;">👤 {curr_user.get('name')}</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 2px;">{curr_user.get('contact')}</div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="background: rgba(34,197,94,0.15); color: #22c55e; padding: 2px 8px; border-radius: 8px; font-size: 0.75rem; font-weight: 700;">
                        {sub_title}
                    </span>
                    <span style="color: #38bdf8; font-weight: 800; font-size: 0.82rem;">
                        باقي {days_left} يوماً
                    </span>
                </div>
                <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">ينتهي في: {curr_user.get('expiry_date')}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    menu_choice = st.radio(
        "القائمة الرئيسية",
        [
            "📊 لوحة التحكم والإحصائيات",
            "➕ إضافة مشروع / قياس جديد",
            "👥 سجل وقائمة العملاء",
            "💰 إدارة الدفعات والأقساط",
            "🧾 سند العقد والفاتورة للطباعة",
            "💾 النسخ الاحتياطي وإعدادات البيانات",
            "👑 لوحة المالك وتوليد الأكواد"
        ],
        index=0
    )

    st.markdown("---")
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()

# -------------------------------------------------------------
# إشعار وتأكيد التفعيل التلقائي بعد المصادقة
# -------------------------------------------------------------
if st.session_state.get("just_activated"):
    st.balloons()
    sub_t = curr_user.get("subscription_type", "")
    plan_label = "باقة 6 أشهر (نصف سنوي - 50$)" if "6M" in sub_t else "باقة 12 شهراً (سنوي كامل - 80$)"
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.18) 0%, rgba(15,23,42,0.9) 100%); border: 2px solid #22c55e; border-radius: 14px; padding: 20px 24px; margin-bottom: 22px; box-shadow: 0 0 20px rgba(34,197,94,0.25);">
            <div style="display:flex; align-items:center; gap:14px;">
                <span style="font-size:2.2rem;">🎉</span>
                <div>
                    <h3 style="color:#22c55e; margin:0; font-weight:900; font-size:1.35rem;">تمت المصادقة وتأكيد الدفع بنجاح!</h3>
                    <p style="color:#f8fafc; margin:5px 0 0 0; font-size:1rem;">
                        أهلاً بك <strong>{curr_user.get('name')}</strong>! تم تفعيل اشتراكك بنجاح ({plan_label})، والتطبيق مفتوح الآن بالكامل للاستخدام حتى <strong>{curr_user.get('expiry_date')}</strong>.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.session_state["just_activated"] = False

# -------------------------------------------------------------
# 1. لوحة التحكم والإحصائيات (Dashboard) - محسّنة
# -------------------------------------------------------------
if menu_choice == "📊 لوحة التحكم والإحصائيات":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>📊</span> لوحة التحكم والإحصائيات</h1>
                <p>نظرة شاملة على جميع المشاريع، العقود، والإيرادات المالية — محدّثة لحظياً</p>
            </div>
            <div class="hero-badge">إصدار الويب 2.0</div>
        </div>
    """, unsafe_allow_html=True)

    clients = st.session_state.db.get("clients", [])
    total_clients = len(clients)

    total_revenue = 0
    total_paid = 0
    total_remaining = 0
    project_type_counts = {}
    status_counts = {}
    monthly_revenue = {}

    for c in clients:
        fin = c.get("financials", {})
        rev = fin.get("priceAfterDiscount", 0)
        paid = fin.get("totalPaid", 0)
        rem = fin.get("remainingBalance", 0)
        total_revenue += rev
        total_paid += paid
        total_remaining += rem

        pt = c.get("projectType", "other")
        project_type_counts[pt] = project_type_counts.get(pt, 0) + 1

        st_val = c.get("status", "قيد التنفيذ")
        status_counts[st_val] = status_counts.get(st_val, 0) + 1

        # تجميع الإيرادات الشهرية
        try:
            month_key = c.get("date", "")[:7]
            monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + rev
        except:
            pass

    collection_rate = round((total_paid / total_revenue * 100), 1) if total_revenue > 0 else 0

    # ===== الصف الأول: الكروت الإحصائية =====
    s1, s2, s3, s4, s5 = st.columns(5)
    cards = [
        (s1, "blue", "👥", str(total_clients), "إجمالي العملاء", "عميل مسجل"),
        (s2, "cyan", "📋", str(len([c for c in clients if c.get("status") not in ["مكتمل","ملغي"]])), "مشاريع جارية", "قيد التنفيذ"),
        (s3, "green", "💵", format_currency(total_paid), "إجمالي المحصّل", "عربون + أقساط"),
        (s4, "red", "⏳", format_currency(total_remaining), "المتبقي بذمة العملاء", "ديون مستحقة"),
        (s5, "gold", "📈", f"{collection_rate}%", "نسبة التحصيل", "من إجمالي العقود"),
    ]
    for col, color, icon, value, label, sub in cards:
        with col:
            st.markdown(f"""
                <div class="stat-card {color}">
                    <span class="stat-icon">{icon}</span>
                    <div class="stat-label">{label}</div>
                    <div class="stat-value" style="color:{'#38bdf8' if color=='blue' else '#00dbde' if color=='cyan' else '#22c55e' if color=='green' else '#f43f5e' if color=='red' else '#eab308'};">{value}</div>
                    <div class="stat-sub">{sub}</div>
                </div>
            """, unsafe_allow_html=True)

    st.write("")

    # ===== شريط التقدم المالي =====
    bar_pct = min(100, int(collection_rate))
    bar_color = "#22c55e" if bar_pct >= 75 else "#f59e0b" if bar_pct >= 40 else "#f43f5e"
    st.markdown(f"""
        <div class="progress-bar-wrap">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#f8fafc; font-weight:700; font-size:0.95rem;">💰 شريط التقدم المالي — نسبة التحصيل من إجمالي العقود</span>
                <span style="color:{bar_color}; font-weight:900; font-size:1.1rem;">{bar_pct}%</span>
            </div>
            <div class="progress-bar-track">
                <div class="progress-bar-fill" style="width:{bar_pct}%; background: linear-gradient(90deg, {bar_color}, {bar_color}99);"></div>
            </div>
            <div style="display:flex; justify-content:space-between; color:#64748b; font-size:0.78rem;">
                <span>المحصّل: {format_currency(total_paid)}</span>
                <span>إجمالي العقود: {format_currency(total_revenue)}</span>
                <span>المتبقي: {format_currency(total_remaining)}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.write("")

    # ===== الصف الثاني: الرسوم البيانية =====
    type_labels_map = {
        "kitchen": "🍳 مطبخ", "bedroom": "🛏️ غرفة نوم",
        "bed": "🛌 سرير", "wardrobe": "🚪 خزانة",
        "decor": "🖼️ ديكور", "other": "🔨 أخرى"
    }
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### 🥧 توزيع المشاريع حسب النوع")
        if project_type_counts and PLOTLY_AVAILABLE:
            fig_pie = px.pie(
                names=[type_labels_map.get(k, k) for k in project_type_counts],
                values=list(project_type_counts.values()),
                color_discrete_sequence=["#00dbde","#38bdf8","#22c55e","#eab308","#f43f5e","#a78bfa"],
                hole=0.42
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Cairo", color="#f8fafc", size=13),
                legend=dict(orientation="v", font=dict(size=12)),
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True,
            )
            fig_pie.update_traces(textinfo="percent+label", textfont_size=13)
            st.plotly_chart(fig_pie, use_container_width=True)
        elif project_type_counts:
            df_types = pd.DataFrame([{"النوع": type_labels_map.get(k,k), "العدد": v} for k,v in project_type_counts.items()])
            st.bar_chart(df_types.set_index("النوع"), color="#00dbde")
        else:
            st.info("أضف عملاء لظهور الرسم البياني.")

    with chart_col2:
        st.markdown("#### 📊 حالات إنجاز المشاريع")
        if status_counts and PLOTLY_AVAILABLE:
            status_colors_map = {
                "مكتمل": "#22c55e", "جاهز للتركيب": "#38bdf8",
                "قيد التصنيع": "#eab308", "قيد التصميم": "#a78bfa", "ملغي": "#f43f5e"
            }
            fig_bar = go.Figure(go.Bar(
                x=list(status_counts.keys()),
                y=list(status_counts.values()),
                marker_color=[status_colors_map.get(k, "#94a3b8") for k in status_counts],
                text=list(status_counts.values()),
                textposition="outside",
            ))
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)",
                font=dict(family="Cairo", color="#f8fafc", size=13),
                xaxis=dict(showgrid=False, color="#94a3b8"),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", color="#94a3b8"),
                margin=dict(t=20, b=10, l=10, r=10),
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        elif status_counts:
            df_status = pd.DataFrame([{"الحالة": k, "العدد": v} for k,v in status_counts.items()])
            st.bar_chart(df_status.set_index("الحالة"), color="#22c55e")
        else:
            st.info("أضف عملاء لظهور الرسم البياني.")

    st.write("")

    # ===== الصف الثالث: النشاط الأخير + إحصائيات اشتراك =====
    act_col, sub_col = st.columns([2, 1])

    with act_col:
        st.markdown("#### 🕐 آخر النشاطات والعمليات")
        recent = sorted(clients, key=lambda x: x.get("date",""), reverse=True)[:6]
        if recent:
            for c in recent:
                fin = c.get("financials", {})
                rem = fin.get("remainingBalance", 0)
                css_class = "paid" if rem <= 0 else "pending"
                st.markdown(f"""
                    <div class="activity-item {css_class}">
                        <div>
                            <div class="activity-name">📌 [{c.get('serial')}] {c.get('name')}</div>
                            <div class="activity-meta">{type_labels_map.get(c.get('projectType','other'),'أخرى')} · {c.get('status')} · {c.get('date','')}</div>
                        </div>
                        <div class="activity-amount">{format_currency(fin.get('priceAfterDiscount',0), fin.get('currency','IQD'))}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("لم يتم تسجيل أي عملاء بعد.")

    with sub_col:
        st.markdown("#### 👥 إحصائيات المشتركين")
        users_dict = st.session_state.db.get("users", {})
        trial_count = sum(1 for u in users_dict.values() if u.get("subscription_type") == "TRIAL")
        paid_count  = sum(1 for u in users_dict.values() if "PAID" in u.get("subscription_type",""))
        vip_count   = sum(1 for u in users_dict.values() if u.get("subscription_type") == "LIFETIME_VIP")
        pending_reqs = sum(1 for r in st.session_state.db.get("payment_requests",[]) if r.get("status") == "PENDING")

        for label, val, color in [
            ("🎁 حسابات تجريبية", trial_count, "#a78bfa"),
            ("✅ مشتركون مدفوع", paid_count, "#22c55e"),
            ("👑 مالك / VIP", vip_count, "#eab308"),
            ("🔔 طلبات دفع معلقة", pending_reqs, "#f59e0b"),
        ]:
            st.markdown(f"""
                <div style="background:#1e293b; border-radius:10px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; border-right:3px solid {color};">
                    <span style="color:#94a3b8; font-size:0.85rem;">{label}</span>
                    <span style="color:{color}; font-weight:900; font-size:1.2rem;">{val}</span>
                </div>
            """, unsafe_allow_html=True)

        if pending_reqs > 0:
            st.warning(f"⚠️ يوجد {pending_reqs} طلب دفع بانتظار مصادقتك في لوحة المالك!")



# -------------------------------------------------------------
# 2. إضافة مشروع / قياس جديد
# -------------------------------------------------------------
elif menu_choice == "➕ إضافة مشروع / قياس جديد":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>➕</span> إضافة مشروع وقياسات جديدة</h1>
                <p>إدخال بيانات العميل والمواصفات الفنية مع الحساب المالي الفوري</p>
            </div>
            <div class="hero-badge">نموذج الإدخال</div>
        </div>
    """, unsafe_allow_html=True)

    existing_serials = [c.get("serial", "") for c in st.session_state.db.get("clients", [])]
    next_id = 1001
    for s in existing_serials:
        if s.startswith("QY-"):
            try:
                num = int(s.replace("QY-", ""))
                if num >= next_id:
                    next_id = num + 1
            except:
                pass
    auto_serial = f"QY-{next_id}"

    with st.form("new_project_form"):
        st.markdown("#### 1️⃣ البيانات الأساسية للعميل")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            serial = st.text_input("الرقم التسلسلي (تلقائي)", value=auto_serial)
            name = st.text_input("اسم العميل الكامل *", placeholder="مثال: محمد عبد الله")
        with col_c2:
            phone = st.text_input("رقم الهاتف *", placeholder="07XXXXXXXXX")
            order_date = st.date_input("تاريخ الطلب", value=date.today())
        with col_c3:
            address = st.text_input("العنوان والمدينة *", placeholder="مثال: بغداد - المنصور")
            status = st.selectbox("حالة الطلب", ["قيد التصميم", "قيد التصنيع", "جاهز للتركيب", "مكتمل", "ملغي"])

        st.markdown("---")
        st.markdown("#### 2️⃣ المواصفات الفنية للعمل")
        project_type = st.selectbox(
            "اختر نوع المشروع *",
            options=["kitchen", "wardrobe", "bedroom", "bed", "decor", "other"],
            format_func=lambda x: {
                "kitchen": "🍳 مطبخ (كاونتر كامل)",
                "wardrobe": "🚪 خزانة ملابس (كبت)",
                "bedroom": "🛏️ غرفة نوم كاملة",
                "bed": "🛌 سرير منفصل",
                "decor": "🖼️ ديكورات وتلبيس جداري / TV Unit",
                "other": "🔨 مشروع أو طلب مخصص آخر"
            }[x]
        )

        specs = {}
        if project_type == "kitchen":
            k_col1, k_col2, k_col3 = st.columns(3)
            with k_col1:
                specs["floorSize"] = st.number_input("قياس القطعة الأرضية (متر طولي) *", min_value=0.0, step=0.1, value=4.5)
                specs["upperSize"] = st.number_input("قياس القطعة العلوية (متر طولي) *", min_value=0.0, step=0.1, value=4.5)
            with k_col2:
                specs["shape"] = st.selectbox("شكل المطبخ", ["I (مستقيم)", "L (زاوي)", "U (حرف يو)", "مع جزيرة (Island)"])
                specs["structureColor"] = st.text_input("لون ونوع الهيكل الداخلي", value="MDF أبيض مقاوم للرطوبة")
            with k_col3:
                specs["doorType"] = st.selectbox("نوع الأبواب والواجهات", ["HDF بالون بريس", "MDF تركي سادة", "MDF هاي جلوس لمعة عالية", "ألمنيوم كلادينج"])
                specs["countertopMain"] = st.selectbox("سطح العمل (المرمر/الكاونتر)", ["كوريان صناعي صب", "كوارتز تركي", "رخام طبيعي غرانيت", "سيراميك وبورسلين"])

            k_sub1, k_sub2, k_sub3 = st.columns(3)
            with k_sub1:
                specs["balloonStyle"] = st.selectbox("نمط الدرف", ["سادة مودرن", "نقش CNC كلاسيك", "فريم زجاج"])
                specs["balloonPatternCode"] = st.text_input("كود النقش (إن وجد)", placeholder="مثال: CNC-402")
            with k_sub2:
                specs["balloonPrimaryColor"] = st.text_input("كود اللون الأساسي للدرف", placeholder="مثال: بيج فاتح B-12")
                specs["balloonSecondaryColor"] = st.text_input("كود اللون الثانوي", placeholder="مثال: خشبي سنديان W-05")
            with k_sub3:
                specs["handles"] = st.selectbox("نوع المقابض", ["بروفيل مخفي دفن (Gola)", "مقابض خارجية مودرن", "نظام ضغط Touch / تكة", "مقابض كلاسيك"])

            st.write("🔌 الأجهزة والملحقات الكهربائية")
            app_col1, app_col2, app_col3 = st.columns(3)
            with app_col1:
                specs["hasAppliances"] = st.checkbox("تجهيز أجهزة كهربائية بلت ان", value=True)
                specs["cookerStatus"] = st.text_input("الطباخ / الهوب", value="بلت ان 90 سم غاز")
            with app_col2:
                specs["hoodSize"] = st.text_input("شفاط الهواء (الهود)", value="90 سم مدمج")
                specs["fridge"] = st.text_input("مقاس فراغ الثلاجة", value="عرض 90 سم × ارتفاع 185 سم")
            with app_col3:
                specs["soapBasket"] = st.selectbox("سلة منظفات هيدروليك", ["نعم", "لا"])
                specs["dishBasket"] = st.selectbox("سلة صحون هيدروليك", ["نعم", "لا"])
                specs["appliancesNotes"] = st.text_input("ملاحظات إضافية للأجهزة", placeholder="مكان غسالة صحون...")

        elif project_type == "wardrobe":
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                specs["width"] = st.number_input("عرض الخزانة (متر)", min_value=0.0, step=0.1, value=3.0)
                specs["height"] = st.number_input("ارتفاع الخزانة (متر)", min_value=0.0, step=0.1, value=2.7)
            with w_col2:
                specs["depth"] = st.number_input("عمق الخزانة (متر)", min_value=0.0, step=0.05, value=0.65)
                specs["doorType"] = st.selectbox("نوع الأبواب", ["أبواب سحاب Sliding", "أبواب مفصلات عادية", "زجاج فيميه وإطار أسود"])
            with w_col3:
                specs["structureColor"] = st.text_input("لون الهيكل الداخلي", value="MDF بيج كتان")
                specs["handles"] = st.text_input("المقابض", value="بروفيل طولي ممتد")
            specs["wardrobeNotes"] = st.text_area("التقسيمات الداخلية والإضاءة", placeholder="عدد المجرات، أماكن التعليق، رفوف...")

        elif project_type == "bedroom":
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                specs["bedSize"] = st.selectbox("مقاس السرير المرفق", ["كينج 200×200 سم", "كوين 180×200 سم", "مزدوج 160×200 سم"])
                specs["wardrobeDims"] = st.text_input("مقاس الكبت / الدولاب", value="عرض 3.20م × ارتفاع 2.70م")
            with b_col2:
                specs["structureColor"] = st.text_input("الألوان المختارة", value="خشبي جوزي مع تطعيم رمادي")
                specs["bedroomNotes"] = st.text_area("القطع الإضافية", value="2x كومودينو جانبي، تسريحة ميز تواليت مع مرآة، بف تنجيد")

        elif project_type == "bed":
            bed_col1, bed_col2 = st.columns(2)
            with bed_col1:
                specs["bedSize"] = st.selectbox("مقاس السرير", ["180 × 200 سم", "200 × 200 سم", "160 × 200 سم", "120 × 200 سم"])
                specs["coverType"] = st.selectbox("نوع التنجيد والهيدبورد", ["قماش مخملي تركي ناعم", "قماش كتان معالج", "جلد صناعي فاخر", "خشب كامل سادة"])
            with bed_col2:
                specs["hydraulic"] = st.selectbox("نظام التخزين السفلي (هيدروليك)", ["نعم، جك هيدروليك تركي أصلي", "لا، قاعدة خشبية ثابتة"])
                specs["bedNotes"] = st.text_area("ملاحظات السرير", placeholder="لون القماش، نقش التاج...")

        elif project_type == "decor":
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                specs["decorType"] = st.selectbox("نوع العمل الرئيسي", ["وحدة تلفزيون TV Unit متكاملة", "جدار بديل رخام وبديل خشب WPC", "قواطع خشبية بارتيشن", "مرايا شطف وليد"])
                specs["dimensions"] = st.text_input("المساحة أو الأبعاد", placeholder="مثال: عرض 4.0م × ارتفاع 3.0م")
            with d_col2:
                specs["decorNotes"] = st.text_area("المواصفات الفنية ومصادر الإضاءة", placeholder="ألوان الشرائح، نوع الإنارة...")

        else:
            specs["otherNotes"] = st.text_area("تفاصيل ومواصفات الطلب المخصص بالكامل *", placeholder="اكتب كافة المواصفات والقياسات...")

        client_notes = st.text_area("ملاحظات عامة حول الطلب والعقد", placeholder="شروط التسليم، مواعيد الدفعات...")

        st.markdown("---")
        st.markdown("#### 3️⃣ الحسابات المالية والأسعار")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            currency = st.selectbox("العملة", ["IQD", "USD"], format_func=lambda x: "دينار عراقي (IQD)" if x == "IQD" else "دولار أمريكي (USD)")
            base_price = st.number_input("السعر الأساسي الإجمالي للعمل *", min_value=0.0, step=50000.0, value=3000000.0)
        with f_col2:
            discount_percent = st.number_input("نسبة الخصم المئوية (%)", min_value=0.0, max_value=100.0, step=0.5, value=0.0)
            discount_amount = (base_price * (discount_percent / 100.0))
            price_after_discount = base_price - discount_amount
            st.markdown(f"**قيمة الخصم:** {format_currency(discount_amount, currency)}")
            st.markdown(f"**السعر النهائي بعد الخصم:** <span style='color:#00dbde; font-weight:700;'>{format_currency(price_after_discount, currency)}</span>", unsafe_allow_html=True)
        with f_col3:
            deposit_paid = st.number_input("المبلغ المدفوع كعربون أولى *", min_value=0.0, step=50000.0, value=1000000.0)
            remaining_balance = max(0.0, price_after_discount - deposit_paid)
            st.markdown(f"**المبلغ المتبقي بذمة العميل:** <span style='color:#f43f5e; font-weight:700;'>{format_currency(remaining_balance, currency)}</span>", unsafe_allow_html=True)

        st.write("")
        submit_btn = st.form_submit_button("💾 حفظ المشروع والعميل فوراً", use_container_width=True, type="primary")

        if submit_btn:
            if not name.strip():
                st.error("يرجى كتابة اسم العميل أولاً!")
            elif not phone.strip():
                st.error("يرجى إدخال رقم هاتف العميل!")
            else:
                new_client = {
                    "serial": serial,
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "address": address.strip(),
                    "date": str(order_date),
                    "projectType": project_type,
                    "status": status,
                    "notes": client_notes,
                    "specs": specs,
                    "financials": {
                        "currency": currency,
                        "basePrice": base_price,
                        "discountPercent": discount_percent,
                        "discountAmount": discount_amount,
                        "priceAfterDiscount": price_after_discount,
                        "depositPaid": deposit_paid,
                        "totalPaid": deposit_paid,
                        "remainingBalance": remaining_balance
                    },
                    "payments": [
                        {
                            "id": 1,
                            "date": str(order_date),
                            "amount": deposit_paid,
                            "note": "العربون الأولي وتثبيت الطلب"
                        }
                    ] if deposit_paid > 0 else []
                }

                st.session_state.db["clients"].append(new_client)
                save_data(st.session_state.db)
                st.success(f"تم بنجاح حفظ المشروع الخاص بالعميل ({name}) بالرقم {serial}!")
                st.balloons()

# -------------------------------------------------------------
# 3. سجل وقائمة العملاء
# -------------------------------------------------------------
elif menu_choice == "👥 سجل وقائمة العملاء":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>👥</span> سجل وقائمة العملاء والمشاريع</h1>
                <p>البحث، التصفية، والتعديل الفوري لبيانات القياسات والعقود</p>
            </div>
            <div class="hero-badge">إدارة السجلات</div>
        </div>
    """, unsafe_allow_html=True)

    clients = st.session_state.db.get("clients", [])
    if not clients:
        st.info("لا يوجد أي عملاء مسجلين حالياً.")
    else:
        s_col1, s_col2, s_col3 = st.columns([2, 1, 1])
        with s_col1:
            search_query = st.text_input("🔍 بحث باسم العميل أو الهاتف أو التسلسل", placeholder="اكتب للبحث...")
        with s_col2:
            filter_type = st.selectbox("تصفية حسب نوع المشروع", ["الكل", "kitchen", "wardrobe", "bedroom", "bed", "decor", "other"],
                                      format_func=lambda x: "الكل" if x == "الكل" else {
                                          "kitchen": "مطبخ", "wardrobe": "خزانة", "bedroom": "غرفة نوم", "bed": "سرير", "decor": "ديكور", "other": "أخرى"
                                      }.get(x, x))
        with s_col3:
            filter_status = st.selectbox("تصفية حسب الحالة", ["الكل", "قيد التصميم", "قيد التصنيع", "جاهز للتركيب", "مكتمل", "ملغي"])

        filtered = []
        for c in clients:
            match_search = True
            if search_query.strip():
                q = search_query.strip().lower()
                c_str = f"{c.get('name','')} {c.get('phone','')} {c.get('serial','')}".lower()
                if q not in c_str:
                    match_search = False

            match_type = True
            if filter_type != "الكل" and c.get("projectType") != filter_type:
                match_type = False

            match_status = True
            if filter_status != "الكل" and c.get("status") != filter_status:
                match_status = False

            if match_search and match_type and match_status:
                filtered.append(c)

        st.write(f"عدد النتائج المطابقة: **{len(filtered)}**")

        for idx, client in enumerate(filtered):
            fin = client.get("financials", {})
            curr = fin.get("currency", "IQD")
            rem = fin.get("remainingBalance", 0)
            status_color = "#22c55e" if client.get("status") == "مكتمل" else "#38bdf8" if client.get("status") == "جاهز للتركيب" else "#f59e0b"

            with st.expander(f"📌 [{client.get('serial')}] {client.get('name')} | الهاتف: {client.get('phone')} | المتبقي: {format_currency(rem, curr)}", expanded=(idx == 0)):
                info_col1, info_col2, info_col3 = st.columns(3)
                with info_col1:
                    st.write(f"**العنوان:** {client.get('address')}")
                    st.write(f"**تاريخ العقد:** {client.get('date')}")
                    st.markdown(f"**الحالة:** <span style='color:{status_color}; font-weight:700;'>{client.get('status')}</span>", unsafe_allow_html=True)
                with info_col2:
                    st.write(f"**السعر الكلي:** {format_currency(fin.get('basePrice', 0), curr)}")
                    st.write(f"**الخصم:** {fin.get('discountPercent', 0)}% ({format_currency(fin.get('discountAmount', 0), curr)})")
                    st.write(f"**الصافي بعد الخصم:** {format_currency(fin.get('priceAfterDiscount', 0), curr)}")
                with info_col3:
                    st.write(f"**المدفوع الكلي:** {format_currency(fin.get('totalPaid', 0), curr)}")
                    st.markdown(f"**المتبقي بذمة العميل:** <span style='color:#f43f5e; font-weight:800; font-size:1.1rem;'>{format_currency(rem, curr)}</span>", unsafe_allow_html=True)

                st.markdown("**المواصفات الفنية:**")
                specs = client.get("specs", {})
                if specs:
                    sp_cols = st.columns(3)
                    i = 0
                    for k, v in specs.items():
                        if v and str(v) != "False":
                            with sp_cols[i % 3]:
                                st.write(f"- **{k}:** {v}")
                            i += 1
                if client.get("notes"):
                    st.info(f"📝 **ملاحظات:** {client.get('notes')}")

                action_col1, action_col2, _ = st.columns([1, 1, 3])
                with action_col1:
                    new_st = st.selectbox(
                        "تحديث الحالة سريعاً",
                        ["قيد التصميم", "قيد التصنيع", "جاهز للتركيب", "مكتمل", "ملغي"],
                        index=["قيد التصميم", "قيد التصنيع", "جاهز للتركيب", "مكتمل", "ملغي"].index(client.get("status", "قيد التصميم")),
                        key=f"st_select_{client.get('serial')}"
                    )
                    if new_st != client.get("status"):
                        client["status"] = new_st
                        save_data(st.session_state.db)
                        st.success("تم تحديث حالة العقد!")
                        st.rerun()

                with action_col2:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ حذف هذا العميل", key=f"del_{client.get('serial')}"):
                        st.session_state.db["clients"] = [c for c in st.session_state.db["clients"] if c.get("serial") != client.get("serial")]
                        save_data(st.session_state.db)
                        st.warning(f"تم حذف العميل {client.get('name')} بنجاح.")
                        st.rerun()

# -------------------------------------------------------------
# 4. إدارة الدفعات والأقساط
# -------------------------------------------------------------
elif menu_choice == "💰 إدارة الدفعات والأقساط":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>💰</span> إدارة الدفعات والأقساط المالية</h1>
                <p>تسجيل الدفعات الإضافية وتحديث حسابات العميل تلقائياً</p>
            </div>
            <div class="hero-badge">المالية والحسابات</div>
        </div>
    """, unsafe_allow_html=True)

    clients = st.session_state.db.get("clients", [])
    if not clients:
        st.info("لا يوجد أي عملاء مسجلين حالياً.")
    else:
        client_options = {f"{c.get('serial')} - {c.get('name')} (المتبقي: {format_currency(c.get('financials',{}).get('remainingBalance',0), c.get('financials',{}).get('currency','IQD'))})": c for c in clients}
        selected_client_key = st.selectbox("اختر العميل لعرض أو إضافة دفعات مالية", list(client_options.keys()))
        selected_client = client_options[selected_client_key]

        fin = selected_client.get("financials", {})
        curr = fin.get("currency", "IQD")
        payments = selected_client.setdefault("payments", [])

        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1:
            st.metric("السعر الإجمالي بعد الخصم", format_currency(fin.get("priceAfterDiscount", 0), curr))
        with c_col2:
            st.metric("إجمالي المبالغ المسددة", format_currency(fin.get("totalPaid", 0), curr))
        with c_col3:
            rem = fin.get("remainingBalance", 0)
            st.metric("المتبقي بذمة العميل", format_currency(rem, curr), delta="-مسدد بالكامل" if rem <= 0 else "متبقي دفعات")

        st.markdown("---")
        st.markdown("#### 📜 سجل الدفعات المسددة للعميل")
        if payments:
            df_pay = pd.DataFrame(payments)
            df_pay["المبلغ"] = df_pay["amount"].apply(lambda a: format_currency(a, curr))
            df_display = df_pay[["id", "date", "المبلغ", "note"]].rename(columns={
                "id": "رقم الدفعة",
                "date": "التاريخ",
                "note": "البيان / الملاحظة"
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد دفعات مسجلة لهذا العميل حتى الآن.")

        st.markdown("#### ➕ تسجيل دفعة / قسط جديد")
        with st.form("add_payment_form"):
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                pay_amount = st.number_input("مبلغ الدفعة المستلمة *", min_value=1.0, step=50000.0, value=min(250000.0, float(rem) if rem > 0 else 50000.0))
            with p_col2:
                pay_date = st.date_input("تاريخ استلام الدفعة", value=date.today())
            with p_col3:
                pay_note = st.text_input("البيان والملاحظة", value="دفعة مرحلية حسب الاتفاق")

            add_pay_btn = st.form_submit_button("💵 اعتماد وتسجيل الدفعة فوراً", type="primary")

            if add_pay_btn:
                new_id = len(payments) + 1
                payments.append({
                    "id": new_id,
                    "date": str(pay_date),
                    "amount": pay_amount,
                    "note": pay_note.strip()
                })

                total_paid = sum(p["amount"] for p in payments)
                fin["totalPaid"] = total_paid
                fin["remainingBalance"] = max(0.0, fin.get("priceAfterDiscount", 0) - total_paid)

                save_data(st.session_state.db)
                st.success(f"تم بنجاح تسجيل دفعة بقيمة {format_currency(pay_amount, curr)}!")
                st.rerun()

# -------------------------------------------------------------
# 5. الفاتورة وسند العقد للطباعة
# -------------------------------------------------------------
elif menu_choice == "🧾 سند العقد والفاتورة للطباعة":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>🧾</span> سند التعاقد وفاتورة القياسات للطباعة</h1>
                <p>توليد سند اتفاق وفاتورة رسمية كاملة جاهزة للطباعة أو الحفظ كـ PDF</p>
            </div>
            <div class="hero-badge">سند معتمد</div>
        </div>
    """, unsafe_allow_html=True)

    clients = st.session_state.db.get("clients", [])
    if not clients:
        st.info("لا توجد مشاريع مسجلة بعد.")
    else:
        client_options = {f"{c.get('serial')} - {c.get('name')}": c for c in clients}
        chosen_client_key = st.selectbox("اختر العميل لإنشاء السند والفاتورة له:", list(client_options.keys()))
        cl = client_options[chosen_client_key]
        fin = cl.get("financials", {})
        curr = fin.get("currency", "IQD")
        specs = cl.get("specs", {})
        payments = cl.get("payments", [])

        st.markdown("""
            <div style="text-align: left; margin-bottom: 10px;">
                <button onclick="window.print()" style="background:#0284c7; color:#fff; border:none; padding:10px 24px; border-radius:8px; font-weight:700; cursor:pointer; font-size:0.95rem;">
                    🖨️ طباعة الفاتورة أو حفظها كـ PDF
                </button>
            </div>
        """, unsafe_allow_html=True)

        specs_rows = ""
        for k, v in specs.items():
            if v and str(v) != "False":
                specs_rows += f"<tr><td style='font-weight:700; width:35%;'>{k}</td><td>{v}</td></tr>"

        payments_rows = ""
        for p in payments:
            payments_rows += f"<tr><td>{p.get('id')}</td><td>{p.get('date')}</td><td>{format_currency(p.get('amount'), curr)}</td><td>{p.get('note')}</td></tr>"

        invoice_html = f"""
        <div class="printable-invoice" id="invoiceArea">
            <div style="border-bottom: 2px solid #0284c7; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin:0; font-size:1.8rem; color:#0369a1 !important; font-weight:900;">معمل وورشة قياساتي للأثاث والديكور</h2>
                    <p style="margin:4px 0 0 0; color:#475569 !important; font-size:0.9rem;">تصميم وتفصيل مطابخ عصرية، غرف نوم، خزائن وديكورات داخلية</p>
                </div>
                <div style="text-align: left; direction:ltr;">
                    <div style="font-weight:800; font-size:1.3rem; color:#0f172a !important;">{cl.get('serial')}</div>
                    <div style="color:#64748b !important; font-size:0.85rem;">تاريخ العقد: {cl.get('date')}</div>
                </div>
            </div>

            <table class="invoice-table">
                <tr>
                    <th colspan="4" style="background:#e0f2fe; color:#0369a1 !important; font-size:1.05rem;">بيانات العميل والطلب</th>
                </tr>
                <tr>
                    <td style="font-weight:700; width:18%;">اسم العميل:</td>
                    <td style="width:32%; font-weight:800;">{cl.get('name')}</td>
                    <td style="font-weight:700; width:18%;">رقم الهاتف:</td>
                    <td style="width:32%;">{cl.get('phone')}</td>
                </tr>
                <tr>
                    <td style="font-weight:700;">العنوان:</td>
                    <td>{cl.get('address')}</td>
                    <td style="font-weight:700;">نوع العمل:</td>
                    <td style="font-weight:800; color:#0284c7 !important;">{cl.get('projectType')}</td>
                </tr>
            </table>

            <table class="invoice-table">
                <tr>
                    <th colspan="2" style="background:#e0f2fe; color:#0369a1 !important; font-size:1.05rem;">المواصفات الفنية المعتمدة للطلب</th>
                </tr>
                {specs_rows if specs_rows else "<tr><td colspan='2'>لا توجد مواصفات مدخلة</td></tr>"}
            </table>

            <table class="invoice-table">
                <tr>
                    <th colspan="4" style="background:#e0f2fe; color:#0369a1 !important; font-size:1.05rem;">البيانات المالية وجدول الدفعات</th>
                </tr>
                <tr>
                    <td style="font-weight:700;">السعر الأساسي:</td>
                    <td>{format_currency(fin.get('basePrice', 0), curr)}</td>
                    <td style="font-weight:700;">الخصم الممنوح:</td>
                    <td>{fin.get('discountPercent', 0)}% ({format_currency(fin.get('discountAmount', 0), curr)})</td>
                </tr>
                <tr>
                    <td style="font-weight:700;">الصافي بعد الخصم:</td>
                    <td style="font-weight:800; color:#0369a1 !important;">{format_currency(fin.get('priceAfterDiscount', 0), curr)}</td>
                    <td style="font-weight:700;">إجمالي المدفوع:</td>
                    <td style="font-weight:800; color:#16a34a !important;">{format_currency(fin.get('totalPaid', 0), curr)}</td>
                </tr>
                <tr>
                    <td colspan="2" style="font-weight:700; background:#fef2f2; color:#b91c1c !important;">المبلغ المتبقي بذمة العميل:</td>
                    <td colspan="2" style="font-weight:900; background:#fef2f2; color:#b91c1c !important; font-size:1.2rem;">
                        {format_currency(fin.get('remainingBalance', 0), curr)}
                    </td>
                </tr>
            </table>

            <h4 style="margin:20px 0 8px 0; color:#0369a1 !important;">سجل الدفعات المسددة:</h4>
            <table class="invoice-table">
                <tr>
                    <th>ت</th>
                    <th>التاريخ</th>
                    <th>المبلغ المسدد</th>
                    <th>البيان والملاحظة</th>
                </tr>
                {payments_rows if payments_rows else "<tr><td colspan='4'>لم تسجل أي دفعات حتى الآن</td></tr>"}
            </table>

            <div style="margin-top: 35px; display: flex; justify-content: space-between; padding: 0 30px;">
                <div style="text-align: center;">
                    <p style="margin: 0; font-weight: 700;">توقيع واستلام العميل</p>
                    <p style="margin-top: 40px; color:#94a3b8 !important;">____________________</p>
                </div>
                <div style="text-align: center;">
                    <p style="margin: 0; font-weight: 700;">ختم وتوقيع الورشة والمعمل</p>
                    <p style="margin-top: 40px; color:#94a3b8 !important;">____________________</p>
                </div>
            </div>
        </div>
        """
        st.markdown(invoice_html, unsafe_allow_html=True)

# -------------------------------------------------------------
# 6. النسخ الاحتياطي
# -------------------------------------------------------------
elif menu_choice == "💾 النسخ الاحتياطي وإعدادات البيانات":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>💾</span> النسخ الاحتياطي وإدارة البيانات</h1>
                <p>تصدير واستيراد بيانات العملاء والقياسات لضمان عدم ضياع أي سجل</p>
            </div>
            <div class="hero-badge">أمان وتخزين</div>
        </div>
    """, unsafe_allow_html=True)

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.markdown("### 📤 تصدير نسخة احتياطية (Download)")
        st.write("تحميل ملف يحتوي على كافة بيانات العملاء والحسابات المسجلة:")
        data_json_str = json.dumps(st.session_state.db, ensure_ascii=False, indent=2)
        st.download_button(
            label="⬇️ تحميل النسخة الاحتياطية (qiyasati_backup.json)",
            data=data_json_str,
            file_name=f"qiyasati_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    with b_col2:
        st.markdown("### 📥 استيراد نسخة احتياطية (Restore)")
        st.write("استرجاع البيانات من ملف JSON محفوظ مسبقاً:")
        uploaded_file = st.file_uploader("اختر ملف النسخة الاحتياطية", type=["json"])
        if uploaded_file is not None:
            try:
                imported_data = json.load(uploaded_file)
                if "clients" in imported_data:
                    if st.button("تأكيد استبدال واسترجاع البيانات", type="primary", use_container_width=True):
                        st.session_state.db = imported_data
                        save_data(imported_data)
                        st.success("تم بنجاح استعادة البيانات!")
                        st.rerun()
                else:
                    st.error("صيغة الملف غير متوافقة.")
            except Exception as ex:
                st.error(f"خطأ أثناء قراءة الملف: {ex}")

# -------------------------------------------------------------
# 7. لوحة المالك وتوليد الأكواد (Owner / Admin Portal)
# -------------------------------------------------------------
elif menu_choice == "👑 لوحة المالك وتوليد الأكواد":
    st.markdown("""
        <div class="hero-header">
            <div class="hero-title-box">
                <h1><span>👑</span> لوحة إدارة الاشتراكات وتوليد الأكواد</h1>
                <p>خاص بمالك البرنامج — توليد أكواد التفعيل وإرسالها عبر واتساب بضغطة واحدة</p>
            </div>
            <div class="hero-badge">لوحة الإدارة</div>
        </div>
    """, unsafe_allow_html=True)

    is_owner_authenticated = is_admin_user
    admin_pin = ""
    if not is_owner_authenticated:
        admin_pin = st.text_input("أدخل الرمز السري للإدارة (Admin PIN):", type="password", placeholder="الرمز الافتراضي: 9988")
        if admin_pin == ADMIN_PIN:
            is_owner_authenticated = True
        elif admin_pin:
            st.error("الرمز السري غير صحيح!")
        else:
            st.info("يرجى إدخال رمز الإدارة السري (PIN) لعرض وتوليد الأكواد.")

    if is_owner_authenticated:
        st.success("✅ تم تأكيد هوية مالك النظام — تحكم كامل ومصادقة فورية.")

        # ===== 1. طلبات الدفع المعلقة =====
        st.markdown("### 🔔 طلبات التحويل والدفع الواردة من العملاء")
        reqs = st.session_state.db.get("payment_requests", [])
        pending_reqs = [r for r in reqs if r.get("status") == "PENDING"]

        if pending_reqs:
            st.warning(f"⚠️ يوجد **{len(pending_reqs)}** طلب تحويل بانتظار مصادقتك. بمجرد تأكيدك، سيفتح التطبيق تلقائياً أمام المشترك:")
            for req in pending_reqs:
                with st.container():
                    st.markdown(f"""
                        <div style="background:#1e293b; border-radius:12px; padding:14px 18px; margin-bottom:10px; border-right:4px solid #f59e0b;">
                            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                                <div>
                                    <span style="color:#facc15; font-weight:900; font-size:1rem;">👤 {req.get('user_name')}</span>
                                    <span style="color:#94a3b8; font-size:0.82rem; margin-right:8px;">({req.get('user_contact')})</span>
                                    <br>
                                    <span style="color:#f8fafc; font-size:0.88rem;">💳 {req.get('payment_method')} — رقم الحوالة: <code>{req.get('ref_info')}</code></span>
                                </div>
                                <div style="text-align:left;">
                                    <span style="background:rgba(245,158,11,0.2); color:#fbbf24; padding:3px 10px; border-radius:8px; font-size:0.8rem; font-weight:700;">{req.get('plan_title')}</span>
                                    <br><span style="color:#64748b; font-size:0.75rem;">⏱️ {req.get('timestamp','')}</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
                    with btn_col1:
                        # إشعار واتساب قبل التأكيد
                        months_r = req.get("months", 6)
                        u_contact_raw = req.get("user_contact", "")
                        # تحضير رقم هاتف للواتساب
                        wa_contact = u_contact_raw.replace("+", "").replace(" ", "").replace("-", "")
                        if wa_contact.startswith("0"):
                            wa_contact = "964" + wa_contact[1:]
                        if not wa_contact.startswith("964") and len(wa_contact) <= 10:
                            wa_contact = "964" + wa_contact
                        wa_preview_msg = f"مرحباً {req.get('user_name')}،\n✅ تم استلام تحويلك بنجاح وتم تفعيل اشتراكك.\n🎁 الباقة: {req.get('plan_title')}\nيمكنك الآن الدخول للنظام مباشرة. شكراً لاختيارك برنامج قياساتي!"
                        wa_url_preview = f"https://wa.me/{wa_contact}?text={wa_preview_msg}"
                        st.markdown(f"""
                            <a href="{wa_url_preview}" target="_blank" class="wa-btn" style="font-size:0.82rem; padding:7px 14px;">
                                💬 إرسال إشعار واتساب للعميل
                            </a>
                        """, unsafe_allow_html=True)
                    with btn_col2:
                        if st.button("✅ تأكيد وتفعيل الحساب فوراً", key=f"appr_{req.get('id')}", type="primary", use_container_width=True):
                            months = req.get("months", 6)
                            u_contact = req.get("user_contact")
                            if u_contact in st.session_state.db.get("users", {}):
                                target_u = st.session_state.db["users"][u_contact]
                                curr_exp = datetime.strptime(target_u["expiry_date"], "%Y-%m-%d").date()
                                base_d = max(date.today(), curr_exp)
                                add_days = 180 if months == 6 else 365
                                new_exp_date = str(base_d + timedelta(days=add_days))
                                target_u["expiry_date"] = new_exp_date
                                target_u["subscription_type"] = f"PAID_{months}M"
                                target_u["pending_payment"] = False
                                req["status"] = "APPROVED"
                                req["approved_at"] = str(datetime.now())
                                save_data(st.session_state.db)
                                # حفظ معلومات للإشعار
                                st.session_state[f"approved_user_{req.get('id')}"] = {
                                    "name": target_u["name"],
                                    "contact": u_contact,
                                    "months": months,
                                    "expiry": new_exp_date
                                }
                                st.success(f"🎉 تمت المصادقة وتفعيل اشتراك {months} شهر للعميل ({target_u['name']}) بنجاح!")
                                st.rerun()
                    with btn_col3:
                        if st.button("❌ رفض الطلب", key=f"rej_{req.get('id')}", use_container_width=True):
                            req["status"] = "REJECTED"
                            req["rejected_at"] = str(datetime.now())
                            save_data(st.session_state.db)
                            st.info("تم رفض الطلب.")
                            st.rerun()
                    st.markdown("<hr style='border-color:#1e293b; margin:6px 0;'>", unsafe_allow_html=True)
        else:
            st.info("✅ لا توجد طلبات دفع معلقة حالياً — كل شيء مرتب!")

        # عرض نتائج المصادقة المؤخرة مع زر واتساب
        for key in list(st.session_state.keys()):
            if key.startswith("approved_user_"):
                info = st.session_state[key]
                wa_c = info["contact"].replace("+","").replace(" ","")
                if wa_c.startswith("0"): wa_c = "964" + wa_c[1:]
                wa_msg_approved = f"مرحباً {info['name']}،\n🎉 تهانينا! تم تفعيل اشتراكك بنجاح لمدة {info['months']} شهر.\n📅 ينتهي اشتراكك بتاريخ: {info['expiry']}\nيمكنك الآن الدخول لنظام قياساتي والاستمتاع بكافة الميزات.\nشكراً لثقتك بنا! 💙"
                wa_url_approved = f"https://wa.me/{wa_c}?text={wa_msg_approved}"
                st.markdown(f"""
                    <div style="background:rgba(34,197,94,0.12); border:1px solid #22c55e; border-radius:10px; padding:12px 16px; margin:10px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                        <span style="color:#22c55e; font-weight:700;">✅ تم تفعيل حساب: {info['name']} ({info['months']} شهر) — ينتهي {info['expiry']}</span>
                        <a href="{wa_url_approved}" target="_blank" class="wa-btn">
                            💬 إرسال تهنئة واتساب فورية
                        </a>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # ===== 2. توليد أكواد التفعيل =====
        gen_col1, gen_col2 = st.columns(2)
        with gen_col1:
            st.markdown("### ⚡ توليد كود تفعيل جديد وإرساله")
            with st.form("gen_code_form"):
                months_select = st.selectbox(
                    "نوع باقة الاشتراك:",
                    [6, 12],
                    format_func=lambda m: f"باقة {m} أشهر ({'50$' if m==6 else '80$'})"
                )
                buyer_note = st.text_input("اسم العميل أو ملاحظة الدفع:", placeholder="مثال: أحمد بغداد — فاست بي")
                buyer_phone = st.text_input("رقم هاتف العميل للواتساب (اختياري):", placeholder="مثال: 07701234567")
                gen_btn = st.form_submit_button("🔑 إنشاء كود التفعيل + رابط واتساب", type="primary", use_container_width=True)

                if gen_btn:
                    new_code = generate_paid_code(months_select, buyer_note)
                    st.session_state.db.setdefault("generated_codes", []).append({
                        "code": new_code,
                        "months": months_select,
                        "buyer_note": buyer_note,
                        "buyer_phone": buyer_phone,
                        "created_at": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    })
                    save_data(st.session_state.db)
                    st.session_state["last_generated_code"] = new_code
                    st.session_state["last_gen_months"] = months_select
                    st.session_state["last_gen_phone"] = buyer_phone
                    st.session_state["last_gen_note"] = buyer_note
                    st.success(f"✅ تم إنشاء الكود بنجاح!")
                    st.rerun()

            # عرض آخر كود تم توليده مع رابط واتساب فوري
            if st.session_state.get("last_generated_code"):
                lcode = st.session_state["last_generated_code"]
                lmonths = st.session_state.get("last_gen_months", 6)
                lphone = st.session_state.get("last_gen_phone", "")
                lnote = st.session_state.get("last_gen_note", "")

                st.markdown(f"""
                    <div style="background:rgba(0,219,222,0.1); border:2px solid #00dbde; border-radius:12px; padding:16px; text-align:center; margin-top:12px;">
                        <div style="color:#94a3b8; font-size:0.82rem; margin-bottom:6px;">✨ آخر كود تم توليده:</div>
                        <div style="color:#00dbde; font-size:1.6rem; font-weight:900; letter-spacing:3px; direction:ltr; font-family:monospace;">{lcode}</div>
                        <div style="color:#94a3b8; font-size:0.78rem; margin-top:4px;">باقة {lmonths} شهر · {lnote}</div>
                    </div>
                """, unsafe_allow_html=True)

                # توليد رابط واتساب مع الكود
                wa_phone = lphone.replace("+","").replace(" ","").replace("-","")
                if wa_phone.startswith("0"): wa_phone = "964" + wa_phone[1:]
                plan_name = f"{lmonths} أشهر ({'50$' if lmonths==6 else '80$'})"
                wa_code_msg = f"مرحباً {lnote}،\n🎁 كود تفعيل اشتراكك في برنامج قياساتي:\n\n🔑 الكود: {lcode}\n\n📦 الباقة: {plan_name}\n\nطريقة التفعيل:\n1️⃣ افتح التطبيق\n2️⃣ اذهب إلى 'التفعيل المباشر بكود الاشتراك'\n3️⃣ أدخل الكود أعلاه\n4️⃣ سيفتح التطبيق تلقائياً ✅\n\nشكراً لاختيارك برنامج قياساتي 💙"

                wa_target = f"https://wa.me/{wa_phone}?text={wa_code_msg}" if wa_phone and len(wa_phone) >= 10 else f"https://wa.me/?text={wa_code_msg}"

                st.markdown(f"""
                    <div style="text-align:center; margin-top:12px;">
                        <a href="{wa_target}" target="_blank" class="wa-btn" style="font-size:0.95rem; padding:12px 24px;">
                            💬 إرسال الكود عبر واتساب الآن
                        </a>
                    </div>
                """, unsafe_allow_html=True)

                if st.button("🗑️ مسح / توليد كود جديد", use_container_width=True):
                    for k in ["last_generated_code","last_gen_months","last_gen_phone","last_gen_note"]:
                        st.session_state.pop(k, None)
                    st.rerun()

        with gen_col2:
            st.markdown("### 📋 سجل الأكواد المولدة")
            codes_list = st.session_state.db.get("generated_codes", [])
            if codes_list:
                display_codes = []
                for c in reversed(codes_list[-20:]):
                    display_codes.append({
                        "كود التفعيل": c.get("code",""),
                        "المدة": f"{c.get('months','')} شهر",
                        "العميل": c.get("buyer_note","")[:20],
                        "التاريخ": c.get("created_at","")[:16]
                    })
                st.dataframe(pd.DataFrame(display_codes), use_container_width=True, hide_index=True)
            else:
                st.info("لم يتم توليد أي أكواد بعد.")

        st.markdown("---")

        # ===== 3. قائمة المستخدمين =====
        st.markdown("### 👥 قائمة المستخدمين المسجلين في النظام")
        users_dict = st.session_state.db.get("users", {})
        if users_dict:
            user_rows = []
            for u in users_dict.values():
                try:
                    exp = datetime.strptime(u.get("expiry_date", "2026-01-01"), "%Y-%m-%d").date()
                    rem_d = (exp - date.today()).days
                except:
                    rem_d = 0
                sub_type = u.get("subscription_type", "")
                status_icon = "👑" if sub_type == "LIFETIME_VIP" else "✅" if "PAID" in sub_type else "🎁" if sub_type == "TRIAL" else "🔒"
                user_rows.append({
                    "": status_icon,
                    "الاسم": u.get("name",""),
                    "الهاتف / البريد": u.get("contact",""),
                    "نوع الاشتراك": sub_type,
                    "ينتهي في": u.get("expiry_date",""),
                    "الأيام المتبقية": f"{rem_d} يوم" if rem_d > 0 else "منتهي",
                    "الحالة": "✅ نشط" if rem_d > 0 else "❌ منتهي"
                })
            st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)

            # رابط واتساب جماعي للتجديد
            st.markdown(f"""
                <div style="margin-top:16px; padding:14px; background:#1e293b; border-radius:10px; border:1px solid #334155;">
                    <div style="color:#94a3b8; font-size:0.85rem; margin-bottom:8px;">📢 إرسال رسالة تجديد جماعية للعملاء المنتهية صلاحيتهم:</div>
                    <a href="https://wa.me/{PAYMENT_INFO['whatsapp']}?text=تذكير: يرجى تجديد اشتراككم في برنامج قياساتي للاستمرار في الوصول لجميع الميزات." target="_blank" class="wa-btn" style="font-size:0.82rem;">
                        💬 فتح واتساب للإرسال الجماعي
                    </a>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("لا يوجد مستخدمون مسجلون بعد.")

    elif admin_pin:
        st.error("الرمز السري غير صحيح!")
    else:
        st.info("يرجى إدخال رمز الإدارة السري (PIN) لعرض وتوليد الأكواد.")

