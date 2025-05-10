import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

# Constants
DATA_FILE_PATH = "latest_packing_plan.xlsx"
UPLOAD_HISTORY_FILE = "upload_history.txt"
LOGO_PATH = "logo.png"

# -------------------------------
# Helper Functions
# -------------------------------

def process_uploaded_file(uploaded_file):
    xl = pd.ExcelFile(uploaded_file)
    df = xl.parse(xl.sheet_names[0])

    if 'Pouch Size' not in df.columns:
        df['Pouch Size'] = None
    if 'ASIN' not in df.columns:
        df['ASIN'] = None

    df['Total Weight Sold (kg)'] = None
    current_parent = None
    parent_indices = []

    for idx, row in df.iterrows():
        item = str(row['Row Labels']).strip()
        if not item.replace('.', '', 1).isdigit():
            current_parent = item
            parent_indices.append(idx)
        else:
            try:
                weight = float(item)
                units = row['Sum of Units Ordered']
                total_weight = weight * units
                df.at[idx, 'Total Weight Sold (kg)'] = total_weight
            except ValueError:
                pass

    for idx in parent_indices:
        total = 0
        for next_idx in range(idx + 1, len(df)):
            next_item = str(df.at[next_idx, 'Row Labels']).strip()
            if not next_item.replace('.', '', 1).isdigit():
                break
            weight = df.at[next_idx, 'Total Weight Sold (kg)']
            if pd.notna(weight):
                total += weight
        df.at[idx, 'Total Weight Sold (kg)'] = total

    df['Contribution %'] = None
    current_parent_total = None

    for idx, row in df.iterrows():
        item = str(row['Row Labels']).strip()
        if not item.replace('.', '', 1).isdigit():
            current_parent_total = row['Total Weight Sold (kg)']
        else:
            try:
                total_weight = row['Total Weight Sold (kg)']
                if pd.notna(total_weight) and pd.notna(current_parent_total) and current_parent_total != 0:
                    contribution = (float(total_weight) / float(current_parent_total)) * 100
                    df.at[idx, 'Contribution %'] = round(contribution, 2)
            except ValueError:
                pass

    return df

def round_to_nearest_2(x):
    return int(2 * round(x / 2)) if pd.notna(x) else None

def adjust_packets(result_df, target_weight):
    packed_weight = result_df['Weight Packed (kg)'].sum()
    deviation = (target_weight - packed_weight) / target_weight

    while (packed_weight > target_weight) or (abs(deviation) > 0.05):
        if packed_weight > target_weight:
            idx = result_df['Variation (kg)'].idxmax()
            if result_df.at[idx, 'Packets to Pack'] >= 2:
                result_df.at[idx, 'Packets to Pack'] -= 2
        elif deviation > 0:
            idx = result_df['Variation (kg)'].idxmin()
            result_df.at[idx, 'Packets to Pack'] += 2
        else:
            break

        result_df['Weight Packed (kg)'] = result_df['Variation (kg)'] * result_df['Packets to Pack']
        packed_weight = result_df['Weight Packed (kg)'].sum()
        deviation = (target_weight - packed_weight) / target_weight

    return result_df

def generate_combined_pdf(packing_summary, combined_total, combined_loose, logo_path):
    pdf = FPDF()
    pdf.add_page()

    if os.path.exists(logo_path):
        pdf.image(logo_path, x=80, y=10, w=50)
        pdf.ln(30)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, f"Mithila Foods Packing Plan", ln=True, align='C')

    pdf.set_font("Arial", size=11)
    pdf.cell(200, 10, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(5)

    for item_block in packing_summary:
        item = item_block['item']
        total_weight = item_block['target_weight']
        packed_weight = item_block['packed_weight']
        loose_weight = item_block['loose_weight']
        variations = item_block['data']

        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, f"Item: {item}", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 8, f"Target: {total_weight} kg | Packed: {packed_weight:.2f} kg | Loose: {loose_weight:.2f} kg", ln=True)
        
        pdf.set_font("Arial", size=10)
        pdf.cell(30, 8, "Variation", border=1)
        pdf.cell(35, 8, "Pouch Size", border=1)
        pdf.cell(45, 8, "ASIN", border=1)
        pdf.cell(30, 8, "Packets", border=1)
        pdf.cell(40, 8, "Packed (kg)", border=1)
        pdf.ln()

        for _, row in variations.iterrows():
            pdf.cell(30, 8, f"{row['Variation (kg)']}", border=1)
            pdf.cell(35, 8, str(row['Pouch Size']), border=1)
            pdf.cell(45, 8, str(row['ASIN']), border=1)
            pdf.cell(30, 8, f"{int(row['Packets to Pack'])}", border=1)
            pdf.cell(40, 8, f"{row['Weight Packed (kg)']:.2f}", border=1)
            pdf.ln()
        
        pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, f"TOTAL PACKED: {combined_total:.2f} kg | TOTAL LOOSE: {combined_loose:.2f} kg", ln=True, align='C')

    return pdf.output(dest='S').encode('latin1')

# -------------------------------
# Streamlit App
# -------------------------------

st.set_page_config(page_title="Mithila Packing Plan", layout="wide")
st.title("📦 Mithila Foods Packing Plan")

mode = st.sidebar.radio("Choose Mode:", ["User", "Admin"])

if mode == "Admin":
    st.sidebar.subheader("🔒 Admin Login")
    password = st.sidebar.text_input("Enter Admin Password", type="password")

    if password == "admin123":
        st.success("Welcome, Admin!")
        st.subheader("📤 Upload New Packing Plan")

        uploaded_file = st.file_uploader("Upload Packing Plan", type=["xlsx"])
        if uploaded_file:
            with open(DATA_FILE_PATH, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with open(UPLOAD_HISTORY_FILE, "a") as f:
                f.write(f"{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n")
            st.success("Packing Plan uploaded successfully!")

        if os.path.exists(UPLOAD_HISTORY_FILE):
            st.subheader("🕒 Upload History")
            with open(UPLOAD_HISTORY_FILE) as f:
                history = f.readlines()
                for line in reversed(history[-5:]):
                    st.text(line.strip())
    else:
        if password:
            st.error("Incorrect password.")

else:
    if not os.path.exists(DATA_FILE_PATH):
        st.error("No packing plan uploaded yet.")
    else:
        df_full = process_uploaded_file(DATA_FILE_PATH)
        parent_items = df_full[~df_full['Row Labels'].astype(str).str.replace('.', '', 1).str.isnumeric()]['Row Labels'].tolist()

        selected_items = st.multiselect("Select Items to Pack:", parent_items)
        packing_summary = []
        total_combined_weight = 0
        total_combined_loose = 0

        for selected_item in selected_items:
            st.subheader(f"📦 {selected_item}")
            target_weight = st.number_input(f"Enter weight to pack for {selected_item} (kg):", min_value=1, value=100, step=10)

            idx_parent = df_full[df_full['Row Labels'] == selected_item].index[0]
            variations = []
            for i in range(idx_parent + 1, len(df_full)):
                label = str(df_full.at[i, 'Row Labels']).strip()
                if not label.replace('.', '', 1).isdigit():
                    break
                variations.append({
                    'Variation (kg)': float(label),
                    'Contribution %': df_full.at[i, 'Contribution %'],
                    'Pouch Size': df_full.at[i, 'Pouch Size'],
                    'ASIN': df_full.at[i, 'ASIN']
                })

            result = []
            for var in variations:
                packets = (var['Contribution %'] / 100) * target_weight / var['Variation (kg)']
                packets = round_to_nearest_2(packets)
                weight_packed = packets * var['Variation (kg)']
                result.append({
                    'Variation (kg)': var['Variation (kg)'],
                    'Pouch Size': var['Pouch Size'],
                    'ASIN': var['ASIN'],
                    'Packets to Pack': packets,
                    'Weight Packed (kg)': weight_packed
                })

            result_df = pd.DataFrame(result)
            result_df = adjust_packets(result_df, target_weight)

            packed_weight = result_df['Weight Packed (kg)'].sum()
            loose_weight = target_weight - packed_weight

            st.dataframe(result_df[['Variation (kg)', 'Pouch Size', 'ASIN', 'Packets to Pack', 'Weight Packed (kg)']])

            packing_summary.append({
                'item': selected_item,
                'target_weight': target_weight,
                'packed_weight': packed_weight,
                'loose_weight': loose_weight,
                'data': result_df
            })

            total_combined_weight += packed_weight
            total_combined_loose += loose_weight

        if packing_summary:
            pdf_data = generate_combined_pdf(packing_summary, total_combined_weight, total_combined_loose, LOGO_PATH)

            st.download_button(
                label="📄 Download Combined Packing Plan PDF",
                data=pdf_data,
                file_name="MithilaFoods_PackingPlan.pdf",
                mime='application/pdf'
            )
