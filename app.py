import streamlit as st
import datetime

# ================================================================
# CONFIG
# ================================================================

st.set_page_config(
    page_title="ID-CDSS | FUO Engine v3",
    layout="wide"
)

# ================================================================
# CSS STYLING
# ================================================================

st.markdown("""
<style>
    .dx-block {
        padding: 8px 12px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .infectious { border-left: 6px solid #198754; background-color: #e9f7ef; }
    .endemic { border-left: 6px solid #fd7e14; background-color: #fff4e6; }
    .immuno { border-left: 6px solid #0dcaf0; background-color: #e8f9ff; }
    .rheum { border-left: 6px solid #6f42c1; background-color: #f3e8ff; }
    .malignancy { border-left: 6px solid #d63384; background-color: #ffe6f0; }
    .noninf { border-left: 6px solid #6c757d; background-color: #f8f9fa; }

    .score-dots {
        float: right; 
        font-size: 16px; 
        letter-spacing: 2px;
    }
</style>
""", unsafe_allow_html=True)


# ================================================================
# HELPERS
# ================================================================

def has_faget(tmax_f, hr):
    return tmax_f >= 102 and hr < 100

def neuro_flag(positives):
    return (
        ("Headache" in positives and "Vision changes" in positives)
        or ("Seizures" in positives)
    )

SHORT_NAME = {
    "Tuberculosis (miliary or extrapulmonary)": "TB",
    "Disseminated histoplasmosis": "Histo",
    "Blastomycosis": "Blasto",
    "Coccidioidomycosis": "Cocci",
    "Cryptococcosis (fungemia or early dissemination)": "Crypto",
    "Cryptococcal meningitis": "Crypto meningitis",
    "Disseminated MAC": "MAC",
    "Inflammatory bowel disease (IBD flare)": "IBD flare",
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

def dots(score, max_score=5):
    filled = "●" * min(score, max_score)
    empty = "○" * (max_score - min(score, max_score))
    return filled + empty


# ================================================================
# DISEASE DATABASE
# ================================================================

DISEASES = [

    # -------------------------------------------------------------
    # INFECTIOUS
    # -------------------------------------------------------------
    {
        "dx": "Infective endocarditis",
        "cat": "Infectious",
        "triggers": ["New murmur", "IV drug use", "Embolic phenomena", "Prosthetic valve"],
        "orders": [
            ("Blood cultures x3", 0),
            ("TTE", 1),
            ("TEE if concern persists after TTE", 3)
        ]
    },

    {
        "dx": "Tuberculosis (miliary or extrapulmonary)",
        "cat": "Infectious",
        "triggers": [
            "Weight loss", "Night sweats",
            "Chronic cough", "Hemoptysis",
            "TB exposure", "Homelessness/incarceration",
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
        "orders": [("LP with CSF studies (if meningitis signs)", 3)]
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
        "triggers": [
            "Unpasteurized dairy", "Livestock exposure",
            "Back pain", "Night sweats",
            "Travel Mediterranean/Mexico"
        ],
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

    # -------------------------------------------------------------
    # ENDEMIC MYCOSES
    # -------------------------------------------------------------
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
        "triggers": ["Missouri/Ohio River Valley", "Skin nodules/lesions",
                     "Chronic cough", "Weight loss"],
        "orders": [("Serum Blastomyces antibody", 1)]
    },

    {
        "dx": "Coccidioidomycosis",
        "cat": "Endemic",
        "triggers": ["US Southwest travel", "Night sweats", "Weight loss", "Chronic cough"],
        "orders": [("Coccidioides serologic cascade (IgG/IgM/CF)", 1)]
    },

    # -------------------------------------------------------------
    # IMMUNOCOMPROMISED
    # -------------------------------------------------------------
    {
        "dx": "Disseminated MAC",
        "cat": "Immunocompromised",
        "requires_hiv": True,
        "triggers": ["HIV", "Night sweats", "Weight loss", "Diarrhea"],
        "soft_triggers_transplant": ["Lung"],
        "orders": [
            ("AFB blood culture", 1),
            ("CT abdomen/pelvis (nodes, organomegaly)", 2)
        ]
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

    # -------------------------------------------------------------
    # RHEUM
    # -------------------------------------------------------------
    {
        "dx": "Temporal arteritis (GCA)",
        "cat": "Rheumatologic",
        "requires_age_min": 50,
        "triggers": ["Headache", "Jaw claudication", "Vision changes"],
        "orders": [
            ("ESR", 0),
            ("CRP", 0),
            ("Temporal artery ultrasound (if ESR/CRP elevated)", 3)
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

    # -------------------------------------------------------------
    # MALIGNANCY / NONINF
    # -------------------------------------------------------------
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
        "dx": "Inflammatory bowel disease (IBD flare)",
        "cat": "Noninfectious",
        "triggers": [
            "Abdominal pain",
            "Diarrhea",
            "Weight loss",
            "Transaminitis"
        ],
        "orders": [
            ("CRP", 0),
            ("Stool calprotectin", 1),
            ("CT abdomen/pelvis with contrast or MR enterography", 2),
            ("GI consult", 3)
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

BASELINE_ORDERS = ["CBC with differential", "CMP", "ESR", "CRP", "Urinalysis"]


# ================================================================
# PRIOR TEST NORMALIZATION MAP
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
# DIFFERENTIAL ENGINE (with corrected MAC gating + sorting)
# ================================================================

def build_differential(inputs):

    positives = set(inputs["positives"])
    age = inputs["age"]
    immune = inputs["immune"]
    cd4 = inputs.get("cd4")
    transplant_type = inputs.get("transplant_type")
    ebv_status = inputs.get("ebv_status")

    risk_hiv = immune == "HIV"
    risk_tx = immune == "Transplant"

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

        # Standard trigger matching
        for t in d["triggers"]:
            if t in positives:
                score += 1
                reasons.append(t)

        # Age gate
        if d.get("requires_age_min") and age < d["requires_age_min"]:
            continue

        # HIV gate
        if d.get("requires_hiv") and not risk_hiv:
            continue

        # Neuro gate
        if d.get("requires_neuro") and not neuro_flag(positives):
            continue

        # Transplant gate
        if d.get("requires_transplant") and not risk_tx:
            continue

        # Soft transplant boosts
        if risk_tx and transplant_type in d.get("soft_triggers_transplant", []):
            score += 1
            reasons.append(f"{transplant_type} transplant")

        # Corrected MAC gating
        if d["dx"] == "Disseminated MAC":
            allow_mac = False
            if risk_hiv and cd4 is not None and cd4 < 50:
                allow_mac = True
            if risk_tx and transplant_type == "Lung":
                allow_mac = True
            if not allow_mac:
                continue

        if score > 0:
            active.append({
                "dx": d["dx"],
                "cat": d["cat"],
                "score": score,
                "reasons": reasons,
                "orders": d["orders"]
            })

    # descending sort
    active.sort(key=lambda x: x["score"], reverse=True)
    return active


# ================================================================
# HELPER: score lookup
# ================================================================

def score_for(active_list, diagnosis):
    for item in active_list:
        if item["dx"] == diagnosis:
            return item["score"]
    return 0


# ================================================================
# ORDER ENGINE
# ================================================================

def build_orders(active, prior_neg):
    orders_by_tier = {0: set(BASELINE_ORDERS), 1: set(), 2: set(), 3: set()}

    for item in active:
        for order, tier in item["orders"]:
            orders_by_tier[tier].add(order)

    # Remove prior-neg equivalents
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
    today = datetime.date.today().isoformat()
    age = inputs["age"]
    sex = inputs["sex"]

    lines = []
    lines.append(f"Date: {today}")
    # Immune-status descriptor for note
    immune_text = ""
    
    if inputs["immune"] == "HIV" and inputs["cd4"] is not None:
        immune_text = f" with HIV (CD4 {inputs['cd4']})"
    
    elif inputs["immune"] == "Transplant" and inputs["transplant_type"]:
        if inputs.get("time_since_tx") is not None:
            immune_text = (
                f" with {inputs['transplant_type'].lower()} transplant "
                f"{inputs['time_since_tx']} months ago"
            )
        else:
            immune_text = (
                f" with {inputs['transplant_type'].lower()} transplant"
            )
            
    elif inputs["immune"] in ["Biologics", "Chemotherapy"]:
        immune_text = f" on {inputs['immune'].lower()}"

# Final line
    lines.append(
        f"{age} year old {sex}{immune_text} with prolonged fever without a clear source."
    )

    lines.append(
        f"Tmax {inputs['tmax']} F with heart rate {inputs['hr']} bpm at peak. "
        f"Fever has been present for {inputs['fever_days']} days."
    )

    if neuro_flag(inputs["positives"]):
        lines.append("Neurologic symptoms present; consider CNS involvement based on overall course.")

    if has_faget(inputs["tmax"], inputs["hr"]):
        lines.append("Relative bradycardia present.")

    if inputs["positives"]:
        lines.append("Features include: " + ", ".join(sorted(inputs["positives"])) + ".")

    if inputs["prior_neg"]:
        lines.append("Prior negative workup: " + ", ".join(inputs["prior_neg"]) + ".")

    lines.append("")
    lines.append("Assessment and differential:")

    # Category grouping
    grouped = {}
    for dx in active:
        grouped.setdefault(dx["cat"], []).append(dx)

    strong = [short_name(active[0]["dx"])] if active else []
    possible = [short_name(d["dx"]) for d in active[1:4]]
    unlikely = [short_name(d["dx"]) for d in active[4:8]]

    if strong:
        lines.append(f"Most consistent with {strong[0]} based on current findings.")
    if possible:
        lines.append(f"Other possible etiologies include: {', '.join(possible)}.")
    if unlikely:
        lines.append(f"Less likely considerations: {', '.join(unlikely)}.")

    lines.append("")
    lines.append("Plan:")

    # TIER 0
    lines.append("Baseline studies:")
    for o in sorted(orders[0]):
        lines.append(f"- [ ] {o}")

    # TIER 1
    if orders[1]:
        lines.append("")
        lines.append("Targeted testing:")
        for o in sorted(orders[1]):
            lines.append(f"- [ ] {o}")

    # TIER 2
    if orders[2]:
        lines.append("")
        lines.append("Imaging:")
        for o in sorted(orders[2]):
            lines.append(f"- [ ] {o}")

    # TIER 3
    if orders[3]:
        lines.append("")
        lines.append("Advanced diagnostics:")
        for o in sorted(orders[3]):
            lines.append(f"- [ ] {o}")

    return "\n".join(lines)
# ================================================================
# SIDEBAR UI — all inputs, no duplicate keys
# ================================================================

with st.sidebar:

    st.title("FUO Engine v3")

    # Clear button
    if st.button("Clear all inputs", key="btn_clear_all"):
        for k in list(st.session_state.keys()):
            if k.startswith("ui_") or k.startswith("btn_"):
                del st.session_state[k]
        st.experimental_rerun()

    # ------------------------------------------------------------
    # Patient data
    # ------------------------------------------------------------
    st.header("Patient Data")
    c1, c2 = st.columns(2)

    age = c1.number_input("Age", 18, 100, 55, key="ui_age")
    sex = c2.selectbox("Sex", ["Female", "Male"], key="ui_sex")

    immune = st.selectbox(
        "Immune status",
        ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"],
        key="ui_immune"
    )

    cd4 = None
    transplant_type = None
    time_since_tx = None
    ebv_status = None

    if immune == "HIV":
        cd4 = st.slider("CD4 count", 0, 1200, 300, key="ui_cd4")

    if immune == "Transplant":
        with st.expander("Transplant details", expanded=True):
            transplant_type = st.selectbox(
                "Type of transplant",
                ["Kidney", "Liver", "Lung", "Heart", "HSCT"],
                key="ui_tx_type"
            )
            time_since_tx = st.number_input(
                "Time since transplant (months)",
                0, 600, 12,
                key="ui_tx_months"
            )
            ebv_status = st.selectbox(
                "EBV status",
                ["Unknown", "Positive", "Negative"],
                key="ui_ebv"
            )

    # ------------------------------------------------------------
    # Fever profile
    # ------------------------------------------------------------
    st.header("Fever Profile")
    tmax = st.number_input("Tmax (F)", 98.0, 107.0, 101.5, step=0.1, key="ui_tmax")
    hr = st.number_input("Heart rate at Tmax", 40, 170, 95, key="ui_hr")
    fever_days = st.number_input("Days of fever", 1, 365, 14, key="ui_fever_days")
    on_abx = st.checkbox("On antibiotics", key="ui_on_abx")

    # ------------------------------------------------------------
    # Symptoms (ROS)
    # ------------------------------------------------------------
    st.header("Symptoms (ROS)")

    with st.expander("Constitutional", expanded=True):
        night_sweats = st.checkbox("Night sweats", key="ui_ns")
        weight_loss = st.checkbox("Weight loss", key="ui_wl")
        fatigue = st.checkbox("Fatigue", key="ui_fat")

    with st.expander("Neurologic", expanded=True):
        headache = st.checkbox("Headache", key="ui_hx")
        vision_changes = st.checkbox("Vision changes", key="ui_vc")
        seizures = st.checkbox("Seizures", key="ui_sz")
        jaw_claudication = st.checkbox("Jaw claudication", key="ui_jc")

    with st.expander("Respiratory", expanded=True):
        chronic_cough = st.checkbox("Chronic cough", key="ui_cc")
        hemoptysis = st.checkbox("Hemoptysis", key="ui_hemo")
        dyspnea = st.checkbox("Dyspnea", key="ui_dysp")

    with st.expander("GI / Hepatic", expanded=True):
        abdominal_pain = st.checkbox("Abdominal pain", key="ui_abd")
        diarrhea = st.checkbox("Diarrhea", key="ui_diarr")
        ruq_pain = st.checkbox("RUQ pain / hepatodynia", key="ui_ruq")

    with st.expander("MSK", expanded=True):
        arthralgia = st.checkbox("Arthralgia", key="ui_arth")
        back_pain = st.checkbox("Back pain", key="ui_bp")
        myalgia = st.checkbox("Myalgias", key="ui_myalg")

    with st.expander("Skin findings", expanded=True):
        rash = st.checkbox("Rash", key="ui_rash")
        palmar_rash = st.checkbox("Palms/soles rash", key="ui_palms")
        nodules = st.checkbox("Skin nodules/lesions", key="ui_nod")

    with st.expander("Lymph / Heme", expanded=True):
        lymphadenopathy = st.checkbox("Lymphadenopathy", key="ui_lad")
        splenomegaly = st.checkbox("Splenomegaly", key="ui_spl")
        pancytopenia = st.checkbox("Pancytopenia", key="ui_pan")

    # ------------------------------------------------------------
    # *** NEW: Cardiac findings ***
    # ------------------------------------------------------------
    with st.expander("Cardiac findings", expanded=True):
        new_murmur = st.checkbox("New murmur", key="ui_new_murmur")
        emboli = st.checkbox("Embolic phenomena", key="ui_emboli")
        prosthetic_valve = st.checkbox("Prosthetic valve", key="ui_pv")
        rel_brady_ck = st.checkbox("Relative bradycardia (manual)", key="ui_relbrady")

    # ------------------------------------------------------------
    # *** NEW: Lab abnormalities ***
    # ------------------------------------------------------------
    with st.expander("Lab abnormalities", expanded=True):
        ferritin_high = st.checkbox("Ferritin > 1000", key="ui_ferritin")
        eosinophilia = st.checkbox("Eosinophilia", key="ui_eos")
        leukopenia = st.checkbox("Leukopenia", key="ui_leuk")
        transaminitis = st.checkbox("Transaminitis", key="ui_trans")

    # ------------------------------------------------------------
    # *** NEW: Recent drug exposures ***
    # ------------------------------------------------------------
    with st.expander("Recent drug exposures", expanded=True):
        new_beta = st.checkbox("New beta-lactam", key="ui_new_beta")
        new_anti = st.checkbox("New anticonvulsant", key="ui_new_anti")
        new_sulfa = st.checkbox("New sulfa", key="ui_new_sulfa")

    # ------------------------------------------------------------
    # Exposures (Animals, TB, Geography)
    # ------------------------------------------------------------
    st.header("Exposures and Risks")

    with st.expander("Animals / Environment", expanded=True):
        cats = st.checkbox("Cat exposure", key="ui_cats")
        livestock = st.checkbox("Livestock / farm animals", key="ui_live")
        bird_bat = st.checkbox("Bird/bat exposure", key="ui_bb")
        unpasteurized_dairy = st.checkbox("Unpasteurized dairy", key="ui_dairy")
        rural = st.checkbox("Rural living", key="ui_rural")
        body_lice = st.checkbox("Body lice", key="ui_lice")

    with st.expander("Social / TB Risk", expanded=True):
        ivdu = st.checkbox("IV drug use", key="ui_ivdu")
        homeless = st.checkbox("Homelessness/incarceration", key="ui_hl")
        tb_contact = st.checkbox("TB exposure", key="ui_tbexp")
        high_tb_travel = st.checkbox("High TB burden travel", key="ui_tbtravel")

    with st.expander("Geography", expanded=True):
        missouri = st.checkbox("Missouri / Ohio River Valley", key="ui_mo")
        sw_us = st.checkbox("US Southwest travel", key="ui_swus")

    # ------------------------------------------------------------
    # Prior negatives
    # ------------------------------------------------------------
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
        ],
        key="ui_priorneg"
    )

    run = st.button("Generate FUO Plan", key="btn_run_fuo")


# ================================================================
# MAIN PANEL — build positives, run engine, safety flags
# ================================================================

st.title("ID-CDSS | FUO Engine v3")

if run:

    positives = []

    # ROS
    if night_sweats: positives.append("Night sweats")
    if weight_loss: positives.append("Weight loss")
    if fatigue: positives.append("Fatigue")

    if headache: positives.append("Headache")
    if vision_changes: positives.append("Vision changes")
    if seizures: positives.append("Seizures")
    if jaw_claudication: positives.append("Jaw claudication")

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

    # Cardiac
    if new_murmur: positives.append("New murmur")
    if emboli: positives.append("Embolic phenomena")
    if prosthetic_valve: positives.append("Prosthetic valve")
    if rel_brady_ck: positives.append("Relative bradycardia")

    # Lab abnormalities
    if ferritin_high: positives.append("Ferritin > 1000")
    if eosinophilia: positives.append("Eosinophilia")
    if leukopenia: positives.append("Leukopenia")
    if transaminitis: positives.append("Transaminitis")

    # Drug exposures
    if new_beta: positives.append("New beta-lactam")
    if new_anti: positives.append("New anticonvulsant")
    if new_sulfa: positives.append("New sulfa")

    # Exposures
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

    # ------------------------------------------------------------
    # Automatic relative bradycardia trigger (Option C)
    # ------------------------------------------------------------
    if has_faget(tmax, hr) and "Relative bradycardia" not in positives:
        positives.append("Relative bradycardia")

    # ------------------------------------------------------------
    # Build engine inputs
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # SAFETY FLAGS
    # ------------------------------------------------------------

    if neuro_flag(positives) and cd4 and cd4 < 100:
        st.error("⚠️ URGENT: Neuro symptoms + CD4 < 100. Consider emergent LP for cryptococcal meningitis.")

    if "Prosthetic valve" in positives and score_for(active, "Infective endocarditis") > 0:
        st.warning("⚠️ Prosthetic valve endocarditis: Consider early TEE rather than TTE.")

    # ------------------------------------------------------------
    # LAYOUT
    # ------------------------------------------------------------
    col1, col2 = st.columns(2)

    # ------------------------------------------------------------
    # Differential
    # ------------------------------------------------------------
    with col1:
        if has_faget(tmax, hr):
            st.markdown("<div class='dx-block noninf'><b>Relative bradycardia detected.</b></div>", unsafe_allow_html=True)

        st.subheader("Weighted Differential (Grouped)")

        if not active:
            st.write("No specific FUO syndromes triggered.")
        else:
            cat_order = ["Infectious", "Endemic", "Immunocompromised", "Rheumatologic", "Malignancy", "Noninfectious"]
            grouped = {cat: [] for cat in cat_order}

            for dx in active:
                grouped[dx["cat"]].append(dx)

            css_map = {
                "Infectious": "infectious",
                "Endemic": "endemic",
                "Immunocompromised": "immuno",
                "Rheumatologic": "rheum",
                "Malignancy": "malignancy",
                "Noninfectious": "noninf"
            }

            for cat in cat_order:
                if grouped[cat]:
                    st.markdown(f"### {cat}")
                    for dx in grouped[cat]:
                        cls = css_map[dx["cat"]]

                        st.markdown(
                            f"<div class='dx-block {cls}'>"
                            f"<b>{dx['dx']}</b>"
                            f"<span class='score-dots'>{dots(dx['score'])}</span>"
                            f"<br>Triggers: {', '.join(dx['reasons'])}"
                            f"</div>",
                            unsafe_allow_html=True
                        )

    # ------------------------------------------------------------
    # Workup + note
    # ------------------------------------------------------------
    with col2:
        note_text = build_note(inputs, active, orders)

        st.subheader("Consult Note Draft")
        st.text_area("Note", note_text, height=380, key="ui_note_text")

        st.download_button(
            "Download note as .txt",
            data=note_text,
            file_name=f"FUO_consult_{datetime.date.today().isoformat()}.txt",
            mime="text/plain",
            key="btn_download_note"
        )
