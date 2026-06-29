import streamlit as st
import pandas as pd
import re
import math

# 1. LINK TO YOUR GOOGLE SHEET
SHARE_LINK = "https://docs.google.com/spreadsheets/d/19J5i22M-gV-6yZeK-Qz5pSsR9O7pAfqgycOi6papMhk/edit?usp=sharing"

def get_csv_url(url):
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            spreadsheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
        return None
    except Exception as e:
        return None

csv_url = get_csv_url(SHARE_LINK)

# 2. LOAD THE DATA
@st.cache_data(ttl=5)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

st.title("🐾 Clinic Multi-Drug Calculator")

# Initialize the app's persistent memory bucket if it doesn't exist yet
if "rx_basket" not in st.session_state:
    st.session_state["rx_basket"] = []

try:
    df_formulary = load_data(csv_url)
    if "Drug Name" not in df_formulary.columns or "Species" not in df_formulary.columns:
        st.error(f"❌ Header Error: Please ensure you have both 'Drug Name' and 'Species' columns.")
        st.stop()
except Exception as error:
    st.error("❌ Connection Failed. Technical details below:")
    st.exception(error)
    st.stop()

# 3. STREAMLIT USER INTERFACE
st.write("Input patient details below to build your multi-drug prescription list.")

col1, col2, col3 = st.columns(3)
with col1:
    species = st.selectbox("Species", ["Canine", "Feline", "Other"])
with col2:
    weight = st.number_input("Weight (kg)", min_value=0.1, value=10.0, step=0.1)
with col3:
    days = st.number_input("Duration (Days)", min_value=1, value=14, step=1)

filtered_df = df_formulary[
    (df_formulary["Species"].str.strip().str.lower() == species.lower()) | 
    (df_formulary["Species"].str.strip().str.lower() == "all")
]

# Ensure unique drug names before creating the dictionary index
filtered_df['Drug Name'] = filtered_df['Drug Name'].str.strip()
filtered_df = filtered_df.drop_duplicates(subset=['Drug Name'])
formulary = filtered_df.set_index("Drug Name").to_dict(orient="index")

if not formulary:
    st.warning(f"⚠️ No medications found in your spreadsheet for {species} yet.")
    st.stop()

selected_drug_name = st.selectbox("Select Drug", list(formulary.keys()))
drug = formulary[selected_drug_name]

# Normalize unit string for checking
unit_type = str(drug["Unit"]).strip().lower() if pd.notna(drug["Unit"]) else ""

if float(drug["Max Dose"]) != float(drug["Min Dose"]):
    chosen_dose = st.slider(
        f"Select Dosage", 
        float(drug["Min Dose"]), 
        float(drug["Max Dose"]), 
        float((drug["Min Dose"] + drug["Max Dose"]) / 2)
    )
else:
    chosen_dose = float(drug["Min Dose"])
    if unit_type in ["vial", "bracket", "tablet per dog", "fixed"]:
        st.info(f"Fixed dosage for this medication: {chosen_dose} {unit_type}")
    else:
        st.info(f"Fixed dosage for this medication: {chosen_dose} mg/kg")

# 4. THE CALCULATION & VETERINARY ROUNDING LOGIC
if unit_type in ["vial", "bracket", "tablet per dog", "fixed"]:
    # Bypass patient weight completely for flat-dose/bracket medications
    quantity_needed = chosen_dose
    chosen_dose_str = "Fixed Dose"
else:
    # Standard math for normal mg/kg dynamic medications
    mg_per_dose = weight * chosen_dose
    quantity_needed = mg_per_dose / float(drug["Concentration Value"])
    chosen_dose_str = f"{int(chosen_dose)}mg/kg" if chosen_dose.is_integer() else f"{chosen_dose}mg/kg"

# Apply precise rounding configurations based on unit definitions
if unit_type == "tablet":
    display_qty = math.floor(quantity_needed * 4) / 4 
    if display_qty == 0.0:
        display_qty = 0.25
    unit_string = "tablets" if display_qty > 1 else "tablet"
elif unit_type in ["vial", "bracket", "tablet per dog", "fixed"]:
    display_qty = round(quantity_needed, 1) if not quantity_needed.is_integer() else int(quantity_needed)
    unit_string = "vials" if "vial" in unit_type else "tablet per dog"
else:
    display_qty = round(quantity_needed, 2) 
    unit_string = str(drug["Unit"]).strip()

duration_string = "1day" if days == 1 else f"{days}days"

# SMART TEXT FIX: Strip parenthetical details out of the base name so it looks like "Sulcrafate" instead of "Sulcrafate (Small Dog)"
base_drug_name = selected_drug_name.split(' (')[0]

# Construct the current single prescription line
current_rx_line = (
    f"{drug['Type']}: {base_drug_name} {drug['Concentration Display']} ({chosen_dose_str})        "
    f"{display_qty} {unit_string}  {drug['Route']} {drug['Freq']} {duration_string}"
)

# 5. CONTROL BUTTONS (Add to Basket / Clear Basket)
st.markdown("---")
btn_col1, btn_col2 = st.columns([1, 4])

with btn_col1:
    if st.button("➕ Add to List", type="primary"):
        st.session_state["rx_basket"].append(current_rx_line)
        st.toast(f"Added {base_drug_name}!", icon="✅")

with btn_col2:
    if st.button("🗑️ Clear Entire List"):
        st.session_state["rx_basket"] = []
        st.rerun()

# 6. GENERATING THE CUMULATIVE OUTPUT BOX
st.subheader("📋 Complete Patient Prescription Output:")

if st.session_state["rx_basket"]:
    # The \n handles linebreaks perfectly inside code blocks
    combined_output = "\n".join(st.session_state["rx_basket"])
    st.code(combined_output, language="text")
    st.info("💡 Pro-Tip: Click the copy icon in the top right corner of the box above to grab all lines at once!")
    
    # Also render them cleanly on the web app below the box
    st.markdown("### Preview:")
    for line in st.session_state["rx_basket"]:
        st.write(line)
else:
    st.code("No medications added yet. Choose a drug above and click 'Add to List'.", language="text")
