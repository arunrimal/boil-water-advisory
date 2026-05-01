import streamlit as st

st.set_page_config(
    page_title="Kansas BWA Dashboard",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

pg = st.navigation([
    st.Page("pages/00_home.py",             title="Home"               ),
    st.Page("pages/01_overview.py",         title="Overview"           ),
    st.Page("pages/02_cause_analysis.py",   title="AI Root Cause Analysis"),
    st.Page("pages/03_severity.py",         title="Severity Analysis"    ),
    st.Page("pages/04_repeat_offenders.py", title="Repeat Offenders" ),
    st.Page("pages/05_buffer_overlap.py",   title="Advisory Zones Overlap"),
])

pg.run()