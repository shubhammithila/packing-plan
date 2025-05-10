import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO

# Function to draw the swimlane diagram
def draw_swimlane_diagram(df, orientation='horizontal'):
    lanes = df['Owner'].unique().tolist()
    lane_positions = {lane: i for i, lane in enumerate(lanes if orientation == 'vertical' else reversed(lanes))}
    lane_count = len(lanes)
    step_count = len(df)

    fig_width = 24 if orientation == 'horizontal' else 10
    fig_height = 0.7 * lane_count if orientation == 'horizontal' else 0.6 * step_count
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')

    # Draw swimlanes
    if orientation == 'horizontal':
        ax.set_xlim(0, step_count)
        ax.set_ylim(0, lane_count)
        for i, lane in enumerate(reversed(lanes)):
            ax.add_patch(patches.Rectangle((0, i), step_count, 1, fill=False, edgecolor='gray'))
            ax.text(-0.3, i + 0.5, lane, va='center', ha='right', fontsize=10, fontweight='bold')
    else:
        ax.set_xlim(0, lane_count)
        ax.set_ylim(0, step_count)
        for i, lane in enumerate(lanes):
            ax.add_patch(patches.Rectangle((i, 0), 1, step_count, fill=False, edgecolor='gray'))
            ax.text(i + 0.5, step_count + 0.2, lane, ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Color mappings
    color_map = {
        "manual": "#e0e0e0",         # Gray
        "auto": "#c7f5d9",           # Green
        "yes": "#fff6bf",            # Yellow (can be automated)
        "partial": "#fff6bf",
        "already automated": "#c7f5d9"
    }

    # Draw each step
    for idx, row in df.iterrows():
        text = row['Activity']
        lane = row['Owner']
        auto_status = str(row['Can Be Automated?']).strip().lower()
        time_note = str(row['Time Taken']).strip()
        label = f"{text}\n⏱️ {time_note}"
        color = color_map.get(auto_status, "#e0e0e0")

        # Positioning
        if orientation == 'horizontal':
            x, y = idx, lane_positions[lane]
            w, h = 1, 1
        else:
            x, y = lane_positions[lane], step_count - idx - 1
            w, h = 1, 1

        # Box type
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", edgecolor='black', facecolor=color)
        ax.add_patch(box)
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=7.8, wrap=True)

    return fig

# Streamlit UI
st.title("🧭 Swimlane Diagram Generator")

uploaded_file = st.file_uploader("Upload process flow Excel or CSV", type=["xlsx", "csv"])
orientation = st.radio("Select Diagram Orientation", ["horizontal", "vertical"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    fig = draw_swimlane_diagram(df, orientation=orientation)
    st.pyplot(fig)

    # PNG export
    buf = BytesIO()
    fig.savefig(buf, format="png")
    st.download_button("📥 Download Diagram as PNG", data=buf.getvalue(), file_name="swimlane_diagram.png", mime="image/png")
