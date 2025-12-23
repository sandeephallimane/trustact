import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO

st.set_page_config(layout="wide", page_title="Trust Auditor Pro v4.0", page_icon="⚖️")

# Custom CSS for high-visibility Audit Alerts
st.markdown("""
    <style>
    .val-box { padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .val-success { background-color: #e6fffa; border: 2px solid #38a169; color: #276749; }
    .val-error { background-color: #fff5f5; border: 2px solid #e53e3e; color: #9b2c2c; }
    </style>
    """, unsafe_allow_html=True)

st.title("ಶ್ರೀದುರ್ಗಾಪರಮೇಶ್ವರಿ ಸೇವಾಟ್ರಸ್ಟ್ | Auditor Pro v4.0")

# --- Side Controls ---
st.sidebar.header("🔑 Baseline Balances")
opn_bank = st.sidebar.number_input("Opening Bank Balance", value=0.0, help="Bank balance on April 1st")
opn_cash = st.sidebar.number_input("Opening Cash Box", value=0.0, help="Physical cash on April 1st")
total_opening = opn_bank + opn_cash

st.sidebar.markdown("---")
trust_id = st.sidebar.text_input("Trust Registration No.", "Example: 12A/xxxx/xxxx")

# --- File Selection ---
col1, col2 = st.columns(2)
with col1:
    bank_file = st.file_uploader("📂 Bank Ledger CSV", type=['csv'])
with col2:
    cash_file = st.file_uploader("📂 Cash Book CSV", type=['csv'])

if bank_file and cash_file:
    # 1. LOAD & SYNC
    df_bank = pd.read_csv(bank_file)
    df_cash = pd.read_csv(cash_file)
    
    # Standardize and Combine
    df_bank['Source'] = 'Bank'
    df_cash['Source'] = 'Cash'
    master = pd.concat([df_bank, df_cash], ignore_index=True)
    master['Date'] = pd.to_datetime(master['Date'], dayfirst=True, errors='coerce')
    
    # 2. CALCULATION ENGINE
    total_inflow = master['Inflow'].sum()
    total_outflow = master['Outflow'].sum()
    expected_closing = total_opening + total_inflow - total_outflow
    
    # Component Balances
    current_bank = opn_bank + df_bank['Net'].sum()
    current_cash = opn_cash + df_cash['Net'].sum()
    actual_closing = current_bank + current_cash
    
    # 3. REPORTING TABS
    tabs = st.tabs(["⚖️ Reconciliation", "📜 Receipts & Payments", "📊 Analytics", "💎 Donor List"])

    # --- TAB 1: MATHEMATICAL RECONCILIATION ---
    with tabs[0]:
        st.subheader("Mathematical Balance Validation")
        diff = round(actual_closing - expected_closing, 2)
        
        if diff == 0:
            st.markdown(f'<div class="val-box val-success"><b>✅ LEDGER RECONCILED</b><br>Total Funds: ₹{actual_closing:,.2f}<br>Difference: ₹0.00</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="val-box val-error"><b>⚠️ DATA DISCREPANCY FOUND</b><br>Ledger Balance: ₹{actual_closing:,.2f}<br>Expected: ₹{expected_closing:,.2f}<br>Mismatch: ₹{diff:,.2f}</div>', unsafe_allow_html=True)
            st.error("Action Needed: Please check if any 'exp-withdrawal' or 'inv-deposit' entries are missing or have mismatched amounts.")

        # Breakdown metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Bank Bal", f"₹{current_bank:,.2f}")
        c2.metric("Current Cash Bal", f"₹{current_cash:,.2f}")
        c3.metric("Net Surplus/Deficit", f"₹{total_inflow - total_outflow:,.2f}")

    # --- TAB 2: RECEIPTS & PAYMENTS ACCOUNT ---
    with tabs[1]:
        st.subheader("Statement of Receipts and Payments")
        st.caption("Standard statutory format for Trust Audit reports.")
        
        # Categorized Summary
        summary = master.groupby(['Items', 'Source']).agg({'Inflow':'sum', 'Outflow':'sum'}).reset_index()
        
        col_r, col_p = st.columns(2)
        with col_r:
            st.write("**RECEIPTS (Inflow)**")
            st.dataframe(summary[summary['Inflow'] > 0][['Items', 'Source', 'Inflow']], use_container_width=True)
            st.write(f"**Total Receipts:** ₹{total_inflow:,.2f}")
            
        with col_p:
            st.write("**PAYMENTS (Outflow)**")
            st.dataframe(summary[summary['Outflow'] > 0][['Items', 'Source', 'Outflow']], use_container_width=True)
            st.write(f"**Total Payments:** ₹{total_outflow:,.2f}")

    # --- TAB 3: ANALYTICS ---
    with tabs[2]:
        st.subheader("Source of Funds vs Application")
        fig = px.pie(master, values='Inflow', names='Items', title="Where did the money come from?", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        
        # Monthly Growth
        master['Month'] = master['Date'].dt.to_period('M').astype(str)
        monthly = master.groupby('Month').agg({'Inflow':'sum', 'Outflow':'sum'}).reset_index()
        fig2 = px.bar(monthly, x='Month', y=['Inflow', 'Outflow'], barmode='group', title="Month-on-Month Performance")
        st.plotly_chart(fig2, use_container_width=True)

    # --- TAB 4: DONOR COMPLIANCE ---
    with tabs[3]:
        st.subheader("80G Compliance Annexure")
        st.write("Transactions requiring detailed PAN verification for filing Form 10BD.")
        donors = master[master['Inflow'] > 0].sort_values(by='Inflow', ascending=False)
        st.dataframe(donors[['Date', 'Name', 'Items', 'Inflow', 'Ref_No', 'Source']], use_container_width=True)

    # --- FINAL EXPORT ---
    st.markdown("---")
    def to_excel(df):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Unified_Ledger')
        summary.to_excel(writer, index=False, sheet_name='Receipts_Payments')
        writer.close()
        return output.getvalue()

    st.download_button(
        label="📥 Download Audit-Ready Master Excel",
        data=to_excel(master),
        file_name=f"Trust_Audit_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )

else:
    st.info("👋 Welcome! Please upload your 'Bank Ledger' and 'Cash Book' CSV files to generate the regulatory audit report.")
    st.image("https://cdn-icons-png.flaticon.com/512/2641/2641409.png", width=100)
