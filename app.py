import streamlit as st
import datetime

# ============================================
# FUO ENGINE — FULL FILE v4 (clean, complete)
# ============================================

st.set_page_config(page_title="ID-CDSS | FUO Engine v4", layout="wide")

st.markdown("""
<style>
    .dx_block { padding: 10px; margin-bottom: 6px; border-left: 8px solid #003366; background-color: #f2f6ff; }
    .dx_high { padding: 10px; margin-bottom: 6px; border-left: 8px solid #d90000; background-color: #ffe6e6; }
    .dx_med { padding: 10px; margin-bottom: 6px; border-left: 8px solid #e69500; background-color: #fff3cd; }
    .dx_low { padding: 10px; margin-bottom: 6px; border-left: 8px solid #3cb371; background-color: #eaffea; }
</style>
""", unsafe_allow_html=True)

# ====================================================================
# UNIVERSAL FUO WORKUP (IDSA CORE)
# ====================================================================
UNIVERSAL = [
    "Blood cultures x3",
    "CBC with differential",
    "CMP",
    "ESR",
    "CRP",
    "Urinalysis",
    "HIV 1/2 Ag/Ab (4th Gen)",
    "Chest X-ray",
]

# ====================================================================
# FUO DATABASE — trimmed to true FUO causes, NO acute killers
# ====================================================================
DATABASE = [
    # ---------------------------
    # ENDOCARDITIS
    # ---------------------------
    {"dx": "Endocarditis", "group": "Infectious",
     "triggers": ["New Murmur", "IVDU", "Prosthetic Valve", "Fever >= 5"],
     "orders": ["Blood cultures x3", "TTE", "TEE"]},

    # ---------------------------
    # TB
    # ---------------------------
    {"dx": "Tuberculosis (Miliary/Extrapulmonary)", "group": "Infectious",
     "triggers": ["Night Sweats", "Weight Loss", "Chronic Cough", "TB Risk", "Fever >= 14"],
     "orders": ["Quantiferon TB", "AFB Smear x3"]},

    # ---------------------------
    # HISTOPLASMOSIS
    # ---------------------------
    {"dx": "Disseminated Histoplasmosis", "group": "Endemic",
     "triggers": ["Missouri", "Bird/Bat", "Pancytopenia", "Fever >= 7"],
     "orders": ["Urine Histoplasma Ag", "Serum Histoplasma Ab"]},

    # ---------------------------
    # BLASTOMYCOSIS — ALWAYS INCLUDE WITH HISTO
    # ---------------------------
    {"dx": "Blastomycosis", "group": "Endemic",
     "triggers": ["Missouri", "Rural Living", "Pneumonia", "Skin Lesions", "Fever >= 7"],
     "orders": ["Urine Blastomyces Ag", "Fungal Culture"]},

    # ---------------------------
    # BARTONELLA
    # ---------------------------
    {"dx": "Bartonella", "group": "Infectious",
     "triggers": ["Cats", "Body Lice", "IVDU", "Fever >= 7"],
     "orders": ["Bartonella Serology"]},

    # ---------------------------
    # BRUCELLOSIS
    # ---------------------------
    {"dx": "Brucellosis", "group": "Infectious",
     "triggers": ["Unpasteurized Dairy", "Livestock", "Travel Med/Mexico", "Night Sweats", "Fever >= 7"],
     "orders": ["Brucella Serology"]},

    # ---------------------------
    # Q FEVER
    # ---------------------------
    {"dx": "Q Fever", "group": "Infectious",
     "triggers": ["Farm Animals", "Rural Living", "Fever >= 7"],
     "orders": ["Coxiella Serology", "TTE"]},

    # ---------------------------
    # CRYPTOCOCCUS (FUO-friendly version — not acute meningitis form)
    # ---------------------------
    {"dx": "Cryptococcosis", "group": "Infectious",
     "triggers": ["Headache", "Vision Changes", "Known HIV", "CD4 < 250", "Fever >= 7"],
     "orders": ["Serum CrAg", "Consider LP if neuro symptoms"]},

    # ---------------------------
    # MAC (FUO form — chronic, weight loss, anemia)
    # ---------------------------
    {"dx": "MAC (Disseminated)", "group": "Infectious",
     "triggers": ["Night Sweats", "Weight Loss", "Diarrhea", "Known HIV", "CD4 < 100", "Fever >= 14"],
     "orders": ["AFB Blood Culture"]},

    # ---------------------------
    # LYMPHOMA — ALWAYS IN FUO
    # ---------------------------
    {"dx": "Lymphoma", "group": "Non-Infectious",
     "triggers": ["Lymphadenopathy", "Night Sweats", "Weight Loss", "Splenomegaly", "Fever >= 14"],
     "orders": ["LDH", "CT Chest/Abd/Pelvis"]},

    # ---------------------------
    # GCA — classic FUO masquerader
    # ---------------------------
    {"dx": "Giant Cell Arteritis", "group": "Non-Infectious",
     "triggers": ["Age > 50", "Headache", "Jaw Claudication", "Vision Changes", "Fever >= 5"],
     "orders": ["ESR/CRP", "Temporal Artery US"]},
]

# ====================================================================
# FUO LOGIC ENGINE
# ====================================================================
def dx_engine(inputs):
    active = []
    for d in DATABASE:
        score = 0
        matched = []
        for t in d["triggers"]:
            if t in inputs["positives"]:
                matched.append(t)
                score += 1
        if score > 0:
            active.append({"dx": d["dx"], "group": d["group"],
                            "score": score, "triggers": matched, "orders": d["orders"]})
    active = sorted(active, key=lambda x: x["score"], reverse=True)
    return active

# ====================================================================
# PLAN BUILDER
# ====================================================================
def plan_builder(active, prior):
    orders = []
    for o in UNIVERSAL:
        if o not in prior:
            orders.append(o)
    for d in active:
        for o in d["orders"]:
            if o not in orders and o not in prior:
                orders.append(o)
    return orders

# ====================================================================
# UI LAYOUT
# ====================================================================
st.title("FUO Engine — ID-CDSS v4")

with st.sidebar:
    st.header("Patient Data")
    age = st.number_input("Age", 18, 100, 55)

    known_hiv = st.checkbox("Known HIV (regardless of prior control)")
    cd4 = st.number_input("CD4 count", 0, 1200, 400) if known_hiv else None

    st.header("Fever Duration")
    fever_days = st.number_input("Days of fever", 0, 365, 21)

    st.header("ROS – Symptoms")
    headache = st.checkbox("Headache")
    vision = st.checkbox("Vision changes")
    cough = st.checkbox("Chronic cough")
    diarrhea = st.checkbox("Diarrhea")
    night = st.checkbox("Night sweats")
    wt = st.checkbox("Weight loss")
    abd = st.checkbox("Abdominal pain")
    rash = st.checkbox("Rash")

    st.header("Exposures")
    cats = st.checkbox("Cats")
    lice = st.checkbox("Body lice")
    dairy = st.checkbox("Unpasteurized dairy")
    livestock = st.checkbox("Livestock")
    farm = st.checkbox("Farm animals")
    bat = st.checkbox("Bird/Bat exposure")
    medtrav = st.checkbox("Travel Med/Mexico")
    mo = st.checkbox("Missouri/Ohio River Valley")
    rural = st.checkbox("Rural living")
    ivdu = st.checkbox("IV drug use")

    st.header("Exam & Labs")
    lad = st.checkbox("Lymphadenopathy")
    splen = st.checkbox("Splenomegaly")
    oral = st.checkbox("Oral ulcers")
    pcyt = st.checkbox("Pancytopenia")

    st.header("Prior Negatives")
    prior = st.multiselect("Prior workup negative", UNIVERSAL + ["Quantiferon TB", "Histo Ag"])

run = st.button("Generate")

if run:
    positives = []

    # Fever duration tiers
    if fever_days >= 5: positives.append("Fever >= 5")
    if fever_days >= 7: positives.append("Fever >= 7")
    if fever_days >= 14: positives.append("Fever >= 14")

    # Symptoms
    for cond, name in [
        (headache, "Headache"), (vision, "Vision Changes"), (cough, "Chronic Cough"),
        (diarrhea, "Diarrhea"), (night, "Night Sweats"), (wt, "Weight Loss"),
        (abd, "Abdominal Pain"), (rash, "Rash"),
    ]:
        if
