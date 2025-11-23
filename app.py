import streamlit as st
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | FUO Engine v1", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .critical { border-left: 6px solid #dc3545; padding: 10px; background-color: #ffe6e6; font-weight: bold; }
    .noninf { border-left: 6px solid #17a2b8; padding: 10px; background-color: #e0f7fa; }
    .endo { border-left: 6px solid #fd7e14; padding: 10px; background-color: #fff3cd; }
</style>
""", unsafe_allow_html=True)

# --- LOGIC HELPERS ---
def faget(tmax, hr):
    return True if tmax >= 102 and hr < 100 else False

# --- DATABASE (FUO ONLY) ---
# Focused list: infections, inflammatory, malignancy, key opportunistics
DATABASE = [
    # INFECTIONS
    {
        "dx": "Endocarditis",
        "group": "Infectious",
        "triggers": ["New Murmur", "Splenomegaly", "IV Drug Use", "Prosthetic Valve"],
        "orders": ["Blood Cx x3", "TTE", "TEE"],
    },
    {
        "dx": "Tuberculosis (Miliary / Extrapulmonary)",
        "group": "Infectious",
        "triggers": ["Weight Loss", "Night Sweats", "Cough", "Hemoptysis", "Homelessness", "Travel TB"],
        "orders": ["Quantiferon TB", "AFB Smear x3"],
    },
    {
        "dx": "Histoplasmosis (Disseminated)",
        "group": "Endemic",
        "triggers": ["Missouri", "Bird/Bat", "Pancytopenia", "Oral Ulcers", "Splenomegaly"],
        "orders": ["Histo Urine/Serum Ag"],
    },
    {
        "dx": "Bartonella (Endocarditis / Bacteremia)",
        "group": "Infectious",
        "triggers": ["Cats", "Homelessness"],
        "orders": ["Bartonella Serology"],
    },
    {
        "dx": "Brucellosis",
        "group": "Infectious",
        "triggers": ["Unpasteurized Dairy", "Livestock", "Travel Med/Mexico"],
        "orders": ["Brucella Serology"],
    },
    {
        "dx": "Q Fever",
        "group": "Infectious",
        "triggers": ["Farm Animals", "Parturient Animals"],
        "orders": ["Coxiella Serology", "TTE"],
    },
    # HIV-OI (FUO eligible — chronic fever presentations)
    {
        "dx": "Cryptococcosis",
        "group": "Infectious",
        "triggers": ["Headache", "Vision Changes", "HIV", "CD4 < 250"],
        "orders": ["Serum CrAg", "LP if focal symptoms"],
    },
    {
        "dx": "MAC (Disseminated)",
        "group": "Infectious",
        "triggers": ["Night Sweats", "Weight Loss", "Anemia", "HIV", "CD4 < 100"],
        "orders": ["AFB Blood Cx"],
    },
    # NON-INFECTIOUS
    {
        "dx": "Temporal Arteritis (GCA)",
        "group": "Non-Infectious",
        "triggers": ["Age > 50", "Headache", "Jaw Claudication", "Vision Changes"],
        "orders": ["ESR/CRP", "Temporal Artery US"],
    },
    {
        "dx": "Adult Still's Disease",
        "group": "Non-Infectious",
        "triggers": ["Arthralgia", "Rash", "Ferritin > 1000"],
        "orders": ["Ferritin", "ANA/RF"],
    },
    {
        "dx": "Lymphoma",
        "group": "Non-Infectious",
        "triggers": ["Weight Loss", "Night Sweats", "Lymphadenopathy", "Splenomegaly"],
        "orders": ["LDH", "CT Chest/Abd/Pelvis"],
    },
]

# --- LOGIC ENGINE ---
def get_dx(inputs):
    active = []
    for d in DATABASE:
        score = 0
        matched = []
        for t in d["triggers"]:
            if t in inputs["positives"]:
                matched.append(t)
                score += 1
        # CD4 soft thresholds
        if "CD4 < 250" in d["triggers"] and inputs.get("cd4", 1000) < 250:
            score += 1
            matched.append("CD4 < 250")
        if score > 0:
            active.append({"dx": d["dx"], "group": d["group"], "score": score, "triggers": matched, "orders": d["orders"]})
    return sorted(active, key=lambda x: x["score"], reverse=True)

# --- PLAN BUILDER ---
def build_plan(active, prior):
    orders = []
    for dx in active:
        for o in dx["orders"]:
            if o not in orders and o not in prior:
                orders.append(o)
    return orders

# --- UI ---
st.title("FUO Engine — ID-CDSS v1")

with st.sidebar:
    st.header("Patient Data")
    age = st.number_input("Age", 18, 100, 55)
    sex = st.selectbox("Sex", ["Male", "Female"])
    immune = st.selectbox("Immune Status", ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"])
    cd4 = st.number_input("CD4 (if HIV)", 0, 1200, 300) if immune == "HIV" else None

    st.header("Symptoms — ROS")
    headache = st.checkbox("Headache")
    vision = st.checkbox("Vision Changes")
    rash = st.checkbox("Rash")
    abd_pain = st.checkbox("Abdominal Pain")
    night_sweats = st.checkbox("Night Sweats")
    weight_loss = st.checkbox("Weight Loss")
    arthralgia = st.checkbox("Joint Pain")

    st.header("Exposure")
    cats = st.checkbox("Cats")
    bats = st.checkbox("Bird/Bat")
    dairy = st.checkbox("Unpasteurized Dairy")
    livestock = st.checkbox("Livestock")
    farm = st.checkbox("Farm Animals")
    medtrav = st.checkbox("Travel Mediterranean/Mexico")
    mo = st.checkbox("Lives in Missouri")

    st.header("Prior Workup Negative")
    prior = st.multiselect("Prior Negative", ["Blood Cx x3", "Quantiferon TB", "Histo Ag", "Bartonella Serology", "Brucella Serology"])

run = st.button("Generate")

if run:
    positives = []
    if headache: positives.append("Headache")
    if vision: positives.append("Vision Changes")
    if rash: positives.append("Rash")
    if abd_pain: positives.append("Abdominal Pain")
    if night_sweats: positives.append("Night Sweats")
    if weight_loss: positives.append("Weight Loss")
    if arthralgia: positives.append("Arthralgia")

    if cats: positives.append("Cats")
    if bats: positives.append("Bird/Bat")
    if dairy: positives.append("Unpasteurized Dairy")
    if livestock
    if livestock: positives.append("Livestock")
    if farm: positives.append("Farm Animals")
    if medtrav: positives.append("Travel Med/Mexico")
    if mo: positives.append("Missouri")

    if immune == "HIV" and cd4 is not None:
        if cd4 < 250: positives.append("CD4 < 250")
        positives.append("HIV")

    inputs = {
        "age": age,
        "sex": sex,
        "immune": immune,
        "cd4": cd4,
        "positives": positives,
    }

    active = get_dx(inputs)
    plan = build_plan(active, prior)

    st.subheader("Differential")
    for d in active:
        st.markdown(f"**{d['dx']}** — triggers: {', '.join(d['triggers'])}")

    st.subheader("Recommended Workup")
    for o in plan:
        st.markdown(f"- [ ] {o}")

