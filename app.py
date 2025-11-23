import streamlit as st
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Medical Director Suite", layout="wide")

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
    # Relative Bradycardia: Temp > 102 with HR < 100 (rough rule)
    if tmax >= 102.0 and hr < 100: return True
    return False

# --- MAPPING ---
PRIOR_MAP = {
    "Negative Blood Cx": ["Blood Cx", "Blood Cx x2", "Blood Cx x3", "Blood Cx (Hold 21d)"],
    "Negative HIV": ["HIV 1/2 Ag/Ab", "HIV 1/2 Ag/Ab (4th Gen)"],
    "Normal CT": ["CT Chest/Abd/Pelvis"],
    "Normal TTE": ["TTE"],
    "Negative O&P": ["Stool O&P", "Stool Pathogen Panel"],
    "Negative ANA/RF": ["ANA (IFA)", "Rheumatoid Factor", "Anti-CCP"]
}

# --- MASTER DATABASE ---
DATABASE = [
    # --- CRITICAL / URGENT ---
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

    # --- ENDEMIC FUNGAL (MO BIAS) ---
    {
        "dx": "Histoplasmosis (Disseminated)", "type": "Endemic Fungal",
        "triggers": ["Missouri Residence", "Bird/Bat Droppings", "Spelunking", "Pancytopenia", "Oral Ulcers"],
        "orders": [("Urine/Serum Histo Ag", 1), ("Ferritin", 1)]
    },
    {
        "dx": "Blastomycosis", "type": "Endemic Fungal",
        "triggers": ["Missouri Residence", "Decaying Wood", "Waterways", "Skin Lesions (Verrucous)"],
        "orders": [("Urine Blasto Ag", 1), ("Sputum Fungal Cx", 1)]
    },

    # --- RARE / "ZEBRAS" (RESTORED) ---
    {
        "dx": "Kikuchi-Fujimoto Disease", "type": "Non-Infectious",
        "triggers": ["Cervical Lymphadenopathy", "Female Sex", "Age < 40", "Night Sweats"],
        "pearl": "Necrotizing lymphadenitis. Asian females > Caucasian.",
        "orders": [("Excisional Node Biopsy", 3)]
    },
    {
        "dx": "Whipple's Disease", "type": "Infectious",
        "triggers": ["Joint Pain (Migratory)", "Diarrhea", "Weight Loss", "CNS Symptoms"],
        "pearl": "Tropheryma whipplei. Joint pain precedes GI symptoms by years.",
        "orders": [("Whipple PCR (Blood/CSF)", 2), ("EGD w/ Biopsy", 3)]
    },
    {
        "dx": "Atrial Myxoma", "type": "Non-Infectious",
        "triggers": ["New Murmur", "Embolic Events", "Constitutional Symptoms"],
        "pearl": "Cardiac tumor producing IL-6 (Fever). Mimics Endocarditis.",
        "orders": [("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Factitious Fever", "type": "Non-Infectious",
        "triggers": ["Healthcare Worker", "Polymicrobial Bacteremia", "Erratic Fever Curve"],
        "pearl": "Diagnosis of exclusion. Lack of diurnal variation.",
        "orders": [("Supervised Temp Check", 0)]
    },

    # --- VECTOR / ZOONOTIC ---
    {
        "dx": "Tularemia (Typhoidal)", "type": "Infectious",
        "triggers": ["Relative Bradycardia", "Rabbit Exposure", "Lawn Mowing", "Tick Bite (Dog/Wood)"],
        "orders": [("Tularemia Agglutination", 1)]
    },
    {
        "dx": "Brucellosis", "type": "Infectious",
        "triggers": ["Relative Bradycardia", "Unpasteurized Dairy", "Livestock", "Travel (Med/Mexico)"],
        "orders": [("Brucella Serology", 1), ("Blood Cx (Hold 21d)", 1)]
    },
    {
        "dx": "Q Fever", "type": "Infectious",
        "triggers": ["Farm Animals", "Rural Area", "Well Water"],
        "orders": [("Coxiella Serology", 1), ("TTE", 2)]
    },
    {
        "dx": "Bartonella (Trench/Cat Scratch)", "type": "Infectious",
        "triggers": ["Cats", "Homelessness", "Body Lice", "IV Drug Use"],
        "orders": [("Bartonella Serology", 1)]
    },
    {
        "dx": "Visceral Leishmaniasis", "type": "Infectious",
        "triggers": ["Military Service", "Travel (Middle East)", "Splenomegaly", "Pancytopenia"],
        "orders": [("rK39 Dipstick", 2), ("Bone Marrow Biopsy", 3)]
    },

    # --- PARASITIC ---
    {
        "dx": "Strongyloidiasis", "type": "Infectious",
        "triggers": ["Eosinophilia", "Travel (Tropics)", "Immunocompromised"],
        "orders": [("Strongyloides IgG", 1), ("Stool O&P x3", 1)]
    },
    {
        "dx": "Paragonimiasis", "type": "Infectious",
        "triggers": ["Raw Crustaceans", "Hemoptysis", "Eosinophilia"],
        "orders": [("Sputum O&P", 1), ("Paragonimus Serology", 2)]
    },

    # --- NON-INFECTIOUS (RHEUM/ONC/DRUG) ---
    {
        "dx": "Drug-Induced Fever", "type": "Non-Infectious",
        "triggers": ["Relative Bradycardia", "New Beta-Lactam", "New Anticonvulsant", "New Sulfa", "Eosinophilia"],
        "orders": [("Discontinue Suspect Agent", 0)]
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
        "dx": "Systemic Lupus (SLE)", "type": "Non-Infectious",
        "triggers": ["Malar Rash", "Joint Pain", "Proteinuria", "Cytopenias"],
        "orders": [("ANA (IFA)", 1), ("dsDNA", 2), ("C3/C4", 1)]
    },
    {
        "dx": "Adult Onset Still's", "type": "Non-Infectious",
        "triggers": ["Ferritin > 1000", "Salmon Rash", "Joint Pain", "Sore Throat"],
        "orders": [("Ferritin", 1), ("Glycosylated Ferritin", 2)]
    },
    {
        "dx": "Malignancy (Lymphoma/RCC)", "type": "Non-Infectious",
        "triggers": ["Weight Loss", "Night Sweats", "Hematuria", "Splenomegaly"],
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2), ("Naproxen Challenge", 1)]
    },
    
    # --- STANDARD INFECTIOUS ---
    {
        "dx": "Tuberculosis (Miliary)", "type": "Infectious",
        "triggers": ["TB Exposure", "Homelessness", "Incarceration"],
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
        final_orders["Immediate"].add("Blood Cx x3 (Hold 21d)")
    
    # Stool Logic (Eosinophilia pivot)
    has_eos = "Eosinophilia" in inputs['all_positives']
    if has_eos and (inputs['social'] or any(x in inputs['all_positives'] for x in ["Diarrhea", "Abd Pain"])):
        final_orders["Targeted"].add("Stool O&P x3")

    # Autoimmune Panels
    if any("Liver Autoimmune" in x for x in all_items):
        final_orders["Targeted"].add("Liver AI Panel (ANA, ASMA, AMA, IgG)")
    if any("dsDNA" in x for x in all_items):
        final_orders["Targeted"].add("Rheum Serologies (ANA, RF, CCP, C3/C4)")

    for item in all_items:
        if any(x in item for x in ["Blood Cx", "Liver AI", "dsDNA", "Stool"]): continue
        
        if "Biopsy" in item or "rK39" in item: final_orders["Contingency"].add(item)
        elif any(x in item for x in ["CT ", "TTE", "TEE"]): final_orders["Structural"].add(item)
        elif any(x in item for x in ["CBC", "CMP", "ESR", "CRP", "HIV", "RPR", "UA"]): final_orders["Immediate"].add(item)
        else: final_orders["Targeted"].add(item)

    # Stewardship (Prior Workup Removal)
    clean_priors = set()
    for p in inputs['prior_workup']:
        if p in PRIOR_MAP: clean_priors.update(PRIOR_MAP[p])
    
    for cat in final_orders:
        final_orders[cat] = {o for o in final_orders[cat] if not any(p in o for p in clean_priors)}

    return final_orders

def get_differential(inputs):
    active_dx = []
    raw_orders = {"0": [], "1": [], "2": [], "3": []}
    
    # Baseline Labs
    raw_orders["0"].extend(["CBC", "CMP", "ESR", "CRP", "UA"])
    if any(r in inputs['all_positives'] for r in ["IV Drug Use", "MSM"]):
        raw_orders["0"].extend(["HIV 1/2 Ag/Ab", "Syphilis Cascade"])

    # Faget Sign Check
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

        # Transplant Logic
        is_tx = inputs['immune'] == "Transplant"
        if d.get("req_tx") and not is_tx: score = 0
        
        # Zebras Logic (Kikuchi Age Limit)
        if d['dx'] == "Kikuchi-Fujimoto Disease" and inputs['age'] > 40: score = 0

        # Overrides
        if d.get("req_med") and not (inputs["meds"] and score >= 1): score = 0

        if score > 0:
            active_dx.append({"dx": d["dx"], "type": d["type"], "triggers": triggers, "score": score})
            for test, tier in d.get('orders', []):
                raw_orders[str(tier)].append(test)

    return sorted(active_dx, key=lambda x: x['score'], reverse=True), raw_orders

def generate_note(inputs, active_dx, optimized_orders):
    # Date header for documentation
    txt = f"Date: {datetime.date.today()}\n"
    txt += f"{inputs['age']}yo {inputs['sex']} "
    if inputs['immune'] != "Immunocompetent": txt += f"({inputs['immune']}) "
    txt += f"presenting with fever (Tmax {inputs['tmax']}, HR {inputs['hr']}) for {inputs['duration_fever_days']} days.\n"
    
    if check_faget(inputs['tmax'], inputs['hr']):
        txt += "Vitals notable for Relative Bradycardia (Faget's Sign).\n"
    
    exposures = [x for x in inputs['all_positives'] if x and x not in ["Relative Bradycardia", "Missouri Residence"]]
    txt += f"Relevant History: {', '.join(exposures) if exposures else 'Non-contributory'}.\n"
    
    if inputs['prior_workup']:
        priors = [p.replace("Negative ", "").replace("Normal ", "") for p in inputs['prior_workup']]
        txt += f"Prior Workup Negative: {', '.join(priors)}.\n"

    txt += "\nAssessment & Differential:\n"
    
    # Critical / Urgent
    crit = [d for d in active_dx if d['type'] == 'CRITICAL']
    if crit:
        names = [d['dx'] for d in crit]
        txt += f"**CRITICAL CONSIDERATIONS**: {', '.join(names)}.\n"

    # Infectious
    inf = [d for d in active_dx if 'Infectious' in d['type'] or 'Endemic' in d['type']]
    if inf:
        names = [d['dx'] for d in inf]
        txt += f"Infectious differential prioritizes {', '.join(names)}.\n"

    # Non-Infectious (Specific Phrasing)
    non_inf = [d for d in active_dx if d['type'] == 'Non-Infectious']
    if non_inf:
        names = [d['dx'] for d in non_inf]
        trigs = set()
        for d in non_inf: trigs.update(d['triggers'])
        txt += f"Non-infectious etiologies also in the differential including {', '.join(names)} based on {', '.join(trigs)}.\n"

    # Prognostic Hedging
    txt += "\nPrognostic Note: 30-50% of FUO cases remain undiagnosed; >75% of those resolve spontaneously. <10% are occult malignancy.\n"

    txt += "\nPlan:\n"
    if "STOP/HOLD" in str(optimized_orders): # Check if antibiotic hold needed
         txt += "1. Therapeutic Hold: Stop empiric antibiotics to define fever curve.\n"

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
    
    # 1. Demographics & Vitals
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 35)
    sex = c2.selectbox("Sex", ["Female", "Male"])
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV+", "Transplant"])
    
    if immune == "HIV Positive": cd4 = st.slider("CD4", 0, 1200, 450)
    if immune == "Transplant":
        st.selectbox("Organ", ["Kidney", "Liver", "Lung", "BMT"])
        st.selectbox("Time from Tx", ["<1 Month", "1-6 Months", ">6 Months"])

    tmax = st.number_input("T-Max (°F)", 98.0, 107.0, 102.5)
    hr = st.number_input("HR at T-Max", 40, 160, 90)
    duration_fever_days = st.number_input("Fever Days", 0, 365, 21)
    
    # 2. History Inputs
    st.header("Subjective History")
    on_abx = st.checkbox("On Antibiotics?")
    
    with st.expander("Risks / Social", expanded=True):
        hc_worker = st.checkbox("Healthcare Worker")
        ivdu = st.checkbox("IV Drug Use")
        msm = st.checkbox("MSM")
        military = st.checkbox("Military Service")
        homeless = st.checkbox("Homelessness")
        farm = st.checkbox("Rural / Farm Living")
        well = st.checkbox("Well Water")
        
    with st.expander("Diet / Vector", expanded=True):
        raw_crab = st.checkbox("Raw Crustaceans")
        tick = st.checkbox("Tick Bite")
        travel_tropics = st.checkbox("Travel (Tropics)")
        cats = st.checkbox("Cats")
        livestock = st.checkbox("Farm Animals")

    meds = st.multiselect("New Meds", ["Antibiotic", "Anticonvulsant", "Sulfa"])
    
    # 3. Objective Inputs
    st.header("Objective Findings")
    with st.expander("Physical Exam", expanded=False):
        murmur = st.checkbox("New Murmur")
        cervical_lad = st.checkbox("Cervical Lymphadenopathy")
        splenomegaly = st.checkbox("Splenomegaly")
        rash = st.checkbox("Rash (Any)")
        
    with st.expander("Labs", expanded=False):
        ferritin_crit = st.checkbox("Ferritin > 3000")
        ferritin_high = st.checkbox("Ferritin > 1000")
        pancytopenia = st.checkbox("Pancytopenia")
        eosinophilia = st.checkbox("Eosinophilia")
        lfts = st.checkbox("Elevated LFTs")
        joint_mig = st.checkbox("Migratory Arthralgia")

    st.header("Prior Workup")
    prior_workup = st.multiselect("Negatives", ["Negative Blood Cx", "Negative HIV", "Negative O&P", "Negative ANA/RF"])
    
    run = st.button("Generate Note")

# --- MAIN ---
st.title("ID-CDSS | Master Edition (v24)")

if run:
    # Aggregation
    all_positives = meds[:]
    # Subjective
    if hc_worker: all_positives.append("Healthcare Worker")
    if ivdu: all_positives.append("IV Drug Use")
    if msm: all_positives.append("MSM")
    if military: all_positives.append("Military Service")
    if homeless: all_positives.append("Homelessness")
    if farm: all_positives.append("Rural Area")
    if well: all_positives.append("Well Water")
    if raw_crab: all_positives.append("Raw Crustaceans")
    if tick: all_positives.append("Tick Bite")
    if travel_tropics: all_positives.append("Travel (Tropics)")
    if cats: all_positives.append("Cats")
    if livestock: all_positives.append("Farm Animals")
    # Objective
    if murmur: all_positives.append("New Murmur")
    if cervical_lad: all_positives.append("Cervical Lymphadenopathy")
    if splenomegaly: all_positives.append("Splenomegaly")
    if rash: all_positives.append("Rash")
    if ferritin_crit: all_positives.append("Ferritin > 3000")
    if ferritin_high: all_positives.append("Ferritin > 1000")
    if pancytopenia: all_positives.append("Pancytopenia")
    if eosinophilia: all_positives.append("Eosinophilia")
    if lfts: all_positives.append("Elevated LFTs")
    if joint_mig: all_positives.append("Joint Pain (Migratory)")
    if sex == "Female": all_positives.append("Female Sex")
    if age < 40: all_positives.append("Age < 40")

    inputs = {
        "age": age, "sex": sex, "immune": immune, 
        "tmax": tmax, "hr": hr, "duration_fever_days": duration_fever_days,
        "all_positives": all_positives, 
        "social": [x for x in all_positives if x in ["IV Drug Use", "MSM"]],
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
            extra_style = "critical" if d['type'] == "CRITICAL" else ("endemic" if "Endemic" in d['type'] else "noninf" if d['type'] == "Non-Infectious" else "")
            
            if extra_style: st.markdown(f"<div class='{extra_style}'>", unsafe_allow_html=True)
            st.markdown(f"**{d['dx']}**")
            st.caption(f"Trigger: {', '.join(d['triggers'])}")
            if extra_style: st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.subheader("Consult Note")
        note_text = generate_note(inputs, active_dx, optimized_orders)
        st.text_area("Output", note_text, height=500)
        
        # DOWNLOAD BUTTON
        st.download_button(
            label="Download Note as .txt",
            data=note_text,
            file_name=f"ID_Consult_{datetime.date.today()}.txt",
            mime="text/plain"
        )
