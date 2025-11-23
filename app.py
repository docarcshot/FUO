import streamlit as st
import datetime

st.set_page_config(page_title="ID-CDSS | FUO Engine v1", layout="wide")

st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .critical { border-left: 6px solid #dc3545; padding: 10px; background-color: #ffe6e6; font-weight: bold; }
    .noninf { border-left: 6px solid #17a2b8; padding: 10px; background-color: #e0f7fa; }
    .endo { border-left: 6px solid #fd7e14; padding: 10px; background-color: #fff3cd; }
</style>
""", unsafe_allow_html=True)

def has_faget(tmax_f, hr):
    return tmax_f >= 102.0 and hr < 100

PRIOR_MAP = {
    "Negative blood cultures": ["Blood cultures x2", "Blood cultures x3", "Blood cultures (hold 21d)"],
    "Negative TB testing": ["Quantiferon TB", "T-Spot TB"],
    "Negative Histo antigen": ["Urine Histoplasma antigen", "Serum Histoplasma antibody"],
    "Negative Bartonella serology": ["Bartonella serology"],
    "Negative Brucella serology": ["Brucella serology"],
    "Negative HIV": ["HIV 1/2 Ag/Ab (4th gen)"],
    "Normal CT chest/abd/pelvis": ["CT chest/abdomen/pelvis with contrast"],
    "Normal echocardiogram": ["TTE", "TEE"],
}

DISEASES = [
    {
        "dx": "Infective endocarditis",
        "category": "Infectious",
        "triggers": ["New murmur", "IV drug use", "Prosthetic valve", "Embolic phenomena"],
        "min_fever_days": 5,
        "orders": [("Blood cultures x3", 0), ("TTE", 2), ("TEE", 3)],
    },
    {
        "dx": "Tuberculosis (miliary or extrapulmonary)",
        "category": "Infectious",
        "triggers": ["Weight loss", "Night sweats", "Chronic cough", "Hemoptysis", "TB exposure",
                     "Homelessness/incarceration", "High TB burden travel"],
        "min_fever_days": 14,
        "orders": [("Quantiferon TB", 1), ("AFB smear x3", 1),
                   ("CT chest/abdomen/pelvis with contrast", 2)],
    },
    {
        "dx": "Disseminated histoplasmosis",
        "category": "Infectious",
        "triggers": ["Bird/bat exposure", "Cave exposure", "Missouri/Ohio River Valley",
                     "Pancytopenia", "Splenomegaly", "Oral ulcers"],
        "min_fever_days": 7,
        "orders": [("Urine Histoplasma antigen", 1), ("Serum Histoplasma antibody", 1),
                   ("Ferritin", 1), ("Serum Blastomyces antibody", 1)],
    },
    {
        "dx": "Bartonella (endocarditis/bacteremia)",
        "category": "Infectious",
        "triggers": ["Cats", "Homelessness/incarceration", "Body lice", "IV drug use"],
        "min_fever_days": 7,
        "orders": [("Bartonella serology", 1)],
    },
    {
        "dx": "Brucellosis",
        "category": "Infectious",
        "triggers": ["Unpasteurized dairy", "Livestock exposure", "Travel Mediterranean/Mexico",
                     "Back pain", "Night sweats"],
        "min_fever_days": 7,
        "orders": [("Brucella serology", 1), ("Blood cultures (hold 21d)", 0)],
    },
    {
        "dx": "Q fever (Coxiella)",
        "category": "Infectious",
        "triggers": ["Farm animals", "Parturient animals", "Rural living", "Well water"],
        "min_fever_days": 7,
        "orders": [("Coxiella serology", 1), ("TTE", 2)],
    },
    {
        "dx": "Cryptococcosis (meningitis/disseminated)",
        "category": "Infectious",
        "triggers": ["Headache", "Vision changes", "HIV", "Biologics", "Chemotherapy"],
        "min_fever_days": 5,
        "orders": [("Serum cryptococcal antigen", 1), ("Consider LP with CSF CrAg", 3)],
    },
    {
        "dx": "Disseminated MAC",
        "category": "Infectious",
        "triggers": ["HIV", "Night sweats", "Weight loss", "Diarrhea"],
        "min_fever_days": 14,
        "orders": [("AFB blood culture", 1),
                   ("CT abdomen/pelvis (nodes, organomegaly)", 2)],
    },
    {
        "dx": "Temporal arteritis (GCA)",
        "category": "Non-infectious",
        "triggers": ["Age > 50", "Headache", "Jaw claudication", "Vision changes"],
        "min_fever_days": 3,
        "orders": [("ESR", 0), ("CRP", 0),
                   ("Temporal artery ultrasound", 2)],
    },
    {
        "dx": "Adult Still disease",
        "category": "Non-infectious",
        "triggers": ["Arthralgia", "Rash", "Ferritin > 1000", "Night sweats"],
        "min_fever_days": 7,
        "orders": [("Ferritin", 0)],
    },
    {
        "dx": "Lymphoma or other occult malignancy",
        "category": "Non-infectious",
        "triggers": ["Weight loss", "Night sweats", "Lymphadenopathy", "Splenomegaly"],
        "min_fever_days": 14,
        "orders": [("LDH", 1),
                   ("CT chest/abdomen/pelvis with contrast", 2)],
    },
]

BASELINE_ORDERS = [
    "CBC with differential",
    "CMP",
    "ESR",
    "CRP",
    "Urinalysis",
]
def build_differential(inputs):
    positives = list(inputs["positives"])
    fever_days = inputs["fever_days"]
    immune = inputs["immune"]
    cd4 = inputs.get("cd4")
    age = inputs["age"]

    risk_hiv = immune == "HIV"
    risk_transplant = immune == "Transplant"
    risk_immunosupp = immune in ["HIV", "Transplant", "Biologics", "Chemotherapy"]

    if risk_hiv:
        positives.append("HIV")
        if cd4 is not None and cd4 < 250:
            positives.append("CD4 < 250")
        if cd4 is not None and cd4 < 100:
            positives.append("CD4 < 100")

    active = []

    for d in DISEASES:
        score = 0
        reasons = []

        for t in d["triggers"]:
            if t in positives:
                score += 1
                reasons.append(t)

        min_days = d.get("min_fever_days", 0)
        if fever_days >= min_days:
            score += 1
            reasons.append(f"Fever ≥ {min_days} days")
        else:
            score -= 1

        if d["dx"] == "Cryptococcosis (meningitis/disseminated)":
            if risk_immunosupp:
                score += 1
                reasons.append("Immunosuppressed")
            if cd4 is not None and cd4 < 200:
                score += 1
                reasons.append("CD4 < 200")

        if d["dx"] == "Disseminated MAC":
            if not risk_hiv:
                continue
            if cd4 is not None and cd4 < 100:
                score += 1
                reasons.append("CD4 < 100")
            if fever_days < 14:
                score -= 1

        if d["dx"] == "Temporal arteritis (GCA)":
            if age < 50:
                continue

        if score > 0:
            active.append({
                "dx": d["dx"],
                "category": d["category"],
                "score": score,
                "reasons": reasons,
                "orders": d["orders"],
            })

    infectious = [x for x in active if x["category"] == "Infectious"]
    noninfectious = [x for x in active if x["category"] != "Infectious"]

    infectious.sort(key=lambda x: x["score"], reverse=True)
    noninfectious.sort(key=lambda x: x["score"], reverse=True)

    return infectious + noninfectious


def build_orders(active, prior_neg, include_rheum):
    orders_by_tier = {0: set(BASELINE_ORDERS), 1: set(), 2: set(), 3: set()}

    for item in active:
        for order_name, tier in item["orders"]:
            orders_by_tier[tier].add(order_name)

    already_done = set()
    for label in prior_neg:
        mapped = PRIOR_MAP.get(label, [])
        already_done.update(mapped)

    for tier in orders_by_tier:
        newset = set()
        for o in orders_by_tier[tier]:
            if not any(done in o for done in already_done):
                newset.add(o)
        orders_by_tier[tier] = newset

    if include_rheum:
        orders_by_tier[1].add("ANA")
        orders_by_tier[1].add("RF")
        orders_by_tier[1].add("CCP antibody")
        orders_by_tier[1].add("ENA reflex panel")
        orders_by_tier[2].add("Temporal artery ultrasound")

    return orders_by_tier


def build_note(inputs, active, orders_by_tier):
    lines = []
    today = datetime.date.today().isoformat()
    age = inputs["age"]
    sex = inputs["sex"]
    immune = inputs["immune"]
    cd4 = inputs.get("cd4")
    tmax = inputs["tmax"]
    hr = inputs["hr"]
    fever_days = inputs["fever_days"]
    positives = inputs["positives"]

    lines.append(f"Date: {today}")
    if immune != "Immunocompetent":
        lines.append(f"{age} year old {sex} with fever of unknown origin with {immune.lower()}.")
    else:
        lines.append(f"{age} year old {sex} with fever of unknown origin.")

    lines.append(f"Fever reported for {fever_days} days, Tmax {tmax} F, HR at Tmax {hr} bpm.")

    if has_faget(tmax, hr):
        lines.append("Vitals notable for relative bradycardia (Faget sign).")

    if positives:
        lines.append("Key history and exam features: " + ", ".join(sorted(set(positives))) + ".")
    else:
        lines.append("No focal symptoms or high risk exposures elicited.")

    if inputs["prior_neg"]:
        prior_clean = ", ".join(inputs["prior_neg"])
        lines.append(f"Prior negative workup includes: {prior_clean}.")

    lines.append("")
    lines.append("Assessment and differential:")

    if not active:
        lines.append("- Persistent FUO with no strong syndromic signals at this stage.")
    else:
        for dx in active[:8]:
            r = ", ".join(sorted(set(dx["reasons"]))) if dx["reasons"] else "clinical context"
            lines.append(f"- {dx['dx']} ({dx['category']}): supported by {r}.")

    lines.append("")
    lines.append("Plan:")

    if orders_by_tier[0]:
        lines.append("Baseline and immediate tests:")
        for o in sorted(orders_by_tier[0]):
            lines.append(f"- [ ] {o}")

    if orders_by_tier[1]:
        lines.append("")
        lines.append("Targeted laboratories and serologies:")
        for o in sorted(orders_by_tier[1]):
            lines.append(f"- [ ] {o}")

    if orders_by_tier[2]:
        lines.append("")
        lines.append("Structural imaging:")
        for o in sorted(orders_by_tier[2]):
            lines.append(f"- [ ] {o}")

    if orders_by_tier[3]:
        lines.append("")
        lines.append("Advanced or invasive diagnostics (second-line):")
        for o in sorted(orders_by_tier[3]):
            lines.append(f"- [ ] {o}")

    if immune != "HIV" and "Negative HIV" not in inputs["prior_neg"]:
        lines.append("")
        lines.append("If HIV screening is positive or CD4 low, evaluate for disseminated MAC.")

    return "\n".join(lines)
st.title("ID-CDSS | FUO Engine")

with st.sidebar:
    st.title("FUO Engine")

    if st.button("Clear all inputs"):
        st.session_state.clear()
        st.experimental_rerun()

    st.header("Patient data")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 55)
    sex = c2.selectbox("Sex", ["Female", "Male"])
    immune = st.selectbox(
        "Immune status",
        ["Immunocompetent", "HIV", "Transplant", "Biologics", "Chemotherapy"],
    )

    cd4 = None
    tx_type = None
    tx_interval = None

    if immune == "HIV":
        cd4 = st.slider("CD4 count", 0, 1200, 300)

    if immune == "Transplant":
        tx_type = st.selectbox("Transplant organ", ["Kidney", "Liver", "Lung", "Heart", "HSCT"])
        tx_interval = st.selectbox(
            "Time since transplant",
            ["<1 month", "1–6 months", ">6 months"],
        )

    st.header("Fever profile")
    tmax = st.number_input("Tmax (F)", 98.0, 107.0, 101.5, step=0.1)
    hr = st.number_input("Heart rate at Tmax", 40, 160, 95)
    fever_days = st.number_input("Days of fever", 3, 365, 21)
    on_abx = st.checkbox("Currently on antibiotics")

    st.header("Symptoms (ROS)")

    st.subheader("Constitutional")
    cons_cols = st.columns(3)
    night_sweats = cons_cols[0].checkbox("Night sweats")
    weight_loss = cons_cols[1].checkbox("Weight loss")
    fatigue = cons_cols[2].checkbox("Fatigue")

    st.subheader("Neurologic")
    neuro_cols = st.columns(3)
    headache = neuro_cols[0].checkbox("Headache")
    vision_changes = neuro_cols[1].checkbox("Vision changes")
    seizures = neuro_cols[2].checkbox("Seizures")

    st.subheader("Respiratory")
    resp_cols = st.columns(3)
    chronic_cough = resp_cols[0].checkbox("Chronic cough")
    hemoptysis = resp_cols[1].checkbox("Hemoptysis")
    dyspnea = resp_cols[2].checkbox("Dyspnea")

    st.subheader("GI and hepatic")
    gi_cols = st.columns(3)
    abdominal_pain = gi_cols[0].checkbox("Abdominal pain")
    diarrhea = gi_cols[1].checkbox("Diarrhea")
    ruq_pain = gi_cols[2].checkbox("RUQ pain / hepatodynia")

    st.subheader("MSK")
    msk_cols = st.columns(3)
    arthralgia = msk_cols[0].checkbox("Joint pain")
    back_pain = msk_cols[1].checkbox("Back pain")
    myalgia = msk_cols[2].checkbox("Myalgias")

    st.subheader("Skin")
    skin_cols = st.columns(3)
    rash = skin_cols[0].checkbox("Rash")
    palmar_rash = skin_cols[1].checkbox("Palms/soles rash")
    nodules = skin_cols[2].checkbox("Skin nodules/lesions")

    st.subheader("Lymph/HEME")
    heme_cols = st.columns(3)
    lymphadenopathy = heme_cols[0].checkbox("Lymphadenopathy")
    splenomegaly = heme_cols[1].checkbox("Splenomegaly")
    pancytopenia = heme_cols[2].checkbox("Pancytopenia")

    st.header("Exposures and risks")

    st.subheader("Animals and environment")
    cats = st.checkbox("Cat exposure")
    livestock = st.checkbox("Livestock/farm animals")
    bird_bat = st.checkbox("Bird/bat or cave exposure")
    unpasteurized_dairy = st.checkbox("Unpasteurized dairy")
    rural = st.checkbox("Rural or farm living")
    body_lice = st.checkbox("Body lice")

    st.subheader("Social / TB risk")
    ivdu = st.checkbox("IV drug use")
    homeless = st.checkbox("Homelessness or incarceration")
    tb_contact = st.checkbox("TB exposure contact")
    high_tb_travel = st.checkbox("High TB burden country travel")

    st.subheader("Geography")
    missouri = st.checkbox("Missouri / Ohio River Valley")
    sw_us = st.checkbox("US Southwest travel")

    st.header("Prior workup (negative)")
    prior_neg = st.multiselect(
        "Mark studies already done and negative/normal",
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

    st.header("Rheumatologic evaluation")
    include_rheum = st.checkbox("Include rheumatologic labs", value=False)

run = st.button("Generate FUO plan")

if run:
    positives = []

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
    if nodules: positives.append("Skin nodules")

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
    if missouri: positives.append("Missouri/Ohio River Valley")
    if sw_us: positives.append("US Southwest travel")

    if ivdu: positives.append("IV drug use")
    if homeless: positives.append("Homelessness/incarceration")
    if tb_contact: positives.append("TB exposure")
    if high_tb_travel: positives.append("High TB burden travel")

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
    orders_by_tier = build_orders(active, prior_neg, include_rheum)
    note_text = build_note(inputs, active, orders_by_tier)

    col1, col2 = st.columns(2)

    with col1:
        if has_faget(tmax, hr):
            st.markdown(
                "<div class='critical'>Relative bradycardia detected (possible Faget sign).</div>",
                unsafe_allow_html=True,
            )
        st.subheader("Weighted differential (FUO-focused)")

        if not active:
            st.write("No specific FUO syndromes triggered.")
        else:
            for dx in active:
                if dx["category"] == "Non-infectious":
                    css_class = "noninf"
                elif dx["category"] == "Infectious" and dx["dx"] in [
                    "Disseminated histoplasmosis", "Cryptococcosis (meningitis/disseminated)",
                    "Disseminated MAC", "Q fever (Coxiella)", "Brucellosis",
                    "Bartonella (endocarditis/bacteremia)"
                ]:
                    css_class = "endo"
                else:
                    css_class = ""

                if css_class:
                    st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)

                st.markdown(f"**{dx['dx']}**")
                st.caption("Triggers: " + ", ".join(sorted(set(dx["reasons"]))))

                if css_class:
                    st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.subheader("Staged workup")

        st.markdown("<div class='tier0'>", unsafe_allow_html=True)
        st.markdown("**Tier 0 – baseline labs**")
        for o in sorted(orders_by_tier[0]):
            st.markdown(f"- [ ] {o}")
        st.markdown("</div><br>", unsafe_allow_html=True)

        if orders_by_tier[1]:
            st.markdown("<div class='tier1'>", unsafe_allow_html=True)
            st.markdown("**Tier 1 – targeted labs/serologies**")
            for o in sorted(orders_by_tier[1]):
                st.markdown(f"- [ ] {o}")
            st.markdown("</div><br>", unsafe_allow_html=True)

        if orders_by_tier[2]:
            st.markdown("<div class='tier2'>", unsafe_allow_html=True)
            st.markdown("**Tier 2 – structural imaging**")
            for o in sorted(orders_by_tier[2]):
                st.markdown(f"- [ ] {o}")
            st.markdown("</div><br>", unsafe_allow_html=True)

        if orders_by_tier[3]:
            st.markdown("<div class='tier3'>", unsafe_allow_html=True)
            st.markdown("**Tier 3 – advanced or invasive tests**")
            for o in sorted(orders_by_tier[3]):
                st.markdown(f"- [ ] {o}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("Consult note draft")
        st.text_area("Note", note_text, height=350)
        st.download_button(
            "Download note as .txt",
            data=note_text,
            file_name=f"FUO_consult_{datetime.date.today().isoformat()}.txt",
            mime="text/plain",
        )
