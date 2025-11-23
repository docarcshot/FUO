import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Custom Note Ed.", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .alert { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .stExpander { border: 1px solid #e0e0e0; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- MAPPING: RESULT INPUT -> ORDER TO REMOVE ---
PRIOR_MAP = {
    "Negative Blood Cx x3": "Blood Cx x3",
    "Negative HIV Screen": "HIV 1/2 Ag/Ab",
    "Negative Syphilis Screen": "Syphilis IgG",
    "Normal CT Chest/Abd/Pelvis": "CT Chest/Abd/Pelvis",
    "Normal TTE": "TTE",
    "Normal TEE": "TEE",
    "Negative ANA": "ANA",
    "Normal Ferritin": "Ferritin"
}

# --- DATABASE ---
DATABASE = [
    {
        "dx": "DRESS Syndrome",
        "triggers": ["Rash (Diffuse)", "Eosinophilia", "Hepatodynia"], 
        "req_med": True,
        "pearl": "Requires drug exposure (2-8 wk latency).",
        "orders": [("CBC (Eosinophils)", 1), ("LFTs", 1), ("HHV-6 PCR", 1)]
    },
    {
        "dx": "Q Fever",
        "triggers": ["Farm Animals", "Parturient Animals", "Dust/Wind Exposure"],
        "req_med": False,
        "pearl": "Culture-neg endocarditis.",
        "orders": [("Coxiella Serology", 1), ("TTE", 2)]
    },
    {
        "dx": "Brucellosis",
        "triggers": ["Unpasteurized Dairy", "Livestock", "Travel (Mexico/Med)", "Back Pain (Lumbar)"],
        "req_med": False,
        "pearl": "Undulating fever. Osteomyelitis (Spine).",
        "orders": [("Brucella Serology", 1), ("Blood Cx (Hold 21d)", 1)]
    },
    {
        "dx": "Bartonella",
        "triggers": ["Cats (Scratch/Bite)", "Homelessness (Lice)"],
        "req_med": False,
        "pearl": "Culture-neg endocarditis.",
        "orders": [("Bartonella Serology", 1)]
    },
    {
        "dx": "Histoplasmosis",
        "triggers": ["Bird/Bat Droppings", "Spelunking", "Pancytopenia", "Oral Ulcers", "Splenomegaly"],
        "req_med": False,
        "pearl": "MO Endemic. Adrenal insufficiency mimic.",
        "orders": [("Urine/Serum Histo Ag", 1), ("Ferritin", 1)]
    },
    {
        "dx": "Temporal Arteritis (GCA)",
        "triggers": ["Jaw Claudication", "Vision Changes", "Age > 50", "New Headache"],
        "req_med": False,
        "pearl": "Emergency. High ESR.",
        "orders": [("ESR & CRP", 1), ("Temporal Artery US", 2), ("Temporal Artery Bx", 3)]
    },
    {
        "dx": "Infectious Endocarditis",
        "triggers": ["New Murmur", "Splinter Hemorrhages", "Prosthetic Valve", "IV Drug Use"],
        "req_med": False,
        "pearl": "Duke Criteria. TTE insensitive for prosthetics.",
        "orders": [("Blood Cx x3", 0), ("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Malignancy (Lymphoma/RCC)",
        "triggers": ["Weight Loss >10%", "Night Sweats", "Hematuria", "Splenomegaly"],
        "req_med": False,
        "pearl": "Consider Naproxen Test if workup negative.",
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2), ("Naproxen Challenge", 1)]
    },
    {
        "dx": "Adult Onset Still's",
        "triggers": ["Ferritin > 1000", "Salmon Rash", "Joint Pain (Arthralgia)", "Sore Throat"],
        "req_med": False,
        "pearl": "Yamaguchi Criteria. Diagnosis of exclusion.",
        "orders": [("Ferritin", 1), ("Glycosylated Ferritin", 1)]
    }
]

# --- LOGIC ENGINE ---
def get_plan(inputs):
    active_dx = []
    # Plan structure: {Category: [List of tests]}
    grouped_orders = {
        "Basic": set(["Blood Cx x2", "CBC", "CMP", "ESR", "CRP"]), 
        "Animal/Vector": set(),
        "Sexual/Blood": set(),
        "Imaging": set(),
        "Other": set()
    }
    
    # Universal Additions based on risk
    if "IV Drug Use" in inputs['social']:
        grouped_orders["Sexual/Blood"].update(["HIV 1/2 Ag/Ab", "Syphilis IgG", "HCV Ab"])
        
    for d in DATABASE:
        score = 0
        triggers = []
        for t in d["triggers"]:
            if t in inputs["all_positives"]:
                score += 1
                triggers.append(t)

        # Logic overrides (DRESS, GCA, etc - kept same as v12)
        if d["dx"] == "DRESS Syndrome":
            if inputs["meds"] and score >= 1:
                days = inputs["days_since_new_med"]
                if days and (days < 5 or days > 90): score = 0
            else: score = 0
        
        if d["dx"] == "Infectious Endocarditis":
            if "Prosthetic Valve" in inputs["social"]:
                d['orders'] = [("Blood Cx x3", 0), ("TEE", 3)]
                if score == 0: score = 1
                
        if d['dx'] == "Temporal Arteritis (GCA)" and inputs['age'] < 50: score = 0

        if score > 0:
            active_dx.append({"dx": d["dx"], "triggers": triggers})
            
            # Assign tests to categories for the Note
            for test, tier in d['orders']:
                if "Serology" in test or "Ag" in test or "PCR" in test:
                    grouped_orders["Animal/Vector"].add(test)
                elif "CT" in test or "TTE" in test or "TEE" in test or "US" in test:
                    grouped_orders["Imaging"].add(test)
                elif test not in grouped_orders["Basic"]:
                    grouped_orders["Other"].add(test)

    # STEWARDSHIP (Remove Done)
    items_to_remove = set()
    for result in inputs["prior_workup"]:
        if result in PRIOR_MAP: items_to_remove.add(PRIOR_MAP[result])
            
    for cat in grouped_orders:
        grouped_orders[cat] -= items_to_remove

    return active_dx, grouped_orders

def generate_note(inputs, active_dx, grouped_orders):
    # 1. HPI SENTENCE
    txt = f"{inputs['age']}yo {inputs['sex']} presenting with fever for {inputs['duration_fever_days']} days, "
    
    # Exposures formatting
    exposures = [x for x in inputs['all_positives'] if x]
    if exposures:
        txt += f"with exposures including {', '.join(exposures)}. "
    else:
        txt += "with no clear localizing exposures. "
        
    # 2. DIFFERENTIAL SENTENCE
    if active_dx:
        # Split into Likely (top 3) and Less Likely
        likely = [d['dx'] for d in active_dx[:3]]
        less_likely = [d['dx'] for d in active_dx[3:]]
        
        txt += f"Differential includes {', '.join(likely)}"
        if less_likely:
            txt += f", less likely {', '.join(less_likely)}."
        else:
            txt += "."
    else:
        txt += "Differential is broad including occult infection, malignancy, and rheumatologic etiology."
        
    # 3. PRIOR WORKUP SENTENCE
    if inputs['prior_workup']:
        # Clean up the strings (e.g., "Negative Blood Cx x3" -> "Blood Cx")
        clean_priors = [p.replace("Negative ", "").replace("Normal ", "") for p in inputs['prior_workup']]
        txt += f" Previous workup negative including {', '.join(clean_priors)}."
    
    txt += "\n"
    
    # 4. PLAN BULLETS (Contextualized)
    
    # Basic
    basics = sorted(list(grouped_orders['Basic']))
    if basics:
        txt += f"- Ordering {', '.join(basics)} for basic workup\n"
        
    # Animal/Vector
    animals = sorted(list(grouped_orders['Animal/Vector']))
    if animals:
        txt += f"- Ordering {', '.join(animals)} for animal/environmental exposures\n"
        
    # Sexual/Blood
    sexual = sorted(list(grouped_orders['Sexual/Blood']))
    if sexual:
        txt += f"- Ordering {', '.join(sexual)} given risk factors\n"
        
    # Imaging
    imaging = sorted(list(grouped_orders['Imaging']))
    if imaging:
        txt += f"- Ordering {', '.join(imaging)} to rule out structural/embolic etiology\n"
        
    # Other
    other = sorted(list(grouped_orders['Other']))
    if other:
        txt += f"- Ordering {', '.join(other)} for expanded differential\n"

    return txt

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("Patient Data")
    if st.button("Clear All Inputs"):
        st.session_state.clear()
        st.rerun()

    # 1. DEMOGRAPHICS
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 28)
    sex = c2.selectbox("Sex", ["Male", "Female"])
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV Positive", "Transplant"])
    
    if immune == "HIV Positive":
        cd4 = st.slider("CD4 Count", 0, 1200, 450)

    # 2. MEDS & ABX
    st.header("Meds & History")
    on_abx = st.checkbox("Currently on Antibiotics?")
    meds = st.multiselect("New/High-Risk Meds", ["New Beta-Lactam", "New Anticonvulsant", "New Sulfa Drug", "Allopurinol"])
    days_since_new_med = None
    if meds:
        days_since_new_med = st.number_input("Days since started", 0, 365, 0)
        
    duration_fever_days = st.number_input("Duration of fever (days)", 0, 365, 42)

    # 3. PRIOR WORKUP (RESULTS BASED)
    st.header("Prior Workup (Results)")
    pw_opts = [
        "Negative Blood Cx x3", "Negative HIV Screen", "Negative Syphilis Screen",
        "Normal CT Chest/Abd/Pelvis", "Normal TTE", "Normal TEE", "Negative ANA", "Normal Ferritin"
    ]
    prior_workup = st.multiselect("Select Negative/Normal Results:", pw_opts)

    # 4. REVIEW OF SYSTEMS (CATEGORIZED)
    st.header("Review of Systems")
    with st.expander("General / HEENT", expanded=False):
        ros_gen = st.multiselect("Constitutional", ["Night Sweats", "Weight Loss >10%", "Fatigue", "New Headache"])
        ros_heent = st.multiselect("Head/Neck", ["Jaw Claudication", "Vision Changes", "Sore Throat", "Oral Ulcers"])  
    with st.expander("CV / Pulmonary", expanded=False):
        ros_cv = st.multiselect("Cardiopulmonary", ["New Murmur", "Splinter Hemorrhages", "Cough", "Hemoptysis"])
    with st.expander("GI / GU", expanded=False):
        ros_gi = st.multiselect("Abdominal", ["Abd Pain", "Diarrhea", "Hepatodynia", "Hematuria"])
    with st.expander("Neuro / MSK / Derm", expanded=False):
        ros_msk = st.multiselect("MSK/Derm", ["Joint Pain (Arthralgia)", "Back Pain (Lumbar)", "Rash (Diffuse)", "Verrucous Lesions"])
    with st.expander("Labs (Objective)", expanded=False):
        ros_labs = st.multiselect("Lab Findings", ["Eosinophilia", "Pancytopenia", "Ferritin > 1000", "Splenomegaly"])

    # 5. EXPOSURES
    st.header("Exposures")
    with st.expander("Vectors", expanded=True):
        cats = st.checkbox("Pet Cat")
        livestock = st.checkbox("Farm Animals")
        birds = st.checkbox("Birds/Bats")
        ticks = st.checkbox("Ticks")
    
    social = st.multiselect("Social", ["Unpasteurized Dairy", "Travel (Mexico/Med)", "Prosthetic Valve", "IV Drug Use", "Sexual Activity"])

    run = st.button("Generate Note")

# --- MAIN DISPLAY ---
st.title("ID-CDSS | Custom Note Generator")

if run:
    # Input Aggregation
    all_symptoms = ros_gen + ros_heent + ros_cv + ros_gi + ros_msk + ros_labs
    all_positives = meds + social + all_symptoms
    if cats: all_positives.append("Pet Cat")
    if livestock: all_positives.append("Farm Animals")
    if birds: all_positives.append("Bird/Bat Droppings")
    if ticks: all_positives.append("Tick Bite")

    inputs = {
        "age": age, "sex": sex, "immune": immune, 
        "on_abx": on_abx, "meds": meds, "days_since_new_med": days_since_new_med,
        "duration_fever_days": duration_fever_days,
        "all_positives": all_positives, "social": social,
        "prior_workup": set(prior_workup),
    }

    active_dx, grouped_orders = get_plan(inputs)

    col1, col2 = st.columns([1,1])

    with col1:
        if on_abx:
            st.markdown("<div class='alert'>⚠️ **STEWARDSHIP:** Patient on antibiotics. Hold recommended.</div>", unsafe_allow_html=True)
        
        st.subheader("Differential Logic")
        if not active_dx:
            st.write("No specific syndromes triggered. Proceed with broad FUO protocol.")
        else:
            for d in active_dx:
                st.markdown(f"**{d['dx']}**")
                st.caption(f"Trigger: {', '.join(d['triggers'])}")

    with col2:
        st.subheader("Consult Note")
        note_text = generate_note(inputs, active_dx, grouped_orders)
        st.text_area("Copy/Paste", note_text, height=400)
