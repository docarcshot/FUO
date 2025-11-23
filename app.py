import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Medical Director Ed.", layout="wide")

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
# This allows the user to select "Negative Blood Cx" and the system knows to remove "Blood Cx" from the plan.
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
        # Toned down: Only triggers if highly specific signs present
        "triggers": ["Rash (Diffuse)", "Eosinophilia", "Hepatodynia"], 
        "req_med": True, # Hard requirement for new med
        "pearl": "Requires drug exposure (2-8 wk latency). Do not diagnose without rash/systemic signs.",
        "orders": [("CBC (Eosinophils)", 1), ("LFTs", 1), ("HHV-6 PCR", 1)]
    },
    {
        "dx": "Q Fever (Coxiella)",
        "triggers": ["Farm Animals", "Parturient Animals", "Dust/Wind Exposure"],
        "req_med": False,
        "pearl": "Culture-neg endocarditis. Doughnut granulomas.",
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
        "dx": "Histoplasmosis (Dissem)",
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
    orders = {0: set(), 1: set(), 2: set(), 3: set()}
    
    # Universal Baseline
    orders[0].add("Blood Cx x3")
    orders[0].add("HIV 1/2 Ag/Ab")
    orders[0].add("Syphilis IgG")
    orders[0].add("CBC, CMP, UA, ESR, CRP, Ferritin")

    for d in DATABASE:
        score = 0
        triggers = []
        for t in d["triggers"]:
            if t in inputs["all_positives"]:
                score += 1
                triggers.append(t)

        # --- DRESS LOGIC (TONED DOWN) ---
        if d["dx"] == "DRESS Syndrome":
            # Must have Meds + (Rash OR Eos OR LFTs)
            if inputs["meds"] and score >= 1:
                # Calculate strict latency (2-8 weeks)
                days = inputs["days_since_new_med"]
                if days and 14 <= days <= 60:
                    score += 2 # Boost only if perfect timing
                elif days and (days < 5 or days > 90):
                    score = 0 # Hard Kill if timing impossible
            else:
                score = 0 # Kill if no meds
        
        # --- ENDOCARDITIS LOGIC ---
        if d["dx"] == "Infectious Endocarditis":
            has_prosthetic = "Prosthetic Valve" in inputs["social"]
            if has_prosthetic:
                d['orders'] = [("Blood Cx x3", 0), ("TEE", 3)] # Skip TTE
                if score == 0: score = 1 # Force inclusion if prosthetic
                
        # --- GCA AGE FILTER ---
        if d['dx'] == "Temporal Arteritis (GCA)" and inputs['age'] < 50:
            score = 0

        if score > 0:
            active_dx.append({"dx": d["dx"], "triggers": triggers, "pearl": d["pearl"]})
            for test, tier in d['orders']:
                orders[tier].add(test)

    # ANTIBIOTIC LOGIC
    if inputs["on_abx"]:
        active_dx.insert(0,
            {"dx": "Medication Effect / Masked Fever",
             "triggers": ["Currently on Antibiotics"],
             "pearl": "Empiric antibiotics may mask culture results and fever curves."})
        
        # Doxycycline Pearl
        if "Doxycycline" in inputs["abx_name"]:
            active_dx[0]['pearl'] += " (Failure of Doxycycline lowers likelihood of Rickettsia/Ehrlichia)."
            
        orders[0].add("STOP/HOLD Empiric Antibiotics (48hr washout)")

    # STEWARDSHIP (Mapping Results to Orders)
    items_to_remove = set()
    for result in inputs["prior_workup"]:
        if result in PRIOR_MAP:
            items_to_remove.add(PRIOR_MAP[result])
            
    for t in orders:
        orders[t] -= items_to_remove

    # ESCALATION LOGIC
    if "Normal CT Chest/Abd/Pelvis" in inputs["prior_workup"]:
        orders[3].add("FDG-PET/CT (Whole Body)")

    return active_dx, orders

def generate_note(inputs, active_dx, orders):
    txt = f"**ID Consult Note**\n"
    txt += f"**Pt:** {inputs['age']}yo {inputs['sex']} | **Immune:** {inputs['immune']}"
    if inputs['immune'] == "HIV Positive": txt += f" (CD4: {inputs['cd4']})"
    txt += "\n\n"
    
    txt += "**History of Present Illness:**\n"
    txt += f"Fever duration: {inputs['duration_fever_days']} days. "
    if inputs['on_abx']: txt += f"Currently on {inputs['abx_name'] or 'Antibiotics'}. "
    txt += "\n\n"
    
    txt += "**Pertinent Positives:**\n"
    positives = [x for x in inputs['all_positives'] if x]
    txt += ", ".join(positives) + "\n\n"

    txt += "**Assessment & Differential:**\n"
    if active_dx:
        for d in active_dx:
            txt += f"- **{d['dx']}**: {', '.join(d['triggers'])}\n"
    else:
        txt += "- True FUO. No specific syndromic matches identified.\n"

    txt += "\n**Plan:**\n"
    if "STOP/HOLD Empiric Antibiotics (48hr washout)" in orders[0]:
        txt += "1. **THERAPEUTIC HOLD:** Discontinue empiric antibiotics.\n"
    
    txt += "2. **Diagnostic Workup:**\n"
    all_orders = []
    for t in [0,1,2,3]: all_orders.extend(orders[t])
    all_orders = [o for o in all_orders if "STOP" not in o]
    
    for o in sorted(set(all_orders)):
        txt += f"- [ ] {o}\n"
    return txt

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("Patient Data")
    if st.button("Clear All Inputs"):
        st.session_state.clear()
        st.rerun()

    # 1. DEMOGRAPHICS
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 50)
    sex = c2.selectbox("Sex", ["Male", "Female"])
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV Positive", "Transplant"])
    
    cd4 = 1000
    # CD4 SLIDER - VISIBLE IMMEDIATELY
    if immune == "HIV Positive":
        cd4 = st.slider("CD4 Count", 0, 1200, 450)

    # 2. MEDS & ABX
    st.header("Meds & History")
    on_abx = st.checkbox("Currently on Antibiotics?")
    abx_name = ""
    if on_abx:
        abx_name = st.text_input("Antibiotic Name (Optional)", placeholder="e.g., Doxycycline, Zosyn")
        
    meds = st.multiselect("New/High-Risk Meds", ["New Beta-Lactam", "New Anticonvulsant", "New Sulfa Drug", "Allopurinol"])
    days_since_new_med = None
    if meds:
        days_since_new_med = st.number_input("Days since started", 0, 365, 0)
        
    duration_fever_days = st.number_input("Duration of fever (days)", 0, 365, 14)

    # 3. PRIOR WORKUP (RESULTS BASED)
    st.header("Prior Workup (Results)")
    # Renamed to reflect results, not just orders
    pw_opts = [
        "Negative Blood Cx x3", "Negative HIV Screen", "Negative Syphilis Screen",
        "Normal CT Chest/Abd/Pelvis", "Normal TTE", "Normal TEE", "Negative ANA", "Normal Ferritin"
    ]
    prior_workup = st.multiselect("Select Negative/Normal Results:", pw_opts)

    # 4. REVIEW OF SYSTEMS (CATEGORIZED)
    st.header("Review of Systems")
    
    with st.expander("General / HEENT", expanded=False):
        ros_gen = st.multiselect("Constitutional", ["Night Sweats", "Weight Loss >10%", "Fatigue", "New Headache"])
        ros_heent = st.multiselect("Head/Neck", ["Jaw Claudication", "Vision Changes", "Sore Throat", "Oral Ulcers", "Neck Pain"])
        
    with st.expander("CV / Pulmonary", expanded=False):
        ros_cv = st.multiselect("Cardiopulmonary", ["New Murmur", "Splinter Hemorrhages", "Cough", "Hemoptysis"])
        
    with st.expander("GI / GU", expanded=False):
        ros_gi = st.multiselect("Abdominal", ["Abd Pain", "Diarrhea", "Hepatodynia", "Hematuria"])
        
    with st.expander("Neuro / MSK / Derm", expanded=False):
        ros_msk = st.multiselect("MSK/Derm", ["Joint Pain (Arthralgia)", "Back Pain (Lumbar)", "Rash (Diffuse)", "Salmon Rash", "Verrucous Lesions"])
        
    with st.expander("Labs (Objective)", expanded=False):
        ros_labs = st.multiselect("Lab Findings", ["Eosinophilia", "Pancytopenia", "Ferritin > 1000", "Splenomegaly"])

    # 5. EXPOSURES
    st.header("Exposures")
    with st.expander("Vectors", expanded=False):
        cats = st.checkbox("Cats (Scratch/Bite)")
        livestock = st.checkbox("Farm Animals")
        birds = st.checkbox("Birds/Bats")
        ticks = st.checkbox("Ticks")
    
    social = st.multiselect("Social", ["Unpasteurized Dairy", "Travel (Mexico/Med)", "Prosthetic Valve", "IV Drug Use", "Homelessness (Lice)"])

    run = st.button("Generate Plan")

# --- MAIN DISPLAY ---
st.title("ID-CDSS | Director Suite v12")

if run:
    # Input Aggregation
    all_symptoms = ros_gen + ros_heent + ros_cv + ros_gi + ros_msk + ros_labs
    all_positives = meds + social + all_symptoms
    if cats: all_positives.append("Cats (Scratch/Bite)")
    if livestock: all_positives.append("Farm Animals")
    if birds: all_positives.append("Bird/Bat Droppings")
    if ticks: all_positives.append("Tick Bite")

    inputs = {
        "age": age, "sex": sex, "immune": immune, "cd4": cd4, 
        "on_abx": on_abx, "abx_name": abx_name,
        "meds": meds, "days_since_new_med": days_since_new_med,
        "duration_fever_days": duration_fever_days,
        "all_positives": all_positives, "social": social,
        "prior_workup": set(prior_workup),
    }

    active_dx, orders = get_plan(inputs)

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
                st.caption(f"Trigger: {', '.join(d['triggers'])} | Pearl: {d['pearl']}")

    with col2:
        st.subheader("Staged Orders")
        st.markdown("<div class='tier0'>", unsafe_allow_html=True)
        st.markdown("**Tier 0: Universal Baseline**")
        for o in sorted(list(orders[0])):
            st.markdown(f"- [ ] **{o}**")
        st.markdown("</div><br>", unsafe_allow_html=True)

        if orders[1]:
            st.markdown("<div class='tier1'>", unsafe_allow_html=True)
            st.markdown("**Tier 1: Targeted Labs**")
            for o in sorted(list(orders[1])): st.markdown(f"- [ ] {o}")
            st.markdown("</div><br>", unsafe_allow_html=True)

        if orders[2]:
            st.markdown("<div class='tier2'>", unsafe_allow_html=True)
            st.markdown("**Tier 2: Structural Imaging**")
            for o in sorted(list(orders[2])): st.markdown(f"- [ ] {o}")
            st.markdown("</div><br>", unsafe_allow_html=True)

        if orders[3]:
            st.markdown("<div class='tier3'>", unsafe_allow_html=True)
            st.markdown("**Tier 3: Escalation**")
            for o in sorted(list(orders[3])): st.markdown(f"- [ ] {o}")
            st.markdown("</div>", unsafe_allow_html=True)

        note_text = generate_note(inputs, active_dx, orders)
        st.divider()
        st.download_button(label="Download Note", data=note_text, file_name="consult_note.txt", mime="text/plain")
        st.text_area("Consult Note", note_text, height=400)
