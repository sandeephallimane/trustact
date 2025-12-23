import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="ಶ್ರೀದುರ್ಗಾಪರಮೇಶ್ವರಿ ಸೇವಾಟ್ರಸ್ಟ್,
ವಿಶ್ವನಾಥಪುರ")

# --- SESSION STATE (Ledger Memory) ---
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        "Date", "ID", "Name", "Items", "Ref_No", "Mode", "Inflow", "Outflow", "Net"
    ])

# --- SIDEBAR: SETTINGS & OPENING BALANCE ---
st.sidebar.header("📍 1. Initial Setup")
trust_name = st.sidebar.text_input("Trust Name", "ಶ್ರೀದುರ್ಗಾಪರಮೇಶ್ವರಿ ಸೇವಾಟ್ರಸ್ಟ್")
opn_bank = st.sidebar.number_input("Opening Bank Balance (₹)", value=0.0, step=0.01)
opn_cash = st.sidebar.number_input("Opening Cash Balance (₹)", value=0.0, step=0.01)

st.sidebar.markdown("---")
inv_pre = st.sidebar.text_input("Invoice Prefix", "INV-")
inv_start = st.sidebar.number_input("Invoice Start #", value=1001)
exp_start = st.sidebar.number_input("Expense Start #", value=5001)

# --- 2. FILE UPLOADER (Fix for Blurred Files) ---
st.header("📂 2. Upload Bank/Cash Statements")
# We set type=None to stop the browser from blurring files. We check the extension later.
uploaded_files = st.file_uploader("Choose Bank or Cash CSV/Excel files", accept_multiple_files=True, type=None)

if st.button("Process Uploaded Files"):
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.csv'):
            new_data = pd.read_csv(uploaded_file)
        else:
            new_data = pd.read_excel(uploaded_file)
        
        # Merge logic (Simple append for this demo)
        st.session_state.ledger = pd.concat([st.session_state.ledger, new_data], ignore_index=True)
    st.success("Files Processed!")

# --- 3. MANUAL ENTRY (With Iterative IDs) ---
st.header("✍️ 3. Add Manual Transaction")
with st.form("manual_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        id_cat = st.selectbox("ID Category", [
            "INV- (Iterative)", "EXP- (Iterative)", 
            "inv-deposit", "inv-loan", "inv-other", "inv-OPBAL",
            "exp-withdrawal", "exp-loan", "exp-FD", "exp-other"
        ])
    with col2:
        mode = st.selectbox("Mode", ["Cash", "Bank"])
    with col3:
        name = st.text_input("Name/Particulars")
    with col4:
        amount = st.number_input("Amount (₹)", min_value=0.0)

    item = st.text_input("Item Description", "Pooja Seve")
    ref = st.text_input("Reference No", "Manual")
    
    if st.form_submit_button("Save Transaction"):
        # ID Logic
        final_id = id_cat
        if id_cat == "INV- (Iterative)":
            existing_invs = st.session_state.ledger[st.session_state.ledger['ID'].str.startswith(inv_pre, na=False)]
            next_num = inv_start if existing_invs.empty else (len(existing_invs) + inv_start)
            final_id = f"{inv_pre}{next_num}"
        elif id_cat == "EXP- (Iterative)":
            existing_exps = st.session_state.ledger[st.session_state.ledger['ID'].str.startswith("EXP-", na=False)]
            next_num = exp_start if existing_exps.empty else (len(existing_exps) + exp_start)
            final_id = f"EXP-{next_num}"

        is_inflow = "inv-" in final_id.lower() or inv_pre in final_id
        
        new_row = {
            "Date": datetime.now().strftime("%d-%m-%Y"),
            "ID": final_id, "Name": name, "Items": item, "Ref_No": ref,
            "Mode": mode, "Inflow": amount if is_inflow else 0,
            "Outflow": 0 if is_inflow else amount, "Net": amount if is_inflow else -amount
        }
        st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_row])], ignore_index=True)

# --- 4. LIVE EDITABLE LEDGER & BALANCE ---
st.header("📊 4. Master Ledger & Live Balance")

# st.data_editor allows you to click and change any cell directly!
edited_df = st.data_editor(st.session_state.ledger, num_rows="dynamic", use_container_width=True)
st.session_state.ledger = edited_df

# Calculations
tot_in = edited_df['Inflow'].sum() + opn_bank + opn_cash
tot_out = edited_df['Outflow'].sum()
closing = tot_in - tot_out

c1, c2, c3 = st.columns(3)
c1.metric("Total Inflow (+Opening)", f"₹{tot_in:,.2f}")
c2.metric("Total Outflow", f"₹{tot_out:,.2f}")
c3.metric("Closing Balance", f"₹{closing:,.2f}")

# --- 5. EXPORT ---
st.markdown("---")
if st.button("Generate Regulatory CSV"):
    csv = edited_df.to_csv(index=False)
    st.download_button("Download CSV", csv, "Trust_Audit_Ready.csv", "text/csv")
