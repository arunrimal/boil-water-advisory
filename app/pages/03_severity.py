import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from shapely import wkt
from scipy.stats import gaussian_kde
from utils.data_loader import load_bwa_data as load_data, load_kansas_counties as load_counties
from utils.styles import load_css, load_footer, PLOT_BASE, AXIS_STYLE, CORAL, ORANGE, BLUE, TEAL, GRAY, SEVERITY_COLORSCALE

load_css()

# =============================================================================
# PAGE CONFIG — must be first Streamlit command
# =============================================================================
# st.set_page_config(
#     page_title="Severity Analysis",
#     page_icon="💧",
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )

# =============================================================================
# LOAD DATA
# =============================================================================
bwa = load_data()
ks_counties = load_counties()

if bwa is None:
    st.error(
        "⚠️ Data not found. Please run the pipeline first so that "
        "`outputs/geocoded_output.gpkg` exists.",
        icon="🚫"
    )
    st.stop()

st.markdown("<div class='hero-title' style='font-size:2rem'>Severity Analysis</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div class='hero-subtitle' style='font-size:0.95rem'>"
    "Not all advisories carry the same public health risk. "
    "A short advisory affecting a small rural system is fundamentally different "
    "from a prolonged advisory affecting thousands of residents with multiple violations. "
    "To capture this, a composite <b>severity index</b> was constructed as "
    "<span style='color:#FF6B6B'><b>Duration</b></span> × "
    "<span style='color:#FF6B6B'><b>Population Served</b></span> × "
    "<span style='color:#FF6B6B'><b>Number of Violations</b></span> — "
    "identifying where the cumulative risk is highest across Kansas."
    "</div>",
    unsafe_allow_html=True
)
 
# =============================================================================
# SIDEBAR FILTERS
# =============================================================================
with st.sidebar:
    all_years     = sorted(bwa["Year"].unique().tolist(), reverse=True)
    selected_year = st.selectbox(
        "📅 Year",
        ["All years"] + [str(y) for y in all_years]
    )
    all_cats      = sorted(bwa["Advisory_Category"].dropna().unique().tolist())
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
 
# -- Compute severity --
filtered["severity_index"] = (
    filtered["Advisory_Duration"] *
    filtered["Population_Served"] *
    filtered["No._of_Violations"]
)
filtered["severity_log"] = np.log1p(filtered["severity_index"])
 
# -- County-level aggregation (from your notebook) --
county_severity = (
    filtered.groupby("County")
    .agg(
        systems        = ("Federal_ID", "nunique"),
        total_days     = ("Advisory_Duration", "sum"),
        total_pop      = ("Population_Served", "sum"),
        total_violations = ("No._of_Violations", "sum"),
        total_severity = ("severity_index", "sum"),
        notice_count   = ("Advisory_Duration", "count"),
    )
    .reset_index()
    .sort_values("total_severity", ascending=False)
)
 
# =============================================================================
# KPI ROW
# =============================================================================
st.markdown("<div class='section-label'>Severity at a Glance</div>",
            unsafe_allow_html=True)
 
top_county = county_severity.iloc[0] if len(county_severity) > 0 else None
top_system = (
    filtered.groupby("PWS_Name")["severity_index"]
    .sum().idxmax()
    if len(filtered) > 0 else "N/A"
)
total_pop_exposed = int(filtered["Population_Served"].sum())
max_severity      = int(filtered["severity_index"].max()) if len(filtered) > 0 else 0
 
c1, c2, c3, c4 = st.columns(4)
c1.metric("Max Single Severity",   f"{max_severity:,}")
c2.metric("Highest Risk County",
          top_county["County"].title() if top_county is not None else "N/A",
          delta=f"{int(top_county['total_severity']):,} total severity"
          if top_county is not None else None)
c3.metric("Highest Risk System",   top_system)
c4.metric("Total Pop. Exposed",    f"{total_pop_exposed:,}")
 
st.markdown("<br>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 1 — County choropleth by total severity
# =============================================================================
st.markdown("<div class='section-label'>County-Level Severity Choropleth</div>",
            unsafe_allow_html=True)
 
# Merge severity with county geometries
ks_map = ks_counties.merge(
    county_severity[["County", "total_severity", "notice_count", "systems"]],
    left_on="NAME",
    right_on="County",
    how="left"
)
ks_map["total_severity"]  = ks_map["total_severity"].fillna(0)
ks_map["notice_count"]    = ks_map["notice_count"].fillna(0)
ks_map["severity_label"]  = ks_map["total_severity"].apply(
    lambda x: f"{x:,.0f}" if x > 0 else "No advisories"
)
ks_map_wgs = ks_map.to_crs(epsg=4326)
ks_map_wgs["lon"] = ks_map_wgs.geometry.centroid.x
ks_map_wgs["lat"] = ks_map_wgs.geometry.centroid.y
 
fig_choro = px.choropleth_mapbox(
    ks_map_wgs,
    geojson=ks_map_wgs.__geo_interface__,
    locations=ks_map_wgs.index,
    color="total_severity",
    hover_name="NAME",
    hover_data={
        "total_severity" : ":,.0f",
        "notice_count"   : True,
        "systems"        : True,
    },
    color_continuous_scale=[
        [0.0,  "#1c2333"],
        [0.25, "#4A9EFF"],
        [0.5,  "#FF8E53"],
        [0.75, "#FF6B6B"],
        [1.0,  "#FF0040"],
    ],
    mapbox_style="carto-darkmatter",
    zoom=6,
    center={"lat": 38.5, "lon": -98.0},
    opacity=0.75,
    height=480,
    labels={"total_severity": "Total Severity"},
)
fig_choro.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0"),
    margin=dict(l=0, r=0, t=0, b=0),
    coloraxis_colorbar=dict(
        title=dict(
            text="Severity",
            font=dict(color="#e0e0e0", size=11)
        ),
        tickfont=dict(color="#e0e0e0", size=10),
        bgcolor="rgba(0,0,0,0)",
        thickness=12,
        len=0.7,
    ),
)
st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
st.plotly_chart(fig_choro, width='stretch', config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 2 — KDE Weighted Hotspot Map (from your notebook)
# =============================================================================
st.markdown("<div class='section-label'>Severity-Weighted Hotspot Map (KDE)</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div style='color:#6e7681;font-size:0.85rem;margin-bottom:0.8rem'>"
    "Kernel Density Estimation weighted by severity index "
    "(Duration × Population × Violations). Brighter = higher risk concentration."
    "</div>",
    unsafe_allow_html=True
)
 
CRS_PROJECTED = "EPSG:32614"
bwa_proj      = filtered.to_crs(CRS_PROJECTED)
 
if len(bwa_proj) >= 2:
    x_coord = bwa_proj.geometry.x.values
    y_coord = bwa_proj.geometry.y.values
    coords  = np.vstack([x_coord, y_coord])
 
    bwa_proj["severity_index_log"] = np.log1p(bwa_proj["severity_index"])

    kde = gaussian_kde(
        coords,
        weights=bwa_proj["severity_index_log"],
        bw_method=0.3
    )
 
    xmin, ymin, xmax, ymax = bwa_proj.total_bounds
    xi, yi = np.mgrid[xmin:xmax:200j, ymin:ymax:200j]
    zi     = kde(np.vstack([xi.ravel(), yi.ravel()])).reshape(xi.shape)
 
    fig_kde, ax = plt.subplots(figsize=(14, 8), facecolor="#0e1117")
    ax.set_facecolor("#0e1117")
 
    ks_counties.to_crs(CRS_PROJECTED).plot(
        ax=ax, color="#1c2333", edgecolor="#2d3748", linewidth=0.6
    )
 
    im = ax.pcolormesh(
        xi, yi, zi,
        shading="gouraud",
        cmap="YlOrRd",
        alpha=0.75
    )
 
    # Overlay individual points
    bwa_proj.plot(
        ax=ax,
        color="#FF6B6B",
        markersize=6,
        alpha=0.5,
        edgecolor="#0e1117",
        linewidth=0.3
    )
 
    cbar = plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Severity-Weighted Density", color="#e0e0e0", fontsize=10)
    cbar.ax.yaxis.set_tick_params(color="#e0e0e0")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#e0e0e0", fontsize=9)
    cbar.outline.set_edgecolor("#2d3748")
 
    ax.set_title(
        "Severity Hotspots — Duration × Population × Violations",
        fontsize=13, fontweight="bold", color="#e0e0e0", pad=12
    )
    ax.set_axis_off()
    plt.tight_layout()
 
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.pyplot(fig_kde, width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)
    plt.close()
else:
    st.info("Not enough data points for KDE. Adjust filters.")
 
# =============================================================================
# VIZ 3 + VIZ 4 — side by side
# =============================================================================
col_scatter, col_bar = st.columns([3, 2])
 
# ── VIZ 3 — Duration vs Population scatter colored by severity ───────────────
with col_scatter:
    st.markdown("<div class='section-label'>Duration vs Population</div>",
                unsafe_allow_html=True)
 
    fig_scatter = px.scatter(
        filtered,
        x="Advisory_Duration",
        y="Population_Served",
        color="severity_log",
        size="No._of_Violations",
        size_max=20,
        hover_name="PWS_Name",
        hover_data={
            "County"           : True,
            "Year"             : True,
            "Advisory_Duration": True,
            "Population_Served": ":,.0f",
            "No._of_Violations": True,
            "severity_index"   : ":,.0f",
            "severity_log"     : False,
        },
        color_continuous_scale=[
            [0.0, "#4A9EFF"],
            [0.5, "#FF8E53"],
            [1.0, "#FF0040"],
        ],
        log_y=True,
        height=400,
        labels={
            "Advisory_Duration" : "Duration (days)",
            "Population_Served" : "Population Served (log)",
            "severity_log"      : "Severity (log)",
            "No._of_Violations" : "Violations",
        },
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter, sans-serif"),
        title=dict(
            text="Duration vs Population (color = severity, size = violations)",
            font=dict(color="#e0e0e0", size=12), x=0.5
        ),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", zeroline=False,
                   title="Duration (days)", title_font=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", zeroline=False,
                   title="Population Served (log)", title_font=dict(size=11)),
        coloraxis_colorbar=dict(
            title=dict(
                text="Severity",
                font=dict(color="#e0e0e0", size=10)
            ),
            tickfont=dict(color="#e0e0e0", size=9),
            bgcolor="rgba(0,0,0,0)",
            thickness=10, len=0.6,
        ),
        margin=dict(l=10, r=10, t=45, b=10),
    )
    fig_scatter.update_traces(
        marker=dict(line=dict(color="#0e1117", width=0.5))
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_scatter, width='stretch',
                    config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
 
# ── VIZ 4 — Top 15 counties by total severity ────────────────────────────────
with col_bar:
    st.markdown("<div class='section-label'>Top 15 Counties by Severity</div>",
                unsafe_allow_html=True)
 
    top15 = county_severity.head(15).copy()
    top15["county_label"] = top15["County"].str.title()
    top15["severity_M"]   = top15["total_severity"] / 1e6
 
    fig_bar = go.Figure(go.Bar(
        x=top15["severity_M"],
        y=top15["county_label"],
        orientation="h",
        marker=dict(
            color=top15["severity_M"],
            colorscale=[
                [0.0, "#4A9EFF"],
                [0.5, "#FF8E53"],
                [1.0, "#FF0040"],
            ],
            line=dict(color="#0e1117", width=1),
            cornerradius=4,
        ),
        text=top15["notice_count"].apply(lambda x: f"{int(x)} notices"),
        textposition="outside",
        textfont=dict(color="#8b949e", size=10),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Total Severity: %{x:.2f}M<br>"
            "<extra></extra>"
        ),
        cliponaxis=False,
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter, sans-serif"),
        title=dict(text="Top 15 Counties — Total Severity (M)",
                   font=dict(color="#e0e0e0", size=12), x=0.5),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", title="Severity (millions)",
                   title_font=dict(size=11), zeroline=False),
        yaxis=dict(showgrid=False, color="#e0e0e0",
                   autorange="reversed", tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=45, b=10),
        height=400,
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_bar, width='stretch',
                    config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================
load_footer()

