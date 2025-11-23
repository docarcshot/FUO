import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Transplant Edition", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .transplant { border-left: 6px solid #6f42c1; padding: 10px; background-color: #f3e5f5; } /* Purple */
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
    "Negative Malaria Smear": "Malaria Smear (Thick/Thin)"
}

# --- DATABASE ---
DATABASE = [
    # --- TRANSPLANT SPECIFIC (NEW) ---
    {
        "dx": "Acute Graft vs Host Disease (GVHD)",
        "triggers": ["Rash (Diffuse)", "Diarrhea", "Elevated LFTs"],
        "req_tx": "BMT/HSCT", # Only triggers for BMT
        "pearl": "Classic Triad: Dermatitis, Enteritis, Hepatitis. Occurs near engraftment.",
        "orders": [("Skin/Gut Biopsy", 3), ("Clinical Diagnosis", 0)]
    },
    {
        "dx": "CMV Syndrome / Tissue Invasive Disease",
        "triggers": ["Leukopenia", "Thrombocytopenia", "Hepatodynia", "Colitis", "Pneumonitis"],
        "req_tx": "ANY",
        "pearl": "Highest risk 1-6 months post-tx. 'Owl's Eye' inclusions.",
        "orders": [("CMV PCR (Quantitative)", 1), ("Tissue Biopsy", 3)]
    },
    {
        "dx": "Post-Transplant Lymphoproliferative Disorder (PTLD)",
        "triggers": ["Lymphadenopathy", "EBV Seropositivity (D+/R-)", "Weight Loss", "Fever"],
        "req_tx": "ANY",
        "pearl": "Driven by EBV proliferation. Mimics sepsis or rejection.",
        "orders": [("EBV PCR", 1), ("PET/CT", 3), ("Excisional Biopsy", 3)]
    },
    {
        "dx": "Invasive Aspergillosis",
        "triggers": ["Hemoptysis", "Pleuritic Pain", "Halo Sign on CT", "Lung Transplant"],
        "req_tx": "Lung/BMT",
        "pearl": "Lung Tx is highest risk. Galactomannan antigen in BAL is gold standard.",
        "orders": [("Serum Galactomannan", 1), ("Chest CT", 2), ("Bronchoscopy w/ BAL", 3)]
    },

    # --- PARASITIC (NEW) ---
    {
        "dx": "Chagas Disease (Reactivation)",
        "triggers": ["Travel (South America)", "Heart Failure", "Arrhythmia", "Esophageal Motility"],
        "req_med": False,
        "pearl": "Trypanosoma cruzi. Reactivation in Transplant/AIDS. Panniculitis (nodules) common in reactivation.",
        "orders": [("Trypanosoma cruzi PCR/Serology", 1), ("Blood Smear (Giemsa)", 1)]
    },
    {
        "dx": "Paragonimiasis (Lung Fluke)",
        "triggers": ["Raw Crustaceans (Crab/Crayfish)", "Hemoptysis", "Eosinophilia", "Travel (SE Asia)"],
        "req_med": False,
        "pearl": "Mimics TB. Eating raw crayfish/freshwater crab. Eggs in sputum.",
        "orders": [("Sputum O&P", 1), ("Paragonimus Serology", 1)]
    },
    
    # --- RICKETTSIAL / VECTOR (EXISTING) ---
    {
        "dx": "Rocky Mountain Spotted Fever (RMSF)",
        "triggers": ["Tick Bite (Dog/Wood)", "Rash (Palms/Soles)", "Thrombocytopenia", "Hyponatremia"],
        "req_med": False,
        "pearl": "CRITICAL: Mortality high. Start Doxycycline immediately.",
        "orders": [("START Doxycycline (Empiric)", 0), ("Rickettsia rickettsii PCR", 1)]
    },
    {
        "dx": "Ehrlichiosis / Anaplasmosis",
        "triggers": ["Tick Bite (Lone Star/Ixodes)", "Leukopenia", "Thrombocytopenia", "Elevated LFTs"],
        "req_med": False,
        "pearl": "Spotless fever. Leukopenia common.",
        "orders": [("Ehrlichia/Anaplasma PCR", 1), ("Peripheral Smear", 1)]
    },

    # --- STANDARD (EXISTING) ---
    {
        "dx": "DRESS Syndrome",
        "triggers": ["Rash (Diffuse)", "Eosinophilia", "Hepatodynia"], 
        "req_med": True,
        "pearl": "Drug exposure (2-8 wk latency). HHV-6 reactivation.",
        "orders": [("CBC (Eosinophils)", 1), ("LFTs", 1), ("HHV-6 PCR", 1)]
    },
    {
        "dx": "Q Fever",
        "triggers": ["Farm Animals", "Parturient Animals"],
        "req_med": False,
        "pearl": "Culture-neg endocarditis.",
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
        "dx": "Histoplasmosis",
        "triggers": ["Bird/Bat Droppings", "Spelunking", "Pancytopenia", "Splenomegaly"],
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
