import streamlit as st
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Immune Expansion", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .critical { border-left: 6px solid #dc3545; padding: 10px; background-color: #ffe6e6; font-weight: bold; }
    .endemic { border-left: 6px solid #fd7e14; padding: 10px; background-color: #fff3cd; }
    .noninf { border-left: 6px solid #17a2b8; padding: 10px; background-color: #e0f7fa; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def check_faget(tmax, hr):
    if tmax >= 102.0 and hr < 100: return True
    return False

# --- MAPPING ---
PRIOR_MAP = {
    "Negative Blood Cx": ["Blood Cx", "Blood Cx x2", "Blood Cx x3", "Blood Cx (Hold 21d)"],
    "Negative HIV": ["HIV 1/2 Ag/Ab", "HIV 1/2 Ag/Ab (4th Gen)"],
    "Normal CT": ["CT Chest/Abd/Pelvis"],
    "Normal TTE": ["TTE"],
    "Negative O&P": ["Stool O&P", "Stool Pathogen Panel"],
    "Negative ANA/RF": ["ANA (IFA)", "Rheumatoid Factor", "Anti-CCP"],
    "Negative Malaria Smear": ["Malaria Smear x3", "Rapid Antigen"]
}

# --- DATABASE ---
DATABASE = [
    # --- CRITICAL / URGENT ---
    {
        "dx": "Neutropenic Fever / Sepsis", "type": "CRITICAL",
        "triggers": ["Chemotherapy", "Neutropenia", "Indwelling Line"],
        "req_immune": "Chemo", # Only triggers for Chemo patients
        "orders": [("Blood Cx x2 (Peripheral + Line)", 0), ("Empiric Cefepime/Zosyn", 0), ("Lactate", 0)]
    },
    {
        "dx": "Hemophagocytic Lymphohistiocytosis (HLH)", "type": "CRITICAL",
        "triggers": ["Ferritin > 3000", "Pancytopenia", "Splenomegaly", "Hypertriglyceridemia"],
        "orders": [("Soluble CD25", 1), ("Fibrinogen", 1), ("Bone Marrow Biopsy", 3)]
    },
    {
        "dx": "Rocky Mountain Spotted Fever", "type": "CRITICAL",
        "triggers": ["Tick Bite (Dog/Wood)", "Rash (Palms/Soles)", "Hyponatremia"],
        "pearl": "Start Doxycycline immediately. Do not wait for serology.",
        "orders": [("START Doxycycline (Empiric)", 0), ("Rickettsia PCR", 1)]
    },
    {
        "dx": "Malaria", "type": "CRITICAL",
        "triggers": ["Travel (Sub-Saharan Africa)", "Travel (SE Asia)", "Travel (South America)"],
        "orders": [("Malaria Smear x3", 0), ("Rapid Antigen", 0)]
    },

    # --- CHEMO / BIOLOGIC SPECIFIC (NEW) ---
    {
        "dx": "Invasive Aspergillosis", "type": "Infectious",
        "triggers": ["Chemotherapy", "Neutropenia", "Lung Transplant", "Biologics (TNFa)", "Hemoptysis"],
        "pearl": "Halo sign on CT. Galactomannan in serum/BAL.",
        "orders": [("Serum Galactomannan", 1), ("Chest CT (Halo Sign)", 2), ("Bronch w/ BAL", 3)]
    },
    {
        "dx": "Hepatitis B Reactivation", "type": "Infectious",
        "triggers": ["Biologics (Rituximab)", "Chemotherapy", "Elevated LFTs"],
        "req_immune": "Biologics",
        "pearl": "Rituximab (anti-CD20) carries high risk of HBV reactivation. Check core antibody.",
        "orders": [("Hep B Core Ab (Total)", 1), ("Hep B Surface Ag", 1), ("HBV DNA", 1)]
    },
    {
        "dx": "Invasive Candidiasis", "type": "Infectious",
        "triggers": ["Chemotherapy", "Neutropenia", "TPN", "Central Line"],
        "pearl": "Hepatosplenic Candida in leukemia recovery phase.",
        "orders": [("Blood Cx", 0), ("Beta-D-Glucan", 1), ("TTE (R/O Endophthalmitis if +)", 2)]
    },

    # --- ENDEMIC FUNGAL ---
    {
        "dx": "Histoplasmosis (Disseminated)", "type": "Endemic Fungal",
        "triggers": ["Missouri Residence", "Biologics (TNFa)", "Chemotherapy", "Bird/Bat Droppings"],
        "pearl": "TNF-alpha blockers release the 'brake' on granulomas.",
        "orders": [("Urine/Serum Histo Ag", 1), ("Ferritin", 1)]
    },
    {
        "dx": "Blastomycosis", "type": "Endemic Fungal",
        "triggers": ["Missouri Residence", "Decaying Wood", "Waterways", "Skin Lesions (Verrucous)"],
        "orders": [("Urine Blasto Ag", 1), ("Sputum Fungal Cx", 1)]
    },

    # --- TROPICAL / TRAVEL ---
    {
        "dx": "Melioidosis", "type": "Tropical",
        "triggers": ["Travel (SE Asia)", "Diabetes", "Pneumonia"],
        "orders": [("Blood/Sputum Cx", 0), ("Burkholderia Serology", 1)]
    },
    {
        "dx": "Paracoccidioidomycosis", "type": "Tropical",
        "triggers": ["Travel (South America)", "Oral Ulcers", "Lymphadenopathy"],
        "orders": [("Fungal Serologies", 1), ("Tissue Biopsy", 3)]
    },
    {
        "dx": "African Trypanosomiasis", "type": "Tropical",
        "triggers": ["Travel (Sub-Saharan Africa)", "Chancre", "CNS Symptoms"],
        "orders": [("Blood Smear", 0), ("CATT Serology", 1)]
    },
    {
        "dx": "Chagas Disease", "type": "Tropical",
        "triggers": ["Travel (South America)", "Heart Failure", "Arrhythmia"],
        "orders": [("Trypanosoma cruzi Serology", 1)]
    },
    {
        "dx": "Leishmaniasis", "type": "Tropical",
        "triggers": ["Travel (Middle East)", "Travel (South America)", "Splenomegaly", "Pancytopenia"],
        "orders": [("rK39 Dipstick", 2), ("Bone Marrow Biopsy", 3)]
    },

    # --- NON-INFECTIOUS ---
    {
        "dx": "Kikuchi-Fujimoto", "type": "Non-Infectious",
        "triggers": ["Cervical Lymphadenopathy", "Female Sex", "Age < 40"],
        "orders": [("Excisional Node Biopsy", 3)]
    },
    {
        "dx": "DRESS Syndrome", "type": "Non-Infectious",
        "triggers": ["Rash (Diffuse)", "Eosinophilia", "Hepatodynia"], 
        "req_med": True,
        "orders": [("CBC (Eosinophils)", 1), ("HHV-6 PCR", 1)]
    },
    {
        "dx": "Autoimmune Hepatitis (AIH)", "type": "Non-Infectious",
        "triggers": ["Elevated LFTs", "Eosinophilia", "Female Sex"],
        "orders": [("Liver Autoimmune Panel", 1)]
    },
    {
        "dx": "Malignancy (Lymphoma)", "type": "Non-Infectious",
        "triggers": ["Weight Loss", "Night Sweats", "Splenomegaly", "LDH Elevation"],
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2)]
    },
    
    # --- STANDARD ---
    {
        "dx": "Tuberculosis", "type": "Infectious",
        "triggers": ["TB Exposure", "Biologics (TNFa)", "Travel (Sub-Saharan Africa)", "Homelessness"],
        "pearl": "High reactivation risk with TNF inhibitors.",
        "orders": [("Quantiferon-TB Gold", 1), ("Sputum AFB x3", 1)]
    },
    {
        "dx": "Infectious Endocarditis", "type": "Infectious",
        "triggers": ["New Murmur", "IV Drug Use", "Prosthetic Valve"],
        "orders": [("Blood Cx x3", 0), ("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Acute HIV / Syphilis", "type": "Infectious",
        "triggers": ["MSM", "High Risk Sexual Activity", "Transactional Sex"],
        "orders": [("HIV 1/2 Ag/Ab (4th Gen)", 0), ("Syphilis Cascade", 0)]
    }
]

# --- LOGIC ENGINE ---
def optimize_orders(raw_orders, inputs):
    final_orders = {"Immediate": set(), "Targeted": set(), "Structural": set(), "Contingency": set()}
    all_items = []
    for cat, items in raw_orders.items(): all_items.extend(items)

    # Superset Logic
    if any("Blood Cx" in x for x in all_items):
        if "Chemotherapy" in inputs['immune']:
            final_orders["Immediate"].add("Blood Cx x2 (Peripheral + Line)")
        else:
            final_orders["Immediate"].add("Blood Cx x3 (Hold 21d)")
    
    # Stool Logic
    has_eos = "Eosinophilia" in inputs['all_positives']
    if has_eos and (inputs['social'] or any(x in inputs['all_positives'] for x in ["Diarrhea", "Abd Pain"])):
        final_orders["Targeted"].add("Stool O&P x3")

    for item in all_items:
        if any(x in item for x in ["Blood Cx", "Stool"]): continue
        
        if "Biopsy" in item or "rK39" in item: final_orders["Contingency"].add(item)
        elif any(x in item for x in ["CT ", "TTE", "TEE"]): final_orders["Structural"].add(item)
        elif any(x in item for x in ["CBC", "CMP", "ESR", "CRP", "HIV", "RPR", "UA", "Lactate"]): final_orders["Immediate"].add(item)
        else: final_orders["Targeted"].add(item)

    # Stewardship
    clean_priors = set()
    for p in inputs['prior_workup']:
        if p in PRIOR_MAP: clean_priors.update(PRIOR_MAP[p])
    for cat in final_orders:
        final_orders[cat] = {o for o in final_orders[cat] if not any(p in o for p in clean_priors)}

    return final_orders

def get_differential(inputs):
    active_dx = []
    raw_orders = {"0": [], "1": [], "2": [], "3": []}
    
    raw_orders["0"].extend(["CBC", "CMP", "ESR", "CRP", "UA"])
    if any(r in inputs['all_positives'] for r in ["IV Drug Use", "MSM", "High Risk Sexual Activity"]):
        raw_orders["0"].extend(["HIV 1/2 Ag/Ab", "Syphilis Cascade"])

    if check_faget(inputs['tmax'], inputs['hr']):
        inputs['all_positives'].append("Relative Bradycardia")

    for d in DATABASE:
        score = 0
        triggers = []
        
        for t in d["triggers"]:
            if any(pos_t in t for pos_t in inputs["all_positives"]) or t in inputs["all_positives"]:
                if t == "Relative Bradycardia": score += 2
                elif "Ferritin > 3000" in t: score += 5
                else: score += 1
                triggers.append(t)
        
        # MO Bias
        if d['dx'] in ["Histoplasmosis (Disseminated)", "Blastomycosis"]:
            score += 1
            if "Missouri Residence" not in triggers: triggers.append("Missouri Residence")

        # Immune Status Gates
        # 1. Transplant
        is_tx = inputs['immune'] == "Transplant"
        if d.get("req_tx") and not is_tx: score = 0
        
        # 2. Chemo / Biologics (NEW)
        req_immune = d.get("req_immune")
        if req_immune:
            if req_immune == "Chemo" and "Chemotherapy" not in inputs['immune']: score = 0
            if req_immune == "Biologics" and "Biologics" not in inputs['immune']: score = 0

        # 3. HIV CD4
        if d.get("req_cd4_ceiling"):
            if inputs['immune'] != "HIV Positive": score = 0
            elif inputs.get("cd4", 1000) > d["req_cd4_ceiling"]: score = 0
            elif score == 0: score = 1; triggers.append(f"CD4 < {d['req_cd4_ceiling']}")

        if d.get("req_med") and not (inputs["meds"] and score >= 1): score = 0
        if d['dx'] == "Kikuchi-Fujimoto Disease" and inputs['age'] > 40: score = 0

        if score > 0:
            active_dx.append({"dx": d["dx"], "type": d["type"], "triggers": triggers, "score": score})
            for test, tier in d.get('orders', []):
                raw_orders[str(tier)].append(test)

    return sorted(active_dx, key=lambda x: x['score'], reverse=True), raw_orders

def generate_note(inputs, active_dx, optimized_orders):
    txt = f"Date: {datetime.date.today()}\n"
    txt += f"{inputs['age']}yo {inputs['sex']} "
    if inputs['immune'] != "Immunocompetent": txt += f"({inputs['immune']}) "
    if "Transplant" in inputs['immune']: txt += f"[{inputs['tx_type']}, {inputs['tx_time']}] "
    
    txt += f"presenting with fever (Tmax {inputs['tmax']}, HR {inputs['hr']}) for {inputs['duration_fever_days']} days.\n"
    
    if check_faget(inputs['tmax'], inputs['hr']):
        txt += "Vitals notable for Relative Bradycardia (Faget's Sign).\n"
    
    exposures = [x for x in inputs['all_positives'] if x and x not in ["Relative Bradycardia", "Missouri Residence"]]
    txt += f"Relevant History: {', '.join(exposures) if exposures else 'Non-contributory'}.\n"
    
    if inputs['prior_workup']:
        priors = [p.replace("Negative ", "").replace("Normal ", "") for p in inputs['prior_workup']]
        txt += f"Prior Workup Negative: {', '.join(priors)}.\n"

    txt += "\nAssessment & Differential:\n"
    
    crit = [d for d in active_dx if d['type'] == 'CRITICAL']
    if crit:
        names = [d['dx'] for d in crit]
        txt += f"**CRITICAL CONSIDERATIONS**: {', '.join(names)}.\n"

    inf = [d for d in active_dx if 'Infectious' in d['type'] or 'Endemic' in d['type'] or 'Tropical' in d['type']]
    if inf:
        names = [d['dx'] for d in inf]
        txt += f"Infectious differential prioritizes {', '.join(names)}.\n"

    non_inf = [d for d in active_dx if d['type'] == 'Non-Infectious']
    if non_inf:
        names = [d['dx'] for d in non_inf]
        trigs = set()
        for d in non_inf: trigs.update(d['triggers'])
        txt += f"Non-infectious etiologies also in the differential including {', '.join(names)} based on {', '.join(trigs)}.\n"

    txt += "\nPrognostic Note: 30-50% of FUO cases remain undiagnosed; >75% of those resolve spontaneously. <10% are occult malignancy.\n"

    txt += "\nPlan:\n"
    if "STOP/HOLD" in str(optimized_orders) or "Discontinue" in str(optimized_orders):
         txt += "1. Therapeutic Hold: Stop empiric antibiotics/suspect agents to define fever curve.\n"

    if optimized_orders['Immediate']:
        txt += f"- Immediate/Basic: {', '.join(sorted(optimized_orders['Immediate']))}\n"
    if optimized_orders['Targeted']:
        txt += f"- Targeted/Serologies: {', '.join(sorted(optimized_orders['Targeted']))}\n"
    if optimized_orders['Structural']:
        txt += f"- Structural: {', '.join(sorted(optimized_orders['Structural']))}\n"
    if optimized_orders['Contingency']:
        txt += f"- Deferred (Phase 2): {', '.join(sorted(optimized_orders['Contingency']))}\n"

    return txt

# --- UI ---
with st.sidebar:
    st.title("Patient Data")
    if st.button("Clear All"): st.session_state.clear(); st.rerun()
    
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 35)
    sex = c2.selectbox("Sex", ["Female", "Male"])
    
    # IMMUNE EXPANSION
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV Positive", "Transplant", "Chemotherapy/Neutropenia", "Biologics (TNFa/Ritux)"])
    
    cd4 = 1000
    tx_type, tx_time = None, None
    if immune == "HIV Positive": 
        cd4 = st.slider("CD4", 0, 1200, 450)
    if immune == "Transplant":
        tx_type = st.selectbox("Organ", ["Kidney", "Liver", "Lung", "BMT"])
        tx_time = st.selectbox("Time from Tx", ["<1 Month", "1-6 Months", ">6 Months"])

    tmax = st.number_input("T-Max (°F)", 98.0, 107.0, 102.5)
    hr = st.number_input("HR at T-Max", 40, 160, 90)
    duration_fever_days = st.number_input("Fever Days", 0, 365, 21)
    
    st.header("Subjective History")
    on_abx = st.checkbox("On Antibiotics?")
    
    with st.expander("Social / Risks", expanded=True):
        ivdu = st.checkbox("IV Drug Use")
        msm = st.checkbox("MSM")
        high_risk_sex = st.checkbox("High Risk Sexual Activity")
        sex_work = st.checkbox("Transactional Sex")
        hc_worker = st.checkbox("Healthcare Worker")
        military = st.checkbox("Military Service")
        homeless = st.checkbox("Homelessness")
        sick_contact = st.checkbox("Sick Contacts")
        
    with st.expander("Vectors / Diet", expanded=False):
        cats = st.checkbox("Cats")
        livestock = st.checkbox("Farm Animals")
        raw_crab = st.checkbox("Raw Crustaceans")
        tick = st.checkbox("Tick Bite")
        farm = st.checkbox("Rural / Farm Living")
        well = st.checkbox("Well Water")
        
    with st.expander("Travel", expanded=False):
        travel_se_asia = st.checkbox("SE Asia")
        travel_sub_sahara = st.checkbox("Sub-Saharan Africa")
        travel_s_amer = st.checkbox("South America")
        travel_mid_east = st.checkbox("Middle East")
        travel_med = st.checkbox("Mediterranean / Mexico")

    meds = st.multiselect("New Meds", ["Antibiotic", "Anticonvulsant", "Sulfa"])
    
    st.header("Objective Findings")
    with st.expander("Physical Exam", expanded=False):
        murmur = st.checkbox("New Murmur")
        cervical_lad = st.checkbox("Cervical Lymphadenopathy")
        splenomegaly = st.checkbox("Splenomegaly")
        rash = st.checkbox("Rash (Any)")
        chancre = st.checkbox("Chancre / Eschar")
        
    with st.expander("Labs", expanded=False):
        ferritin_crit = st.checkbox("Ferritin > 3000")
        ferritin_high = st.checkbox("Ferritin > 1000")
        pancytopenia = st.checkbox("Pancytopenia")
        eosinophilia = st.checkbox("Eosinophilia")
        lfts = st.checkbox("Elevated LFTs")
        diabetes = st.checkbox("Diabetes")

    st.header("Prior Workup")
    prior_workup = st.multiselect("Negatives", ["Negative Blood Cx", "Negative HIV", "Negative O&P", "Negative ANA/RF", "Negative Quantiferon", "Negative Malaria Smear"])
    
    run = st.button("Generate Note")

# --- MAIN ---
st.title("ID-CDSS | Director Suite v28")

if run:
    all_positives = meds[:]
    # Social
    if ivdu: all_positives.append("IV Drug Use")
    if msm: all_positives.append("MSM")
    if high_risk_sex: all_positives.append("High Risk Sexual Activity")
    if sex_work: all_positives.append("Transactional Sex")
    if sick_contact: all_positives.append("Sick Contacts")
    if hc_worker: all_positives.append("Healthcare Worker")
    if military: all_positives.append("Military Service")
    if homeless: all_positives.append("Homelessness")
    # Vectors
    if farm: all_positives.append("Rural Area")
    if well: all_positives.append("Well Water")
    if raw_crab: all_positives.append("Raw Crustaceans")
    if tick: all_positives.append("Tick Bite")
    if cats: all_positives.append("Cats")
    if livestock: all_positives.append("Farm Animals")
    # Travel
    if travel_se_asia: all_positives.append("Travel (SE Asia)")
    if travel_sub_sahara: all_positives.append("Travel (Sub-Saharan Africa)")
    if travel_s_amer: all_positives.append("Travel (South America)")
    if travel_mid_east: all_positives.append("Travel (Middle East)")
    if travel_med: all_positives.append("Travel (Med/Mexico)")
    # Obj
    if murmur: all_positives.append("New Murmur")
    if cervical_lad: all_positives.append("Cervical Lymphadenopathy")
    if splenomegaly: all_positives.append("Splenomegaly")
    if rash: all_positives.append("Rash")
    if chancre: all_positives.append("Chancre")
    if ferritin_crit: all_positives.append("Ferritin > 3000")
    if ferritin_high: all_positives.append("Ferritin > 1000")
    if pancytopenia: all_positives.append("Pancytopenia")
    if eosinophilia: all_positives.append("Eosinophilia")
    if lfts: all_positives.append("Elevated LFTs")
    if diabetes: all_positives.append("Diabetes")
    if sex == "Female": all_positives.append("Female Sex")
    if age < 40: all_positives.append("Age < 40")

    inputs = {
        "age": age, "sex": sex, "immune": immune, "cd4": cd4,
        "tx_type": tx_type, "tx_time": tx_time,
        "tmax": tmax, "hr": hr, "duration_fever_days": duration_fever_days,
        "all_positives": all_positives, 
        "social": [x for x in all_positives if x in ["IV Drug Use", "MSM", "High Risk Sexual Activity"]],
        "meds": meds, "prior_workup": set(prior_workup)
    }

    active_dx, raw_orders = get_differential(inputs)
    optimized_orders = optimize_orders(raw_orders, inputs)

    c1, c2 = st.columns([1, 1])
    with c1:
        if check_faget(tmax, hr):
            st.error(f"📉 **Faget's Sign Detected** (Temp {tmax}, HR {hr}).")
        
        st.subheader("Weighted Differential")
        for d in active_dx:
            extra_style = "critical" if d['type'] == "CRITICAL" else ("tropical" if d['type'] == "Tropical" else ("endemic" if "Endemic" in d['type'] else "noninf" if d['type'] == "Non-Infectious" else ""))
            
            if extra_style: st.markdown(f"<div class='{extra_style}'>", unsafe_allow_html=True)
            st.markdown(f"**{d['dx']}**")
            st.caption(f"Trigger: {', '.join(d['triggers'])}")
            if extra_style: st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.subheader("Consult Note")
        note_text = generate_note(inputs, active_dx, optimized_orders)
        st.text_area("Output", note_text, height=500)
        
        st.download_button(
            label="Download Note as .txt",
            data=note_text,
            file_name=f"ID_Consult_{datetime.date.today()}.txt",
            mime="text/plain"
        )
