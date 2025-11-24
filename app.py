import streamlit as st
import datetime

# ================================================================
# CONFIG
# ================================================================

st.set_page_config(
    page_title="ID-CDSS | FUO Engine v3",
    layout="wide"
)

# Color blocks for differential
st.markdown("""
<style>
    .dx-block {
        padding: 8px 12px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .infectious {
        border-left: 6px solid #198754;  /* green */
        background-color: #e9f7ef;
    }
    .endemic {
        border-left: 6px solid #fd7e14;  /* orange */
        background-color: #fff4e6;
    }
    .immuno {
        border-left: 6px solid #0dcaf0;  /* blue */
        background-color: #e8f9ff;
    }
    .rheum {
        border-left: 6px solid #6f42c1;  /* purple */
        background-color: #f3e8ff;
    }
    .malignancy {
        border-left: 6px solid #d63384;  /* pink */
        background-color: #ffe6f0;
    }
    .noninf {
        border-left: 6px solid #6c757d;  /* gray */
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def has_faget(tmax_f, hr):
    return tmax_f >= 102 and hr < 100

def neuro_flag(positives):
    return ("Headache" in positives and "Vision changes" in positives) or ("Seizures" in positives)


# Short attending-style names for note
SHORT_NAME = {
    "Tuberculosis (miliary or extrapulmonary)": "TB",
    "Disseminated histoplasmosis": "Histo",
    "Blastomycosis": "Blasto",
    "Coccidioidomycosis": "Cocci",
    "Cryptococcosis (fungemia or early dissemination)": "Crypto",
    "Cryptococcal meningitis": "Crypto meningitis",
    "Disseminated MAC": "MAC",
    "Temporal arteritis (GCA)": "GCA",
    "Adult Still disease": "Still's",
    "Lymphoma or occult malignancy": "Lymphoma",
    "Bartonella (endocarditis/bacteremia)": "Bartonella",
    "Brucellosis": "Brucella",
    "Q fever (Coxiella)": "Q fever",
    "Infective endocarditis": "Endocarditis",
    "Drug fever": "Drug fever",
    "Post-transplant lymphoproliferative disorder (PTLD)": "PTLD"
}

def short_name(dx):
    return SHORT_NAME.get(dx, dx)


# ================================================================
# DISEASE DATABASE (FUO ENGINE v3)
# ================================================================

DISEASES = [

    # ------------------------------------------------------------
    # INFECTIOUS
    # ------------------------------------------------------------
    {
        "dx": "Infective endocarditis",
        "cat": "Infectious",
        "triggers": ["New murmur", "IV drug use", "Embolic phenomena", "Prosthetic valve"],
        "orders": [
            ("Blood cultures x3", 0),
            ("TTE", 1),
            ("TEE (if endocarditis concern persists after TTE)", 3)
        ]
    },

    {
        "dx": "Tuberculosis (miliary or extrapulmonary)",
        "cat": "Infectious",
        "triggers": [
            "Weight loss", "Night sweats",
            "Chronic cough", "Hemoptysis",
            "TB exposure",
            "Homelessness/incarceration",
            "High TB burden travel"
        ],
        "orders": [
            ("Quantiferon TB", 1),
            ("AFB smear x3", 1),
            ("CT chest/abdomen/pelvis with contrast", 2)
        ]
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
        "requires_neuro": True,
        "triggers": ["Headache", "Vision changes", "Seizures", "HIV", "Cirrhosis"],
        "orders": [
            ("LP with CSF studies (consider if meningitis features)", 3)
        ]
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
        "triggers": ["Unpasteurized dairy", "Livestock exposure",
                     "Travel Mediterranean/Mexico", "Back pain", "Night sweats"],
        "orders": [
            ("Brucella serology", 1),
            ("Blood cultures (hold 21d)", 0)
        ]
    },

    {
        "dx": "Q fever (Coxiella)",
        "cat": "Infectious",
        "triggers": ["Farm animals", "Parturient animals", "Rural living", "Well water"],
        "orders": [
            ("Coxiella serology", 1),
            ("TTE", 1)
        ]
    },

    # ------------------------------------------------------------
    # ENDEMIC MYCOSES
    # ------------------------------------------------------------
    {
        "dx": "Disseminated histoplasmosis",
        "cat": "Endemic",
        "triggers": ["Bird/bat exposure", "Missouri/Ohio River Valley",
                     "Pancytopenia", "Splenomegaly", "Oral ulcers"],
        "orders": [
            ("Urine Histoplasma antigen", 1),
            ("Serum Histoplasma antibody", 1)
        ]
    },

    {
        "dx": "Blastomycosis",
        "cat": "Endemic",
        "triggers": ["Missouri/Ohio River Valley",
                     "Skin nodules/lesions", "Chronic cough", "Weight loss"],
        "orders": [("Serum Blastomyces antibody", 1)]
    },

    {
        "dx": "Coccidioidomycosis",
        "cat": "Endemic",
        "triggers": ["US Southwest travel", "Night sweats", "Weight loss", "Chronic cough"],
        "orders": [("Coccidioides serologic cascade (IgG/IgM/CF)", 1)]
    },

    # ------------------------------------------------------------
    # IMMUNOCOMPROMISED
    # ------------------------------------------------------------
    {
        "dx": "Disseminated MAC",
        "cat": "Immunocompromised",
        "requires_hiv": True,
        "triggers": ["HIV", "Night sweats", "Weight loss", "Diarrhea"],
        "orders": [
            ("AFB blood culture", 1),
            ("CT abdomen/pelvis (nodes, organomegaly)", 2)
        ],
        "soft_triggers_transplant": ["Lung transplant"]  # special rule
    },

    {
        "dx": "Post-transplant lymphoproliferative disorder (PTLD)",
        "cat": "Immunocompromised",
        "requires_transplant": True,
        "triggers": ["Lymphadenopathy", "Weight loss", "Night sweats", "EBV positive"],
        "orders": [
            ("EBV PCR", 1),
            ("CT chest/abdomen/pelvis with contrast", 2),
            ("Bone marrow biopsy (if cytopenias persist or LAD unexplained)", 3)
        ]
    },

    # ------------------------------------------------------------
    # RHEUMATOLOGIC
    # ------------------------------------------------------------
    {
        "dx": "Temporal arteritis (GCA)",
        "cat": "Rheumatologic",
        "requires_age_min": 50,
        "triggers": ["Headache", "Jaw claudication", "Vision changes"],
        "orders": [
            ("ESR", 0),
            ("CRP", 0),
            ("Temporal artery ultrasound (if ESR/CRP elevated or classic symptoms)", 3)
        ]
    },

    {
        "dx": "Adult Still disease",
        "cat": "Rheumatologic",
        "triggers": ["Arthralgia", "Rash", "Ferritin > 1000", "Night sweats"],
        "orders": [
            ("Ferritin", 0),
            ("ANA", 1),
            ("RF", 1)
        ]
    },

    # ------------------------------------------------------------
    # MALIGNANCY / NONINFECTIOUS
    # ------------------------------------------------------------
    {
        "dx": "Lymphoma or occult malignancy",
        "cat": "Malignancy",
        "triggers": ["Weight loss", "Night sweats", "Lymphadenopathy", "Splenomegaly"],
        "orders": [
            ("LDH", 1),
            ("CT chest/abdomen/pelvis with contrast", 2)
        ]
    },

    {
        "dx": "Drug fever",
        "cat": "Noninfectious",
        "triggers": ["Relative bradycardia", "New beta-lactam", "New anticonvulsant", "New sulfa", "Eosinophilia"],
        "orders": [
            ("Discontinue suspect agent", 0)
        ]
    }
]

# Baseline tests
BASELINE_ORDERS = [
    "CBC with differential",
    "CMP",
    "ESR",
    "CRP",
    "Urinalysis"
]
# ================================================================
# PRIOR TEST NORMALIZATION
# ================================================================

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


# ================================================================
# DIFFERENTIAL ENGINE
# ================================================================

def build_differential(inputs):
    positives = set(inputs["positives"])
    age = inputs["age"]
    immune = inputs["immune"]
    cd4 = inputs.get("cd4")
    transplant_type = inputs.get("transplant_type")
    ebv_status = inputs.get("ebv_status")

    risk_hiv = immune == "HIV"
    risk_transplant = immune == "Transplant"

    # HIV logic
    if risk_hiv:
        positives.add("HIV")
        if cd4 is not None and cd4 < 250:
            positives.add("CD4 < 250")
        if cd4 is not None and cd4 < 100:
            positives.add("CD4 < 100")

    # EBV logic
    if ebv_status == "Positive":
        positives.add("EBV positive")

    active = []

    for d in DISEASES:
        score = 0
        reasons = []

        # Matched triggers
        for t in d["triggers"]:
            if t in positives:
                score += 1
                reasons.append(t)

        # Age gating
        if d.get("requires_age_min") and age < d["requires_age_min"]:
            continue

        # HIV gating
        if d.get("requires_hiv") and not risk_hiv:
            continue

        # Neuro gating
        if d.get("requires_neuro") and not neuro_flag(positives):
            continue

        # Transplant gating
        if d.get("requires_transplant") and not risk_transplant:
            continue

        # Soft lung-transplant MAC logic
        if risk_transplant and transplant_type == "Lung" and "soft_triggers_transplant" in d:
            score += 1
            reasons.append("Lung transplant")

        if score > 0:
            active.append({
                "dx": d["dx"],
                "cat": d["cat"],
                "score": score,
                "reasons": reasons,
                "orders": d["orders"]
            })

    # Sort by score descending
    active.sort(key=lambda x: x["score"], reverse=True)
    return active


# ================================================================
# ORDER ENGINE
# ================================================================

def build_orders(active, prior_neg):
    orders_by_tier = {
        0: set(BASELINE_ORDERS),
        1: set(),
        2: set(),
        3: set()
    }

    # Pull all disease-driven orders
    for item in active:
        for order, tier in item["orders"]:
            orders_by_tier[tier].add(order)

    # Remove orders already done
    already_done = set()
    for neg in prior_neg:
        already_done.update(PRIOR_MAP.get(neg, []))

    for tier in orders_by_tier:
        orders_by_tier[tier] = {
            o for o in orders_by_tier[tier]
            if not any(done in o for done in already_done)
        }

    return orders_by_tier
    # ================================================================
# NOTE BUILDER
# ================================================================

def build_note(inputs, active, orders):
    lines = []
    today = datetime.date.today().isoformat()

    age = inputs["age"]
    sex = inputs["sex"]
    tmax = inputs["tmax"]
    hr = inputs["hr"]
    fever_days = inputs["fever_days"]
    positives = inputs["positives"]

    # Header
    lines.append(f"Date: {today}")
    lines.append(f"{age} year old {sex} with prolonged fever without a clear source.")
    lines.append(f"Tmax {tmax} F with heart rate {hr} bpm at peak. Fever has been present for {fever_days} days.")

    # Neuro flag
    if neuro_flag(positives):
        lines.append("Neurologic symptoms present; consider CNS involvement based on overall exam and course.")

    # Features section
    if positives:
        lines.append("Features reported include: " + ", ".join(positives) + ".")
    else:
        lines.append("No focal symptoms or exposures identified.")

    # --- Differential summary ---
    lines.append("")
    lines.append("Assessment and differential:")

    if not active:
        lines.append("No syndromic pattern identified at this time.")
    else:
        # 1) Most likely = top 1–2
        top = active[:2]
        likely_names = [short_name(dx["dx"]) for dx in top]
        lines.append(f"Symptoms seem most consistent with {', '.join(likely_names)} based on the current findings.")

        # 2) Possible but less supported
        mid = active[2:7]
        if mid:
            mid_names = [short_name(dx["dx"]) for dx in mid]
            lines.append(f"{', '.join(mid_names)} remain possible but are not strongly supported at this stage.")

        # 3) Least likely
        low = active[7:]
        if low:
            low_names = [short_name(dx["dx"]) for dx in low]
            lines.append(f"{', '.join(low_names)} appear unlikely given the current pattern.")

    # --- PLAN section ---
    lines.append("")
    lines.append("Plan:")

    # Baseline labs
    if orders[0]:
        lines.append("Baseline studies:")
        for o in sorted(orders[0]):
            lines.append(f"- [ ] {o}")

    # Targeted labs
    if orders[1]:
        lines.append("")
        lines.append("Targeted testing:")
        for o in sorted(orders[1]):
            lines.append(f"- [ ] {o}")

    # Imaging
    if orders[2]:
        lines.append("")
        lines.append("Imaging:")
        for o in sorted(orders[2]):
            lines.append(f"- [ ] {o}")

    # Advanced tests
    if orders[3]:
        lines.append("")
        lines.append("Advanced or invasive diagnostics:")
        for o in sorted(orders[3]):
            lines.append(f"- [ ] {o}")

    return "\n".join(lines)


# ================================================================
# DIFFERENTIAL RENDERING (colored blocks)
# ================================================================

def render_dx_block(dx):
    cat = dx["cat"]
    cls = {
        "Infectious": "infectious",
        "Endemic": "endemic",
        "Immunocompromised": "immuno",
        "Rheumatologic": "rheum",
        "Malignancy": "malignancy"
    }.get(cat, "noninf")

    with st.container():
        st.markdown(f"<div class='dx-block {cls}'>", unsafe_allow_html=True)
        st.markdown(f"**{short_name(dx['dx'])}**", unsafe_allow_html=True)
        if dx["reasons"]:
            st.markdown("Triggers: " + ", ".join(dx["reasons"]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ================================================================
# SIDEBAR UI
# ================================================================

with st.sidebar:
    st.title("FUO Engine v3")

    if st.button("Clear all inputs", key="clear_all"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()

    # Patient details
    st.header("Patient Data")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 55)
    sex = c2.selectbox("Sex", ["Female", "Male"])

    immune = st.selectbox(
        "Immune status",
        ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"]
    )

    cd4 = None
    transplant_type = None
    time_since_tx = None
    ebv_status = None

    # HIV block
    if immune == "HIV":
        cd4 = st.slider("CD4 count", 0, 1200, 300)

    # TRANSPLANT BLOCK (Option B)
    if immune == "Transplant":
        with st.expander("Transplant details", expanded=True):
            transplant_type = st.selectbox(
                "Type of transplant",
                ["Kidney", "Liver", "Lung", "Heart", "HSCT"]
            )
            time_since_tx = st.number_input("Time since transplant (months)", 0, 600, 12)
            ebv_status = st.selectbox("EBV status", ["Unknown", "Positive", "Negative"])

    st.header("Fever Profile")
    tmax = st.number_input("Tmax (F)", 98.0, 107.0, 101.5, step=0.1)
    hr = st.number_input("Heart rate at Tmax", 40, 170, 95)
    fever_days = st.number_input("Days of fever", 1, 365, 14)
    on_abx = st.checkbox("On antibiotics")

    # ============================================================
    # ROS
    # ============================================================
    st.header("Symptoms (ROS)")

    with st.expander("Constitutional", expanded=True):
        night_sweats = st.checkbox("Night sweats")
        weight_loss = st.checkbox("Weight loss")
        fatigue = st.checkbox("Fatigue")

    with st.expander("Neurologic", expanded=True):
        headache = st.checkbox("Headache")
        vision_changes = st.checkbox("Vision changes")
        seizures = st.checkbox("Seizures")
        jaw_claudication = st.checkbox("Jaw claudication")

    with st.expander("Respiratory", expanded=True):
        chronic_cough = st.checkbox("Chronic cough")
        hemoptysis = st.checkbox("Hemoptysis")
        dyspnea = st.checkbox("Dyspnea")

    with st.expander("GI / Hepatic", expanded=True):
        abdominal_pain = st.checkbox("Abdominal pain")
        diarrhea = st.checkbox("Diarrhea")
        ruq_pain = st.checkbox("RUQ pain / hepatodynia")

    with st.expander("MSK", expanded=True):
        arthralgia = st.checkbox("Arthralgia")
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

    # ============================================================
    # EXPOSURES
    # ============================================================

    st.header("Exposures and Risks")

    with st.expander("Animals / Environment", expanded=True):
        cats = st.checkbox("Cat exposure")
        livestock = st.checkbox("Livestock / farm animals")
        bird_bat = st.checkbox("Bird/bat or cave exposure")
        unpasteurized_dairy = st.checkbox("Unpasteurized dairy")
        rural = st.checkbox("Rural living")
        body_lice = st.checkbox("Body lice")

    with st.expander("Social / TB Risk", expanded=True):
        ivdu = st.checkbox("IV drug use")
        homeless = st.checkbox("Homelessness/incarceration")
        tb_contact = st.checkbox("TB exposure")
        high_tb_travel = st.checkbox("High TB burden travel")

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
            "Normal echocardiogram"
        ]
    )

    run = st.button("Generate FUO Plan")
# ================================================================
# NOTE BUILDER
# ================================================================

def build_note(inputs, active, orders):
    lines = []
    today = datetime.date.today().isoformat()

    # Header
    lines.append(f"Date: {today}")
    intro = f"{inputs['age']} year old {inputs['sex']} with prolonged fever without a clear source."
    lines.append(intro)

    # Fever profile
    lines.append(
        f"Tmax {inputs['tmax']} F with heart rate {inputs['hr']} bpm at peak. "
        f"Fever has been present for {inputs['fever_days']} days."
    )

    # Neuro warning
    if neuro_flag(inputs["positives"]):
        lines.append("Neurologic symptoms present; consider CNS involvement based on overall exam and course.")

    # Faget
    if has_faget(inputs["tmax"], inputs["hr"]):
        lines.append("Relative bradycardia noted (possible Faget sign).")

    # Findings
    if inputs["positives"]:
        clean = sorted(inputs["positives"])
        lines.append("Features reported include: " + ", ".join(clean) + ".")
    else:
        lines.append("No focal symptoms or exposures identified.")

    # Prior workup
    if inputs["prior_neg"]:
        lines.append("Prior negative workup: " + ", ".join(inputs["prior_neg"]) + ".")

    lines.append("")
    lines.append("Assessment and differential:")

    # If none
    if not active:
        lines.append("No syndrome-specific patterns identified at this stage.")
        lines.append("")
        lines.append("Plan:")
        return "\n".join(lines)

    # Top-level synthesis
    # Group by score:
    top_scores = active[0]["score"]
    top_dxs = [short_name(dx["dx"]) for dx in active if dx["score"] == top_scores]

    mid_dxs = [short_name(dx["dx"]) for dx in active if 0 < dx["score"] < top_scores]

    # Those with score == 1 only, and not in top or mid
    all_names = [dx["dx"] for dx in active]
    low_dxs = [short_name(dx["dx"]) for dx in active if dx["score"] == 1 and short_name(dx["dx"]) not in top_dxs]

    # Construct narrative
    if top_dxs:
        lines.append(f"Symptoms seem most consistent with {', '.join(top_dxs)} based on the current findings.")

    if mid_dxs:
        lines.append(f"{', '.join(mid_dxs)} remain possible but are not strongly supported at this stage.")

    if low_dxs:
        lines.append(f"{', '.join(low_dxs)} appear unlikely given the available information.")

    # PLAN
    lines.append("")
    lines.append("Plan:")

    # Tier 0
    if orders[0]:
        lines.append("Baseline studies:")
        for o in sorted(orders[0]):
            lines.append(f"- [ ] {o}")

    # Tier 1
    if orders[1]:
        lines.append("")
        lines.append("Targeted infectious and rheumatologic testing:")
        for o in sorted(orders[1]):
            lines.append(f"- [ ] {o}")

    # Tier 2
    if orders[2]:
        lines.append("")
        lines.append("Cross-sectional imaging:")
        for o in sorted(orders[2]):
            lines.append(f"- [ ] {o}")

    # Tier 3 — invasive or conditional
    if orders[3]:
        lines.append("")
        lines.append("Advanced or invasive diagnostics:")
        for o in sorted(orders[3]):
            lines.append(f"- [ ] {o}")

    return "\n".join(lines)



# ================================================================
# DIFFERENTIAL RENDERING (CATEGORY BLOCKS)
# ================================================================

def render_dx_block(dx):
    cat = dx["cat"]
    if cat == "Infectious":
        css = "infectious"
    elif cat == "Endemic":
        css = "endemic"
    elif cat == "Immunocompromised":
        css = "immuno"
    elif cat == "Rheumatologic":
        css = "rheum"
    elif cat == "Malignancy":
        css = "malignancy"
    else:
        css = "noninf"

    with st.container():
        st.markdown(f"<div class='dx-block {css}'>", unsafe_allow_html=True)
        st.markdown(f"**{dx['dx']}**", unsafe_allow_html=True)
        if dx["reasons"]:
            st.markdown("Triggers: " + ", ".join(dx["reasons"]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)



# ================================================================
# SIDEBAR — INPUTS
# ================================================================

with st.sidebar:
    st.title("FUO Engine v3")

    if st.button("Clear all inputs", key="clear_all"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

    # Patient data
    st.header("Patient Data")

    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 55)
    sex = c2.selectbox("Sex", ["Female", "Male"])

    immune = st.selectbox(
        "Immune status",
        ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"]
    )

    cd4 = None
    transplant_type = None
    transplant_months = None
    ebv_status = None

    # HIV
    if immune == "HIV":
        cd4 = st.slider("CD4 count", 0, 1200, 300)

    # TRANSPLANT SECTION (Option B — dedicated expander)
    if immune == "Transplant":
        with st.expander("Transplant details", expanded=True):
            transplant_type = st.selectbox(
                "Type of transplant",
                ["Kidney", "Liver", "Lung", "Heart", "HSCT"]
            )
            transplant_months = st.number_input(
                "Months since transplant",
                0, 360, 12
            )
            ebv_status = st.selectbox("EBV status", ["Unknown", "Positive", "Negative"])

    # Fever
    st.header("Fever Profile")
    tmax = st.number_input("Tmax (F)", 98.0, 107.0, 101.5, step=0.1)
    hr = st.number_input("Heart rate at Tmax", 40, 160, 95)
    fever_days = st.number_input("Days of fever", 3, 365, 21)
    on_abx = st.checkbox("Currently on antibiotics")
# ================================================================
# NOTE BUILDER
# ================================================================

def build_note(inputs, active, orders):
    lines = []
    today = datetime.date.today().isoformat()

    # --- HEADER ---
    lines.append(f"Date: {today}")
    intro = f"{inputs['age']} year old {inputs['sex']} with prolonged fever without a clear source."
    lines.append(intro)

    lines.append(
        f"Tmax {inputs['tmax']} F with heart rate {inputs['hr']} bpm at peak. "
        f"Fever has been present for {inputs['fever_days']} days."
    )

    # Neuro flagging
    if neuro_flag(inputs["positives"]):
        lines.append("Neurologic symptoms present; consider CNS involvement based on overall exam and course.")

    # Key features
    if inputs["positives"]:
        lines.append(
            "Features reported include: " + ", ".join(sorted(inputs["positives"])) + "."
        )
    else:
        lines.append("No focal symptoms or exposures identified.")

    lines.append("")
    lines.append("Assessment and differential:")

    # --- DIFFERENTIAL SUMMARY ---
    if not active:
        lines.append("- No strong syndromic signals; FUO remains undifferentiated.")
    else:
        # Strong = top 1–2 diagnoses
        strong = active[:2]
        possible = active[2:6]
        unlikely = active[6:]

        if strong:
            strong_names = ", ".join(short_name(dx["dx"]) for dx in strong)
            lines.append(f"Symptoms seem most consistent with {strong_names} based on the current findings.")

        if possible:
            poss_names = ", ".join(short_name(dx["dx"]) for dx in possible)
            lines.append(f"{poss_names} remain possible but are not strongly supported at this stage.")

        if unlikely:
            unlik_names = ", ".join(short_name(dx["dx"]) for dx in unlikely)
            lines.append(f"{unlik_names} appear unlikely based on the current pattern.")

    lines.append("")
    lines.append("Plan:")

    # --- PLAN BLOCK ---
    if orders[0]:
        lines.append("Baseline studies:")
        for o in sorted(orders[0]):
            lines.append(f"- [ ] {o}")

    if orders[1]:
        lines.append("")
        lines.append("Targeted infectious and rheumatologic testing:")
        for o in sorted(orders[1]):
            lines.append(f"- [ ] {o}")

    if orders[2]:
        lines.append("")
        lines.append("Imaging:")
        for o in sorted(orders[2]):
            lines.append(f"- [ ] {o}")

    if orders[3]:
        lines.append("")
        lines.append("Advanced or invasive diagnostics:")
        for o in sorted(orders[3]):
            lines.append(f"- [ ] {o}")

    return "\n".join(lines)


# ================================================================
# DIFFERENTIAL RENDERING (COLOR BLOCKS)
# ================================================================

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


# ================================================================
# SIDEBAR UI (INCLUDING TRANSPLANT LOGIC)
# ================================================================

with st.sidebar:
    st.title("FUO Engine v3")

    # Reset
    if st.button("Clear all inputs"):
        st.session_state.clear()
        st.rerun()

    # --- Patient data ---
    st.header("Patient Data")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 55)
    sex = c2.selectbox("Sex", ["Male", "Female"])

    immune = st.selectbox(
        "Immune status",
        ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"]
    )

    cd4 = None
    if immune == "HIV":
        cd4 = st.slider("CD4 count", 0, 1200, 300)

    # --- Transplant sub-expander (Option A) ---
    transplant_type = None
    time_since_tx = None
    ebv_status = None

    if immune == "Transplant":
        with st.expander("Transplant details", expanded=True):
            transplant_type = st.selectbox(
                "Type of transplant",
                ["Kidney", "Liver", "Lung", "Heart", "HSCT"]
            )
            time_since_tx = st.number_input("Time since transplant (months)", 0, 600, 12)
            ebv_status = st.selectbox("EBV status (if known)", ["Unknown", "Positive", "Negative"])

    # --- Fever profile ---
    st.header("Fever Profile")
    tmax = st.number_input("Tmax (F)", 98.0, 107.0, 101.5, step=0.1)
    hr = st.number_input("Heart rate at Tmax", 40, 180, 95)
    fever_days = st.number_input("Days of fever", 3, 365, 21)
    on_abx = st.checkbox("Currently on antibiotics")

    # --- ROS ---
    st.header("Symptoms (ROS)")

    with st.expander("Constitutional", expanded=True):
        night_sweats = st.checkbox("Night sweats")
        weight_loss = st.checkbox("Weight loss")
        fatigue = st.checkbox("Fatigue")

    with st.expander("Neurologic", expanded=True):
        headache = st.checkbox("Headache")
        vision_changes = st.checkbox("Vision changes")
        seizures = st.checkbox("Seizures")
        jaw_claudication = st.checkbox("Jaw claudication")

    with st.expander("Respiratory", expanded=True):
        chronic_cough = st.checkbox("Chronic cough")
        hemoptysis = st.checkbox("Hemoptysis")
        dyspnea = st.checkbox("Dyspnea")

    with st.expander("GI / Hepatic", expanded=True):
        abdominal_pain = st.checkbox("Abdominal pain")
        diarrhea = st.checkbox("Diarrhea")
        ruq_pain = st.checkbox("RUQ pain / hepatodynia")

    with st.expander("MSK", expanded=True):
        arthralgia = st.checkbox("Arthralgia")
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

    # --- Exposures / Risks ---
    st.header("Exposures and Risks")

    with st.expander("Animals and environment", expanded=True):
        cats = st.checkbox("Cat exposure")
        livestock = st.checkbox("Livestock/farm animals")
        bird_bat = st.checkbox("Bird/bat or cave exposure")
        unpasteurized_dairy = st.checkbox("Unpasteurized dairy")
        rural = st.checkbox("Rural or farm living")
# ================================================================
# DIFFERENTIAL DISPLAY (CATEGORY BLOCKS)
# ================================================================

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
        st.markdown(f"**{dx['dx']}**")
        if dx["reasons"]:
            r = ", ".join(sorted(dx["reasons"]))
            st.markdown(f"Triggers: {r}")
        st.markdown("</div>", unsafe_allow_html=True)



# ================================================================
# MAIN LAYOUT
# ================================================================

st.title("ID-CDSS | FUO Engine v3")

if run:

    # ------------------------------
    # Build positives list
    # ------------------------------
    positives = []

    # ROS
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

    # Exposures
    if cats: positives.append("Cats")
    if livestock: positives.append("Livestock exposure")
    if bird_bat: positives.append("Bird/bat exposure")
    if unpasteurized_dairy: positives.append("Unpasteurized dairy")
    if rural: positives.append("Rural living")
    if body_lice: positives.append("Body lice")
    if ivdu: positives.append("IV drug use")
    if homeless: positives.append("Homelessness/incarceration")
    if tb_contact: positives.append("TB exposure")
    if high_tb_travel: positives.append("High TB burden travel")

    if missouri: positives.append("Missouri/Ohio River Valley")
    if sw_us: positives.append("US Southwest travel")

    # Add transplant metadata
    if immune == "Transplant":
        if transplant_type:
            positives.append(f"{transplant_type} transplant")
        if ebv_status == "Positive":
            positives.append("EBV positive")


    # -------------------------------------
    # Build differential + orders
    # -------------------------------------
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
        "transplant_type": transplant_type,
        "ebv_status": ebv_status
    }

    active = build_differential(inputs)
    orders = build_orders(active, prior_neg)
    note_text = build_note(inputs, active, orders)

    # ============================================================
    # 2-column layout for differential + plan
    # ============================================================
    col1, col2 = st.columns(2)

    # ---------------------------
    # LEFT COLUMN — Differential
    # ---------------------------
    with col1:
        if has_faget(tmax, hr):
            st.markdown("<div class='dx-block noninf'><b>Relative bradycardia detected (possible Faget sign)</b></div>",
                        unsafe_allow_html=True)

        st.subheader("Weighted Differential by Category")

        if not active:
            st.write("No specific FUO patterns triggered.")
        else:
            cat_order = ["Infectious", "Endemic", "Immunocompromised", "Rheumatologic", "Malignancy", "Noninfectious"]
            grouped = {c: [] for c in cat_order}

            for dx in active:
                grouped[dx["cat"]].append(dx)

            for cat in cat_order:
                if grouped[cat]:
                    st.markdown(f"### {cat}")
                    for dx in grouped[cat]:
                        render_dx_block(dx)

    # ---------------------------
    # RIGHT COLUMN — Plan
    # ---------------------------
    with col2:
        st.subheader("Staged Workup")

        # Baseline
        st.markdown("**Baseline studies**")
        for o in sorted(orders[0]):
            st.markdown(f"- [ ] {o}")

        # Targeted labs
        if orders[1]:
            st.markdown("**Targeted laboratory evaluation**")
            for o in sorted(orders[1]):
                st.markdown(f"- [ ] {o}")

        # Imaging
        if orders[2]:
            st.markdown("**Imaging**")
            for o in sorted(orders[2]):
                st.markdown(f"- [ ] {o}")

        # Invasive / advanced
        if orders[3]:
            st.markdown("**Advanced diagnostics**")
            for o in sorted(orders[3]):
                st.markdown(f"- [ ] {o}")

        st.subheader("Consult Note Draft")
        st.text_area("", note_text, height=350)

        st.download_button(
            "Download note as .txt",
            note_text,
            file_name=f"FUO_consult_{datetime.date.today().isoformat()}.txt",
            mime="text/plain"
        )

