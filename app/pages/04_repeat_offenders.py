import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import datetime
from pathlib import Path
from utils.data_loader import load_bwa_data as load_data, load_kansas_counties as load_counties
from utils.styles import load_css, load_footer, apply_layout, PLOT_BASE, AXIS_STYLE, CORAL, ORANGE, BLUE, TEAL, GRAY, SEVERITY_COLORSCALE

load_css()


# =============================================================================
# PAGE CONFIG — must be first Streamlit command
# =============================================================================
st.set_page_config(
    page_title="Severity Analysis",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown("<div class='hero-title' style='font-size:2rem'>Repeat Offenders</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div class='hero-subtitle' style='font-size:0.95rem'>"
    "Which water systems are chronically failing? "
    "Identifying systems with multiple advisories and whether they cluster geographically."
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
    # Minimum notice count filter — key for this page
    min_notices = st.slider(
        "🔁 Minimum Notices per System",
        min_value=1,
        max_value=10,
        value=2,
        help="Only show systems with at least this many advisories"
    )
 
# -- Apply filters --
filtered = bwa.copy()
if selected_year != "All years":
    filtered = filtered[filtered["Year"] == int(selected_year)]
if selected_cats:
    filtered = filtered[filtered["Advisory_Category"].isin(selected_cats)]
 
# -- Compute severity --
filtered["severity_index"] = (
    filtered["Advisory_Duration"] *
    filtered["Population_Served"] *
    filtered["No._of_Violations"]
)
 
# -- System-level aggregation --
system_stats = (
    filtered.groupby(["Federal_ID", "PWS_Name", "County", "lat", "lon"])
    .agg(
        notice_count    = ("Advisory_Duration", "count"),
        total_days      = ("Advisory_Duration", "sum"),
        avg_duration    = ("Advisory_Duration", "mean"),
        avg_population  = ("Population_Served", "mean"),
        total_violations= ("No._of_Violations", "sum"),
        total_severity  = ("severity_index", "sum"),
        first_notice    = ("Issues_Date", "min"),
        last_notice     = ("Issues_Date", "max"),
        years_active    = ("Year", "nunique"),
    )
    .reset_index()
    .sort_values("notice_count", ascending=False)
)
 
# -- Repeat vs single split --
repeat_systems = system_stats[system_stats["notice_count"] >= min_notices]
single_systems = system_stats[system_stats["notice_count"] == 1]
 
# =============================================================================
# KPI ROW
# =============================================================================
st.markdown("<div class='section-label'>Repeat Offender Overview</div>",
            unsafe_allow_html=True)
 
top_system    = system_stats.iloc[0] if len(system_stats) > 0 else None
pct_repeat    = (
    len(repeat_systems) / len(system_stats) * 100
    if len(system_stats) > 0 else 0
)
top_county_repeat = (
    repeat_systems.groupby("County")["notice_count"]
    .sum().idxmax()
    if len(repeat_systems) > 0 else "N/A"
)
 
c1, c2, c3, c4 = st.columns(4)
c1.metric("Most Notices — Single System",
          top_system["PWS_Name"] if top_system is not None else "N/A",
          delta=f"{int(top_system['notice_count'])} notices"
          if top_system is not None else None)
c2.metric("Repeat Systems",
          len(repeat_systems),
          delta=f"{pct_repeat:.1f}% of all systems")
c3.metric("Single-Notice Systems", len(single_systems))
c4.metric("County with Most Repeats",
          top_county_repeat.title() if top_county_repeat != "N/A" else "N/A")
 
st.markdown("<br>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 1 — Top 15 repeat systems horizontal bar
# =============================================================================
st.markdown("<div class='section-label'>Top 15 Systems by Notice Count</div>",
            unsafe_allow_html=True)
 
top15 = system_stats.head(15).copy()
top15["label"] = top15["PWS_Name"].str.title().str.replace(", City Of", "")
top15["avg_duration_r"] = top15["avg_duration"].round(1)
 
fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=top15["notice_count"],
    y=top15["label"],
    orientation="h",
    marker=dict(
        color=top15["notice_count"],
        colorscale=[
            [0.0, "#4A9EFF"],
            [0.5, "#FF8E53"],
            [1.0, "#FF6B6B"],
        ],
        line=dict(color="#0e1117", width=1),
        cornerradius=4,
    ),
    text=top15.apply(
        lambda r: f"{int(r['notice_count'])} notices · {r['avg_duration_r']}d avg",
        axis=1
    ),
    textposition="outside",
    textfont=dict(color="#8b949e", size=10),
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Notices: %{x}<br>"
        "Avg Duration: %{customdata[0]:.1f} days<br>"
        "County: %{customdata[1]}<br>"
        "Total Violations: %{customdata[2]}<br>"
        "<extra></extra>"
    ),
    customdata=top15[["avg_duration", "County", "total_violations"]].values,
    cliponaxis=False,
))
 
fig_bar.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0", family="Inter, sans-serif"),
    title=dict(text="Top 15 Repeat Offender Water Systems",
               font=dict(color="#e0e0e0", size=13), x=0.5),
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
               color="#6e7681", title="Number of Advisories",
               title_font=dict(size=11), zeroline=False),
    yaxis=dict(showgrid=False, color="#e0e0e0",
               autorange="reversed", tickfont=dict(size=10)),
    margin=dict(l=10, r=120, t=45, b=10),
    height=430,
)
 
st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
st.plotly_chart(fig_bar, width='stretch', config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 2 — Map of repeat systems
# =============================================================================
st.markdown("<div class='section-label'>Geographic Distribution of Repeat Systems</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div style='color:#6e7681;font-size:0.85rem;margin-bottom:0.8rem'>"
    f"Showing systems with {min_notices}+ advisories. "
    "Dot size = notice count · Color = total severity."
    "</div>",
    unsafe_allow_html=True
)
 
if len(repeat_systems) > 0:
    repeat_systems["label"] = (
        repeat_systems["PWS_Name"].str.title()
        .str.replace(", City Of", "")
    )
    repeat_systems["severity_log"] = np.log1p(repeat_systems["total_severity"])
 
    fig_map = px.scatter_mapbox(
        repeat_systems,
        lat="lat",
        lon="lon",
        color="severity_log",
        size="notice_count",
        size_max=25,
        hover_name="label",
        hover_data={
            "County"         : True,
            "notice_count"   : True,
            "total_days"     : True,
            "avg_duration"   : ":.1f",
            "total_violations": True,
            "years_active"   : True,
            "lat"            : False,
            "lon"            : False,
            "severity_log"   : False,
        },
        color_continuous_scale=[
            [0.0, "#4A9EFF"],
            [0.5, "#FF8E53"],
            [1.0, "#FF0040"],
        ],
        zoom=6,
        center={"lat": 38.5, "lon": -98.0},
        height=480,
        mapbox_style="carto-darkmatter",
        labels={
            "notice_count"   : "Notices",
            "total_days"     : "Total Days",
            "avg_duration"   : "Avg Duration",
            "total_violations": "Violations",
            "years_active"   : "Years Active",
            "severity_log"   : "Severity (log)",
        },
    )
    fig_map.update_layout(
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
            thickness=12, len=0.7,
        ),
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_map, width='stretch', config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info(f"No systems found with {min_notices}+ notices. Lower the minimum notices filter.")
 
# =============================================================================
# VIZ 3 + VIZ 4 — side by side
# =============================================================================
col_timeline, col_compare = st.columns([3, 2])
 
# ── VIZ 3 — Timeline scatter — notices over time per system ──────────────────
with col_timeline:
    st.markdown("<div class='section-label'>Advisory Timeline — Top 10 Systems</div>",
                unsafe_allow_html=True)
 
    # Get top 10 repeat systems
    top10_names = system_stats.head(10)["PWS_Name"].tolist()
    timeline_df = filtered[filtered["PWS_Name"].isin(top10_names)].copy()
    timeline_df["Issues_Date"] = pd.to_datetime(timeline_df["Issues_Date"])
    timeline_df["label"] = (
        timeline_df["PWS_Name"].str.title()
        .str.replace(", City Of", "")
    )
 
    fig_timeline = px.scatter(
        timeline_df,
        x="Issues_Date",
        y="label",
        color="Advisory_Duration",
        size="Advisory_Duration",
        size_max=18,
        hover_name="label",
        hover_data={
            "Issues_Date"      : True,
            "Advisory_Duration": True,
            "Advisory_Category": True,
            "Population_Served": ":,.0f",
            "label"            : False,
        },
        color_continuous_scale=[
            [0.0, "#4A9EFF"],
            [0.5, "#FF8E53"],
            [1.0, "#FF0040"],
        ],
        height=420,
        labels={
            "Issues_Date"      : "Date Issued",
            "label"            : "Water System",
            "Advisory_Duration": "Duration (days)",
        },
    )
    fig_timeline.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter, sans-serif"),
        title=dict(text="Advisory Timeline — Top 10 Repeat Systems",
                   font=dict(color="#e0e0e0", size=12), x=0.5),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", title="", tickfont=dict(size=10)),
        yaxis=dict(showgrid=False, color="#e0e0e0",
                   title="", tickfont=dict(size=9)),
        coloraxis_colorbar=dict(
            title=dict(
                text="Days",
                font=dict(color="#e0e0e0", size=10)
            ),
            tickfont=dict(color="#e0e0e0", size=9),
            bgcolor="rgba(0,0,0,0)",
            thickness=10, len=0.6,
        ),
        margin=dict(l=10, r=10, t=45, b=10),
    )
    fig_timeline.update_traces(
        marker=dict(line=dict(color="#0e1117", width=0.5))
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_timeline, width='stretch',
                    config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
 
# ── VIZ 4 — Repeat vs Single comparison ─────────────────────────────────────
with col_compare:
    st.markdown("<div class='section-label'>Repeat vs Single-Notice Systems</div>",
                unsafe_allow_html=True)
 
    metrics    = ["avg_duration", "avg_population", "total_violations"]
    labels     = ["Avg Duration (days)", "Avg Population", "Avg Violations"]
    repeat_vals = [
        repeat_systems["avg_duration"].mean(),
        repeat_systems["avg_population"].mean(),
        repeat_systems["total_violations"].mean(),
    ] if len(repeat_systems) > 0 else [0, 0, 0]
    single_vals = [
        single_systems["avg_duration"].mean(),
        single_systems["avg_population"].mean(),
        single_systems["total_violations"].mean(),
    ] if len(single_systems) > 0 else [0, 0, 0]
 
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        name=f"Repeat ({min_notices}+ notices)",
        x=labels,
        y=repeat_vals,
        marker=dict(color="#FF6B6B", line=dict(color="#0e1117", width=1),
                    cornerradius=4),
        hovertemplate="<b>%{x}</b><br>Repeat: %{y:.1f}<extra></extra>",
    ))
    fig_compare.add_trace(go.Bar(
        name="Single notice",
        x=labels,
        y=single_vals,
        marker=dict(color="#4A9EFF", line=dict(color="#0e1117", width=1),
                    cornerradius=4),
        hovertemplate="<b>%{x}</b><br>Single: %{y:.1f}<extra></extra>",
    ))
 
    fig_compare.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter, sans-serif"),
        title=dict(text="Repeat vs Single-Notice Systems",
                   font=dict(color="#e0e0e0", size=12), x=0.5),
        xaxis=dict(showgrid=False, color="#6e7681", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#6e7681", zeroline=False),
        barmode="group",
        bargap=0.25,
        bargroupgap=0.1,
        legend=dict(
            font=dict(color="#e0e0e0", size=10),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        margin=dict(l=10, r=10, t=60, b=10),
        height=420,
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_compare, width='stretch',
                    config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
 
# =============================================================================
# DETAILED TABLE — all repeat systems
# =============================================================================
st.markdown("<div class='section-label'>Full Repeat Offender Table</div>",
            unsafe_allow_html=True)
 
table_df = repeat_systems[[
    "PWS_Name", "County", "notice_count", "total_days",
    "avg_duration", "avg_population", "total_violations", "years_active"
]].copy()
table_df.columns = [
    "System", "County", "Notices", "Total Days",
    "Avg Duration", "Avg Population", "Total Violations", "Years Active"
]
table_df["Avg Duration"]   = table_df["Avg Duration"].round(1)
table_df["Avg Population"] = table_df["Avg Population"].apply(lambda x: f"{x:,.0f}")
table_df["System"]         = table_df["System"].str.title().str.replace(", City Of", "")
 
st.dataframe(
    table_df,
    width='stretch',
    hide_index=True,
    height=320,
    column_config={
        "System"          : st.column_config.TextColumn("System",      width="medium"),
        "County"          : st.column_config.TextColumn("County",      width="small"),
        "Notices"         : st.column_config.NumberColumn("Notices",   format="%d"),
        "Total Days"      : st.column_config.NumberColumn("Total Days",format="%d"),
        "Avg Duration"    : st.column_config.NumberColumn("Avg Duration (days)"),
        "Avg Population"  : st.column_config.TextColumn("Avg Pop"),
        "Total Violations": st.column_config.NumberColumn("Violations",format="%d"),
        "Years Active"    : st.column_config.NumberColumn("Years",     format="%d"),
    }
)

# =============================================================================
# FOOTER
# =============================================================================
load_footer()