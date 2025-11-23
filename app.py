import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Comprehensive", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .transplant { border-left: 6px solid #6f42c1; padding: 10px; background-color: #f3e5f5; }
    .alert { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
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
    "Normal Ferritin": "Ferritin",
    "Negative Malaria Smear": "Malaria Smear x3",
    "Negative Quantiferon": "Quantiferon-TB Gold"
}

# --- DATABASE ---
DATABASE = [
    # --- SOCIAL / ENVIRONMENTAL SPECIFIC (NEW) ---
    {
        "dx": "Tuberculosis (Active/Miliary)",
        "triggers": ["TB Exposure (Known)", "Homelessness", "Incarceration", "Born in Endemic Area"],
        "req_med": False,
        "pearl": "Miliary TB can present as pure FUO w/o lung cavitation. Biopsy often needed (Liver/Bone Marrow).",
        "orders": [("Quantiferon-TB Gold", 1), ("Sputum AFB x3", 1), ("Urine AFB", 1)]
    },
    {
        "dx": "Visceral Leishmaniasis (Kala-Azar)",
        "triggers": ["Military Service (Deployed)", "Travel (Middle East/Tropics)", "Pancytopenia", "Splenomegaly"],
        "req_med": False,
        "pearl": "Classic in Veterans. Fever + Massive Spleen + Pancytopenia. Bone Marrow is diagnostic.",
        "orders": [("rK39 Dipstick / Serology", 1), ("Bone Marrow Biopsy", 3)]
    },
    {
        "dx": "Acute HIV / Dissem. GC / Syphilis",
        "triggers": ["MSM", "High Risk Sexual Activity", "Transactional Sex", "Sick Contacts"],
        "req_med": False,
        "pearl": "Acute HIV can mimic Mononucleosis. Disseminated GC causes fever + tenosynovitis.",
        "orders": [("HIV 1/2 Ag/Ab (4th Gen)", 0), ("HIV Viral Load (PCR)", 1), ("RPR/VDRL", 0), ("NAAT (GC/CT) All Sites", 1)]
    },
    {
        "dx": "Enteric Pathogens (Giardia/Crypto)",
        "triggers": ["Well Water", "Rural Area", "Diarrhea"],
        "req_med": False,
        "pearl": "Chronic Giardiasis causes malabsorption/fever. Well water is a vector.",
        "orders": [("Stool Pathogen Panel (PCR)", 1), ("Stool O&P", 1)]
    },
    {
        "dx": "Bartonella quintana (Trench Fever)",
        "triggers": ["Homelessness", "Body Lice", "Alcohol Use Disorder"],
        "req_med": False,
        "pearl": "Bone pain ('Shin Bone Fever'). Endocarditis risk.",
        "orders": [("Bartonella Serology", 1), ("Blood Cx (Hold 21d)", 0)]
    },

    # --- TRANSPLANT SPECIFIC ---
    {
        "dx": "Acute Graft vs Host Disease (GVHD)",
        "triggers": ["Rash (Diffuse)", "Diarrhea", "Elevated LFTs"],
        "req_tx": "BMT/HSCT",
        "pearl": "Classic Triad: Dermatitis, Enteritis, Hepatitis.",
        "orders": [("Skin/Gut Biopsy", 3)]
    },
    {
        "dx": "CMV Syndrome",
        "triggers": ["Leukopenia", "Thrombocytopenia", "Hepatodynia"],
        "req_tx": "ANY",
        "pearl": "Highest risk 1-6 months post-tx.",
        "orders": [("CMV PCR (Quantitative)", 1)]
    },
    {
        "dx": "Invasive Aspergillosis",
        "triggers": ["Hemoptysis", "Pleuritic Pain", "Lung Transplant"],
        "req_tx": "Lung/BMT",
        "pearl": "Galactomannan in BAL is gold standard.",
        "orders": [("Serum Galactomannan", 1), ("Chest CT", 2)]
    },

    # --- PARASITIC / ZOONOTIC ---
    {
        "dx": "Chagas Disease",
        "triggers": ["Travel (South America)", "Heart Failure", "Arrhythmia"],
        "req_med": False,
        "pearl": "Trypanosoma cruzi. Reactivation in Transplant/AIDS.",
        "orders": [("Trypanosoma cruzi Serology", 1)]
    },
    {
        "dx": "Paragonimiasis",
        "triggers": ["Raw Crustaceans (Crab/Crayfish)", "Hemoptysis", "Eosinophilia"],
        "req_med": False,
        "pearl": "Eating raw crayfish/freshwater crab.",
        "orders": [("Sputum O&P", 1), ("Paragonimus Serology", 1)]
    },
    {
        "dx": "Rocky Mountain Spotted Fever",
        "triggers": ["Tick Bite (Dog/Wood)", "Rash (Palms/Soles)", "Hyponatremia"],
        "req_med": False,
        "pearl": "CRITICAL: Start Doxycycline immediately.",
        "orders": [("START Doxycycline (Empiric)", 0), ("Rickettsia rickettsii PCR", 1)]
    },
    
    # --- STANDARD ---
    {
        "dx": "DRESS Syndrome",
        "triggers": ["Rash (Diffuse)", "Eosinophilia", "Hepatodynia"], 
        "req_med": True,
        "pearl": "Drug exposure (2-8 wk latency).",
        "orders": [("CBC (Eosinophils)", 1), ("LFTs", 1), ("HHV-6 PCR", 1)]
    },
    {
        "dx": "Q Fever",
        "triggers": ["Farm Animals", "Rural Area", "Farm Living"],
        "req_med": False,
        "pearl": "Aerosolized transmission (wind).",
        "orders": [("Coxiella Serology", 1), ("TTE", 2)]
    },
    {
        "dx": "Brucellosis",
        "triggers": ["Unpasteurized Dairy", "Livestock", "Travel (Med/Mexico)"],
        "req_med": False,
        "pearl": "Undulating fever. Osteomyelitis.",
        "orders": [("Brucella Serology", 1), ("Blood Cx (Hold 21d)", 1)]
    },
    {
        "dx": "Temporal Arteritis (GCA)",
        "triggers": ["Jaw Claudication", "Vision Changes", "Age > 50"],
        "req_med": False,
        "pearl": "Emergency. High ESR.",
        "orders": [("ESR & CRP", 1), ("Temporal Artery US", 2), ("Temporal Artery Bx", 3)]
    },
    {
        "dx": "Infectious Endocarditis",
        "triggers": ["New Murmur", "Splinter Hemorrhages", "Prosthetic Valve", "IV Drug Use"],
        "req_med": False,
        "pearl": "Duke Criteria.",
        "orders": [("Blood Cx x3", 0), ("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Malignancy (Lymphoma/RCC)",
        "triggers": ["Weight Loss >10%", "Night Sweats", "Hematuria"],
        "req_med": False,
        "pearl": "Consider Naproxen Test if workup negative.",
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2), ("Naproxen Challenge", 1)]
    },
    {
        "dx": "Malaria",
        "triggers": ["Travel (Sub-Saharan Africa)", "Travel (SE Asia)", "Travel (South America)"],
        "req_med": False,
        "pearl": "Medical Emergency.",
        "orders": [("Malaria Smear x3", 0), ("Rapid Antigen", 0)]
    }
]

# --- LOGIC ENGINE ---
def get_plan(inputs):
    active_dx = []
    grouped_orders = {
        "Immediate/Baseline": set(["Blood Cx x2", "CBC", "CMP", "ESR", "CRP"]), 
        "Vector/Travel": set(),
        "Imaging": set(),
        "Transplant Specific": set(),
        "Other": set()
    }
    
    # Universal Additions based on risk
    if any(r in inputs['all_positives'] for r in ["IV Drug Use", "MSM", "High Risk Sexual Activity", "Transactional Sex"]):
        grouped_orders["Immediate/Baseline"].update(["HIV 1/2 Ag/Ab", "Syphilis IgG", "HCV Ab"])
        
    for d in DATABASE:
        score = 0
        triggers = []
        
        # Trigger Matching
        for t in d["triggers"]:
            if any(pos_t in t for pos_t in inputs["all_positives"]) or t in inputs["all_positives"]:
                score += 1
                triggers.append(t)

        # --- TRANSPLANT LOGIC ---
        is_transplant = inputs['immune'] == "Transplant"
        if "req_tx" in d:
            if not is_transplant: score = 0
            elif d["req_tx"] != "ANY" and d["req_tx"] not in inputs.get("tx_type", ""): score = 0
                
        # --- GENERAL OVERRIDES ---
        if d.get("req_med") and not (inputs["meds"] and score >= 1): score = 0
        if d['dx'] == "Temporal Arteritis (GCA)" and inputs['age'] < 50: score = 0
        if d['dx'] in ["Malaria", "Rocky Mountain Spotted Fever (RMSF)"] and score > 0:
            triggers.append("CRITICAL HISTORY")

        if score > 0:
            active_dx.append({"dx": d["dx"], "triggers": triggers})
            for test, tier in d['orders']:
                if is_transplant and tier > 0: grouped_orders["Transplant Specific"].add(test)
                elif tier == 0: grouped_orders["Immediate/Baseline"].add(test)
                elif "CT" in test or "TTE" in test or "TEE" in test: grouped_orders["Imaging"].add(test)
                elif "Serology" in test or "PCR" in test or "Smear" in test or "IGRA" in test: grouped_orders["Vector/Travel"].add(test)
                else: grouped_orders["Other"].add(test)

    # Stewardship
    items_to_remove = set()
    for result in inputs["prior_workup"]:
        if result in PRIOR_MAP: items_to_remove.add(PRIOR_MAP[result])
            
    for cat in grouped_orders:
        grouped_orders[cat] -= items_to_remove

    return active_dx, grouped_orders

def generate_note(inputs, active_dx, grouped_orders):
    txt = f"{inputs['age']}yo {inputs['sex']} "
    
    if inputs['immune'] == "Transplant":
        txt += f"status post {inputs['tx_type']} transplant ({inputs['tx_time']} ago), "
    elif inputs['immune'] == "HIV Positive":
        txt += f"with HIV (CD4 {inputs['cd4']}), "
        
    txt += f"presenting with fever for {inputs['duration_fever_days']} days. "
    
    exposures = [x for x in inputs['all_positives'] if x]
    if exposures: txt += f"Relevant history: {', '.join(exposures)}. "
    else: txt += "No distinct localization vectors identified. "
        
    if active_dx:
        likely = [d['dx'] for d in active_dx[:3]]
        less_likely = [d['dx'] for d in active_dx[3:]]
        txt += f"\nDifferential prioritizes {', '.join(likely)}"
        if less_likely: txt += f", consider {', '.join(less_likely)}."
    else:
        txt += "\nDifferential is broad (True FUO)."
        
    if inputs['prior_workup']:
        clean_priors = [p.replace("Negative ", "").replace("Normal ", "") for p in inputs['prior_workup']]
        txt += f"\nPrevious workup negative: {', '.join(clean_priors)}."
    
    txt += "\n\nPlan:"
    
    # Order by clinical priority
    base = sorted(list(grouped_orders['Immediate/Baseline']))
    if base: txt += f"\n- Immediate/Basic: {', '.join(base)}"
    
    tx_spec = sorted(list(grouped_orders['Transplant Specific']))
    if tx_spec: txt += f"\n- Transplant Protocol: {', '.join(tx_spec)}"
        
    vec = sorted(list(grouped_orders['Vector/Travel']))
    if vec: txt += f"\n- Vector/Travel specific: {', '.join(vec)}"
        
    img = sorted(list(grouped_orders['Imaging']))
    if img: txt += f"\n- Structural: {', '.join(img)}"
        
    oth = sorted(list(grouped_orders['Other']))
    if oth: txt += f"\n- Extended: {', '.join(oth)}"

    return txt

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("Patient Data")
    if st.button("Clear All"):
        st.session_state.clear()
        st.rerun()

    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 45)
    sex = c2.selectbox("Sex", ["Male", "Female"])
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV Positive", "Transplant"])
    
    tx_type, tx_time, cd4 = None, None, None
    if immune == "HIV Positive": 
        cd4 = st.slider("CD4 Count", 0, 1200, 450)
    elif immune == "Transplant":
        st.markdown("**Transplant Details**")
        tx_type = st.selectbox("Organ Type", ["Kidney", "Liver", "Lung", "Heart", "BMT/HSCT"])
        tx_time = st.selectbox("Time from Tx", ["<1 Month", "1-6 Months", ">6 Months"])

    st.header("History")
    on_abx = st.checkbox("On Antibiotics?")
    meds = st.multiselect("New Meds", ["Beta-Lactam", "Anticonvulsant", "Sulfa", "Allopurinol"])
    days_since_new_med = st.number_input("Days since started", 0, 365, 0) if meds else 0
    duration_fever_days = st.number_input("Fever Days", 0, 365, 10)

    # --- EXPANDED SOCIAL & ENVIRONMENTAL ---
    st.header("Social & Environmental")
    
    with st.expander("Living & Occupational", expanded=True):
        homeless = st.checkbox("Homelessness")
        prison = st.checkbox("Incarceration (Current/Prior)")
        military = st.checkbox("Military Service (Deployed)")
        farm_living = st.checkbox("Rural / Farm Living")
        well_water = st.checkbox("Well Water Consumption")
        sick_contacts = st.checkbox("Sick Contacts")

    with st.expander("Behaviors & TB Risk", expanded=True):
        tb_exposure = st.checkbox("TB Exposure (Known/Suspected)")
        ivdu = st.checkbox("IV Drug Use")
        msm = st.checkbox("MSM")
        sex_high_risk = st.checkbox("High Risk Sexual Activity")
        sex_transactional = st.checkbox("Transactional Sex")

    with st.expander("Animals", expanded=False):
        cats = st.checkbox("Cats")
        livestock = st.checkbox("Farm Animals (Contact)")
        birds = st.checkbox("Birds/Bats")

    with st.expander("Dietary & Travel", expanded=False):
        raw_shell = st.checkbox("Raw Shellfish")
        raw_crab = st.checkbox("Raw Crustacean")
        pork_game = st.checkbox("Undercooked Pork/Game")
        unpast_dairy = st.checkbox("Unpasteurized Dairy")
        travel_se_asia = st.checkbox("SE Asia")
        travel_sub_sahara = st.checkbox("Sub-Saharan Africa")
        travel_s_amer = st.checkbox("South America")
        travel_med = st.checkbox("Mediterranean")

    st.header("Symptoms (ROS)")
    with st.expander("Review of Systems", expanded=False):
        s_gen = st.multiselect("Gen", ["Night Sweats", "Weight Loss", "New Headache"])
        s_msk = st.multiselect("MSK/Derm", ["Rash (Palms/Soles)", "Rash (Diffuse)", "Joint Pain", "Myalgia"]) 
        s_lab = st.multiselect("Labs", ["Eosinophilia", "Thrombocytopenia", "Leukopenia", "Elevated LFTs", "Hyponatremia", "Pancytopenia", "Splenomegaly"])
        s_oth = st.multiselect("Other", ["Jaw Claudication", "Vision Changes", "New Murmur", "Hemoptysis", "Hepatodynia", "Diarrhea", "Arrhythmia"])

    st.header("Prior Workup")
    prior_workup = st.multiselect("Select Negatives", ["Negative Blood Cx x3", "Negative Malaria Smear", "Normal CT Chest/Abd/Pelvis", "Normal TTE", "Negative Quantiferon"])

    run = st.button("Generate Note")

# --- MAIN ---
st.title("ID-CDSS | Comprehensive Edition")

if run:
    # Aggregate Inputs
    all_positives = meds + s_gen + s_msk + s_lab + s_oth
    if raw_shell: all_positives.append("Raw Shellfish/Oysters")
    if raw_crab: all_positives.append("Raw Crustaceans (Crab/Crayfish)")
    if pork_game: all_positives.append("Undercooked Pork/Game")
    if unpast_dairy: all_positives.append("Unpasteurized Dairy")
    if travel_se_asia: all_positives.append("Travel (SE Asia)")
    if travel_sub_sahara: all_positives.append("Travel (Sub-Saharan Africa)")
    if travel_s_amer: all_positives.append("Travel (South America)")
    if travel_med: all_positives.append("Travel (Med/Mexico)")
    if cats: all_positives.append("Cats")
    if livestock: all_positives.append("Farm Animals")
    if birds: all_positives.append("Bird/Bat Droppings")
    if ivdu: all_positives.append("IV Drug Use")
    if homeless: all_positives.append("Homelessness")
    if prison: all_positives.append("Incarceration")
    if military: all_positives.append("Military Service (Deployed)")
    if farm_living: all_positives.append("Rural Area")
    if well_water: all_positives.append("Well Water")
    if sick_contacts: all_positives.append("Sick Contacts")
    if tb_exposure: all_positives.append("TB Exposure (Known)")
    if msm: all_positives.append("MSM")
    if sex_high_risk: all_positives.append("High Risk Sexual Activity")
    if sex_transactional: all_positives.append("Transactional Sex")

    inputs = {
        "age": age, "sex": sex, "immune": immune, 
        "tx_type": tx_type, "tx_time": tx_time, "cd4": cd4,
        "on_abx": on_abx, "meds": meds, "days_since_new_med": days_since_new_med,
        "duration_fever_days": duration_fever_days,
        "all_positives": all_positives, "social": [x for x in all_positives if x in ["IV Drug Use", "Prosthetic Valve"]],
        "prior_workup": set(prior_workup),
    }

    active_dx, grouped_orders = get_plan(inputs)

    c1, c2 = st.columns([1, 1])
    with c1:
        if on_abx: st.error("⚠️ STEWARDSHIP: Patient on Abx. Hold recommended.")
        st.subheader("Differential")
        if active_dx:
            for d in active_dx:
                extra_style = ""
                if "Rubin" in str(d['triggers']) or "Reactivation" in d['dx']: extra_style = "transplant"
                elif "CRITICAL" in str(d['triggers']): extra_style = "tier3"
                
                if extra_style: st.markdown(f"<div class='{extra_style}'>", unsafe_allow_html=True)
                st.markdown(f"**{d['dx']}**")
                st.caption(f"Trigger: {', '.join(d['triggers'])}")
                if extra_style: st.markdown("</div>", unsafe_allow_html=True)
        else: st.info("No specific pattern matches.")

    with c2:
        st.subheader("Note Generation")
        st.text_area("Consult Note", generate_note(inputs, active_dx, grouped_orders), height=500)
