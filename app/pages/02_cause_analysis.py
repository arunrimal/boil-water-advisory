import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
from pathlib import Path
from utils.data_loader import load_bwa_data as load_data, load_kansas_counties as load_counties
from utils.styles import load_css, load_footer, PLOT_BASE, AXIS_STYLE, CORAL, ORANGE, BLUE, TEAL, GRAY, SEVERITY_COLORSCALE
# from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

load_css()

# =============================================================================
# PAGE CONFIG — must be first Streamlit command
# =============================================================================
st.set_page_config(
    page_title="Cause Analysis",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# LOAD DATA
# =============================================================================
bwa = load_data()

if bwa is None:
    st.error(
        "⚠️ Data not found. Please run the pipeline first so that "
        "`outputs/geocoded_output.gpkg` exists.",
        icon="🚫"
    )
    st.stop()

ks_counties = load_counties()

# =============================================================================
# COLOR MAP — one color per Advisory_Category
# =============================================================================
CATEGORY_COLORS = {
    "infrastructure_failure"   : "#FF6B6B",
    "equipment_failure"        : "#57DCF3",
    "planned_maintenance"      : "#4A9EFF",
    "contamination_confirmed"  : "#FFFFFF",
    "natural_disaster"         : "#00D4AA",
    "other"                    : "#efe559",
}
 
# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown("<div class='hero-title' style='font-size:2rem'>Cause-Type Analysis</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div class='hero-subtitle' style='font-size:0.95rem'>"
    "Do different advisory causes cluster in different parts of Kansas? "
    "Exploring spatial and temporal patterns by Advisory Category."
    "</div>",
    unsafe_allow_html=True
)
 
# =============================================================================
# SIDEBAR FILTERS  
# =============================================================================
with st.sidebar:
    # -- copy sidebar CSS wrapper from main.py --
 
    all_years    = sorted(bwa["Year"].unique().tolist(), reverse=True)
    selected_year = st.selectbox(
        "📅 Year",
        ["All years"] + [str(y) for y in all_years]
    )
    all_cats     = sorted(bwa["Advisory_Category"].dropna().unique().tolist())
    selected_cats = st.multiselect(
        "🔬 Advisory Category",
        options=all_cats,
        default=[],
        placeholder="All categories"
    )
    dur_range = st.slider(
        "⏱️ Duration (days)",
        min_value=1,
        max_value=int(bwa["Advisory_Duration"].max()),
        value=(1, int(bwa["Advisory_Duration"].max()))
    )
 
# -- Apply filters --
filtered = bwa.copy()
if selected_year != "All years":
    filtered = filtered[filtered["Year"] == int(selected_year)]
if selected_cats:
    filtered = filtered[filtered["Advisory_Category"].isin(selected_cats)]
filtered = filtered[
    (filtered["Advisory_Duration"] >= dur_range[0]) &
    (filtered["Advisory_Duration"] <= dur_range[1])
]
 
# =============================================================================
# KPI ROW — cause-specific metrics
# =============================================================================
st.markdown("<div class='section-label'>Cause Breakdown</div>", unsafe_allow_html=True)
 
cat_counts = filtered["Advisory_Category"].value_counts()
top_cat    = cat_counts.index[0] if len(cat_counts) > 0 else "N/A"
top_count  = cat_counts.iloc[0]  if len(cat_counts) > 0 else 0
avg_dur_by_cat = filtered.groupby("Advisory_Category")["Advisory_Duration"].mean()
longest_cat    = avg_dur_by_cat.idxmax() if len(avg_dur_by_cat) > 0 else "N/A"
 
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Notices",      len(filtered))
c2.metric("Categories Present", filtered["Advisory_Category"].nunique())
c3.metric("Most Frequent",      top_cat.replace("_", " ").title(), delta=f"{top_count} notices")
c4.metric("Longest Avg Duration", longest_cat.replace("_", " ").title(),
          delta=f"{avg_dur_by_cat.max():.1f} days avg")
 
st.markdown("<br>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 1 — Color-coded interactive map (all categories on one map)
# =============================================================================
st.markdown("<div class='section-label'>Spatial Distribution by Category</div>",
            unsafe_allow_html=True)
 
filtered["category_label"] = filtered["Advisory_Category"].str.replace("_", " ").str.title()

# # Use st.toggle for a more modern, compact look than st.checkbox
# is_light_map = st.toggle("Light Map", value=False, key="map_theme_toggle")    
# map_style = "carto-positron" if is_light_map else "carto-darkmatter"
with st.container():
    is_light_map = st.toggle(
        "☀️ Light Mode",
        value=False,
        key="map_theme_toggle"
    )

    map_style = "carto-positron" if is_light_map else "carto-darkmatter"

fig_map = px.scatter_mapbox(
    filtered,
    lat="lat",
    lon="lon",
    color="category_label",
    size="Advisory_Duration",
    size_max=18,
    hover_name="PWS_Name",
    hover_data={
        "County"           : True,
        "Year"             : True,
        "Advisory_Duration": True,
        "Population_Served": True,
        "category_label"   : False,
        "lat"              : False,
        "lon"              : False,
    },
    color_discrete_map={
        k.replace("_", " ").title(): v for k, v in CATEGORY_COLORS.items()
    },
    zoom=6,
    center={"lat": 38.5, "lon": -98.0},
    height=500,
    mapbox_style=map_style,
    labels={"category_label": "Category"},
)
fig_map.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0"),
    margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(
        title=dict(text="Category", font=dict(color="#8b949e", size=11)),
        font=dict(color="#e0e0e0", size=11),
        bgcolor="rgba(22,27,34,0.85)",
        bordercolor="rgba(255,255,255,0.08)",
        borderwidth=1,
    ),
)
st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
st.plotly_chart(fig_map, width='stretch', config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 2 — Faceted map (from your notebook — one subplot per category)
# =============================================================================
st.markdown("<div class='section-label'>Faceted Map — One Panel per Category</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div style='color:#6e7681;font-size:0.85rem;margin-bottom:0.8rem'>"
    "Each panel shows where that cause type occurs geographically across Kansas."
    "</div>",
    unsafe_allow_html=True
)
 
categories  = sorted(filtered["Advisory_Category"].dropna().unique())
n_cats      = len(categories)
n_cols      = 3
n_rows      = int(np.ceil(n_cats / n_cols))
 
fig_facet, axes = plt.subplots(
    n_rows, n_cols,
    figsize=(18, n_rows * 5),
    facecolor="#0e1117"
)
axes = axes.flatten()
 
for i, cat in enumerate(categories):
    ax     = axes[i]
    subset = filtered[filtered["Advisory_Category"] == cat]
    # color  = CATEGORY_COLORS.get(cat, "#888888")
    color  = CATEGORY_COLORS.get(cat, "#F2EEEE")


    # County base layer
    ks_counties.plot(ax=ax, color="#03132E80", edgecolor="#ced4df", linewidth=0.5)
 
    # Advisory points sized by population
    if len(subset) > 0:
        subset.plot(
            ax=ax,
            color=color,
            # markersize=subset["Population_Served"].clip(upper=35000) / 40,
            markersize=subset["Population_Served"].clip(upper=filtered["Population_Served"].max()) / 25,
            alpha=0.75,
            edgecolor="#0e1117",
            linewidth=0.3,
        )
 
    ax.set_facecolor("#0e1117")
    ax.set_title(
        f"{cat.replace('_', ' ').title()}  (n={len(subset)})",
        fontsize=11, fontweight="bold",
        color="#e0e0e0", pad=8
    )
    ax.set_axis_off()
    
    # Add dot-size legend
    ax.annotate(
        "● size = population served",
        xy=(0.02, 0.02), xycoords="axes fraction",
        fontsize=7, color="#6e7681"
    )
 
# Hide unused subplots
for j in range(len(categories), len(axes)):
    axes[j].set_visible(False)
 
plt.suptitle(
    "Boil Water Advisory Cause-Type — Spatial Distribution",
    fontsize=14, fontweight="bold",
    color="#e0e0e0", y=1.01
)
plt.tight_layout()
 
st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
st.pyplot(fig_facet, width='stretch')
st.markdown("</div>", unsafe_allow_html=True)
plt.close()
 
# =============================================================================
# VIZ 3 + VIZ 4 — side by side
# =============================================================================
col_box, col_trend = st.columns(2)
 
# ── VIZ 3 — Duration boxplot by category ────────────────────────────────────
with col_box:
    st.markdown("<div class='section-label'>Duration by Category</div>",
                unsafe_allow_html=True)
 
    box_data = []
    for cat in categories:
        subset = filtered[filtered["Advisory_Category"] == cat]["Advisory_Duration"]
        for val in subset:
            box_data.append({"Category": cat.replace("_", " ").title(), "Duration": val})
    box_df = pd.DataFrame(box_data)
 
    fig_box = go.Figure()
    for cat in categories:
        label  = cat.replace("_", " ").title()
        subset = box_df[box_df["Category"] == label]["Duration"]
        fig_box.add_trace(go.Box(
            y=subset,
            name=label,
            marker=dict(color=CATEGORY_COLORS.get(cat, "#888")),
            line=dict(color=CATEGORY_COLORS.get(cat, "#888")),
            boxmean=True,
            hovertemplate=f"<b>{label}</b><br>Duration: %{{y}} days<extra></extra>",
        ))
 
    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter, sans-serif"),
        title=dict(text="Advisory Duration by Cause Type",
                   font=dict(color="#e0e0e0", size=13), x=0.5),
        xaxis=dict(showgrid=False, color="#6e7681",
                   tickfont=dict(size=9), tickangle=-20),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", title="Days",
                   title_font=dict(size=11), zeroline=False),
        showlegend=False,
        height=400,
        margin=dict(l=10, r=10, t=45, b=60),
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_box, width='stretch', config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
 
# ── VIZ 4 — Category trend over years ───────────────────────────────────────
with col_trend:
    st.markdown("<div class='section-label'>Category Trend Over Years</div>",
                unsafe_allow_html=True)
 
    trend_df = (
        bwa.groupby(["Year", "Advisory_Category"])
        .size()
        .reset_index(name="count")
    )
    trend_df["label"] = trend_df["Advisory_Category"].str.replace("_", " ").str.title()
 
    fig_trend = go.Figure()
    for cat in sorted(bwa["Advisory_Category"].dropna().unique()):
        subset = trend_df[trend_df["Advisory_Category"] == cat]
        label  = cat.replace("_", " ").title()
        fig_trend.add_trace(go.Scatter(
            x=subset["Year"],
            y=subset["count"],
            mode="lines+markers",
            name=label,
            line=dict(color=CATEGORY_COLORS.get(cat, "#888"), width=2.5),
            marker=dict(size=7, color=CATEGORY_COLORS.get(cat, "#888"),
                        line=dict(color="#0e1117", width=1.5)),
            hovertemplate=f"<b>{label}</b><br>Year: %{{x}}<br>Count: %{{y}}<extra></extra>",
        ))
 
    fig_trend.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter, sans-serif"),
        title=dict(text="Advisory Category Trend by Year",
                   font=dict(color="#e0e0e0", size=13), x=0.5),
        xaxis=dict(showgrid=False, color="#6e7681",
                   dtick=1, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", title="Count",
                   title_font=dict(size=11), zeroline=False),
        legend=dict(
            font=dict(color="#e0e0e0", size=10),
            bgcolor="rgba(0,0,0,0)",
            orientation="v",
        ),
        height=400,
        margin=dict(l=10, r=10, t=45, b=10),
        hovermode="x unified",
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_trend, width='stretch', config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================
load_footer()