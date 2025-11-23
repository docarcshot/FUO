import streamlit as st
import datetime

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
st.set_page_config(page_title="ID-CDSS | FUO Engine v1", layout="wide")

# ---------------------------------------------------------------------
# STYLE
# ---------------------------------------------------------------------
st.markdown("""
<style>
.tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
.crit { border-left: 6px solid #dc3545; padding: 10px; background-color: #ffe6e6; }
.inf  { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
.endemic { border-left: 6px solid #fd7e14; padding: 10px; background-color: #fff3cd; }
.noninf { border-left: 6px solid #17a2b8; padding: 10px; background-color: #e0f7fa; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------
def faget(t, hr):
    return t >= 102.2 and hr < 100


# ---------------------------------------------------------------------
# CORE FUO DATABASE (CLEAN)
# ---------------------------------------------------------------------
FUO_DB = [
    # --- CRITICAL FIRST ---
    {
        "dx": "HLH",
        "type": "CRITICAL",
        "triggers": ["Ferritin >3000", "Pancytopenia", "Splenomegaly", "Hypertriglyceridemia"],
        "orders": ["Soluble CD25", "Fibrinogen", "Bone Marrow Biopsy"]
    },
    {
        "dx": "Malaria",
        "type": "CRITICAL",
        "triggers": ["Travel Africa", "Travel SE Asia", "Travel S America"],
        "orders": ["Malaria Smear x3", "Rapid Antigen"]
    },
    {
        "dx": "Miliary TB",
        "type": "CRITICAL",
        "triggers": ["TB Exposure", "Homelessness", "Immunocompromised"],
        "orders": ["Quantiferon TB", "AFB x3"]
    },

    # --- INFECTIOUS HIGH-YIELD ---
    {
        "dx": "Infectious Endocarditis",
        "type": "INF",
        "triggers": ["New Murmur", "IV Drug Use", "Prosthetic Valve"],
        "orders": ["Blood Cx x3", "TTE", "TEE"]
    },
    {
        "dx": "Histoplasmosis (Disseminated)",
        "type": "ENDEMIC",
        "triggers": ["MO Residence", "Bird/Bat Droppings", "Pancytopenia", "Oral Ulcers"],
        "orders": ["Urine/Serum Histo Ag", "Ferritin"]
    },
    {
        "dx": "Q Fever",
        "type": "INF",
        "triggers": ["Farm Animals", "Parturient Animals"],
        "orders": ["Coxiella Serology", "TTE"]
    },
    {
        "dx": "Brucellosis",
        "type": "INF",
        "triggers": ["Unpasteurized Dairy", "Livestock", "Back Pain"],
        "orders": ["Brucella Serology", "Blood Cx (21d)"]
    },

    # --- HIV OIs (only relevant if HIV+) ---
    {
        "dx": "PCP",
        "type": "INF",
        "requires_hiv": True,
        "cd4_ceiling": 200,
        "triggers": ["Dyspnea", "Dry Cough", "Hypoxia"],
        "orders": ["Beta-D-Glucan", "LDH", "CT Chest HR"]
    },
    {
        "dx": "MAC (Disseminated)",
        "type": "INF",
        "requires_hiv": True,
        "cd4_ceiling": 50,
        "triggers": ["Night Sweats", "Weight Loss", "Anemia"],
        "orders": ["AFB Blood Cx", "CT Abd/Pelvis"]
    },

    # --- NON-INFECTIOUS ---
    {
        "dx": "GCA",
        "type": "NONINF",
        "triggers": ["Age >50", "Jaw Claudication", "Vision Changes"],
        "orders": ["ESR & CRP", "Temporal Artery US", "Temporal Artery Bx"]
    },
    {
        "dx": "Malignancy (Lymphoma/RCC)",
        "type": "NONINF",
        "triggers": ["Night Sweats", "Weight Loss", "Hematuria"],
        "orders": ["LDH", "CT CAP", "Naproxen Test"]
    },
    {
        "dx": "DRESS",
        "type": "NONINF",
        "requires_med": True,
        "triggers": ["Rash", "Eosinophilia"],
        "orders": ["CBC (Eos)", "LFTs", "HHV-6 PCR"]
    }
]

# ---------------------------------------------------------------------
# LOGIC ENGINE (CLEAN)
# ---------------------------------------------------------------------
def run_engine(inputs):
    dx_list = []
    orders = set()

    for d in FUO_DB:
        score = 0
        # HIV gating
        if d.get("requires_hiv"):
            if not inputs["hiv"]:
                continue
            if inputs["cd4"] > d["cd4_ceiling"]:
                continue

        # Drug gating for DRESS
        if d.get("requires_med") and not inputs["on_med"]:
            continue

        # Trigger match
        matched = []
        for t in d["triggers"]:
            if t in inputs["positives"]:
                score += 1
                matched.append(t)

        # special: endemic MO
        if d["dx"].startswith("Histo") and inputs["missouri"]:
            score += 1
            matched.append("MO Residence")

        if score > 0:
            dx_list.append({
                "dx": d["dx"],
                "type": d["type"],
                "score": score,
                "triggers": matched,
                "orders": d["orders"]
            })
            for o in d["orders"]:
                orders.add(o)

    # universal baseline
    baseline = ["CBC", "CMP", "ESR", "CRP", "UA", "HIV 4th Gen", "Syphilis IgG"]
    for b in baseline:
        orders.add(b)

    # remove priors
    orders = {o for o in orders if o not in inputs["prior_details"]}

    dx_sorted = sorted(dx_list, key=lambda x: x["score"], reverse=True)
    return dx_sorted, orders


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
st.title("ID-CDSS | FUO Engine")

with st.sidebar:
    st.header("Patient Info")
    age = st.number_input("Age", 18, 100, 55)
    sex = st.selectbox("Sex", ["Male", "Female"])
    duration = st.number_input("Days of Fever", 1, 365, 21)
    tmax = st.number_input("Maximum Temp (°F)", 98.0, 107.0, 102.5)
    hr = st.number_input("HR at Tmax", 40, 160, 90)

    st.header("Immune Status")
    immune = st.selectbox("Immune State",
                          ["Normal", "HIV+", "Transplant"])
    hiv = (immune == "HIV+")
    cd4 = 1000
    if hiv:
        cd4 = st.slider("CD4 Count", 0, 1200, 350)

    transplant = (immune == "Transplant")
    tx_type = None
    tx_time = None
    if transplant:
        tx_type = st.selectbox("Organ", ["Kidney", "Liver", "Lung", "BMT"])
        tx_time = st.selectbox("Timeline", ["<1 mo", "1–6 mo", ">6 mo"])

    st.header("Medications")
    on_abx = st.checkbox("On Antibiotics?")
    on_med = st.checkbox("New High-Risk Drug? (Sulfa, Anticonvulsant, BL)")

    st.header("Exposures & Travel")
    missouri = st.checkbox("Missouri Residence")
    farm = st.checkbox("Farm Animals")
    bats = st.checkbox("Bird/Bat Droppings")
    dairy = st.checkbox("Unpasteurized Dairy")
    africa = st.checkbox("Travel Africa")
    se_asia = st.checkbox("Travel SE Asia")
    s_amer = st.checkbox("Travel S America")
    tb = st.checkbox("TB Exposure")
    ivdu = st.checkbox("IV Drug Use")
    prosthetic = st.checkbox("Prosthetic Valve")

    st.header("Review of Systems")
    sweats = st.checkbox("Night Sweats")
    wl = st.checkbox("Weight Loss")
    backpain = st.checkbox("Back Pain")
    cough = st.checkbox("Dry Cough")
    dyspnea = st.checkbox("Dyspnea")
    vision = st.checkbox("Vision Changes")
    jaw = st.checkbox("Jaw Claudication")
    murmur = st.checkbox("New Murmur")
    eos = st.checkbox("Eosinophilia")
    rash = st.checkbox("Rash")
    pancytopenia = st.checkbox("Pancytopenia")
    ferritin3k = st.checkbox("Ferritin >3000")
    trig = st.checkbox("Hypertriglyceridemia")

    st.header("Prior Workup")
    prior = st.multiselect(
        "Negative:",
        ["Blood Cx", "HIV", "CT CAP", "Quantiferon", "AFB Smear", "Malaria Smear"]
    )

    run = st.button("Generate")

# ---------------------------------------------------------------------
# Run app
# ---------------------------------------------------------------------
if run:
    positives = []
    if sweats: positives.append("Night Sweats")
    if wl: positives.append("Weight Loss")
    if backpain: positives.append("Back Pain")
    if bats: positives.append("Bird/Bat Droppings")
    if farm: positives.append("Farm Animals")
    if dairy: positives.append("Unpasteurized Dairy")
    if africa: positives.append("Travel Africa")
    if se_asia: positives.append("Travel SE Asia")
    if s_amer: positives.append("Travel S America")
    if tb: positives.append("TB Exposure")
    if ivdu: positives.append("IV Drug Use")
    if prosthetic: positives.append("Prosthetic Valve")
    if murmur: positives.append("New Murmur")
    if dyspnea: positives.append("Dyspnea")
    if eos: positives.append("Eosinophilia")
    if rash: positives.append("Rash")
    if pancytopenia: positives.append("Pancytopenia")
    if ferritin3k: positives.append("Ferritin >3000")
    if trig: positives.append("Hypertriglyceridemia")

    inputs = {
        "age": age,
        "hiv": hiv,
        "cd4": cd4,
        "on_med": on_med,
        "on_abx": on_abx,
        "missouri": missouri,
        "positives": positives,
        "prior_details": prior
    }

    dx, orders = run_engine(inputs)

    col1, col2 = st.columns([1,1])

    with col1:
        st.subheader("Differential (Weighted)")

        for d in dx:
            style = "crit" if d["type"]=="CRITICAL" else \
                    "endemic" if d["type"]=="ENDEMIC" else \
                    "noninf" if d["type"]=="NONINF" else "inf"

            st.markdown(f"<div class='{style}'>", unsafe_allow_html=True)
            st.markdown(f"### {d['dx']}")
            st.caption("Triggers: " + ", ".join(d["triggers"]))
            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.subheader("Recommended Workup")

        st.markdown("<div class='tier0'>", unsafe_allow_html=True)
        for o in sorted(orders):
            st.markdown(f"- {o}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("Consult Note")
        text = f"{age}yo {sex} with {duration} days of fever. Tmax {tmax}, HR {hr}.\n"
        if faget(tmax, hr):
            text += "Relative bradycardia present.\n"
        text += "Differential: " + ", ".join([d["dx"] for d in dx]) + "\n"
        text += "Recommended workup: " + ", ".join(sorted(orders)) + "\n"
        st.text_area("Note", text, height=300)
