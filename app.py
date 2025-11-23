import streamlit as st
import datetime

# ------------------------------------------
# CONFIG
# ------------------------------------------
st.set_page_config(page_title="FUO-CDSS | Version A", layout="wide")

# ------------------------------------------
# STYLES
# ------------------------------------------
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; margin-bottom:6px; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; margin-bottom:6px; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; margin-bottom:6px; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; margin-bottom:6px; }
    .critical { border-left: 6px solid #dc3545; padding: 10px; background-color: #ffe6e6; font-weight:bold; margin-bottom:6px;}
    .inf      { border-left: 6px solid #0d6efd; padding:10px; background-color:#e7f1ff; margin-bottom:6px;}
    .noninf   { border-left: 6px solid #20c997; padding:10px; background-color:#e8fff8; margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------
# HELPER – RELATIVE BRADYCARDIA CHECK
# ------------------------------------------
def faget(temp, hr):
    try:
        return temp >= 102 and hr < 90
    except:
        return False

# ------------------------------------------
# DATABASE — CORE REAL FUO CAUSES ONLY
# ------------------------------------------
DATABASE = [

    # ------------------------------
    # HIGH-PRIORITY / CRITICAL
    # ------------------------------
    {
        "dx": "Infective Endocarditis",
        "type": "infectious",
        "triggers": ["New Murmur", "Splinter Hemorrhages", "IVDU", "Prosthetic Valve"],
        "orders": [("Blood Cx x3", 0), ("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Miliary / Disseminated TB",
        "type": "infectious",
        "triggers": ["Night Sweats", "Weight Loss", "Cough", "Hemoptysis", "TB Exposure", "Homelessness", "Incarceration"],
        "orders": [("Quantiferon-TB", 1), ("AFB Sputum x3", 1), ("CT Chest", 2)]
    },
    {
        "dx": "HLH (Hemophagocytic Lymphohistiocytosis)",
        "type": "critical",
        "triggers": ["Ferritin >3000", "Pancytopenia", "Splenomegaly"],
        "orders": [("Triglycerides", 1), ("Fibrinogen", 1), ("Soluble IL-2R", 1)]
    },

    # ------------------------------
    # HIV-ASSOCIATED FUO PATHOLOGY
    # (CD4 GRADIENT – NOT HARD CUTOFF)
    # ------------------------------
    {
        "dx": "Cryptococcal Meningitis",
        "type": "infectious",
        "triggers": ["Headache", "Vision Changes", "Photophobia", "Nausea"],
        "cd4_prefer": 150,      # but NOT strict cutoff
        "orders": [("Serum CrAg", 1), ("LP w/ Opening Pressure", 3)]
    },
    {
        "dx": "Disseminated MAC",
        "type": "infectious",
        "triggers": ["Night Sweats", "Weight Loss", "Diarrhea", "Anemia"],
        "cd4_prefer": 75,
        "orders": [("AFB Blood Cx", 1), ("CT Abd/Pelvis", 2)]
    },
    {
        "dx": "PCP (Pneumocystis jirovecii)",
        "type": "infectious",
        "triggers": ["Dyspnea", "Dry Cough", "Hypoxia"],
        "cd4_prefer": 250,
        "orders": [("Beta-D-Glucan", 1), ("LDH", 1)]
    },

    # ------------------------------
    # ENDEMIC FUNGAL FUO
    # ------------------------------
    {
        "dx": "Disseminated Histoplasmosis",
        "type": "infectious",
        "triggers": ["Bird/Bat Exposure", "Caves", "Pancytopenia", "Oral Ulcers", "Splenomegaly"],
        "orders": [("Urine/Serum Histo Ag", 1)]
    },
    {
        "dx": "Blastomycosis",
        "type": "infectious",
        "triggers": ["Waterways", "Outdoors", "Pneumonia"],
        "orders": [("Urine Blasto Ag", 1)]
    },

    # ------------------------------
    # CLASSIC AUTOIMMUNE FUO
    # ------------------------------
    {
        "dx": "Temporal Arteritis (GCA)",
        "type": "noninfectious",
        "triggers": ["Headache", "Jaw Claudication", "Vision Changes", "Age >50"],
        "orders": [("ESR/CRP", 1), ("Temporal Artery US", 2)]
    },
    {
        "dx": "Adult-Onset Still’s Disease",
        "type": "noninfectious",
        "triggers": ["High Spiking Fevers", "Arthralgia", "Rash", "Elevated Ferritin"],
        "orders": [("Ferritin", 1), ("ANA/RF", 1)]
    },
    {
        "dx": "Autoimmune Hepatitis",
        "type": "noninfectious",
        "triggers": ["Elevated LFTs", "Female Sex", "Arthralgia"],
        "orders": [("Liver AI Panel", 1)]
    },

    # ------------------------------
    # MALIGNANCY FUO
    # ------------------------------
    {
        "dx": "Lymphoma (Occult)",
        "type": "noninfectious",
        "triggers": ["Night Sweats", "Weight Loss", "Lymphadenopathy", "Splenomegaly"],
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2)]
    }
]

# ------------------------------------------
# LOGIC ENGINE
# ------------------------------------------
def compute_differential(inputs):
    results = []
    orders_raw = {0: set(), 1: set(), 2: set(), 3: set()}

    positives = inputs["positives"]

    for item in DATABASE:
        score = 0
        found_triggers = []

        # match triggers
        for t in item["triggers"]:
            if t in positives:
                score += 1
                found_triggers.append(t)

        # CD4 gradient logic (not hard cutoff)
        if "cd4_prefer" in item:
            cd4 = inputs.get("cd4", 1000)
            if cd4 <= item["cd4_prefer"] + 50:  # soft buffer
                score += 1
                found_triggers.append(f"CD4 ~ {cd4}")

        # age logic for GCA
        if item["dx"] == "Temporal Arteritis (GCA)" and inputs["age"] < 50:
            score = 0

        if score > 0:
            results.append({
                "dx": item["dx"],
                "type": item["type"],
                "triggers": found_triggers,
                "score": score
            })
            for o, tier in item["orders"]:
                orders_raw[tier].add(o)

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results, orders_raw


def clean_orders(orders_raw, inputs):
    out = {"Baseline": set(), "Targeted": set(), "Imaging": set(), "Escalation": set()}

    # Always include these
    out["Baseline"].update(["CBC", "CMP", "ESR", "CRP", "UA", "HIV Ag/Ab", "Blood Cx x3"])

    # Add DB-driven
    for tier, items in orders_raw.items():
        if tier == 0:
            out["Baseline"].update(items)
        elif tier == 1:
            out["Targeted"].update(items)
        elif tier == 2:
            out["Imaging"].update(items)
        elif tier == 3:
            out["Escalation"].update(items)

    return out


def note_text(inputs, diffs, orders):
    txt = f"Date: {datetime.date.today()}\n"
    txt += f"{inputs['age']}yo {inputs['sex']} with {inputs['duration']} days of fever."
    if inputs['immune'] == "HIV":
        txt += f" CD4 ~ {inputs['cd4']}."
    txt += "\n\n"

    txt += "Assessment / Differential:\n"
    for d in diffs:
        txt += f"- {d['dx']} (Triggers: {', '.join(d['triggers'])})\n"

    txt += "\nPlan:\n"
    txt += f"Baseline: {', '.join(sorted(orders['Baseline']))}\n"
    txt += f"Targeted: {', '.join(sorted(orders['Targeted']))}\n"
    txt += f"Imaging: {', '.join(sorted(orders['Imaging']))}\n"
    txt += f"Escalation: {', '.join(sorted(orders['Escalation']))}\n"
    return txt


# ------------------------------------------
# UI – SIDEBAR INPUTS
# ------------------------------------------
with st.sidebar:
    st.title("FUO Input")

    age = st.number_input("Age", 18, 100, 45)
    sex = st.selectbox("Sex", ["Male", "Female"])
    duration = st.number_input("Duration of Fever (days)", 3, 365, 21)

    immune = st.selectbox("Immune Status", ["Immunocompetent", "HIV", "Transplant"])
    cd4 = 1000
    if immune == "HIV":
        cd4 = st.slider("CD4 Count", 0, 1200, 250)

    # ROS – structured
    st.header("ROS – Neurologic")
    headache = st.checkbox("Headache")
    vision = st.checkbox("Vision Changes")
    photophobia = st.checkbox("Photophobia")

    st.header("ROS – Respiratory")
    cough = st.checkbox("Cough")
    hemoptysis = st.checkbox("Hemoptysis")
    dyspnea = st.checkbox("Dyspnea")

    st.header("ROS – Constitutional")
    ns = st.checkbox("Night Sweats")
    wl = st.checkbox("Weight Loss")

    st.header("ROS – GI")
    abd = st.checkbox("Abdominal Pain")
    diarrhea = st.checkbox("Diarrhea")

    st.header("ROS – MSK / Rheum")
    arthralgia = st.checkbox("Arthralgia")
    rash = st.checkbox("Rash")

    st.header("Exposures")
    bats = st.checkbox("Bird/Bat Exposure")
    caves = st.checkbox("Caves")
    ivdu = st.checkbox("IVDU")
    prosthetic = st.checkbox("Prosthetic Valve")

    prior = st.multiselect("Prior Workup", ["Normal CT", "Negative Blood Cx", "Negative TB Testing"])

    run = st.button("Generate")


# ------------------------------------------
# MAIN
# ------------------------------------------
st.title("FUO Clinical Decision Support – Version A")

if run:
    positives = []
    if headache: positives.append("Headache")
    if vision: positives.append("Vision Changes")
    if photophobia: positives.append("Photophobia")
    if cough: positives.append("Cough")
    if hemoptysis: positives.append("Hemoptysis")
    if dyspnea: positives.append("Dyspnea")
    if ns: positives.append("Night Sweats")
    if wl: positives.append("Weight Loss")
    if abd: positives.append("Abdominal Pain")
    if diarrhea: positives.append("Diarrhea")
    if arthralgia: positives.append("Arthralgia")
    if rash: positives.append("Rash")
    if bats: positives.append("Bird/Bat Exposure")
    if caves: positives.append("Caves")
    if ivdu: positives.append("IVDU")
    if prosthetic: positives.append("Prosthetic Valve")

    inputs = {
        "age": age,
        "sex": sex,
        "duration": duration,
        "immune": immune,
        "cd4": cd4,
        "positives": positives,
        "prior": prior
    }

    diffs, raw_orders = compute_differential(inputs)
    cleaned = clean_orders(raw_orders, inputs)

    c1, c2 = st.columns([1,1])
    with c1:
        st.subheader("Differential")
        for d in diffs:
            style = "critical" if d["type"] == "critical" else ("inf" if d["type"]=="infectious" else "noninf")
            st.markdown(f"<div class='{style}'><b>{d['dx']}</b><br>Triggers: {', '.join(d['triggers'])}</div>", unsafe_allow_html=True)

    with c2:
        st.subheader("Consult Note")
        txt = note_text(inputs, diffs, cleaned)
        st.text_area("Output", txt, height=500)
        st.download_button("Download .txt", txt, f"FUO_{datetime.date.today()}.txt")
