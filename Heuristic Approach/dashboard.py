"""
Streamlit Dashboard for Lead Generation
Interactive UI with sorting, filtering, and export capabilities
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import datetime

# Page configuration
st.set_page_config(
    page_title="Lead Generation Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .high-priority {
        background-color: #d4edda;
    }
    .medium-priority {
        background-color: #fff3cd;
    }
    .low-priority {
        background-color: #f8d7da;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data
def load_data(file_path: str = "enriched_leads.csv") -> pd.DataFrame:
    """Load lead data from CSV"""
    if not Path(file_path).exists():
        st.error(f"❌ Data file not found: {file_path}")
        st.info("Please run `python alternative_pipeline.py` first to generate the data.")
        st.stop()
    
    df = pd.read_csv(file_path)
    
    # Add action status column if not present
    if 'action_status' not in df.columns:
        df['action_status'] = 'Not Contacted'
    
    return df


def get_priority_category(score: float) -> str:
    """Categorize priority based on score"""
    if score >= 80:
        return "🔴 High Priority"
    elif score >= 60:
        return "🟡 Medium Priority"
    else:
        return "🟢 Low Priority"


def color_code_row(row):
    """Apply color coding based on priority"""
    if row['probability_score'] >= 80:
        return ['background-color: #d4edda'] * len(row)
    elif row['probability_score'] >= 60:
        return ['background-color: #fff3cd'] * len(row)
    else:
        return ['background-color: #f8d7da'] * len(row)


def main():
    # Header
    st.title("🎯 Lead Generation Dashboard")
    st.markdown("### Propensity-to-Buy Analysis for 3D In-Vitro Models")
    st.markdown("---")
    
    # Load data
    df = load_data()
    
    # Sidebar - Filters
    st.sidebar.header("🔍 Filters")
    
    # Priority filter
    priority_filter = st.sidebar.multiselect(
        "Priority Level",
        options=["🔴 High Priority", "🟡 Medium Priority", "🟢 Low Priority"],
        default=["🔴 High Priority", "🟡 Medium Priority", "🟢 Low Priority"]
    )
    
    # Score range filter
    min_score, max_score = st.sidebar.slider(
        "Probability Score Range",
        min_value=0,
        max_value=100,
        value=(0, 100),
        step=5
    )
    
    # Location filter
    all_locations = df['person_location'].unique().tolist()
    location_filter = st.sidebar.multiselect(
        "Location",
        options=all_locations,
        default=all_locations
    )
    
    # Company filter
    company_search = st.sidebar.text_input("🏢 Search Company", "")
    
    # Title filter
    title_search = st.sidebar.text_input("💼 Search Title", "")
    
    # Name filter
    name_search = st.sidebar.text_input("👤 Search Name", "")
    
    # Work mode filter
    work_mode_filter = st.sidebar.multiselect(
        "Work Mode",
        options=df['work_mode'].unique().tolist(),
        default=df['work_mode'].unique().tolist()
    )
    
    # Action status filter
    action_filter = st.sidebar.multiselect(
        "Action Status",
        options=df['action_status'].unique().tolist(),
        default=df['action_status'].unique().tolist()
    )
    
    st.sidebar.markdown("---")
    
    # Apply filters
    df['priority_category'] = df['probability_score'].apply(get_priority_category)
    
    filtered_df = df[
        (df['priority_category'].isin(priority_filter)) &
        (df['probability_score'] >= min_score) &
        (df['probability_score'] <= max_score) &
        (df['person_location'].isin(location_filter)) &
        (df['company'].str.contains(company_search, case=False, na=False)) &
        (df['title'].str.contains(title_search, case=False, na=False)) &
        (df['name'].str.contains(name_search, case=False, na=False)) &
        (df['work_mode'].isin(work_mode_filter)) &
        (df['action_status'].isin(action_filter))
    ]
    
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Total Leads", len(df))
    
    with col2:
        st.metric("✅ Filtered Leads", len(filtered_df))
    
    with col3:
        high_priority_count = len(df[df['probability_score'] >= 80])
        st.metric("🔴 High Priority", high_priority_count)
    
    with col4:
        avg_score = filtered_df['probability_score'].mean() if len(filtered_df) > 0 else 0
        st.metric("📈 Avg Score", f"{avg_score:.1f}")
    
    with col5:
        avg_pubs = filtered_df['publications'].mean() if len(filtered_df) > 0 else 0
        st.metric("📚 Avg Publications", f"{avg_pubs:.1f}")
    
    st.markdown("---")
    
    # Sorting options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📋 Lead List ({len(filtered_df)} results)")
    
    with col2:
        sort_by = st.selectbox(
            "Sort by:",
            options=['probability_score', 'rank', 'name', 'title', 'company', 'publications'],
            index=0
        )
        sort_order = st.radio("Order:", ["Descending", "Ascending"], horizontal=True)
    
    # Sort data
    ascending = sort_order == "Ascending"
    sorted_df = filtered_df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
    
    # Display data table
    if len(sorted_df) > 0:
        # Prepare display DataFrame
        display_df = sorted_df[[
            'rank', 'probability_score', 'name', 'title', 'company',
            'person_location', 'company_hq', 'work_mode', 'email',
            'linkedin_url', 'publications', 'action_status'
        ]].copy()
        
        # Rename columns for display
        display_df.columns = [
            'Rank', 'Probability', 'Name', 'Title', 'Company',
            'Location', 'HQ', 'Work Mode', 'Email',
            'LinkedIn', 'Publications', 'Action'
        ]
        
        # Make LinkedIn clickable
        display_df['LinkedIn'] = display_df['LinkedIn'].apply(
            lambda x: f'<a href="{x}" target="_blank">Profile</a>' if pd.notna(x) else ''
        )
        
        # Display table with styling
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                "Probability": st.column_config.ProgressColumn(
                    "Probability",
                    format="%.1f",
                    min_value=0,
                    max_value=100
                ),
                "Publications": st.column_config.NumberColumn("Pubs", format="%d"),
                "LinkedIn": st.column_config.LinkColumn("LinkedIn"),
            }
        )
        
        # Detailed view section
        st.markdown("---")
        st.subheader("🔍 Detailed View")
        
        selected_name = st.selectbox(
            "Select a lead to view details:",
            options=sorted_df['name'].tolist()
        )
        
        if selected_name:
            lead = sorted_df[sorted_df['name'] == selected_name].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Name:** {lead['name']}")
                st.markdown(f"**Title:** {lead['title']}")
                st.markdown(f"**Company:** {lead['company']}")
                st.markdown(f"**Location:** {lead['person_location']}")
            
            with col2:
                st.markdown(f"**Rank:** #{int(lead['rank'])}")
                st.markdown(f"**Probability Score:** {lead['probability_score']:.1f}/100")
                st.markdown(f"**Publications:** {int(lead['publications'])}")
                st.markdown(f"**Work Mode:** {lead['work_mode']}")
            
            with col3:
                st.markdown(f"**Email:** {lead['email']}")
                st.markdown(f"**LinkedIn:** [Profile]({lead['linkedin_url']})")
                st.markdown(f"**Company HQ:** {lead['company_hq']}")
                st.markdown(f"**Action Status:** {lead['action_status']}")
        
        # Export section
        st.markdown("---")
        st.subheader("📥 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV export
            csv = sorted_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download as CSV",
                data=csv,
                file_name=f"leads_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel export (requires openpyxl)
            try:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    sorted_df.to_excel(writer, index=False, sheet_name='Leads')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_data,
                    file_name=f"leads_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("Install openpyxl to enable Excel export: `pip install openpyxl`")
        
        with col3:
            # High priority only export
            high_priority_df = sorted_df[sorted_df['probability_score'] >= 80]
            if len(high_priority_df) > 0:
                csv_high = high_priority_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download High Priority",
                    data=csv_high,
                    file_name=f"high_priority_leads_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    else:
        st.warning("⚠️ No leads match the current filters. Try adjusting your search criteria.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p>🎯 Lead Generation Dashboard | Data sourced from PubMed & Scientific Publications</p>
            <p>Scoring based on: Role Relevance (30%) | Funding Stage (20%) | Tech Adoption (15%) | 
            NAM Openness (10%) | Biotech Hub (10%) | Recent Publications (40%)</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
