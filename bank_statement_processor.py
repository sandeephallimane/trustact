import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# Page configuration
st.set_page_config(
    page_title="Bank Statement Processor",
    page_icon="💰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'transactions' not in st.session_state:
    st.session_state.transactions = None
if 'invoice_start' not in st.session_state:
    st.session_state.invoice_start = 1001
if 'expense_start' not in st.session_state:
    st.session_state.expense_start = 2001


def parse_bank_statement(pdf_file):
    """Extract transactions from Karnataka Bank statement"""
    transactions = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            tables = page.extract_tables()
            
            # Try to extract from tables first
            for table in tables:
                if not table:
                    continue
                    
                for row in table:
                    if not row or len(row) < 4:
                        continue
                    
                    # Skip header rows
                    if 'Date' in str(row[0]) or 'Particulars' in str(row[1]):
                        continue
                    
                    # Parse transaction row
                    date_str = str(row[0]).strip() if row[0] else ''
                    particulars = str(row[1]).strip() if row[1] else ''
                    
                    # Skip if date doesn't match pattern
                    if not re.match(r'\d{2}-\d{2}-\d{4}', date_str):
                        continue
                    
                    withdrawals = str(row[2]).strip() if len(row) > 2 and row[2] else ''
                    deposits = str(row[3]).strip() if len(row) > 3 and row[3] else ''
                    balance = str(row[4]).strip() if len(row) > 4 and row[4] else ''
                    
                    # Clean amounts
                    withdrawals = withdrawals.replace(',', '').replace('None', '').strip()
                    deposits = deposits.replace(',', '').replace('None', '').strip()
                    balance = balance.replace(',', '').replace('None', '').strip()
                    
                    # Determine transaction type and amount
                    if withdrawals and withdrawals != '':
                        try:
                            amount = float(withdrawals)
                            trans_type = 'Debit'
                        except:
                            continue
                    elif deposits and deposits != '':
                        try:
                            amount = float(deposits)
                            trans_type = 'Credit'
                        except:
                            continue
                    else:
                        continue
                    
                    transactions.append({
                        'Date': date_str,
                        'Particulars': particulars,
                        'Type': trans_type,
                        'Amount': amount,
                        'Balance': balance,
                        'Classification': 'Unclassified',
                        'Number': '',
                        'Selected': False
                    })
    
    return pd.DataFrame(transactions)


def assign_numbers(df, classification_type, start_number):
    """Assign sequential numbers to classified transactions"""
    filtered = df[df['Classification'] == classification_type].copy()
    filtered = filtered.sort_values('Date')
    
    for idx, (i, row) in enumerate(filtered.iterrows()):
        df.at[i, 'Number'] = f"{classification_type[:3].upper()}-{start_number + idx:04d}"
    
    return df


def generate_invoice_pdf(selected_transactions, invoice_start):
    """Generate A4 PDF with 20 invoices per page"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=5*mm, bottomMargin=5*mm, 
                           leftMargin=5*mm, rightMargin=5*mm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading2'],
        fontSize=8,
        alignment=TA_CENTER,
        spaceAfter=2
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=6,
        leading=8
    )
    
    # Sort by date
    invoices = selected_transactions.sort_values('Date')
    
    # Create mini invoices - 4 columns x 5 rows = 20 per page
    invoices_per_page = 20
    cols = 4
    rows = 5
    
    page_width, page_height = A4
    cell_width = (page_width - 10*mm) / cols
    cell_height = (page_height - 10*mm) / rows
    
    for page_num in range(0, len(invoices), invoices_per_page):
        page_invoices = invoices.iloc[page_num:page_num + invoices_per_page]
        
        # Create table data for this page
        table_data = []
        
        for row_idx in range(rows):
            row_cells = []
            for col_idx in range(cols):
                inv_idx = row_idx * cols + col_idx
                
                if inv_idx < len(page_invoices):
                    inv = page_invoices.iloc[inv_idx]
                    
                    cell_content = [
                        Paragraph(f"<b>INVOICE</b>", title_style),
                        Paragraph(f"<b>{inv['Number']}</b>", title_style),
                        Paragraph(f"Date: {inv['Date']}", normal_style),
                        Spacer(1, 2*mm),
                        Paragraph(f"<b>Amount: ₹{inv['Amount']:,.2f}</b>", normal_style),
                        Spacer(1, 2*mm),
                        Paragraph(f"{inv['Particulars'][:80]}", normal_style),
                    ]
                    
                    # Create a mini table for this invoice
                    mini_table = Table([[c] for c in cell_content], colWidths=[cell_width - 2*mm])
                    mini_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    
                    row_cells.append(mini_table)
                else:
                    row_cells.append('')
            
            table_data.append(row_cells)
        
        # Create main table for page
        main_table = Table(table_data, colWidths=[cell_width]*cols, 
                          rowHeights=[cell_height]*rows)
        main_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1*mm),
            ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
        ]))
        
        elements.append(main_table)
        
        if page_num + invoices_per_page < len(invoices):
            elements.append(PageBreak())
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_accounting_statements(df):
    """Generate comprehensive accounting statements"""
    
    # Calculate totals
    total_credits = df[df['Type'] == 'Credit']['Amount'].sum()
    total_debits = df[df['Type'] == 'Debit']['Amount'].sum()
    net_change = total_credits - total_debits
    
    # Get opening and closing balance
    opening_balance = 0
    closing_balance = 0
    if not df.empty:
        try:
            closing_balance = float(df.iloc[-1]['Balance'].replace(',', ''))
            opening_balance = closing_balance - net_change
        except:
            pass
    
    # Income Statement (P&L)
    income_data = {
        'Revenue (Credits)': [total_credits],
        'Expenses (Debits)': [total_debits],
        'Net Income/Loss': [net_change]
    }
    income_statement = pd.DataFrame(income_data).T
    income_statement.columns = ['Amount (₹)']
    
    # Balance Sheet
    balance_data = {
        'Assets': {
            'Cash and Bank Balance': closing_balance
        },
        'Liabilities': {
            'Opening Balance': opening_balance,
            'Net Income': net_change
        }
    }
    
    # Transaction Summary by Classification
    classification_summary = df.groupby(['Classification', 'Type'])['Amount'].agg(['sum', 'count']).reset_index()
    
    # Monthly Summary
    df_copy = df.copy()
    df_copy['Month'] = pd.to_datetime(df_copy['Date'], format='%d-%m-%Y').dt.to_period('M')
    monthly_summary = df_copy.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
    
    return {
        'income_statement': income_statement,
        'balance_data': balance_data,
        'classification_summary': classification_summary,
        'monthly_summary': monthly_summary,
        'totals': {
            'total_credits': total_credits,
            'total_debits': total_debits,
            'net_change': net_change,
            'opening_balance': opening_balance,
            'closing_balance': closing_balance
        }
    }


# Main App
st.markdown('<div class="main-header">🏦 Bank Statement Processor & Accounting System</div>', unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.subheader("Starting Numbers")
    invoice_start = st.number_input("Invoice Starting Number", 
                                    min_value=1, 
                                    value=st.session_state.invoice_start,
                                    step=1)
    st.session_state.invoice_start = invoice_start
    
    expense_start = st.number_input("Expense Starting Number", 
                                    min_value=1, 
                                    value=st.session_state.expense_start,
                                    step=1)
    st.session_state.expense_start = expense_start
    
    st.divider()
    
    st.subheader("📤 Upload Statement")
    uploaded_file = st.file_uploader("Upload Karnataka Bank PDF", type=['pdf'])
    
    if uploaded_file:
        if st.button("🔄 Process Statement", type="primary"):
            with st.spinner("Processing PDF..."):
                df = parse_bank_statement(uploaded_file)
                if not df.empty:
                    st.session_state.transactions = df
                    st.success(f"✅ Extracted {len(df)} transactions!")
                else:
                    st.error("No transactions found in PDF")

# Main content
if st.session_state.transactions is not None:
    df = st.session_state.transactions.copy()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Transactions", "🧾 Invoice Generator", "📈 Accounting Statements", "📋 Reports"])
    
    with tab1:
        st.markdown('<div class="sub-header">Transaction Management</div>', unsafe_allow_html=True)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transactions", len(df))
        with col2:
            st.metric("Total Credits", f"₹{df[df['Type']=='Credit']['Amount'].sum():,.2f}")
        with col3:
            st.metric("Total Debits", f"₹{df[df['Type']=='Debit']['Amount'].sum():,.2f}")
        with col4:
            net = df[df['Type']=='Credit']['Amount'].sum() - df[df['Type']=='Debit']['Amount'].sum()
            st.metric("Net Change", f"₹{net:,.2f}")
        
        st.divider()
        
        # Interactive classification table
        st.subheader("Classify Transactions")
        
        # Create editable dataframe
        edited_df = st.data_editor(
            df,
            column_config={
                "Selected": st.column_config.CheckboxColumn("Select", default=False),
                "Classification": st.column_config.SelectboxColumn(
                    "Classification",
                    options=["Unclassified", "Invoice", "Expense"],
                    required=True
                ),
                "Amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
                "Date": st.column_config.TextColumn("Date"),
                "Type": st.column_config.TextColumn("Type"),
                "Particulars": st.column_config.TextColumn("Particulars", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed"
        )
        
        # Update session state
        st.session_state.transactions = edited_df
        
        # Assign numbers button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔢 Assign Invoice Numbers", type="primary"):
                edited_df = assign_numbers(edited_df, 'Invoice', invoice_start)
                st.session_state.transactions = edited_df
                st.rerun()
        
        with col2:
            if st.button("🔢 Assign Expense Numbers", type="primary"):
                edited_df = assign_numbers(edited_df, 'Expense', expense_start)
                st.session_state.transactions = edited_df
                st.rerun()
    
    with tab2:
        st.markdown('<div class="sub-header">Invoice Generator</div>', unsafe_allow_html=True)
        
        # Filter for selected invoices
        selected_invoices = edited_df[(edited_df['Selected'] == True) & 
                                     (edited_df['Classification'] == 'Invoice')]
        
        st.info(f"📌 {len(selected_invoices)} invoices selected for printing")
        
        if len(selected_invoices) > 0:
            # Preview
            st.dataframe(selected_invoices[['Date', 'Number', 'Amount', 'Particulars']], 
                        use_container_width=True)
            
            # Generate PDF button
            if st.button("📄 Generate Invoice PDF (20 per A4 page)", type="primary"):
                with st.spinner("Generating PDF..."):
                    pdf_buffer = generate_invoice_pdf(selected_invoices, invoice_start)
                    
                    st.success("✅ PDF Generated!")
                    st.download_button(
                        label="⬇️ Download Invoice PDF",
                        data=pdf_buffer,
                        file_name=f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.warning("⚠️ Select transactions and classify them as 'Invoice' to generate PDF")
    
    with tab3:
        st.markdown('<div class="sub-header">Accounting Statements</div>', unsafe_allow_html=True)
        
        statements = generate_accounting_statements(edited_df)
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Opening Balance", f"₹{statements['totals']['opening_balance']:,.2f}")
        with col2:
            st.metric("Closing Balance", f"₹{statements['totals']['closing_balance']:,.2f}")
        with col3:
            st.metric("Net Change", f"₹{statements['totals']['net_change']:,.2f}",
                     delta=f"{statements['totals']['net_change']:,.2f}")
        
        st.divider()
        
        # Income Statement
        st.subheader("📊 Income Statement (Profit & Loss)")
        st.dataframe(statements['income_statement'], use_container_width=True)
        
        st.divider()
        
        # Balance Sheet
        st.subheader("💰 Balance Sheet Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Assets**")
            st.write(f"Cash & Bank: ₹{statements['balance_data']['Assets']['Cash and Bank Balance']:,.2f}")
        
        with col2:
            st.markdown("**Liabilities & Equity**")
            st.write(f"Opening Balance: ₹{statements['balance_data']['Liabilities']['Opening Balance']:,.2f}")
            st.write(f"Net Income: ₹{statements['balance_data']['Liabilities']['Net Income']:,.2f}")
        
        st.divider()
        
        # Classification Summary
        st.subheader("📋 Classification Summary")
        st.dataframe(statements['classification_summary'], use_container_width=True)
        
        st.divider()
        
        # Monthly Summary
        st.subheader("📅 Monthly Summary")
        st.dataframe(statements['monthly_summary'], use_container_width=True)
    
    with tab4:
        st.markdown('<div class="sub-header">Detailed Reports</div>', unsafe_allow_html=True)
        
        # Export options
        st.subheader("📥 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export all transactions
            csv = edited_df.to_csv(index=False)
            st.download_button(
                label="📊 Download All Transactions (CSV)",
                data=csv,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Export invoices only
            invoices_df = edited_df[edited_df['Classification'] == 'Invoice']
            if not invoices_df.empty:
                csv_inv = invoices_df.to_csv(index=False)
                st.download_button(
                    label="🧾 Download Invoices (CSV)",
                    data=csv_inv,
                    file_name=f"invoices_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            # Export expenses only
            expenses_df = edited_df[edited_df['Classification'] == 'Expense']
            if not expenses_df.empty:
                csv_exp = expenses_df.to_csv(index=False)
                st.download_button(
                    label="💸 Download Expenses (CSV)",
                    data=csv_exp,
                    file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        st.divider()
        
        # Detailed transaction list
        st.subheader("🔍 Transaction Details")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            type_filter = st.multiselect("Filter by Type", 
                                        options=df['Type'].unique(),
                                        default=df['Type'].unique())
        with col2:
            class_filter = st.multiselect("Filter by Classification",
                                         options=df['Classification'].unique(),
                                         default=df['Classification'].unique())
        
        filtered_df = edited_df[
            (edited_df['Type'].isin(type_filter)) &
            (edited_df['Classification'].isin(class_filter))
        ]
        
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

else:
    # Welcome screen
    st.info("👈 Please upload a Karnataka Bank statement PDF from the sidebar to get started!")
    
    # Instructions
    st.markdown("""
    ### 📚 How to Use:
    
    1. **Upload PDF**: Upload your Karnataka Bank statement PDF from the sidebar
    2. **Process**: Click "Process Statement" to extract transactions
    3. **Classify**: In the Transactions tab, classify each entry as Invoice or Expense
    4. **Assign Numbers**: Use the buttons to assign sequential numbers
    5. **Generate Invoices**: Select transactions and generate printable invoices (20 per A4 page)
    6. **View Statements**: Check the Accounting Statements tab for financial summaries
    7. **Export**: Download reports and data from the Reports tab
    
    ### ✨ Features:
    - 📄 Automatic PDF parsing
    - ✅ Interactive transaction classification with checkboxes
    - 🔢 Customizable invoice and expense numbering
    - 🖨️ Generate printable invoices (20 per A4 page)
    - 📊 Complete accounting statements (P&L, Balance Sheet)
    - 📈 Monthly summaries and reports
    - 💾 Export to CSV
    """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    <p>Bank Statement Processor v1.0 | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
