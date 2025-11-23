import streamlit as st
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | FUO Engine v2", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .infectious { border-left: 6px solid #28a745; background-color: #e6fffa; padding: 10px; }
    .endemic { border-left: 6px solid #fd7e14; background-color: #fff3cd; padding: 10px; }
    .rheum { border-left: 6px solid #6610f2; background-color: #f3e5f5; padding: 10px; }
    .malignancy { border-left: 6px solid #d63384; background-color: #fce4ec; padding: 10px; }
    .tier0 { border-left: 6px solid #000; background-color: #f0f0f0; padding: 10px; }
    .tier1 { border-left: 6px solid #28a745; background-color: #e8fff1; padding: 10px; }
    .tier2 { border-left: 6px solid #ffc107; background-color: #fff9e6; padding: 10px; }
    .tier3 { border-left: 6px solid #dc3545; background-color: #ffeaea; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- CANONICAL TRIGGER MAP (Option 2) ---
CANONICAL_MAP = {
    "night_sweats": {"Night sweats"},
    "weight_loss": {"Weight loss"},
    "fatigue": {"Fatigue"},
    "headache": {"Headache"},
    "vision_changes": {"Vision changes"},
    "chronic_cough": {"Chronic cough"},
    "hemoptysis": {"Hemoptysis"},
    "dyspnea": {"Dyspnea"},
    "abdominal_pain": {"Abdominal pain"},
    "diarrhea": {"Diarrhea"},
    "ruq_pain": {"RUQ pain"},
    "arthralgia": {"Arthralgia"},
    "back_pain": {"Back pain", "Back pain (focal)"},
    "myalgia": {"Myalgias"},
    "rash": {"Rash"},
    "palmar_rash": {"Palmar/soles rash"},
    "nodules": {"Skin nodules"},
    "lymphadenopathy": {"Lymphadenopathy"},
    "splenomegaly": {"Splenomegaly"},
    "pancytopenia": {"Pancytopenia"},
    "cats": {"Cats"},
    "livestock": {"Livestock exposure", "Farm animals"},
    "bird_bat": {"Bird/bat exposure"},
    "unpasteurized_dairy": {"Unpasteurized dairy"},
    "rural": {"Rural living"},
    "body_lice": {"Body lice"},
    "ivdu": {"IV drug use"},
    "homeless": {"Homelessness/incarceration"},
    "tb_contact": {"TB exposure"},
    "high_tb_travel": {"High TB burden travel"},
    "missouri": {"Missouri/Ohio Valley"},
    "sw_travel": {"Southwest US travel"},
    "cirrhosis": {"Cirrhosis"},
}

def canonicalize(raw_inputs):
    """Convert checked UI items into canonical trigger names."""
    out = set()
    for key, raw_set in CANONICAL_MAP.items():
        if raw_inputs.get(key):
            out |= raw_set
    return out

# --- DISEASE DATABASE (Strict FUO List + Corrected Logic) ---
DISEASES = [
    {
        "dx": "Subacute bacterial endocarditis",
        "cat": "Infectious",
        "triggers": {"New murmur", "IV drug use", "Prosthetic valve", "Embolic phenomena"},
        "orders": [
            ("Blood cultures x3", 0),
            ("TTE", 2),
            ("TEE", 3),
        ],
    },
    {
        "dx": "Tuberculosis (miliary/extrapulmonary)",
        "cat": "Infectious",
        "triggers": {"Weight loss", "Night sweats", "Chronic cough", "TB exposure", "Homelessness/incarceration", "High TB burden travel"},
        "orders": [
            ("Quantiferon TB", 1),
            ("AFB smear x3", 1),
            ("CT chest/abdomen/pelvis with contrast", 2),
        ],
    },
    {
        "dx": "Q fever (Coxiella)",
        "cat": "Infectious",
        "triggers": {"Farm animals", "Rural living", "Prosthetic valve"},
        "orders": [
            ("Coxiella serology", 1),
            ("TTE", 2),
        ],
    },
    {
        "dx": "Bartonella (endocarditis/bacteremia)",
        "cat": "Infectious",
        "triggers": {"Cats", "Body lice", "Homelessness/incarceration"},
        "orders": [
            ("Bartonella serology", 1),
        ],
    },
    {
        "dx": "Brucellosis",
        "cat": "Infectious",
        "triggers": {"Unpasteurized dairy", "Livestock exposure", "Travel Mediterranean/Mexico"},
        "orders": [
            ("Brucella serology", 1),
            ("Blood cultures (hold 21d)", 1),
        ],
    },
    {
        "dx": "Whipple disease",
        "cat": "Infectious",
        "triggers": {"Arthralgia", "Diarrhea", "Weight loss", "CNS symptoms"},
        "orders": [
            ("Whipple PCR (blood/CSF)", 3),
            ("EGD with biopsy", 3),
        ],
    },
    {
        "dx": "Vertebral osteomyelitis",
        "cat": "Infectious",
        "triggers": {"Back pain", "IV drug use", "Recent bacteremia"},
        "orders": [
            ("ESR", 1),
            ("CRP", 1),
            ("MRI spine", 2),
        ],
    },
    {
        "dx": "Endemic fungal infection (Histo/Blasto)",
        "cat": "Endemic",
        "triggers": {"Missouri/Ohio Valley", "Bird/bat exposure", "Pancytopenia", "Splenomegaly"},
        "orders": [
            ("Histo/Blasto panel (Urine Histo Ag + Serum Histo Ab + Serum Blasto Ab)", 1),
            ("Ferritin", 1),
        ],
    },
    {
        "dx": "Coccidioidomycosis",
        "cat": "Infectious",
        "triggers": {"Southwest US travel"},
        "orders": [
            ("Coccidioides serology", 1),
            ("CT chest", 2),
        ],
    },
    {
        "dx": "Cryptococcosis",
        "cat": "Infectious",
        "triggers": {"Headache", "Vision changes", "Weight loss", "Cirrhosis"},
        "immune_required": {"HIV", "Transplant", "Biologics", "Chemotherapy", "Cirrhosis"},
        "orders": [
            ("Serum cryptococcal antigen", 1),
            ("Consider LP for CSF CrAg if neurologic symptoms", 3),
        ],
    },
    {
        "dx": "Disseminated MAC",
        "cat": "Infectious",
        "immune_required": {"HIV"},
        "cd4_ceiling": 100,
        "triggers": {"Night sweats", "Weight loss", "Diarrhea"},
        "orders": [
            ("AFB blood culture", 1),
            ("CT abdomen/pelvis (nodes)", 2),
        ],
    },
    {
        "dx": "CMV syndrome",
        "cat": "Infectious",
        "immune_required": {"Transplant"},
        "orders": [
            ("CMV PCR (quantitative)", 1),
        ],
    },
    {
        "dx": "Adult Still disease",
        "cat": "Rheumatologic",
        "triggers": {"Arthralgia", "Rash", "Ferritin > 1000", "Night sweats"},
        "orders": [
            ("Ferritin", 1),
            ("ANA", 2),
            ("RF", 2),
            ("CCP antibody", 2),
        ],
    },
    {
        "dx": "Temporal arteritis (GCA)",
        "cat": "Rheumatologic",
        "triggers": {"Headache", "Jaw claudication", "Vision changes"},
        "age_floor": 50,
        "orders": [
            ("ESR", 1),
            ("CRP", 1),
            ("Temporal artery ultrasound", 2),
        ],
    },
    {
        "dx": "Systemic lupus erythematosus",
        "cat": "Rheumatologic",
        "triggers": {"Malar rash", "Arthralgia", "Proteinuria"},
        "orders": [
            ("ANA", 2),
            ("dsDNA", 2),
            ("C3/C4", 2),
        ],
    },
    {
        "dx": "Lymphoma",
        "cat": "Malignancy",
        "triggers": {"Night sweats", "Weight loss", "Lymphadenopathy", "Splenomegaly"},
        "orders": [
            ("LDH", 1),
            ("CT chest/abdomen/pelvis", 2),
        ],
    },
    {
        "dx": "Renal cell carcinoma",
        "cat": "Malignancy",
        "triggers": {"Hematuria", "Weight loss"},
        "orders": [
            ("CT chest/abdomen/pelvis", 2),
        ],
    },
]
# --- MATCHING ENGINE ---
def match_differential(canonical_triggers, immune_status, cd4, age):
    active = []
    raw_orders = {0: [], 1: [], 2: [], 3: []}

    for d in DISEASES:
        score = 0
        matched = []

        # Trigger match (canonical)
        for t in d.get("triggers", []):
            if t in canonical_triggers:
                matched.append(t)
                score += 1

        # Immune requirements
        if "immune_required" in d:
            if immune_status not in d["immune_required"]:
                continue

        # CD4 ceiling (MAC)
        if "cd4_ceiling" in d:
            if immune_status == "HIV" and cd4 < d["cd4_ceiling"]:
                score = max(score, 1)
            else:
                continue

        # Age filter (GCA)
        if d.get("age_floor") and age < d["age_floor"]:
            continue

        if score > 0:
            active.append({
                "dx": d["dx"],
                "cat": d["cat"],
                "score": score,
                "matched": matched,
            })
            for test, tier in d["orders"]:
                raw_orders[tier].append(test)

    # Sort diseases by descending score (red → yellow → green)
    active_sorted = sorted(active, key=lambda x: x["score"], reverse=True)
    return active_sorted, raw_orders


# --- ORDER OPTIMIZER ---
def optimize_orders(raw_orders, prior_negatives, suspect_rheum=False):
    final = {"Tier 0": set(), "Tier 1": set(), "Tier 2": set(), "Tier 3": set()}

    # Deduplicate
    for tier, items in raw_orders.items():
        for it in items:
            # Remove items blocked by prior negatives
            if any(prev in it for prev in prior_negatives):
                continue

            if tier == 0:
                final["Tier 0"].add(it)
            elif tier == 1:
                final["Tier 1"].add(it)
            elif tier == 2:
                # rheum gating
                if not suspect_rheum and any(r in it for r in ["ANA", "RF", "CCP", "dsDNA", "C3", "C4"]):
                    continue
                final["Tier 2"].add(it)
            elif tier == 3:
                final["Tier 3"].add(it)

    return final


# --- GENERATE ORGANIC NOTE ---
def build_note(age, sex, immune_status, fever_days, canonical_triggers, differential, orders):
    txt = f"ID Consult – Fever of Unknown Origin\n"
    txt += f"{age} year old {sex} with fever for {fever_days} days.\n"
    txt += f"Immune status: {immune_status}.\n\n"

    if canonical_triggers:
        txt += "Relevant findings: " + ", ".join(sorted(canonical_triggers)) + ".\n\n"

    txt += "Differential diagnosis (ranked):\n"
    if not differential:
        txt += "No specific pattern identified. FUO remains broad.\n"
    else:
        for d in differential:
            txt += f"- {d['dx']} ({d['cat']}) – matched: {', '.join(d['matched'])}\n"

    txt += "\nDiagnostic plan:\n"

    if orders["Tier 0"]:
        txt += "Tier 0: " + ", ".join(sorted(orders["Tier 0"])) + "\n"

    if orders["Tier 1"]:
        txt += "Tier 1: " + ", ".join(sorted(orders["Tier 1"])) + "\n"

    if orders["Tier 2"]:
        txt += "Tier 2: " + ", ".join(sorted(orders["Tier 2"])) + "\n"

    if orders["Tier 3"]:
        txt += "Tier 3: " + ", ".join(sorted(orders["Tier 3"])) + "\n"

    return txt


# --- UI ---
st.sidebar.title("FUO Engine (>3 weeks)")

# Basic demographics
age = st.sidebar.number_input("Age", 18, 100, 50)
sex = st.sidebar.selectbox("Sex", ["Male", "Female"])
fever_days = st.sidebar.number_input("Duration of fever (days)", 21, 365, 30)
immune_status = st.sidebar.selectbox("Immune status", ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy", "Cirrhosis"])
cd4 = 500
if immune_status == "HIV":
    cd4 = st.sidebar.slider("CD4", 0, 1200, 450)

suspect_rheum = st.sidebar.checkbox("Suspect rheumatologic disease", value=False)

st.sidebar.markdown("---")

# UI → trigger booleans
raw_ui = {
    "night_sweats": st.sidebar.checkbox("Night sweats"),
    "weight_loss": st.sidebar.checkbox("Weight loss"),
    "arthralgia": st.sidebar.checkbox("Joint pain/arthralgia"),
    "back_pain": st.sidebar.checkbox("Back pain"),
    "headache": st.sidebar.checkbox("Headache"),
    "vision_changes": st.sidebar.checkbox("Vision changes"),
    "diarrhea": st.sidebar.checkbox("Diarrhea"),
    "pancytopenia": st.sidebar.checkbox("Pancytopenia"),
    "lymphadenopathy": st.sidebar.checkbox("Lymphadenopathy"),
    "splenomegaly": st.sidebar.checkbox("Splenomegaly"),
    "cats": st.sidebar.checkbox("Cats"),
    "livestock": st.sidebar.checkbox("Livestock"),
    "bird_bat": st.sidebar.checkbox("Bird/bat exposure"),
    "unpasteurized_dairy": st.sidebar.checkbox("Unpasteurized dairy"),
    "ivdu": st.sidebar.checkbox("IV drug use"),
    "homeless": st.sidebar.checkbox("Homelessness/incarceration"),
    "tb_contact": st.sidebar.checkbox("TB exposure"),
    "high_tb_travel": st.sidebar.checkbox("Travel to high TB region"),
    "missouri": st.sidebar.checkbox("Missouri/Ohio Valley"),
    "sw_travel": st.sidebar.checkbox("Southwest US travel"),
    "cirrhosis": st.sidebar.checkbox("Cirrhosis"),
}

canonical_triggers = canonicalize(raw_ui)

# Prior negatives
prior_negatives = st.sidebar.multiselect(
    "Prior negative tests",
    ["Blood cultures", "HIV", "Quantiferon", "ANA", "RF", "CCP", "dsDNA", "C3/C4", "Histo", "Blasto", "Cocci", "Crypto"]
)

run = st.sidebar.button("Run FUO Logic")


# --- MAIN OUTPUT ---
st.title("FUO Engine v2")

if run:
    differential, raw_orders = match_differential(canonical_triggers, immune_status, cd4, age)
    optimized = optimize_orders(raw_orders, prior_negatives, suspect_rheum)
    note = build_note(age, sex, immune_status, fever_days, canonical_triggers, differential, optimized)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Differential")
        for d in differential:
            css = (
                "infectious" if d["cat"] == "Infectious" else
                "endemic" if d["cat"] == "Endemic" else
                "rheum" if d["cat"] == "Rheumatologic" else
                "malignancy"
            )
            st.markdown(f"<div class='{css}'><b>{d['dx']}</b><br>{', '.join(d['matched'])}</div>", unsafe_allow_html=True)

    with c2:
        st.subheader("Plan")
        st.text_area("Consult Note", note, height=600)
