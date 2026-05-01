import streamlit as st
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely import wkt
from datetime import datetime
import time
from utils.styles import load_css, load_footer
from utils.data_loader import load_bwa_data, get_data_path, validate_and_warn
import os

load_css()


# =============================================================================
# PAGE CONFIG — first Streamlit command
# =============================================================================
st.set_page_config(
    page_title="Kansas BWA | Geospatial Dashboard",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# DATA LOADING
# =============================================================================
# ROOT          = Path(__file__).resolve().parent
# while not (ROOT / "outputs").exists():
#     ROOT = ROOT.parent

# OUTPUTS_FILE  = ROOT / "outputs" / "geocoded_output.gpkg"
# COUNTIES_SHP  = ROOT / "tl_2024_us_county" / "tl_2024_us_county.shp"

# data_exists = OUTPUTS_FILE.exists()


# Replace all path logic with just:
data_path = get_data_path()
data_exists = True if os.getenv("ENV") == "cloud" else Path(str(data_path)).exists()




@st.cache_data(show_spinner=False)
def load_summary():
    """Load minimal summary stats for landing page metrics."""
    gdf = load_bwa_data()
    # validate_and_warn(gdf)  # ← only in main.py, not in any other page
    
    if gdf is None:
        return None
    
    return {
        "total"     : len(gdf),
        "counties"  : gdf["County"].nunique(),
        "systems"   : gdf["Federal_ID"].nunique(),
        "years"     : f"{int(gdf['Year'].min())}–{int(gdf['Year'].max())}",
        "year_count": gdf["Year"].nunique(),
        "pop"       : int(gdf["Population_Served"].sum()),
        "updated"   : datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

summary = load_summary()
data_exists = summary is not None


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:1rem 0 0.5rem'>"
        "<span style='font-size:2.5rem'>💧</span><br>"
        "<span style='font-size:1.1rem;font-weight:700;color:#e0e0e0'>"
        "Kansas BWA</span><br>"
        "<span style='font-size:0.78rem;color:#6e7681'>"
        "Geospatial Dashboard</span>"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    st.markdown(
        "<div style='color:#8b949e;font-size:0.82rem;line-height:1.7'>"
        "End-to-end geospatial analysis of <b style='color:#e0e0e0'>"
        "Boil Water Advisories</b> issued by the Kansas Department of "
        "Health & Environment (KDHE) across all 105 Kansas counties."
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Pipeline status
    st.markdown(
        "<div style='color:#6e7681;font-size:0.72rem;text-transform:uppercase;"
        "letter-spacing:1px;margin-bottom:0.5rem'>Pipeline Status</div>",
        unsafe_allow_html=True
    )
    if data_exists and summary:
        st.markdown(
            f"<div class='status-ok'>"
            f"<span class='dot-ok'></span> Data Ready"
            f"</div>"
            f"<div style='color:#6e7681;font-size:0.75rem;margin-top:0.4rem'>"
            f"Updated: {summary['updated']}"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div class='status-err'>"
            "<span class='dot-err'></span> No Data Found"
            "</div>"
            "<div style='color:#6e7681;font-size:0.75rem;margin-top:0.4rem'>"
            "Run the pipeline to generate outputs/"
            "</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Data source info
    st.markdown(
        "<div style='color:#6e7681;font-size:0.72rem;text-transform:uppercase;"
        "letter-spacing:1px;margin-bottom:0.5rem'>Data Source</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='color:#8b949e;font-size:0.8rem;line-height:1.7'>"
        "🌐 KDHE Disruption in Water Service<br>"
        "📅 2021 – 2026<br>"
        "📍 265 geocoded notices<br>"
        "🗺️ 10 km impact buffers"
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Tech stack
    st.markdown(
        "<div style='color:#6e7681;font-size:0.72rem;text-transform:uppercase;"
        "letter-spacing:1px;margin-bottom:0.5rem'>Built With</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='color:#8b949e;font-size:0.8rem;line-height:1.8'>"
        "⚙️ Airflow + Docker<br>"
        "🐍 Python · GeoPandas<br>"
        "📊 Plotly · Folium<br>"
        "🚀 Streamlit"
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown(
        "<div style='color:#6e7681;font-size:0.75rem;text-align:center'>"
        "Arun Rimal · aarunrimal92@gmail.com"
        "</div>",
        unsafe_allow_html=True
    )


# =============================================================================
# HERO SECTION
# =============================================================================
st.markdown(
    "<div class='hero-title'>"
    "Kansas Boil Water<br>Advisory Analysis"
    "</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div class='hero-subtitle'>"
    "A geospatial investigation into public water safety across 105 Kansas counties · "
    "Scraped · NER Extracted · AI Classified · Geocoded · "
    "Orchestrated on Airflow + Docker"
    "</div>",
    unsafe_allow_html=True
)

st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)


# =============================================================================
# ANIMATED METRIC CARDS
# =============================================================================
st.markdown(
    "<div class='section-label'>At a glance</div>",
    unsafe_allow_html=True
)

if summary:
    c1, c2, c3, c4, c5 = st.columns(5)

    cards = [
        (c1, summary["total"],      "Total Advisories",    "2021 – 2026"),
        (c2, summary["counties"],   "Counties Affected",   "of 105 in Kansas"),
        (c3, summary["systems"],    "Unique Water Systems", "Federal IDs"),
        (c4, summary["year_count"], "Years of Data",        summary["years"]),
        (c5, f"{summary['pop']:,}", "Population Exposed",   "cumulative"),
    ]

    for col, number, label, sub in cards:
        with col:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-number'>{number}</div>"
                f"<div class='metric-label'>{label}</div>"
                f"<div class='metric-sub'>{sub}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
else:
    st.warning(
        "⚠️ Pipeline output not found. "
        "Run the Airflow pipeline to generate `outputs/geocoded_output.gpkg`.",
        icon="🚫"
    )

st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)


# =============================================================================
# PAGE NAVIGATION CARDS
# =============================================================================
st.markdown(
    "<div class='section-label'>Explore the Dashboard</div>",
    unsafe_allow_html=True
)

pages = [
    {
        "icon"  : "🗺️",
        "title" : "Overview",
        "desc"  : "County choropleth, point map, temporal trends, "
                  "and top systems by severity. The full picture at a glance.",
        "tag"   : "Start here",
        "tag_color": "rgba(255,107,107,0.15)",
        "tag_text" : "#FF6B6B",
        "file"  : "pages/01_overview.py",
    },
    {
        "icon"  : "🔬",
        "title" : "Cause Analysis",
        "desc"  : "Spatial clustering of advisory categories — infrastructure "
                  "failure, contamination, equipment failure and more.",
        "tag"   : "Spatial",
        "tag_color": "rgba(74,158,255,0.15)",
        "tag_text" : "#4A9EFF",
        "file"  : "pages/02_cause_analysis.py",
    },
    {
        "icon"  : "🌡️",
        "title" : "Severity Analysis",
        "desc"  : "KDE hotspot map weighted by Duration × Population × Violations. "
                  "Where is the public health risk highest?",
        "tag"   : "Risk",
        "tag_color": "rgba(255,142,83,0.15)",
        "tag_text" : "#FF8E53",
        "file"  : "pages/03_severity.py",
    },
    {
        "icon"  : "🔁",
        "title" : "Repeat Offenders",
        "desc"  : "Water systems with chronic advisory histories. "
                  "Identifying infrastructure failure patterns over time.",
        "tag"   : "Systems",
        "tag_color": "rgba(0,212,170,0.15)",
        "tag_text" : "#00D4AA",
        "file"  : "pages/04_repeat_offenders.py",
    },
    {
        "icon"  : "📡",
        "title" : "Buffer Overlap",
        "desc"  : "Concurrent 10 km impact zone overlaps between water systems. "
                  "Where did multiple advisories hit the same area simultaneously?",
        "tag"   : "Spatial",
        "tag_color": "rgba(139,92,246,0.15)",
        "tag_text" : "#8B5CF6",
        "file"  : "pages/05_buffer_overlap.py",
    },
]

cols = st.columns(5)

for col, page in zip(cols, pages):
    with col:
        st.markdown(
            f"<div class='page-card'>"
            f"<span class='page-icon'>{page['icon']}</span>"
            f"<div class='page-title'>{page['title']}</div>"
            f"<div class='page-desc'>{page['desc']}</div>"
            f"<span class='page-tag' style='"
            f"background:{page['tag_color']};"
            f"color:{page['tag_text']};'>"
            f"{page['tag']}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        # Add real navigation link below each card
        st.page_link(
            page["file"],
            label=f"Open {page['title']} →",
            width='stretch'
        )

st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)


# =============================================================================
# ABOUT THE DATA
# =============================================================================
st.markdown(
    "<div class='section-label'>About the Data & Methodology</div>",
    unsafe_allow_html=True
)

col_about, col_pipeline = st.columns([3, 2])

with col_about:
    st.markdown(
        "<div class='about-box'>"
        "The <b>Kansas Department of Health and Environment (KDHE)</b> issues "
        "Boil Water Advisories (BWAs) when a public water supply system reports "
        "that contamination may pose a threat to public health. This dashboard "
        "analyzes every advisory issued between <b>2021 and 2026</b>, scraped "
        "directly from the KDHE public bulletin.<br><br>"
        "Each advisory was <b>geocoded</b> to its city centroid, and a "
        "<b>10 km circular buffer</b> was applied as a proxy for the distribution "
        "system's impact area — since advisories are issued at the system level, "
        "not the county level. Advisory reasons were extracted using a "
        "<b>custom NER pipeline</b> and classified into six categories.<br><br>"
        "Severity is computed as: "
        "<b>Duration (days) × Population Served × Number of Violations</b>."
        "</div>",
        unsafe_allow_html=True
    )

with col_pipeline:
    st.markdown(
        "<div class='about-box'>"
        "<b>Pipeline Architecture</b><br><br>"
        "⚙️ <b>Airflow</b> — DAG Orchestration<br>"
        "🐳 <b>Docker</b> — Containerized Environment<br>"
        "🕷️ <b>Web Scraping</b> — KDHE Bulletin<br>"
        "🔧 <b>Feature Engineering</b> — Date, Duration<br>"
        "📖 <b>NER</b> — NLP extraction<br>"
        "🧠 <b>LLM</b> — Advisory Classification<br>"
        "🗺️ <b>Geocoding</b> — City → Lat/Lon<br>"
        "📦 <b>GeoPackage output</b> — Final .gpkg<br>"
        "</div>",
        unsafe_allow_html=True
    )

st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)


# =============================================================================
# TECH STACK BADGES
# =============================================================================
st.markdown(
    "<div class='section-label'>Tech Stack</div>",
    unsafe_allow_html=True
)

badges = [
    # Core language & framework
    "Python 3.11", "Streamlit",
    # Pipeline & orchestration
    "Apache Airflow", "Docker",
    # NLP & AI
    "spaCy", "Gemini 2.5 Flash",
    # Geospatial
    "GeoPandas", "Shapely", "Folium", "Plotly",
    # Data
    "Pandas",
    # Infrastructure
    "Google Cloud", "Compute Engine", "Cloud Storage",
    # DevOps
    "Terraform", "Jenkins", "GitHub",
]

st.markdown(
    "".join(f"<span class='badge'>{b}</span>" for b in badges),
    unsafe_allow_html=True
)


# =============================================================================
# FOOTER
# =============================================================================
load_footer()