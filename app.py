import streamlit as st
import datetime

st.set_page_config(page_title="ID-CDSS | FUO Master v40", layout="wide")

########################################
# STYLE
########################################

st.markdown("""
<style>
.tier0 { border-left: 6px solid #000; padding: 10px; background-color:#f0f0f0; }
.tier1 { border-left: 6px solid #28a745; padding: 10px; background-color:#e6fffa; }
.tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color:#fffbe6; }
.tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color:#ffe6e6; font-weight:bold; }
.critical { border-left: 6px solid #dc3545; padding: 10px; background-color:#ffe6e6; }
.endemic { border-left: 6px solid #fd7e14; padding: 10px; background-color:#fff3cd; }
.noninf { border-left: 6px solid #17a2b8; padding: 10px; background-color:#e0f7fa; }
.infectious { border-left: 6px solid #198754; padding: 10px; background-color:#e9fff8; }
</style>
""", unsafe_allow_html=True)



########################################
# HELPER: Faget's sign
########################################

def faget(t, hr):
    return t >= 102 and hr < 100



########################################
# FUO DATABASE — curated to be realistic
########################################

DATABASE = [

    # CRITICAL
    {
        "dx": "HLH",
        "type": "Critical",
        "triggers": ["Ferritin >3000", "Pancytopenia", "Splenomegaly", "Hypertriglyceridemia"],
        "orders": [("Soluble CD25",1), ("Fibrinogen",1), ("Bone Marrow Biopsy",3)]
    },
    {
        "dx": "Miliary Tuberculosis",
        "type": "Critical",
        "triggers": ["Night Sweats","Weight Loss","TB Exposure","Homelessness"],
        "orders": [("Quantiferon-TB Gold",1), ("Sputum AFB x3",1)]
    },

    # INFECTIOUS
    {
        "dx": "Infectious Endocarditis",
        "type": "Infectious",
        "triggers": ["New Murmur","IVDU","Prosthetic Valve"],
        "orders": [("Blood Cx x3",0), ("TTE",2), ("TEE",3)]
    },
    {
        "dx": "Disseminated Histoplasmosis",
        "type": "Endemic Fungal",
        "triggers": ["Missouri Residence","Bird/Bat Droppings","Pancytopenia"],
        "orders": [("Urine/Serum Histo Ag",1)]
    },
    {
        "dx": "Q Fever",
        "type": "Infectious",
        "triggers": ["Farm Animals","Well Water","Parturient Animals"],
        "orders": [("Coxiella Serology",1)]
    },
    {
        "dx": "Brucellosis",
        "type": "Infectious",
        "triggers": ["Unpasteurized Dairy","Livestock","Back Pain","Relative Bradycardia"],
        "orders": [("Brucella Serology",1)]
    },
    {
        "dx": "Bartonella (Cat / Homelessness)",
        "type": "Infectious",
        "triggers": ["Cats","Homelessness","Body Lice"],
        "orders": [("Bartonella Serology",1)]
    },
    {
        "dx": "Strongyloidiasis",
        "type": "Infectious",
        "triggers": ["Eosinophilia","Travel (Tropics)"],
        "orders": [("Strongyloides IgG",1)]
    },

    # HIV ONLY (nailed down)
    {
        "dx": "PCP",
        "type": "Infectious",
        "triggers": ["Dry Cough","Dyspnea","Hypoxia"],
        "req_cd4": 200,
        "orders": [("Beta-D-Glucan",1)]
    },
    {
        "dx": "Toxoplasmosis",
        "type": "Infectious",
        "triggers": ["Headache","Vision Changes","Neuro Deficit"],
        "req_cd4": 100,
        "orders": [("Toxo IgG",1), ("MRI Brain",2)]
    },

    # NON-INFECTIOUS
    {
        "dx": "Giant Cell Arteritis (GCA)",
        "type": "Non-Infectious",
        "triggers": ["Headache","Jaw Claudication","Vision Changes","Age >50"],
        "orders": [("ESR & CRP",1), ("Temporal Artery US",2)]
    },
    {
        "dx": "Autoimmune Hepatitis",
        "type": "Non-Infectious",
        "triggers": ["Elevated LFTs","Female Sex"],
        "orders": [("Liver Autoimmune Panel",1)]
    },
    {
        "dx": "Systemic Lupus",
        "type": "Non-Infectious",
        "triggers": ["Malar Rash","Joint Pain","Proteinuria","Cytopenias"],
        "orders": [("ANA",1), ("dsDNA",1), ("C3/C4",1)]
    },
    {
        "dx": "Malignancy (Lymphoma/RCC)",
        "type": "Non-Infectious",
        "triggers": ["Night Sweats","Weight Loss","Hematuria","Splenomegaly"],
        "orders": [("CT Chest/Abd/Pelvis",2), ("LDH",1)]
    },
]



########################################
# LOGIC ENGINE
########################################

def get_diff(inputs):
    dx_list = []
    order_bucket = {0:[],1:[],2:[],3:[]}

    # relative bradycardia detection
    if faget(inputs["tmax"], inputs["hr"]):
        inputs["positives"].append("Relative Bradycardia")

    for d in DATABASE:
        score = 0
        triggers_hit = []

        # trigger matching
        for t in d["triggers"]:
            if t in inputs["positives"]:
                score += 1
                triggers_hit.append(t)

        # HIV restrictions
        if "req_cd4" in d and inputs["immune"] == "HIV Positive":
            if inputs["cd4"] < d["req_cd4"]:
                score += 1
                triggers_hit.append(f"CD4 < {d['req_cd4']}")
            else:
                score = 0

        # age restrictions
        if d["dx"] == "GCA" and inputs["age"] < 50:
            score = 0

        if score > 0:
            dx_list.append({"dx": d["dx"],"type": d["type"],"triggers": triggers_hit,"score":score})
            for o,tier in d["orders"]:
                order_bucket[tier].append(o)

    dx_list = sorted(dx_list, key=lambda x: x["score"], reverse=True)
    return dx_list, order_bucket



def optimize_orders(order_bucket, inputs):

    final = {"Actions":set(),"Immediate":set(),"Targeted":set(),"Imaging":set(),"Escalation":set()}

    for tier,items in order_bucket.items():
        for it in items:

            if tier == 0:
                final["Actions"].add(it)
            elif tier == 1:
                final["Immediate"].add(it)
            elif tier == 2:
                final["Imaging"].add(it)
            elif tier == 3:
                final["Escalation"].add(it)

    # Universal baseline
    final["Immediate"].update(["CBC","CMP","ESR","CRP","UA","HIV 1/2 Ag/Ab","Syphilis IgG"])

    # Remove priors
    for cat in final:
        final[cat] = {o for o in final[cat] if not any(p in o for p in inputs["prior"])}

    return final



def note(inputs, dx_list, orders):

    txt = f"Date: {datetime.date.today()}\n"
    txt += f"{inputs['age']}yo {inputs['sex']} ({inputs['immune']}) "
    txt += f"with fever for {inputs['dur']} days, Tmax {inputs['tmax']} with HR {inputs['hr']}.\n"

    if faget(inputs['tmax'], inputs['hr']):
        txt += "Vitals notable for Relative Bradycardia (Faget's Sign).\n"

    txt += "\nAssessment & Differential:\n"
    if not dx_list:
        txt += "No syndromic matches. FUO category.\n"
    else:
        for d in dx_list:
            txt += f"- {d['dx']} ({d['type']}) — triggers: {', '.join(d['triggers'])}\n"

    txt += "\nPlan:\n"
    if orders["Actions"]:
        txt += "Actions:\n"
        for a in sorted(orders["Actions"]):
            txt += f"- [ ] {a}\n"

    if orders["Immediate"]:
        txt += "Immediate labs:\n"
        txt += "- " + ", ".join(sorted(orders["Immediate"])) + "\n"

    if orders["Targeted"]:
        txt += "Targeted Tests:\n"
        txt += "- " + ", ".join(sorted(orders["Targeted"])) + "\n"

    if orders["Imaging"]:
        txt += "Imaging:\n"
        txt += "- " + ", ".join(sorted(orders["Imaging"])) + "\n"

    if orders["Escalation"]:
        txt += "Escalation (High-Yield/Phase 2):\n"
        txt += "- " + ", ".join(sorted(orders["Escalation"])) + "\n"

    return txt



########################################
# UI
########################################

with st.sidebar:
    st.title("Patient Data")

    age = st.number_input("Age",18,100,50)
    sex = st.selectbox("Sex",["Male","Female"])

    immune = st.selectbox("Immune Status",
                           ["Immunocompetent","HIV Positive","Transplant","Biologics","Chemotherapy"])

    cd4 = 1000
    tx_type = None
    if immune == "HIV Positive":
        cd4 = st.slider("CD4 Count",0,1200,450)
    if immune == "Transplant":
        tx_type = st.selectbox("Transplant Type",["Kidney","Liver","Lung","BMT"])
        tx_time = st.selectbox("Time Since Tx",["<1 Month","1-6 Months",">6 Months"])

    tmax = st.number_input("Tmax (°F)",98.0,107.0,102.2,step=.1)
    hr = st.number_input("HR at Tmax",40,160,95)
    dur = st.number_input("Duration of fever (days)",0,365,21)

    st.header("Medications")
    meds = st.multiselect("Recent / New Medications",["Antibiotic","Anticonvulsant","Sulfa"])

    st.header("ROS – System Based")

    st.subheader("Constitutional")
    night_sweats = st.checkbox("Night Sweats")
    weight_loss = st.checkbox("Weight Loss")
    fatigue = st.checkbox("Fatigue")

    st.subheader("Neuro")
    ha = st.checkbox("Headache")
    seizure = st.checkbox("Seizure")
    neuro_def = st.checkbox("Focal Neuro Deficit")

    st.subheader("HEENT")
    vision = st.checkbox("Vision Changes")
    jaw = st.checkbox("Jaw Claudication")

    st.subheader("Respiratory")
    cough = st.checkbox("Dry Cough")
    dyspnea = st.checkbox("Dyspnea")

    st.subheader("GI")
    abd = st.checkbox("Abdominal Pain")
    diarrhea = st.checkbox("Diarrhea")
    hepatodynia = st.checkbox("Hepatodynia")

    st.subheader("Skin")
    rash = st.checkbox("Rash")
    palmsoles = st.checkbox("Palms/Soles Rash")

    st.subheader("MSK")
    joint = st.checkbox("Joint Pain")

    st.header("Exposures")
    cats = st.checkbox("Cats")
    livestock = st.checkbox("Livestock")
    bats = st.checkbox("Bird/Bat Droppings")
    dairy = st.checkbox("Unpasteurized Dairy")
    well = st.checkbox("Well Water")
    ivdu = st.checkbox("IV Drug Use")
    homeless = st.checkbox("Homelessness")
    tbexp = st.checkbox("TB Exposure")

    st.header("Travel")
    tropics = st.checkbox("Travel (Tropics)")
    mexico = st.checkbox("Travel (Mexico/Mediterranean)")
    swus = st.checkbox("Travel (Southwest US)")
    africa = st.checkbox("Travel (Sub-Saharan Africa)")

    st.header("Labs")
    pancyt = st.checkbox("Pancytopenia")
    ferritin3k = st.checkbox("Ferritin >3000")
    hypertrig = st.checkbox("Hypertriglyceridemia")
    lfts = st.checkbox("Elevated LFTs")
    eos = st.checkbox("Eosinophilia")
    splen = st.checkbox("Splenomegaly")
    hematuria = st.checkbox("Hematuria")

    st.header("Prior Workup")
    prior = st.multiselect("Prior Negatives",["Blood Cx","CT Chest/Abd/Pelvis","HIV","AFB","ANA","TB"])

    run = st.button("Generate")
    

########################################
# MAIN PANEL
########################################

st.title("FUO Grand Master v40")

if run:

    positives = []

    if night_sweats: positives.append("Night Sweats")
    if weight_loss: positives.append("Weight Loss")
    if ha: positives.append("Headache")
    if vision: positives.append("Vision Changes")
    if jaw: positives.append("Jaw Claudication")
    if cough: positives.append("Dry Cough")
    if dyspnea: positives.append("Dyspnea")
    if abd: positives.append("Abdominal Pain")
    if diarrhea: positives.append("Diarrhea")
    if hepatodynia: positives.append("Hepatodynia")
    if rash: positives.append("Rash")
    if palmsoles: positives.append("Rash (Palms/Soles)")
    if joint: positives.append("Joint Pain")
    if ivdu: positives.append("IVDU")
    if cats: positives.append("Cats")
    if livestock: positives.append("Farm Animals")
    if bats: positives.append("Bird/Bat Droppings")
    if dairy: positives.append("Unpasteurized Dairy")
    if well: positives.append("Well Water")
    if homeless: positives.append("Homelessness")
    if tbexp: positives.append("TB Exposure")
    if pancyt: positives.append("Pancytopenia")
    if ferritin3k: positives.append("Ferritin >3000")
    if hypertrig: positives.append("Hypertriglyceridemia")
    if eos: positives.append("Eosinophilia")
    if splen: positives.append("Splenomegaly")
    if hematuria: positives.append("Hematuria")
    if tropics: positives.append("Travel (Tropics)")
    if mexico: positives.append("Travel (Med/Mexico)")
    if swus: positives.append("Travel (Southwest US)")
    if africa: positives.append("Travel (Sub-Saharan Africa)")
    if age>50: positives.append("Age >50")
    if sex=="Female": positives.append("Female Sex")

    inputs = {
        "age": age,
        "sex": sex,
        "immune": immune,
        "cd4": cd4,
        "positives": positives,
        "prior": prior,
        "tmax": tmax,
        "hr": hr,
        "dur": dur,
    }

    dx_list, order_bucket = get_diff(inputs)
    optimized = optimize_orders(order_bucket, inputs)
    note_text = note(inputs, dx_list, optimized)

    col1, col2 = st.columns([1,1])

    with col1:
        st.subheader("Differential")
        if faget(tmax,hr):
            st.error("Relative Bradycardia (Faget's Sign)")

        for d in dx_list:
            css = "critical" if d["type"]=="Critical" else ("endemic" if "Endemic" in d["type"] else ("noninf" if d["type"]=="Non-Infectious" else "infectious"))
            st.markdown(f"<div class='{css}'>**{d['dx']}**<br><small>{', '.join(d['triggers'])}</small></div>", unsafe_allow_html=True)

    with col2:
        st.subheader("Consult Note")
        st.text_area("",note_text,height=500)
        st.download_button("Download Note",note_text,file_name="FUO_note.txt")
