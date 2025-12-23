import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Auditor Pro v5.1")

# --- 1. SESSION STATE INITIALIZATION ---
# This keeps your data alive across reruns
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        "Date", "ID", "Name", "Items", "Ref_No", "Mode", "Inflow", "Outflow", "Net"
    ])

# --- 2. SETTINGS ---
st.sidebar.header("📍 Setup")
opn_bal = st.sidebar.number_input("Opening Balance (Total)", value=0.0)
inv_pre = st.sidebar.text_input("Invoice Prefix", "INV-")

# --- 3. IMPROVED FILE UPLOADER ---
# Removed strict 'type' to prevent "blurred" files in some browsers
uploaded_files = st.file_uploader("Upload CSV or Excel Statements", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        # Check if we already processed this specific file to avoid duplicates
        file_key = f"processed_{uploaded_file.name}"
        if file_key not in st.session_state:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Append to our persistent ledger
                st.session_state.ledger = pd.concat([st.session_state.ledger, df], ignore_index=True)
                st.session_state[file_key] = True
                st.success(f"Loaded: {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error loading {uploaded_file.name}: {e}")

# --- 4. MANUAL ENTRY ---
with st.expander("➕ Add Manual Entry", expanded=False):
    with st.form("manual_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            id_type = st.selectbox("ID", ["INV-", "EXP-", "inv-deposit", "exp-withdrawal", "inv-loan"])
            mode = st.selectbox("Mode", ["Cash", "Bank"])
        with col2:
            name = st.text_input("Name")
            item = st.text_input("Item", "Pooja Seve")
        with col3:
            amt = st.number_input("Amount", min_value=0.0)
            ref = st.text_input("Ref No", "Manual")
        
        if st.form_submit_button("Add Record"):
            # Logic to generate next ID
            if id_type == "INV-":
                count = len(st.session_state.ledger[st.session_state.ledger['ID'].str.contains(inv_pre, na=False)])
                id_type = f"{inv_pre}{1001 + count}"
            
            new_row = pd.DataFrame([{
                "Date": datetime.now().strftime("%d-%m-%Y"),
                "ID": id_type, "Name": name, "Items": item, "Ref_No": ref,
                "Mode": mode, "Inflow": amt if "inv" in id_type.lower() else 0,
                "Outflow": amt if "exp" in id_type.lower() else 0,
                "Net": amt if "inv" in id_type.lower() else -amt
            }])
            st.session_state.ledger = pd.concat([st.session_state.ledger, new_row], ignore_index=True)
            st.rerun() # Refresh to show new data immediately

# --- 5. DISPLAY & DISCREPANCIES ---
if not st.session_state.ledger.empty:
    st.subheader("📊 Master Ledger")
    
    # Editable table - changes here update the session_state automatically
    edited_df = st.data_editor(st.session_state.ledger, use_container_width=True, num_rows="dynamic")
    st.session_state.ledger = edited_df

    # Live Totals
    total_in = edited_df['Inflow'].sum() + opn_bal
    total_out = edited_df['Outflow'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Inflow", f"₹{total_in:,.2f}")
    m2.metric("Total Outflow", f"₹{total_out:,.2f}")
    m3.metric("Net Balance", f"₹{total_in - total_out:,.2f}")

    # --- DISCREPANCY HIGHLIGHT ---
    # Example: Highlight if any Cash Withdrawal from Bank doesn't match a Cash Deposit
    bank_withdrawals = edited_df[(edited_df['ID'] == 'exp-withdrawal') & (edited_df['Mode'] == 'Bank')]['Outflow'].sum()
    cash_deposits = edited_df[(edited_df['ID'] == 'inv-deposit') & (edited_df['Mode'] == 'Cash')]['Inflow'].sum()
    
    if bank_withdrawals != cash_deposits:
        st.error(f"⚠️ Mismatch: Bank Withdrawal (₹{bank_withdrawals}) does not match Cash Deposit (₹{cash_deposits})")
else:
    st.info("Upload a file or add a manual entry to see the ledger.")

