import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="ID-CDSS | Director Suite", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    .tier0 { border-left: 6px solid #000; padding: 10px; background-color: #f0f0f0; }
    .tier1 { border-left: 6px solid #28a745; padding: 10px; background-color: #e6fffa; }
    .tier2 { border-left: 6px solid #ffc107; padding: 10px; background-color: #fffbe6; }
    .tier3 { border-left: 6px solid #dc3545; padding: 10px; background-color: #fff1f0; }
    .alert { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DATABASE = [
    {
        "dx": "Drug-Induced Fever",
        "triggers": ["New Beta-Lactam", "New Anticonvulsant", "New Sulfa Drug", "Eosinophilia", "Relative Bradycardia"],
        "pearl": "Diagnosis of exclusion: typical onset ~7-10 days; resolves ~48-72 h after discontinuation.",
        "orders": [("Discontinue Suspect Agent (Washout)", 0)]
    },
    {
        "dx": "DRESS Syndrome",
        "triggers": ["New Anticonvulsant", "Allopurinol", "Rash (General)", "Eosinophilia", "Hepatodynia", "Lymphadenopathy"],
        "pearl": "Latency most often 2-6 weeks (though <2 wks possible); rash + eosinophilia + organ involvement typical.",
        "orders": [("CBC (Eosinophils)", 1), ("LFTs", 1), ("HHV-6 PCR", 1)]
    },
    {
        "dx": "Q Fever (Coxiella)",
        "triggers": ["Farm Animals", "Parturient Animals", "Wind/Dust"],
        "pearl": "Culture-neg endocarditis; “doughnut” granulomas.",
        "orders": [("Coxiella Serology", 1), ("TTE", 2)]
    },
    {
        "dx": "Brucellosis",
        "triggers": ["Unpasteurized Dairy", "Livestock", "Travel (Mexico/Med)"],
        "pearl": "Undulating fever. Spine osteomyelitis common.",
        "orders": [("Brucella Serology", 1), ("Blood Cx x3", 1)]
    },
    {
        "dx": "Bartonella",
        "triggers": ["Cats (Scratch/Bite)", "Homelessness (Lice)"],
        "pearl": "Culture-negative endocarditis in homeless/cat exposures.",
        "orders": [("Bartonella Serology", 1)]
    },
    {
        "dx": "Histoplasmosis (Dissem)",
        "triggers": ["Bird/Bat Droppings", "Spelunking", "Pancytopenia"],
        "pearl": "MO/Ohio endemic; can mimic adrenal insufficiency.",
        "orders": [("Urine/Serum Histo Ag", 1), ("Ferritin", 1)]
    },
    {
        "dx": "Temporal Arteritis (GCA)",
        "triggers": ["Jaw Claudication", "Vision Changes", "Age >50", "New Headache"],
        "pearl": "Emergency — high ESR/CRP.",
        "orders": [("ESR & CRP", 1), ("Temporal Artery US", 2), ("Temporal Artery Bx", 3)]
    },
    {
        "dx": "Infectious Endocarditis",
        "triggers": ["New Murmur", "Splinter Hemorrhages", "Prosthetic Valve", "IV Drug Use"],
        "pearl": "Duke Criteria; TEE preferred in prosthetic valve/IVDU.",
        "orders": [("Blood Cx x3", 0), ("TTE", 2), ("TEE", 3)]
    },
    {
        "dx": "Malignancy (Lymphoma/RCC)",
        "triggers": ["Weight Loss >10%", "Night Sweats", "Hematuria"],
        "pearl": "If infection work-up negative consider malignancy; naproxen test optional.",
        "orders": [("LDH", 1), ("CT Chest/Abd/Pelvis", 2), ("Naproxen Challenge", 1)]
    }
]

# --- LOGIC ENGINE ---
def get_plan(inputs):
    active_dx = []
    orders = {0: set(), 1: set(), 2: set(), 3: set()}

    # Universal baseline orders
    orders[0].add("Blood Cx x3")
    orders[0].add("HIV 1/2 Ag/Ab")
    orders[0].add("Syphilis IgG")
    orders[0].add("CBC, CMP, UA, ESR, CRP, Ferritin")

    for d in DATABASE:
        score = 0
        triggers = []
        for t in d["triggers"]:
            if t in inputs["all_positives"]:
                score += 1
                triggers.append(t)

        # Stricter gating: DRESS
        if d["dx"] == "DRESS Syndrome" and inputs["meds"]:
            days = inputs.get("days_since_new_med")
            if days is not None and 14 <= days <= 42:
                score += 2
            else:
                # require key features for weaker latency
                if not ("Rash (General)" in inputs["symptoms"] and "Eosinophilia" in inputs["symptoms"]):
                    score = 0
                    # keep pearl unchanged
                else:
                    d["pearl"] = "⚠️ Typical latency 2-8 weeks; clinical correlation required."

        # Drug-Induced Fever timing adjustment
        if d["dx"] == "Drug-Induced Fever" and inputs["meds"]:
            days = inputs.get("days_since_new_med")
            if days is not None and days > 21:
                d["pearl"] += " (Latency >21 d makes this less likely.)"
                score -= 1

        # Infectious Endocarditis enhancement
        if d["dx"] == "Infectious Endocarditis":
            has_prosthetic = "Prosthetic Valve" in inputs["social"]
            has_ivdu = "IV Drug Use" in inputs["social"]
            if has_prosthetic or has_ivdu:
                if score == 0:
                    score = 1
                    triggers.append("High-Risk Substrate (Prosthetic/IVDU)")
            if has_prosthetic:
                orders_for_dx = [("Blood Cx x3", 0), ("TEE", 3)]
            else:
                orders_for_dx = d["orders"]
        else:
            orders_for_dx = d["orders"]

        # GCA age filter
        if d["dx"] == "Temporal Arteritis (GCA)" and inputs["age"] < 50:
            score = 0

        if score > 0:
            active_dx.append({"dx": d["dx"], "triggers": triggers, "pearl": d["pearl"]})
            for test, tier in orders_for_dx:
                orders[tier].add(test)

    # Antibiotic hold if on empiric
    if inputs["on_abx"]:
        active_dx.insert(0, {"dx": "Medication Effect / Masked Fever",
                             "triggers": ["Currently on Antibiotics"],
                             "pearl": "Empiric antibiotics may mask culture results and fever curves."})
        orders[0].add("STOP/HOLD Empiric Antibiotics (48 h washout)")

    # Remove prior work-up
    for t in orders:
        orders[t] -= inputs["prior_workup"]

    # Escalation rule for PET/CT
    if "CT Chest/Abd/Pelvis" in inputs["prior_workup"]:
        orders[3].add("FDG-PET/CT (Whole Body)")

    # Naproxen test for malignancy context
    if any("Malignancy" in dx["dx"] for dx in active_dx) and not inputs["on_abx"]:
        orders[1].add("Naproxen Test (375 mg BID ×3 days)")

    return active_dx, orders

def generate_note(inputs, active_dx, orders):
    txt = (f"ID Consult Note\nPatient: {inputs['age']}yo {inputs['sex']} | Immune: {inputs['immune']}\n"
           f"Duration of fever: {inputs['duration_fever_days']} days | Days since new med: {inputs.get('days_since_new_med','N/A')} days\n\n"
           "Assessment & Differential:\n")
    if active_dx:
        for d in active_dx:
            triggers_str = ", ".join(d["triggers"]) if d["triggers"] else "clinical context"
            txt += f"- {d['dx']}: {triggers_str}\n"
    else:
        txt += "- True FUO. No specific syndromic matches identified.\n"

    txt += "\nPlan:\n"
    if "STOP/HOLD Empiric Antibiotics (48 h washout)" in orders[0]:
        txt += "1. Therapeutic hold: Discontinue empiric antibiotics to define fever curve and allow recultures.\n"
    txt += "2. Diagnostic work-up:\n"
    all_orders = []
    for t in [0,1,2,3]:
        all_orders.extend(orders[t])
    all_orders = [o for o in all_orders if "STOP/HOLD" not in o]
    for o in sorted(set(all_orders)):
        txt += f"- [ ] {o}\n"
    return txt

# --- SESSION HISTORY ---
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("Patient Data")
    if st.button("Clear All Inputs"):
        st.session_state.clear()
        st.experimental_rerun()

    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 18, 100, 50, help="Patient age in years")
    sex = c2.selectbox("Sex", ["Male", "Female"])
    immune = st.selectbox("Immune", ["Immunocompetent", "HIV+", "Transplant"])

    st.header("1. Meds & History")
    on_abx = st.checkbox("Currently on Antibiotics?", help="Is patient on empiric or ongoing antibiotics?")
    meds = st.multiselect("New/High-Risk Meds", ["New Beta-Lactam", "New Anticonvulsant", "New Sulfa Drug", "Allopurinol"],
                         help="Select recent initiation of higher-risk drugs")
    days_since_new_med = None
    if meds:
        days_since_new_med = st.number_input("Days since new/high-risk med started", 0, 365, 0,
                                             help="Enter days since drug started")

    st.header("2. Duration & Timing")
    duration_fever_days = st.number_input("Duration of fever (in days)", 0, 365, 7,
                                          help="Enter number of days patient has had documented fever")

    st.header("3. Prior Work-up")
    prior_workup = st.multiselect("Already Done", ["Blood Cx x3", "HIV 1/2 Ag/Ab", "Syphilis IgG",
                                                    "CT Chest/Abd/Pelvis", "TTE", "TEE"],
                                   help="Select any tests/imaging already completed")

    st.header("4. Exposures")
    with st.expander("Animals", expanded=False):
        cats = st.checkbox("Cats (Scratch/Bite)", help="Cat scratch or bite exposure")
        livestock = st.checkbox("Farm Animals", help="Livestock exposure e.g., brucella")
        birds = st.checkbox("Birds/Bats", help="Bird/bat droppings or cave exposure")
        ticks = st.checkbox("Ticks", help="Tick bite or vector exposure")

    social = st.multiselect("Social/Env", ["Unpasteurized Dairy", "Travel (Mexico/Med)", "Prosthetic Valve", "IV Drug Use", "Homelessness (Lice)"],
                             help="Select relevant social or environmental exposures")

    st.header("5. Symptoms")
    symptoms = st.multiselect("Review of Systems",
                              ["New Murmur", "Jaw Claudication", "Vision Changes", "Weight Loss >10%",
                               "Night Sweats", "Rash (General)", "Eosinophilia", "Hepatodynia", "Hematuria", "Pancytopenia"],
                              help="Select relevant symptoms or lab abnormalities")

    run = st.button("Generate Plan")

# --- MAIN DISPLAY ---
st.title("ID-CDSS | Director Suite")

if run:
    if duration_fever_days <= 0:
        st.warning("Duration of fever is zero or less: please verify.")
    if meds and days_since_new_med is None:
        st.warning("New/high-risk med selected: please enter days since started.")

    all_positives = meds + social + symptoms
    if cats:
        all_positives.append("Cats (Scratch/Bite)")
    if livestock:
        all_positives.append("Farm Animals")
    if birds:
        all_positives.append("Bird/Bat Droppings")
    if ticks:
        all_positives.append("Tick Bite")

    inputs = {
        "age": age,
        "sex": sex,
        "immune": immune,
        "on_abx": on_abx,
        "meds": meds,
        "days_since_new_med": days_since_new_med,
        "duration_fever_days": duration_fever_days,
        "all_positives": all_positives,
        "social": social,
        "symptoms": symptoms,
        "prior_workup": set(prior_workup),
    }

    active_dx, orders = get_plan(inputs)
    st.session_state["history"].append({"inputs": inputs, "dx": active_dx})

    col1, col2 = st.columns([1,1])
    with col1:
        if on_abx:
            st.markdown("<div class='alert'>⚠️ STEWARDSHIP ALERT: Patient is on empiric antibiotics. Consider a 48-h hold to evaluate fever curve.</div>",
                        unsafe_allow_html=True)
        st.subheader("Differential Logic")
        if not active_dx:
            st.write("No specific syndromes triggered. Consider broad FUO protocol.")
        else:
            for d in active_dx:
                st.markdown(f"**{d['dx']}**")
                st.caption(f"Triggers: {', '.join(d['triggers'])} | Pearl: {d['pearl']}")

    with col2:
        st.subheader("Staged Orders")
        st.markdown("<div class='tier0'>", unsafe_allow_html=True)
        st.markdown("**Tier 0: Universal Baseline & Actions**")
        for o in sorted(list(orders[0])):
            st.markdown(f"- [ ] **{o}**")
        st.markdown("</div><br>", unsafe_allow_html=True)

        if orders[1]:
            st.markdown("<div class='tier1'>", unsafe_allow_html=True)
            st.markdown("**Tier 1: Targeted Labs**")
            for o in sorted(list(orders[1])):
                st.markdown(f"- [ ] {o}")
            st.markdown("</div><br>", unsafe_allow_html=True)

        if orders[2]:
            st.markdown("<div class='tier2'>", unsafe_allow_html=True)
            st.markdown("**Tier 2: Structural Imaging**")
            for o in sorted(list(orders[2])):
                st.markdown(f"- [ ] {o}")
            st.markdown("</div><br>", unsafe_allow_html=True)

        if orders[3]:
            st.markdown("<div class='tier3'>", unsafe_allow_html=True)
            st.markdown("**Tier 3: Escalation (High Cost/Risk)**")
            for o in sorted(list(orders[3])):
                st.markdown(f"- [ ] {o}")
            st.markdown("</div>", unsafe_allow_html=True)

        note_text = generate_note(inputs, active_dx, orders)
        st.download_button(label="Download Note", data=note_text, file_name="consult_note.txt", mime="text/plain", help="Download the consult note as a text file")
        st.text_area("Consult Note", note_text, height=350)
    
# Sidebar: recent cases
with st.sidebar.expander("Recent Cases", expanded=False):
    for i, h in enumerate(reversed(st.session_state["history"][-5:])):
        st.write(f"Case {len(st.session_state['history'])-i}: Age {h['inputs']['age']}yo | Dx: {[dx['dx'] for dx in h['dx']]}")
