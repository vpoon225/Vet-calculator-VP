import streamlit as str
import pandas as pd
import math

# Set page layout to wide for better screen usage on clinic devices
str.set_page_config(page_title="🐾 Clinic Drug Dose Calculator", layout="wide")

str.title("🐾 Multi-Drug Clinic Calculator")
str.write("Enter the patient's details below to calculate safe and accurate medication dosages.")

# --- GOOGLE SHEET CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/19J5i22M-gV-6yZeK-Qz5pSsR9O7pAfqgycOi6papMhk/export?format=csv"

@str.cache_data(ttl=60) # Automatically pulls any Google Sheet edits every 60 seconds
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        # Standardize column naming rules and strip trailing white spaces
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        str.error(f"Error loading your Google Sheet formulary: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- USER INPUT AREA ---
    col1, col2 = str.columns(2)
    
    with col1:
        weight = str.number_input("Patient Weight (kg):", min_value=0.1, value=10.0, step=0.1)
    
    with col2:
        species_choice = str.selectbox("Patient Species:", ["Canine", "Feline"])

    # Filter rules matching the specific species profile
    filtered_df = df[df['Species'].str.lower().str.strip().isin([species_choice.lower(), 'all'])]
    
    # Strip any potential hidden empty spaces inside the main drug name index
    filtered_df['Drug Name'] = filtered_df['Drug Name'].str.strip()
    filtered_df = filtered_df.drop_duplicates(subset=['Drug Name'])
    
    formulary = filtered_df.set_index("Drug Name").to_dict(orient="index")
    
    str.markdown("---")
    str.subheader("💊 Select Medications")

    # Dropdown menu containing every drug associated with your species selection
    selected_drugs = str.multiselect("Choose medications to calculate:", list(formulary.keys()))

    if selected_drugs:
        str.markdown("### 📋 Generated Prescription Details")
        
        for drug_name in selected_drugs:
            drug = formulary[drug_name]
            unit_type = str(drug["Unit"]).lower().strip()
            
            # --- SMART VETERINARY CALCULATION PIPELINE ---
            # Bypass patient weight multipliers entirely if the record uses fixed unit rules
            if unit_type in ["vial", "bracket", "tablet per dog", "fixed"]:
                min_quantity = float(drug["Min Dose"])
                max_quantity = float(drug["Max Dose"])
                chosen_dose_display = "Fixed Dose"
            else:
                # Dynamic weight multiplication logic for standard medications
                mg_min = weight * float(drug["Min Dose"])
                mg_max = weight * float(drug["Max Dose"])
                
                concentration = float(drug["Concentration Value"])
                min_quantity = mg_min / concentration
                max_quantity = mg_max / concentration
                
                # Format dosage text cleanly for display purposes
                if float(drug["Min Dose"]) == float(drug["Max Dose"]):
                    chosen_dose_display = f"{drug['Min Dose']} mg/kg"
                else:
                    chosen_dose_display = f"{drug['Min Dose']}-{drug['Max Dose']} mg/kg"

            # --- SMART CLINICAL ROUNDING RULES ---
            if unit_type == "tablet":
                # Safely round down to the nearest quarter tablet to simplify instructions
                def round_quarter(val):
                    return math.floor(val * 4) / 4 if val >= 0.25 else 0.25
                min_dispense = f"{round_quarter(min_quantity)} tab"
                max_dispense = f"{round_quarter(max_quantity)} tab"
            elif unit_type in ["vial", "bracket"]:
                # Keep fixed tiers perfectly intact
                min_dispense = f"{min_quantity} vial" if min_quantity == max_quantity else f"{min_quantity}-{max_quantity} vial"
                max_dispense = "" 
            else:
                # Keep liquid medication quantities perfectly exact to 2 decimal places (e.g., 0.42 ml)
                min_dispense = f"{min_quantity:.2f} {drug['Unit']}"
                max_dispense = f"{max_quantity:.2f} {drug['Unit']}"

            # --- PRINT READY PRESCRIPTION LOGIC OUTPUT ---
            if min_dispense == max_dispense or max_dispense == "":
                final_volume_string = min_dispense
            else:
                final_volume_string = f"{min_dispense} - {max_dispense}"

            # Clean output structure matching formal clinic labels
            str.markdown(
                f"**{drug['Type']}**: {drug_name} ({chosen_dose_display}) &nbsp;&nbsp;➔&nbsp;&nbsp; "
                f"`{final_volume_string}` &nbsp;&nbsp;|&nbsp;&nbsp; {drug['Route']} &nbsp;&nbsp;|&nbsp;&nbsp; {drug['Freq']}"
            )
else:
    str.warning("Please verify your Google Sheet CSV export parameters. No records could be read successfully.")
