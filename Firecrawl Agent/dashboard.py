import streamlit as st
import pandas as pd
import io

# Page config
st.set_page_config(
    page_title="Lead Scoring Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for color coding
st.markdown("""
    <style>
    .high-score {
        background-color: #d4edda;
        padding: 5px;
        border-radius: 5px;
        font-weight: bold;
    }
    .medium-score {
        background-color: #fff3cd;
        padding: 5px;
        border-radius: 5px;
        font-weight: bold;
    }
    .low-score {
        background-color: #f8d7da;
        padding: 5px;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('scored_leads.csv')
    return df

df = load_data()

# Title
st.title("🎯 Lead Scoring Dashboard")
st.markdown("---")

# Filters in columns
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input(
        "🔍 Search by name, company, title, or location",
        placeholder="Type to search..."
    )

with col2:
    min_score, max_score = st.slider(
        "Probability Score Range",
        min_value=0,
        max_value=100,
        value=(0, 100),
        step=5
    )

with col3:
    work_modes = st.multiselect(
        "Work Mode",
        options=df['work_mode'].unique().tolist(),
        default=df['work_mode'].unique().tolist()
    )

st.markdown("---")

# Apply filters
filtered_df = df.copy()

# Search filter
if search_query:
    mask = (
        filtered_df['name'].str.contains(search_query, case=False, na=False) |
        filtered_df['company'].str.contains(search_query, case=False, na=False) |
        filtered_df['title'].str.contains(search_query, case=False, na=False) |
        filtered_df['person_locaton'].str.contains(search_query, case=False, na=False) |
        filtered_df['company_hq'].str.contains(search_query, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

# Probability score filter
filtered_df = filtered_df[
    (filtered_df['probability_score'] >= min_score) &
    (filtered_df['probability_score'] <= max_score)
]

# Work mode filter
if work_modes:
    filtered_df = filtered_df[filtered_df['work_mode'].isin(work_modes)]

# Display count
st.write(f"**Showing {len(filtered_df)} of {len(df)} leads**")

# Function to apply color coding to probability score
def color_probability(val):
    if val > 70:
        return 'background-color: #d4edda; font-weight: bold'
    elif val >= 40:
        return 'background-color: #fff3cd; font-weight: bold'
    else:
        return 'background-color: #f8d7da; font-weight: bold'

# Display table with color coding
if len(filtered_df) > 0:
    styled_df = filtered_df.style.applymap(
        color_probability,
        subset=['probability_score']
    ).format({'probability_score': '{:.0f}'})
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600
    )
else:
    st.warning("No leads match the current filters.")

# Export buttons
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    # CSV export
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export to CSV",
        data=csv,
        file_name="filtered_leads.csv",
        mime="text/csv"
    )

with col2:
    # Excel export
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Leads')
    
    st.download_button(
        label="📥 Export to Excel",
        data=buffer.getvalue(),
        file_name="filtered_leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
