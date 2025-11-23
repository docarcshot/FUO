import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Academic Grade", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .critical { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff5f5; font-weight: bold; }
    .high-prob { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .med-prob { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
</style>
""", unsafe_allow_html=True)

# --- LOGIC HELPERS ---
def check_faget_sign(temp_f, hr):
    """
    Faget's Sign: Relative Bradycardia.
    Rule of Thumb: For every 1°F > 101, HR should increase by 10.
    If Temp > 102 and HR < 100, suspicion is high.
    """
    if temp_f > 102 and hr < 100: return True
    return False

# --- DATABASE WITH WEIGHTED SCORING (The "Bayesian" Update) ---
# Weights: 1 (Nonspecific), 3 (Suggestive), 5 (Pathognomonic/High LR)
DATABASE = [
    {
        "dx": "Hemophagocytic Lymphohistiocytosis (HLH)",
        "type": "CRITICAL",
        "criteria": [
            {"trig": "Ferritin > 3000", "weight": 10}, # Massive weight
            {"trig": "Splenomegaly", "weight": 3},
            {"trig": "Pancytopenia", "weight": 3},
            {"trig": "Hypertriglyceridemia", "weight": 2}
        ],
        "pearl": "Medical Emergency. Check HScore. Order Soluble CD25 immediately.",
        "orders": [("Ferritin", 1), ("Soluble CD25 (IL-2R)", 1), ("Fibrinogen", 1), ("Bone Marrow Biopsy", 3)]
    },
    {
        "dx": "Tularemia (Typhoidal)",
        "type": "Infectious",
        "criteria": [
            {"trig": "Relative Bradycardia (Faget's)", "weight": 5},
            {"trig": "Tick Bite", "weight": 3},
            {"trig": "Lawn Mowing / Rabbit Exposure", "weight": 4},
            {"trig": "Missouri Residence", "weight": 1}
        ],
        "pearl": "Pulse-Temp dissociation is a classic clue.",
        "orders": [("Tularemia Agglutination", 1)]
    },
    {
        "dx": "Drug-Induced Fever",
        "type": "Non-Infectious",
        "criteria": [
            {"trig": "Relative Bradycardia (Faget's)", "weight": 4},
            {"trig": "New Beta-Lactam/Sulfa", "weight": 3},
            {"trig": "Eosinophilia", "weight": 2},
            {"trig": "Patient looks 'well'", "weight": 2}
        ],
        "pearl": "Look for the 'well-appearing' febrile patient.",
        "orders": [("Discontinue Suspect Agent", 0)]
    },
    {
        "dx": "Histoplasmosis (Dissem)",
        "type": "Endemic Fungal",
        "criteria": [
            {"trig": "Pancytopenia", "weight": 4},
            {"trig": "Oral Ulcers", "weight": 4},
            {"trig": "Splenomegaly", "weight": 3},
            {"trig": "Missouri Residence", "weight": 2}, # Baseline risk
            {"trig": "Spelunking/Guano", "weight": 5}
        ],
        "pearl": "Adrenal insufficiency mimic.",
        "orders": [("Urine Histo Ag", 1), ("Ferritin", 1)]
    },
    {
        "dx": "Adult Onset Still's",
        "type": "Non-Infectious",
        "criteria": [
            {"trig": "Ferritin > 1000", "weight": 5},
            {"trig": "Quotidian Fever (Spikes daily)", "weight": 4},
            {"trig": "Salmon Rash", "weight": 5},
            {"trig": "Joint Pain", "weight": 2}
        ],
        "pearl": "Yamaguchi Criteria.",
        "orders": [("Ferritin", 1), ("Glycosylated Ferritin", 2)]
    }
]

def calculate_bayesian_score(inputs):
    scored_dx = []
    
    # 1. Calculate Faget's
    is_faget = check_faget_sign(inputs['tmax'], inputs['hr'])
    if is_faget: inputs['all_positives'].append("Relative Bradycardia (Faget's)")

    for d in DATABASE:
        score = 0
        triggers = []
        
        for criterion in d['criteria']:
            # Check if trigger is in our inputs
            t = criterion['trig']
            if t in inputs['all_positives'] or (t == "Missouri Residence"): # MO is always True
                score += criterion['weight']
                triggers.append(t)
        
        # Normalizing score for display (threshold > 3 to show)
        if score > 3:
            scored_dx.append({
                "dx": d['dx'], 
                "type": d['type'], 
                "score": score, 
                "triggers": triggers,
                "pearl": d['pearl'],
                "orders": d['orders']
            })
            
    # Sort by Weight (Highest Probability First)
    return sorted(scored_dx, key=lambda x: x['score'], reverse=True)

def generate_note(inputs, scored_dx):
    txt = f"**ID Consult Note**\n"
    txt += f"{inputs['age']}yo {inputs['sex']} | {inputs['immune']}\n"
    txt += f"Vitals: Tmax {inputs['tmax']}°F, HR {inputs['hr']} bpm "
    if check_faget_sign(inputs['tmax'], inputs['hr']):
        txt += "(Positive for Relative Bradycardia/Faget's Sign).\n"
    else:
        txt += "(Appropriate tachycardia).\n"
        
    txt += "\n**Assessment:**\n"
    
    # Grouping by Probability
    critical = [d for d in scored_dx if d['type'] == 'CRITICAL']
    if critical:
        txt += "🚨 **CRITICAL CONSIDERATIONS:**\n"
        for c in critical:
            txt += f"- {c['dx']} (Score: {c['score']}): Driven by {', '.join(c['triggers'])}\n"
            
    top_tier = [d for d in scored_dx if d['score'] >= 6 and d['type'] != 'CRITICAL']
    if top_tier:
        txt += "\n**High Probability:**\n"
        for t in top_tier:
            txt += f"- {t['dx']}: {', '.join(t['triggers'])}\n"
            
    lower_tier = [d for d in scored_dx if d['score'] < 6 and d['type'] != 'CRITICAL']
    if lower_tier:
        txt += "\n**Consider Also:**\n"
        for l in lower_tier:
            txt += f"- {l['dx']}\n"
            
    return txt

# --- UI ---
with st.sidebar:
    st.header("1. Demographics & Vitals")
    age = st.number_input("Age", 18, 90, 45)
    sex = st.selectbox("Sex", ["Male", "Female"])
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV+", "Transplant"])
    
    # VITAL SIGNS INPUT (New)
    c1, c2 = st.columns(2)
    tmax = c1.number_input("T-Max (°F)", 98.0, 107.0, 102.5)
    hr = c2.number_input("HR at T-Max", 40, 180, 88, help="Heart rate during fever spike")

    st.header("2. Physical Exam (Objective)")
    pe_findings = st.multiselect("Exam Findings", 
        ["Splenomegaly", "Hepatodynia", "Rash (Diffuse)", "Rash (Salmon)", 
         "Oral Ulcers", "Lymphadenopathy", "New Murmur"])
    
    st.header("3. Labs (Objective)")
    lab_findings = st.multiselect("Lab Data",
        ["Ferritin > 1000", "Ferritin > 3000", "Pancytopenia", "Eosinophilia", 
         "Hypertriglyceridemia", "Elevated LFTs"])

    st.header("4. History (Subjective)")
    hx_findings = st.multiselect("Exposures/Symptoms",
        ["Tick Bite", "Lawn Mowing / Rabbit Exposure", "Spelunking/Guano", 
         "New Beta-Lactam/Sulfa", "Joint Pain"])

    run = st.button("Run Bayesian Analysis")

st.title("ID-CDSS | Academic Grade (v22)")
st.caption("Featuring Weighted Logic & Faget's Sign Calculation")

if run:
    all_positives = pe_findings + lab_findings + hx_findings
    inputs = {
        "age": age, "sex": sex, "immune": immune, "tmax": tmax, "hr": hr,
        "all_positives": all_positives
    }
    
    scored_dx = calculate_bayesian_score(inputs)
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        # VITALS CHECK
        if check_faget_sign(tmax, hr):
            st.error(f"📉 **Faget's Sign Detected:** HR {hr} is inappropriately low for Temp {tmax}°F.")
            st.caption("Differential narrowed to: Tularemia, Brucella, Legionella, Drug Fever, Typhoid.")
            
        st.subheader("Weighted Differential")
        for d in scored_dx:
            # Dynamic Styling based on Score
            style = "critical" if d['type'] == 'CRITICAL' else ("high-prob" if d['score'] >= 6 else "med-prob")
            
            st.markdown(f"<div class='{style}'>", unsafe_allow_html=True)
            st.markdown(f"**{d['dx']}** (Score: {d['score']})")
            st.caption(f"Drivers: {', '.join(d['triggers'])}")
            st.markdown(f"*{d['pearl']}*")
            st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.subheader("Consult Note")
        st.text_area("Output", generate_note(inputs, scored_dx), height=500)
