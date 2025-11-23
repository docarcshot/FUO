import streamlit as st
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | FUO Engine v2", layout="wide")

# --- CSS FOR CATEGORY BLOCKS (OPTION 3 LAYOUT) ---
st.markdown("""
<style>
    .dx-block {
        padding: 8px 12px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .infectious {
        border-left: 6px solid #198754;
        background-color: #e9f7ef;
    }
    .endemic {
        border-left: 6px solid #fd7e14;
        background-color: #fff4e6;
    }
    .immuno {
        border-left: 6px solid #0dcaf0;
        background-color: #e8f9ff;
    }
    .rheum {
        border-left: 6px solid #6f42c1;
        background-color: #f3e8ff;
    }
    .malignancy {
        border-left: 6px solid #d63384;
        background-color: #ffe6f0;
    }
    .noninf {
        border-left: 6px solid #6c757d;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def has_faget(tmax_f, hr):
    return tmax_f >= 102.0 and hr < 100

def neuro_flag(inputs):
    return ("Headache" in inputs["positives"] and "Vision changes" in inputs["positives"]) or ("Seizures" in inputs["positives"])

# --- PRIOR TEST NORMALIZATION MAP ---
PRIOR_MAP = {
    "Negative blood cultures": ["Blood cultures x2", "Blood cultures x3", "Blood cultures (hold 21d)"],
    "Negative TB testing": ["Quantiferon TB", "T-Spot TB"],
    "Negative Histo antigen": ["Urine Histoplasma antigen"],
    "Negative Bartonella serology": ["Bartonella serology"],
    "Negative Brucella serology": ["Brucella serology"],
    "Negative HIV": ["HIV 1/2 Ag/Ab (4th gen)"],
    "Normal CT chest/abd/pelvis": ["CT chest/abdomen/pelvis with contrast"],
    "Normal echocardiogram": ["TTE", "TEE"]
}

# --- DISEASE DATABASE (CORRECTED) ---
DISEASES = [
    {
        "dx": "Infective endocarditis",
        "cat": "Infectious",
        "triggers": ["New murmur", "IV drug use", "Prosthetic valve", "Embolic phenomena"],
        "orders": [("Blood cultures x3", 0), ("TTE", 1), ("TEE", 2)]
    },
    {
        "dx": "Tuberculosis (miliary or extrapulmonary)",
        "cat": "Infectious",
        "triggers": ["Weight loss", "Night sweats", "Chronic cough", "Hemoptysis", "TB exposure", "Homelessness/incarceration", "High TB burden travel"],
        "orders": [("Quantiferon TB", 1), ("AFB smear x3", 1), ("CT chest/abdomen/pelvis with contrast", 2)]
    },
    {
        "dx": "Disseminated histoplasmosis",
        "cat": "Endemic",
        "triggers": ["Bird/bat exposure", "Missouri/Ohio River Valley", "Pancytopenia", "Splenomegaly", "Oral ulcers"],
        "orders": [("Urine Histoplasma antigen", 1), ("Serum Histoplasma antibody", 1)]
    },
    {
        "dx": "Blastomycosis",
        "cat": "Endemic",
        "triggers": ["Missouri/Ohio River Valley", "Skin nodules/lesions", "Chronic cough", "Weight loss"],
        "orders": [("Serum Blastomyces antibody", 1)]
    },
    {
        "dx": "Coccidioidomycosis",
        "cat": "Endemic",
        "triggers": ["US Southwest travel", "Night sweats", "Weight loss", "Chronic cough"],
        "orders": [("Coccidioides serologic cascade (IgG/IgM/CF)", 1)]
    },
    {
        "dx": "Cryptococcosis (fungemia or early dissemination)",
        "cat": "Infectious",
        "triggers": ["Headache", "Vision changes", "HIV", "Biologics", "Chemotherapy", "Cirrhosis"],
        "orders": [("Serum cryptococcal antigen", 1)]
    },
    {
        "dx": "Cryptococcal meningitis",
        "cat": "Infectious",
        "triggers": ["Headache", "Vision changes", "Seizures", "HIV", "Cirrhosis"],
        "requires_neuro": True,
        "orders": [("LP with CSF CrAg", 2)]
    },
    {
        "dx": "Bartonella (endocarditis/bacteremia)",
        "cat": "Infectious",
        "triggers": ["Cats", "Homelessness/incarceration", "Body lice", "IV drug use"],
        "orders": [("Bartonella serology", 1)]
    },
    {
        "dx": "Brucellosis",
        "cat": "Infectious",
        "triggers": ["Unpasteurized dairy", "Livestock exposure", "Travel Mediterranean/Mexico", "Back pain", "Night sweats"],
        "orders": [("Brucella serology", 1), ("Blood cultures (hold 21d)", 0)]
    },
    {
        "dx": "Q fever (Coxiella)",
        "cat": "Infectious",
        "triggers": ["Farm animals", "Parturient animals", "Rural living", "Well water"],
        "orders": [("Coxiella serology", 1), ("TTE", 1)]
    },
    {
        "dx": "Disseminated MAC",
        "cat": "Immunocompromised",
        "triggers": ["HIV", "Night sweats", "Weight loss", "Diarrhea"],
        "requires_hiv": True,
        "orders": [("AFB blood culture", 1), ("CT abdomen/pelvis (nodes, organomegaly)", 2)]
    },
    {
        "dx": "Temporal arteritis (GCA)",
        "cat": "Rheumatologic",
        "triggers": ["Age > 50", "Headache", "Jaw claudication", "Vision changes"],
        "requires_age_min": 50,
        "orders": [("ESR", 0), ("CRP", 0), ("Temporal artery ultrasound", 2)]
    },
    {
        "dx": "Adult Still disease",
        "cat": "Rheumatologic",
        "triggers": ["Arthralgia", "Rash", "Ferritin > 1000", "Night sweats"],
        "orders": [("Ferritin", 0), ("ANA", 1), ("RF", 1)]
    },
    {
        "dx": "Lymphoma or occult malignancy",
        "cat": "Malignancy",
        "triggers": ["Weight loss", "Night sweats", "Lymphadenopathy", "Splenomegaly"],
        "orders": [("LDH", 1), ("CT chest/abdomen/pelvis with contrast", 2)]
    },
    {
        "dx": "Drug fever",
        "cat": "Noninfectious",
        "triggers": ["Relative bradycardia", "New beta-lactam", "New anticonvulsant", "New sulfa", "Eosinophilia"],
        "orders": [("Discontinue suspect agent", 0)]
    }
]

BASELINE_ORDERS = [
    "CBC with differential",
    "CMP",
    "ESR",
    "CRP",
    "Urinalysis"
]
# --- DIFFERENTIAL ENGINE ---
def build_differential(inputs):
    positives = set(inputs["positives"])
    fever_days = inputs["fever_days"]
    immune = inputs["immune"]
    cd4 = inputs.get("cd4")
    age = inputs["age"]

    # Derived immuno flags
    risk_hiv = immune == "HIV"
    risk_transplant = immune == "Transplant"
    risk_immunosupp = immune in ["HIV", "Transplant", "Biologics", "Chemotherapy"]

    # Auto-add HIV markers
    if risk_hiv:
        positives.add("HIV")
        if cd4 is not None and cd4 < 250:
            positives.add("CD4 < 250")
        if cd4 is not None and cd4 < 100:
            positives.add("CD4 < 100")

    active = []

    for d in DISEASES:
        score = 0
        reasons = []

        # Trigger matching (simple)
        for t in d["triggers"]:
            if t in positives:
                score += 1
                reasons.append(t)

        # Age gating
        if d.get("requires_age_min") and age < d["requires_age_min"]:
            continue

        # HIV gating for MAC
        if d.get("requires_hiv") and not risk_hiv:
            continue

        # Cryptococcal meningitis gating (requires neuro features)
        if d.get("requires_neuro") and not neuro_flag(inputs):
            continue

        # Only keep if score > 0
        if score > 0:
            active.append({
                "dx": d["dx"],
                "cat": d["cat"],
                "score": score,
                "reasons": reasons,
                "orders": d["orders"]
            })

    # Sort by (category grouping later), but for now score only
    active.sort(key=lambda x: x["score"], reverse=True)
    return active


# --- ORDER ENGINE ---
def build_orders(active, prior_neg, suspect_rheum=False):
    orders_by_tier = {
        0: set(BASELINE_ORDERS),
        1: set(),
        2: set(),
        3: set(),
    }

    # collect raw orders
    for item in active:
        for order_name, tier in item["orders"]:
            orders_by_tier[tier].add(order_name)

    # --- RHEUMATOLOGY GATE ---
    rheum_tests = {
        "ANA",
        "RF",
        "CCP",
        "C3/C4",
        "ENA cascade",
        "ANA (IFA)",
        "Anti-CCP",
    }

    # determine if rheum should be forced on
    rheum_forced = any(
        dx["dx"] in [
            "Adult Still disease",
            "Temporal arteritis (GCA)",
            "Systemic Lupus (SLE)"
        ]
        for dx in active
    )

    # apply suppression if rheum not suspected and not forced
    if not suspect_rheum and not rheum_forced:
        for tier in [1, 2]:
            orders_by_tier[tier] = {
                o for o in orders_by_tier[tier]
                if not any(rt in o for rt in rheum_tests)
            }

    # --- PRIOR NEGATIVES REMOVAL ---
    already_done = set()
    for label in prior_neg:
        already_done.update(PRIOR_MAP.get(label, []))

    for tier in orders_by_tier:
        orders_by_tier[tier] = {
            o for o in orders_by_tier[tier]
            if not any(p in o for p in already_done)
        }

    return orders_by_tier

# --- NOTE BUILDER ---
def build_note(inputs, active, orders):
    lines = []
    today = datetime.date.today().isoformat()

    lines.append(f"Date: {today}")
    intro = f"{inputs['age']} year old {inputs['sex']} with fever of unknown origin"
    if inputs["immune"] != "Immunocompetent":
        intro += f" with {inputs['immune'].lower()}."
    else:
        intro += "."
    lines.append(intro)

    lines.append(
        f"Fever duration {inputs['fever_days']} days, Tmax {inputs['tmax']} F, HR at Tmax {inputs['hr']} bpm."
    )

    if has_faget(inputs["tmax"], inputs["hr"]):
        lines.append("Relative bradycardia present (possible Faget sign).")

    # Context
    if inputs["positives"]:
        lines.append("Key features: " + ", ".join(sorted(inputs["positives"])) + ".")
    else:
        lines.append("No focal symptoms or exposures identified.")

    if inputs["prior_neg"]:
        lines.append("Prior negative workup: " + ", ".join(inputs["prior_neg"]) + ".")

    lines.append("")
    lines.append("Assessment and differential:")

    if not active:
        lines.append("- Persistent FUO without clear syndromic direction.")
    else:
        # Group by category
        grouped = {}
        for dx in active:
            grouped.setdefault(dx["cat"], []).append(dx)

        # Ordered categories
        cat_order = ["Infectious", "Endemic", "Immunocompromised", "Rheumatologic", "Malignancy", "Noninfectious"]

        for cat in cat_order:
            if cat in grouped:
                lines.append(f"{cat}:")
                for dx in sorted(grouped[cat], key=lambda x: x["score"], reverse=True):
                    r_str = ", ".join(sorted(dx["reasons"])) if dx["reasons"] else "clinical context"
                    lines.append(f"- {dx['dx']} (supported by {r_str})")

    lines.append("")
    lines.append("Plan:")

    # Tier 0
    if orders[0]:
        lines.append("Baseline tests:")
        for o in sorted(orders[0]):
            lines.append(f"- [ ] {o}")

    # Tier 1
    if orders[1]:
        lines.append("")
        lines.append("Targeted labs:")
        for o in sorted(orders[1]):
            lines.append(f"- [ ] {o}")

    # Tier 2
    if orders[2]:
        lines.append("")
        lines.append("Imaging:")
        for o in sorted(orders[2]):
            lines.append(f"- [ ] {o}")

    # Tier 3
    if orders[3]:
        lines.append("")
        lines.append("Advanced or invasive diagnostics:")
        for o in sorted(orders[3]):
            lines.append(f"- [ ] {o}")

    return "\n".join(lines)


# --- DIFFERENTIAL RENDERING (OPTION 3 CONTAINERS) ---
def render_dx_block(dx):
    cat = dx["cat"]
    if cat == "Infectious":
        cls = "infectious"
    elif cat == "Endemic":
        cls = "endemic"
    elif cat == "Immunocompromised":
        cls = "immuno"
    elif cat == "Rheumatologic":
        cls = "rheum"
    elif cat == "Malignancy":
        cls = "malignancy"
    else:
        cls = "noninf"

    with st.container():
        st.markdown(f"<div class='dx-block {cls}'>", unsafe_allow_html=True)
        st.markdown(f"**{dx['dx']}**", unsafe_allow_html=True)
        if dx["reasons"]:
            st.markdown("Triggers: " + ", ".join(sorted(dx["reasons"])), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
# --- UI LAYOUT: SIDEBAR ---
with st.sidebar:
    st.title("FUO Engine")

    if st.button("Clear all inputs"):
        st.session_state.clear()
        st.experimental_rerun()

    st.header("Patient Data")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 55)
    sex = c2.selectbox("Sex", ["Female", "Male"])
    immune = st.selectbox(
        "Immune status",
        ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"],
    )

    cd4 = None
    if immune == "HIV":
        cd4 = st.slider("CD4 count", 0, 1200, 300)

    st.header("Fever Profile")
    tmax = st.number_input("Tmax (F)", 98.0, 107.0, 101.5, step=0.1)
    hr = st.number_input("Heart rate at Tmax", 40, 160, 95)
    fever_days = st.number_input("Days of fever", 3, 365, 21)
    on_abx = st.checkbox("Currently on antibiotics")

    # RHEUMATOLOGY GATE (restored)
    suspect_rheum = st.checkbox("Suspect rheumatologic etiology", value=False)

st.header("Symptoms (ROS)")

with st.expander("Constitutional", expanded=True):
    night_sweats = st.checkbox("Night sweats")
    weight_loss = st.checkbox("Weight loss")
    fatigue = st.checkbox("Fatigue")

with st.expander("Neurologic", expanded=True):
    headache = st.checkbox("Headache")
    vision_changes = st.checkbox("Vision changes")
    seizures = st.checkbox("Seizures")

with st.expander("Respiratory", expanded=True):
    chronic_cough = st.checkbox("Chronic cough")
    hemoptysis = st.checkbox("Hemoptysis")
    dyspnea = st.checkbox("Dyspnea")

with st.expander("GI / Hepatic", expanded=True):
    abdominal_pain = st.checkbox("Abdominal pain")
    diarrhea = st.checkbox("Diarrhea")
    ruq_pain = st.checkbox("RUQ pain / hepatodynia")

with st.expander("MSK", expanded=True):
    arthralgia = st.checkbox("Joint pain")
    back_pain = st.checkbox("Back pain")
    myalgia = st.checkbox("Myalgias")

with st.expander("Skin findings", expanded=True):
    rash = st.checkbox("Rash")
    palmar_rash = st.checkbox("Palms/soles rash")
    nodules = st.checkbox("Skin nodules/lesions")

with st.expander("Lymph / Heme", expanded=True):
    lymphadenopathy = st.checkbox("Lymphadenopathy")
    splenomegaly = st.checkbox("Splenomegaly")
    pancytopenia = st.checkbox("Pancytopenia")

st.header("Exposures and Risks")

with st.expander("Animals and environment", expanded=True):
    cats = st.checkbox("Cat exposure")
    livestock = st.checkbox("Livestock / farm animals")
    bird_bat = st.checkbox("Bird / bat or cave exposure")
    unpasteurized_dairy = st.checkbox("Unpasteurized dairy")
    rural = st.checkbox("Rural or farm living")
    body_lice = st.checkbox("Body lice")

with st.expander("Social / TB risk", expanded=True):
    ivdu = st.checkbox("IV drug use")
    homeless = st.checkbox("Homelessness or incarceration")
    tb_contact = st.checkbox("TB exposure")
    high_tb_travel = st.checkbox("High TB burden country travel")

with st.expander("Geography", expanded=True):
    missouri = st.checkbox("Missouri / Ohio River Valley")
    sw_us = st.checkbox("US Southwest travel")


    st.header("Prior Workup (Negative)")
    prior_neg = st.multiselect(
        "Mark studies already done and negative",
        [
            "Negative blood cultures",
            "Negative TB testing",
            "Negative Histo antigen",
            "Negative Bartonella serology",
            "Negative Brucella serology",
            "Negative HIV",
            "Normal CT chest/abd/pelvis",
            "Normal echocardiogram",
        ],
    )

    run = st.button("Generate FUO Plan")


# --- MAIN PANEL ---
st.title("ID-CDSS | FUO Engine v2")

if run:
    positives = []

    # Build positives list
    if night_sweats: positives.append("Night sweats")
    if weight_loss: positives.append("Weight loss")
    if fatigue: positives.append("Fatigue")

    if headache: positives.append("Headache")
    if vision_changes: positives.append("Vision changes")
    if seizures: positives.append("Seizures")

    if chronic_cough: positives.append("Chronic cough")
    if hemoptysis: positives.append("Hemoptysis")
    if dyspnea: positives.append("Dyspnea")

    if abdominal_pain: positives.append("Abdominal pain")
    if diarrhea: positives.append("Diarrhea")
    if ruq_pain: positives.append("RUQ pain / hepatodynia")

    if arthralgia: positives.append("Arthralgia")
    if back_pain: positives.append("Back pain")
    if myalgia: positives.append("Myalgias")

    if rash: positives.append("Rash")
    if palmar_rash: positives.append("Palms/soles rash")
    if nodules: positives.append("Skin nodules/lesions")

    if lymphadenopathy: positives.append("Lymphadenopathy")
    if splenomegaly: positives.append("Splenomegaly")
    if pancytopenia: positives.append("Pancytopenia")

    if cats: positives.append("Cats")
    if livestock:
        positives.append("Livestock exposure")
        positives.append("Farm animals")
    if bird_bat: positives.append("Bird/bat exposure")
    if unpasteurized_dairy: positives.append("Unpasteurized dairy")
    if rural:
        positives.append("Rural living")
        positives.append("Farm animals")
    if body_lice: positives.append("Body lice")

    if ivdu: positives.append("IV drug use")
    if homeless: positives.append("Homelessness/incarceration")
    if tb_contact: positives.append("TB exposure")
    if high_tb_travel: positives.append("High TB burden travel")

    if missouri: positives.append("Missouri/Ohio River Valley")
    if sw_us: positives.append("US Southwest travel")

    inputs = {
        "age": age,
        "sex": sex,
        "immune": immune,
        "cd4": cd4,
        "tmax": tmax,
        "hr": hr,
        "fever_days": fever_days,
        "positives": positives,
        "prior_neg": prior_neg,
        "on_abx": on_abx,
    }

    active = build_differential(inputs)
    orders = build_orders(active, prior_neg, suspect_rheum=suspect_rheum)
    note_text = build_note(inputs, active, orders)

    col1, col2 = st.columns(2)

    with col1:
        if has_faget(tmax, hr):
            st.markdown("<div class='dx-block noninf'><b>Relative bradycardia detected (Faget sign).</b></div>", unsafe_allow_html=True)

        st.subheader("Weighted Differential (Grouped)")

        if not active:
            st.write("No specific FUO syndromes triggered.")
        else:
            # Group by category in defined order
            cat_order = ["Infectious", "Endemic", "Immunocompromised", "Rheumatologic", "Malignancy", "Noninfectious"]
            grouped = {cat: [] for cat in cat_order}
            for dx in active:
                if dx["cat"] in grouped:
                    grouped[dx["cat"]].append(dx)
                else:
                    grouped["Noninfectious"].append(dx)

            for cat in cat_order:
                if grouped[cat]:
                    st.markdown(f"### {cat}")
                    for dx in grouped[cat]:
                        render_dx_block(dx)

    with col2:
        st.subheader("Staged Workup")

        # Tier 0
        st.markdown("**Tier 0 – Baseline labs**")
        for o in sorted(orders[0]):
            st.markdown(f"- [ ] {o}")

        # Tier 1
        if orders[1]:
            st.markdown("**Tier 1 – Targeted labs/serologies**")
            for o in sorted(orders[1]):
                st.markdown(f"- [ ] {o}")

        # Tier 2
        if orders[2]:
            st.markdown("**Tier 2 – Imaging**")
            for o in sorted(orders[2]):
                st.markdown(f"- [ ] {o}")

        # Tier 3
        if orders[3]:
            st.markdown("**Tier 3 – Advanced diagnostics**")
            for o in sorted(orders[3]):
                st.markdown(f"- [ ] {o}")

        st.subheader("Consult Note Draft")
        st.text_area("Note", note_text, height=350)
        st.download_button(
            "Download note as .txt",
            data=note_text,
            file_name=f"FUO_consult_{datetime.date.today().isoformat()}.txt",
            mime="text/plain",
        )
