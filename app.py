import streamlit as st
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Director Gold Master", layout="wide")

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
    .tropical { border-left: 6px solid #6610f2; padding: 10px; background-color: #e0cffc; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def check_faget(tmax, hr):
    if tmax >= 102.0 and hr < 100: return True
    return False

# --- MAPPING (Prior Workup Removal) ---
PRIOR_MAP = {
    "Negative Blood Cx": ["Blood Cx", "Blood Cx x2", "Blood Cx x3", "Blood Cx (Hold 21d)"],
    "Negative HIV": ["HIV 1/2 Ag/Ab", "HIV 1/2 Ag/Ab (4th Gen)"],
    "Normal CT": ["CT Chest/Abd/Pelvis"],
    "Normal TTE": ["TTE"],
    "Negative O&P": ["Stool O&P", "Stool Pathogen Panel"],
    "Negative ANA/RF": ["ANA (IFA)", "Rheumatoid Factor", "Anti-CCP"],
    "Negative Quantiferon": ["Quantiferon-TB Gold"],
    "Negative Malaria": ["Malaria Smear x3", "Rapid Antigen"]
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
        "triggers": ["Tick: Dog/Wood", "Rash (Palms/Soles)", "Hyponatremia", "Severe Headache"],
        "pearl": "Start Doxycycline immediately. Do not wait for serology.",
        "orders": [("START Doxycycline (Empiric)", 0), ("Rickettsia PCR", 1)]
    },
    {
        "dx": "Malaria", "type": "CRITICAL",
        "triggers": ["Travel (Sub-Saharan Africa)", "Travel (SE Asia)", "Travel (South America)"],
        "orders": [("Malaria Smear x3", 0), ("Rapid Antigen", 0)]
    },
    {
        "dx": "Acute HIV / Disseminated GC", "type": "CRITICAL",
        "triggers": ["MSM", "High Risk Sex", "Transactional Sex", "Sick Contacts"],
        "pearl": "Acute HIV mimics Mono. Dissem GC causes fever/tenosynovitis.",
        "orders": [("HIV 1/2 Ag/Ab (4th Gen)", 0), ("HIV Viral Load (PCR)", 1), ("NAAT (GC/CT) All Sites", 1)]
    },
    {
        "dx": "Vibrio vulnificus / Sepsis", "type": "CRITICAL",
        "triggers": ["Raw Shellfish/Oysters", "Cirrhosis/Liver Disease"],
        "pearl": "Life-threatening in cirrhotics. Bullous lesions.",
        "orders": [("Blood Cx (Aerobic/Anaerobic)", 0), ("Wound Cx", 1)]
    },

    # --- HIV SPECIFIC OIs (CD4 Stratified) ---
    {
        "dx": "Pneumocystis jirovecii (PCP)", "type": "Infectious",
        "triggers": ["Dyspnea", "Dry Cough", "Hypoxia", "LDH Elevation"],
        "req_cd4_ceiling": 200,
        "orders": [("Beta-D-Glucan", 1), ("LDH", 1), ("ABG", 1)]
    },
    {
        "dx": "Toxoplasmosis", "type": "Infectious",
        "triggers": ["Headache", "Seizure", "Vision Changes", "Neurologic Deficit"],
        "req_cd4_ceiling": 100,
        "orders": [("Toxo IgG", 1), ("MRI Brain", 2)]
    },
    {
        "dx": "Disseminated MAC", "type": "Infectious",
        "triggers": ["Night Sweats", "Weight Loss", "Severe Anemia", "Diarrhea", "Abd Pain"],
        "req_cd4_ceiling": 50,
        "orders": [("AFB Blood Cx", 1), ("CT Abd (Lymphadenopathy)", 2)]
    },
    {
        "dx": "CMV (Retinitis/Colitis)", "type": "Infectious",
        "triggers": ["Vision Changes", "Diarrhea", "Hepatodynia"],
        "req_cd4_ceiling": 50,
        "orders": [("CMV PCR", 1), ("Dilated Fundoscopy", 2)]
    },

    # --- TRANSPLANT SPECIFIC (Rubin's Timeline) ---
    {
        "dx": "Nosocomial Bacterial / Line Infection", "type": "Infectious",
        "triggers": ["Indwelling Line"],
        "req_tx_timeline": "<1 Month",
        "orders": [("Blood Cx x2 (Line+Periph)", 0)]
    },
    {
        "dx": "CMV Syndrome", "type": "Infectious",
        "triggers": ["Leukopenia", "Thrombocytopenia", "Hepatodynia"],
        "req_tx_timeline": "1-6 Months",
        "orders": [("CMV PCR (Quant)", 1)]
    },
    {
        "dx": "Post-Transplant Lymphoproliferative (PTLD)", "type": "Non-Infectious",
        "triggers": ["Lymphadenopathy", "Weight Loss", "Fever", "EBV History"],
        "req_tx_timeline": ">6 Months", # Or late 1-6
        "orders": [("EBV PCR", 1), ("PET/CT", 3), ("Excisional Biopsy", 3)]
    },

    # --- ENDEMIC FUNGAL (MO BIAS) ---
    {
        "dx": "Histoplasmosis (Disseminated)", "type": "Endemic Fungal",
        "triggers": ["Missouri Residence", "Bird/Bat Droppings", "Spelunking", "Pancytopenia", "Oral Ulcers", "Splenomegaly"],
        "orders": [("Urine/Serum Histo Ag", 1), ("Ferritin", 1)]
    },
    {
        "dx": "Blastomycosis", "type": "Endemic Fungal",
        "triggers": ["Missouri Residence", "Decaying Wood", "Waterways", "Verrucous Lesions", "Pneumonia"],
        "orders": [("Urine Blasto Ag", 1), ("Sputum Fungal Cx", 1)]
    },
    {
        "dx": "Coccidioidomycosis", "type": "Endemic Fungal",
        "triggers": ["Travel (Southwest US)", "Dust Exposure", "Eosinophilia"],
        "orders": [("Coccidioides Serology", 1)]
    },

    # --- VECTOR / ZOONOTIC ---
    {
        "dx": "Tularemia (Typhoidal)", "type": "Infectious",
        "triggers": ["Relative Bradycardia", "Rabbit Exposure", "Lawn Mowing", "Tick: Dog/Wood"],
        "orders": [("Tularemia Agglutination", 1)]
    },
    {
        "dx": "Brucellosis", "type": "Infectious",
        "triggers": ["Relative Bradycardia", "Unpasteurized Dairy", "Livestock", "Travel (Med/Mexico)", "Back Pain"],
        "orders": [("Brucella Serology", 1), ("Blood Cx (Hold 21d)", 1)]
    },
    {
        "dx": "Q Fever", "type": "Infectious",
        "triggers": ["Farm Animals", "Rural Area", "Well Water", "Parturient Animals"],
        "orders": [("Coxiella Serology", 1), ("TTE", 2)]
    },
    {
        "dx": "Bartonella (Trench/Cat Scratch)", "type": "Infectious",
        "triggers": ["Cats", "Homelessness", "Body Lice", "IV Drug Use"],
        "orders": [("Bartonella Serology", 1)]
    },

    # --- TROPICAL / TRAVEL ---
    {
        "dx": "Visceral Leishmaniasis (Kala-Azar)", "type": "Tropical",
        "triggers": ["Military Service", "Travel (Middle East)", "Travel (South America)", "Splenomegaly", "Pancytopenia"],
        "pearl": "Amastigotes in bone marrow.",
        "orders": [("rK39 Dipstick", 2), ("Bone Marrow Biopsy", 3)]
    },
    {
        "dx": "Melioidosis", "type": "Tropical",
        "triggers": ["Travel (SE Asia)", "Diabetes", "Pneumonia", "Abscess (Any)"],
        "orders": [("Blood/Sputum Cx", 0), ("Burkholderia Serology", 1)]
    },
    {
        "dx": "Paracoccidioidomycosis", "type": "Tropical",
        "triggers": ["Travel (South America)", "Oral Ulcers", "Lymphadenopathy"],
        "pearl": "Mariner's Wheel yeast.",
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

    # --- PARASITIC / DIETARY ---
    {
        "dx": "Strongyloidiasis", "type": "Infectious",
        "triggers": ["Eosinophilia", "Travel (Tropics)", "Immunocompromised", "HTLV-1"],
        "orders": [("Strongyloides IgG", 1), ("Stool O&P x3", 1)]
    },
    {
        "dx": "Paragonimiasis", "type": "Infectious",
        "triggers": ["Raw Crustaceans", "Hemoptysis", "Eosinophilia", "Travel (SE Asia)"],
        "orders": [("Sputum O&P", 1), ("Paragonimus Serology", 2)]
    },
    {
        "dx": "Trichinellosis", "type": "Infectious",
        "triggers": ["Undercooked Pork/Game", "Eosinophilia", "Myalgia", "Periorbital Edema"],
        "orders": [("CK Level", 1), ("Trichinella Serology", 1)]
    },

    # --- NON-INFECTIOUS ---
    {
        "dx": "Kikuchi-Fujimoto Disease", "type": "Non-Infectious",
        "triggers": ["Cervical Lymphadenopathy", "Female Sex", "Age < 40"],
        "orders": [("Excisional Node Biopsy", 3)]
    },
    {
        "dx": "Whipple's Disease", "type": "Infectious",
        "triggers": ["Joint Pain (Migratory)", "Diarrhea", "Weight Loss", "CNS Symptoms"],
        "orders": [("Whipple PCR", 2)]
    },
    {
        "dx": "Factitious Fever", "type": "Non-Infectious",
        "triggers": ["Healthcare Worker", "Polymicrobial Bacteremia", "Erratic Fever Curve"],
        "orders": [("Supervised Temp Check", 0)]
    },
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
        "dx": "Malignancy (Lymphoma/RCC)", "type": "Non-Infectious",
        "triggers": ["Weight Loss", "Night Sweats", "Hematuria", "Splenomegaly"],
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2), ("Naproxen Challenge", 1)]
    },
    {
        "dx": "Temporal Arteritis (GCA)", "type": "Non-Infectious",
        "triggers": ["Headache", "Jaw Claudication", "Vision Changes", "Age > 50"],
        "orders": [("ESR & CRP", 1), ("Temporal Artery US", 2), ("Temporal Artery Bx", 3)]
    },
    
    # --- STANDARD INFECTIOUS ---
    {
        "dx": "Tuberculosis (Miliary)", "type": "Infectious",
        "triggers": ["TB Exposure", "Homelessness", "Incarceration", "Travel (Sub-Saharan Africa)"],
        "orders": [("Quantiferon-TB Gold", 1), ("Sputum AFB x3", 1)]
    },
    {
        "dx": "Infectious Endocarditis", "type": "Infectious",
        "triggers": ["New Murmur", "IV Drug Use", "Prosthetic Valve"],
        "orders": [("Blood Cx x3", 0), ("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Acute HIV / Syphilis", "type": "Infectious",
        "triggers": ["MSM", "High Risk Sex", "Transactional Sex"],
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
    
    # Stool Logic
    has_eos = "Eosinophilia" in inputs['all_positives']
    if has_eos and (inputs['social'] or any(x in inputs['all_positives'] for x in ["Diarrhea", "Abd Pain"])):
        final_orders["Targeted"].add("Stool O&P x3")

    # Panel Consolidations
    if any("Liver Autoimmune" in x for x in all_items):
        final_orders["Targeted"].add("Liver AI Panel (ANA, ASMA, AMA, IgG)")
    if any("dsDNA" in x for x in all_items):
        final_orders["Targeted"].add("Rheum Serologies (ANA, RF, CCP, C3/C4)")

    for item in all_items:
        # Skip consolidated items
        if any(x in item for x in ["Blood Cx", "Liver AI", "dsDNA", "Stool"]): continue
        
        if "Biopsy" in item or "rK39" in item: final_orders["Contingency"].add(item)
        elif any(x in item for x in ["CT ", "TTE", "TEE", "MRI"]): final_orders["Structural"].add(item)
        elif any(x in item for x in ["CBC", "CMP", "ESR", "CRP", "HIV", "RPR", "UA"]): final_orders["Immediate"].add(item)
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
    
    # Universal Baseline
    raw_orders["0"].extend(["CBC", "CMP", "ESR", "CRP", "UA"])
    if any(r in inputs['all_positives'] for r in ["IV Drug Use", "MSM", "High Risk Sex"]):
        raw_orders["0"].extend(["HIV 1/2 Ag/Ab", "Syphilis Cascade"])

    if check_faget(inputs['tmax'], inputs['hr']):
        inputs['all_positives'].append("Relative Bradycardia")

    for d in DATABASE:
        score = 0
        triggers = []
        
        for t in d["triggers"]:
            if any(pos_t in t for pos_t in inputs["all_positives"]) or t in inputs["all_positives"]:
                # Scoring Weights
                if t == "Relative Bradycardia": score += 2
                elif "Ferritin > 3000" in t: score += 5
                else: score += 1
                triggers.append(t)
        
        # MO Bias
        if d['dx'] in ["Histoplasmosis (Disseminated)", "Blastomycosis"]:
            score += 1
            if "Missouri Residence" not in triggers: triggers.append("Missouri Residence")

        # Transplant Logic (Rubin's Timeline + Organ Type)
        is_tx = inputs['immune'] == "Transplant"
        if d.get("req_tx_timeline"):
            if not is_tx:
                score = 0
            elif d["req_tx_timeline"] != inputs.get("tx_time"):
                # Allow overlap logic if needed, but for now hard filter
                score = 0 
        
        # HIV Logic
        if d.get("req_cd4_ceiling"):
            if inputs['immune'] != "HIV Positive": score = 0
            elif inputs.get("cd4", 1000) > d["req_cd4_ceiling"]: score = 0
            elif score == 0: score = 1; triggers.append(f"CD4 < {d['req_cd4_ceiling']}")

        # Med Requirement
        if d.get("req_med") and not (inputs["meds"] and score >= 1): score = 0
        
        # Age exclusions
        if d['dx'] == "Kikuchi-Fujimoto Disease" and inputs['age'] > 40: score = 0
        if d['dx'] == "Temporal Arteritis (GCA)" and inputs['age'] < 50: score = 0

        if score > 0:
            active_dx.append({"dx": d["dx"], "type": d["type"], "triggers": triggers, "score": score})
            for test, tier in d.get('orders', []):
                raw_orders[str(tier)].append(test)

    return sorted(active_dx, key=lambda x: x['score'], reverse=True), raw_orders

def generate_note(inputs, active_dx, optimized_orders):
    txt = f"Date: {datetime.date.today()}\n"
    txt += f"{inputs['age']}yo {inputs['sex']} "
    if inputs['immune'] != "Immunocompetent": txt += f"({inputs['immune']}) "
    if "Transplant" in inputs['immune']: txt += f"[{inputs['tx_type']}, {inputs['tx_time']} post-op] "
    
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

    inf = [d for d in active_dx if d['type'] in ['Infectious', 'Endemic Fungal', 'Tropical']]
    if inf:
        names = [d['dx'] for d in inf]
        txt += f"Infectious/Tropical differential prioritizes {', '.join(names)}.\n"

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
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV Positive", "Transplant", "Chemotherapy", "Biologics"])
    
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
    
    with st.expander("Risks / Social", expanded=True):
        ivdu = st.checkbox("IV Drug Use")
        msm = st.checkbox("MSM")
        high_risk_sex = st.checkbox("High Risk Sex")
        sex_work = st.checkbox("Transactional Sex")
        hc_worker = st.checkbox("Healthcare Worker")
        military = st.checkbox("Military Service")
        homeless = st.checkbox("Homelessness")
        sick_contact = st.checkbox("Sick Contacts")
        
    with st.expander("Vectors / Diet", expanded=False):
        cats = st.checkbox("Cats")
        livestock = st.checkbox("Farm Animals")
        raw_crab = st.checkbox("Raw Crustaceans")
        raw_shell = st.checkbox("Raw Shellfish/Oysters")
        pork = st.checkbox("Undercooked Pork")
        tick_dog = st.checkbox("Tick: Dog/Wood")
        tick_lone = st.checkbox("Tick: Lone Star")
        birds = st.checkbox("Bird/Bat Droppings")
        farm = st.checkbox("Rural / Farm Living")
        well = st.checkbox("Well Water")
        
    with st.expander("Travel", expanded=False):
        travel_tropics = st.checkbox("Travel (Sub-Saharan Africa)")
        travel_se_asia = st.checkbox("Travel (SE Asia)")
        travel_s_amer = st.checkbox("Travel (South America)")
        travel_mid_east = st.checkbox("Travel (Middle East)")
        travel_med = st.checkbox("Travel (Med/Mexico)")
        travel_sw = st.checkbox("Travel (Southwest US)")

    meds = st.multiselect("New Meds", ["Antibiotic", "Anticonvulsant", "Sulfa"])
    
    st.header("Objective / ROS")
    with st.expander("Physical / Symptoms", expanded=False):
        murmur = st.checkbox("New Murmur")
        cervical_lad = st.checkbox("Cervical Lymphadenopathy")
        splenomegaly = st.checkbox("Splenomegaly")
        rash = st.checkbox("Rash (Any)")
        chancre = st.checkbox("Chancre / Eschar")
        oral_ulcers = st.checkbox("Oral Ulcers")
        headache = st.checkbox("Severe Headache")
        jaw = st.checkbox("Jaw Claudication")
        joint = st.checkbox("Joint Pain")
        vision = st.checkbox("Vision Changes")
        abd_pain = st.checkbox("Abd Pain")
        diarrhea = st.checkbox("Diarrhea")
        
    with st.expander("Labs", expanded=False):
        ferritin_crit = st.checkbox("Ferritin > 3000")
        ferritin_high = st.checkbox("Ferritin > 1000")
        pancytopenia = st.checkbox("Pancytopenia")
        eosinophilia = st.checkbox("Eosinophilia")
        lfts = st.checkbox("Elevated LFTs")
        hyponatremia = st.checkbox("Hyponatremia")
        cirrhosis = st.checkbox("Cirrhosis/Liver Disease")
        diabetes = st.checkbox("Diabetes")

    st.header("Prior Workup")
    prior_workup = st.multiselect("Negatives", ["Negative Blood Cx", "Negative HIV", "Negative O&P", "Negative ANA/RF", "Negative Quantiferon", "Negative Malaria"])
    
    run = st.button("Generate Note")

# --- MAIN ---
st.title("ID-CDSS | Director Gold Master (v30)")

if run:
    all_positives = meds[:]
    # Social
    if ivdu: all_positives.append("IV Drug Use")
    if msm: all_positives.append("MSM")
    if high_risk_sex: all_positives.append("High Risk Sex")
    if sex_work: all_positives.append("Transactional Sex")
    if sick_contact: all_positives.append("Sick Contacts")
    if hc_worker: all_positives.append("Healthcare Worker")
    if military: all_positives.append("Military Service")
    if homeless: all_positives.append("Homelessness")
    # Vectors/Diet
    if farm: all_positives.append("Rural Area")
    if well: all_positives.append("Well Water")
    if raw_crab: all_positives.append("Raw Crustaceans")
    if raw_shell: all_positives.append("Raw Shellfish/Oysters")
    if pork: all_positives.append("Undercooked Pork/Game")
    if tick_dog: all_positives.append("Tick: Dog/Wood")
    if tick_lone: all_positives.append("Tick: Lone Star")
    if cats: all_positives.append("Cats")
    if livestock: all_positives.append("Farm Animals")
    if birds: all_positives.append("Bird/Bat Droppings")
    # Travel
    if travel_tropics: all_positives.append("Travel (Sub-Saharan Africa)")
    if travel_se_asia: all_positives.append("Travel (SE Asia)")
    if travel_s_amer: all_positives.append("Travel (South America)")
    if travel_mid_east: all_positives.append("Travel (Middle East)")
    if travel_med: all_positives.append("Travel (Med/Mexico)")
    if travel_sw: all_positives.append("Travel (Southwest US)")
    # Obj/ROS
    if murmur: all_positives.append("New Murmur")
    if cervical_lad: all_positives.append("Cervical Lymphadenopathy")
    if splenomegaly: all_positives.append("Splenomegaly")
    if rash: all_positives.append("Rash")
    if chancre: all_positives.append("Chancre")
    if oral_ulcers: all_positives.append("Oral Ulcers")
    if headache: all_positives.append("Severe Headache")
    if jaw: all_positives.append("Jaw Claudication")
    if joint: all_positives.append("Joint Pain")
    if vision: all_positives.append("Vision Changes")
    if abd_pain: all_positives.append("Abd Pain")
    if diarrhea: all_positives.append("Diarrhea")
    # Labs
    if ferritin_crit: all_positives.append("Ferritin > 3000")
    if ferritin_high: all_positives.append("Ferritin > 1000")
    if pancytopenia: all_positives.append("Pancytopenia")
    if eosinophilia: all_positives.append("Eosinophilia")
    if lfts: all_positives.append("Elevated LFTs")
    if hyponatremia: all_positives.append("Hyponatremia")
    if cirrhosis: all_positives.append("Cirrhosis/Liver Disease")
    if diabetes: all_positives.append("Diabetes")
    
    if sex == "Female": all_positives.append("Female Sex")
    if age < 40: all_positives.append("Age < 40")
    if age > 50: all_positives.append("Age > 50")

    inputs = {
        "age": age, "sex": sex, "immune": immune, "cd4": cd4,
        "tx_type": tx_type, "tx_time": tx_time,
        "tmax": tmax, "hr": hr, "duration_fever_days": duration_fever_days,
        "all_positives": all_positives, 
        "social": [x for x in all_positives if x in ["IV Drug Use", "MSM", "High Risk Sex"]],
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
