import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
from shapely import wkt
from datetime import datetime
from utils.data_loader import load_bwa_data as load_data, load_kansas_counties as load_counties
from utils.styles import load_css, load_footer, apply_layout, PLOT_BASE, AXIS_STYLE, CORAL, ORANGE, BLUE, TEAL, GRAY, SEVERITY_COLORSCALE

load_css()


# bwa         = load_data()
# ks_counties = load_counties()

# =============================================================================
# PAGE CONFIG — must be first Streamlit command
# =============================================================================
# st.set_page_config(
#     page_title="BWA Dashboard | Overview",
#     page_icon="💧",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

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


# =============================================================================
# SIDEBAR — Global Filters
# =============================================================================
with st.sidebar:
    st.markdown("## 💧 BWA Dashboard")
    st.markdown(
        "<div style='color:#e0e0e0;font-size:0.8rem;margin-bottom:1.2rem'>"
        "Kansas Boil Water Advisory Analysis<br>KDHE · 2021 – 2026"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown(
        "<div class='section-label'>Filters</div>",
        unsafe_allow_html=True
    )

    # Year filter
    all_years = sorted(bwa["Year"].unique().tolist(), reverse=True)
    year_options = ["All years"] + [str(y) for y in all_years]
    selected_year = st.selectbox("📅 Year", year_options, index=0)

    # Advisory category filter
    all_cats = sorted(bwa["Advisory_Category"].dropna().unique().tolist())
    selected_cats = st.multiselect(
        "🔬 Advisory Category",
        options=all_cats,
        default=[],
        placeholder="All categories"
    )

    # Duration filter
    max_dur = int(bwa["Advisory_Duration"].max())
    dur_range = st.slider(
        "⏱️ Duration (days)",
        min_value=1,
        max_value=max_dur,
        value=(1, max_dur)
    )

    # PWS Type filter
    pws_types = sorted(bwa["PWS_Type"].dropna().unique().tolist())
    selected_pws = st.multiselect(
        "🏙️ PWS Type",
        options=pws_types,
        default=[],
        placeholder="All types"
    )

    st.markdown("---")
    st.markdown(
        f"<div style='color:#6e7681;font-size:0.78rem'>"
        f"Last pipeline run<br>"
        f"<span style='color:#c9d1d9'>{datetime.now().strftime('%Y-%m-%d')}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

# ── Apply filters ────────────────────────────────────────────────────────────
filtered = bwa.copy()

if selected_year != "All years":
    filtered = filtered[filtered["Year"] == int(selected_year)]

if selected_cats:
    filtered = filtered[filtered["Advisory_Category"].isin(selected_cats)]

filtered = filtered[
    (filtered["Advisory_Duration"] >= dur_range[0]) &
    (filtered["Advisory_Duration"] <= dur_range[1])
]

if selected_pws:
    filtered = filtered[filtered["PWS_Type"].isin(selected_pws)]

# Store in session state for other pages
st.session_state["filtered_data"] = filtered
st.session_state["all_data"] = bwa


# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown(
    "<div class='hero-title'> Kansas Boil Water Advisory Dashboard</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div class='info-banner'>"
    "Advisory data scraped from KDHE was geocoded to city centroids and surrounded by a "
    "<b>10 km impact buffer</b> to approximate each system's distribution zone. "
    "A composite <b>severity index</b> (Duration × Population × Violations) measures cumulative risk, "
    "while root causes were <b>AI classified</b> using Gemini 2.5 Flash."
    "</div>",
    unsafe_allow_html=True
)


# =============================================================================
# KPI METRICS
# =============================================================================
st.markdown("<div class='section-label'>Key Metrics</div>", unsafe_allow_html=True)

prev = bwa[bwa["Year"] == (int(selected_year) - 1)] if selected_year != "All years" else None

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    delta = f"+{len(filtered) - len(prev)} vs prev year" if prev is not None else None
    st.metric("Total Advisories", len(filtered), delta=delta, delta_color="inverse")

with c2:
    n_counties = filtered["County"].nunique()
    st.metric("Counties Affected", n_counties,
              delta=f"of 105 Kansas counties")

with c3:
    avg_dur = filtered["Advisory_Duration"].mean()
    prev_dur = prev["Advisory_Duration"].mean() if prev is not None else None
    delta_dur = f"{avg_dur - prev_dur:+.1f}d vs prev year" if prev_dur else None
    st.metric("Avg Duration", f"{avg_dur:.1f} days", delta=delta_dur, delta_color="inverse")

with c4:
    total_pop = int(filtered["Population_Served"].sum())
    st.metric("Total Pop. Exposed", f"{total_pop:,}")

with c5:
    n_systems = filtered["Federal_ID"].nunique()
    st.metric("Unique PWS", n_systems)

st.markdown("<br>", unsafe_allow_html=True)


# =============================================================================
# ROW 1 — MAP + YEARLY TREND
# =============================================================================
st.markdown("<div class='section-label'>Geographic Distribution & Temporal Trend</div>",
            unsafe_allow_html=True)

col_map, col_trend = st.columns([2, 1])

with col_map:
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
        color="Advisory_Duration",
        size="Population_Served",
        size_max=22,
        hover_name="PWS_Name",
        hover_data={
            "Advisory_Notice_URL": False,
            "County": True,
            "Year": True,
            "Advisory_Duration": True,
            "Advisory_Category": True,
            "Population_Served": ":,.0f",
            "No._of_Violations": True,
            "lat": False,
            "lon": False,
        },
        color_continuous_scale=[TEAL, BLUE, ORANGE, CORAL, "#FF0000"],
        range_color=[
            filtered["Advisory_Duration"].min(),
            filtered["Advisory_Duration"].max()
        ],
        zoom=5.5,
        center={"lat": 38.5, "lon": -98.0},
        height=480,
        # mapbox_style="carto-darkmatter",
        mapbox_style=map_style,
        # mapbox_style="carto-positron",
        # mapbox_style="open-street-map",
        # mapbox_style = "stamen-watercolor"
    )
    fig_map.update_layout(
        **PLOT_BASE,
        # margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(
            title=dict(
                text="Duration<br>(days)",
                font=dict(color="#e0e0e0", size=11),
                side="right"
            ),
            tickfont=dict(color="#e0e0e0", size=10),
            bgcolor="rgba(0,0,0,0)",
            thickness=12,
            len=0.7,
            x=1.01,
        ),
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_map, width="stretch", config={"displayModeBar": True})
    st.markdown("</div>", unsafe_allow_html=True)

with col_trend:
    # Advisory count per year
    year_counts = (
        bwa.groupby("Year").size().reset_index(name="count")
    )
    # Highlight selected year
    year_counts["color"] = year_counts["Year"].apply(
        lambda y: CORAL if selected_year != "All years" and y == int(selected_year) else BLUE
    )

    fig_year = go.Figure()
    fig_year.add_trace(go.Bar(
        x=year_counts["Year"],
        y=year_counts["count"],
        marker=dict(
            color=year_counts["color"],
            line=dict(color="#0e1117", width=1),
            cornerradius=5,
        ),
        text=year_counts["count"],
        textposition="outside",
        textfont=dict(color="#e0e0e0", size=11),
        hovertemplate="<b>%{x}</b><br>Advisories: %{y}<extra></extra>",
    ))

    # Trend line
    z = np.polyfit(year_counts["Year"], year_counts["count"], 1)
    p = np.poly1d(z)
    fig_year.add_trace(go.Scatter(
        x=year_counts["Year"],
        y=p(year_counts["Year"]),
        mode="lines",
        line=dict(color=ORANGE, width=2, dash="dot"),
        name="Trend",
        hoverinfo="skip",
    ))

    fig_year.update_layout(
        **PLOT_BASE,
        title=dict(text="Advisories by Year", font=dict(color="#e0e0e0", size=13), x=0.5),
        xaxis={
            **AXIS_STYLE,
            "showgrid": False,
            "dtick": 1,
            "title": "",
            "tickfont": {
                **AXIS_STYLE.get("tickfont", {}),
                "size": 11
            }
        },
        yaxis=dict(**AXIS_STYLE, title=dict(text="Count", font=dict(size=11))),
        showlegend=False,
        height=220,
        bargap=0.25,
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_year, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Monthly distribution (all years stacked)
    filtered["month"] = pd.to_datetime(filtered["Issues_Date"]).dt.month
    month_counts = filtered.groupby("month").size().reset_index(name="count")
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    month_counts["month_name"] = month_counts["month"].map(month_names)

    fig_month = go.Figure(go.Bar(
        x=month_counts["month_name"],
        y=month_counts["count"],
        marker=dict(
            color=month_counts["count"],
            colorscale=[[0, BLUE], [0.5, ORANGE], [1, CORAL]],
            line=dict(color="#0e1117", width=1),
            cornerradius=4,
        ),
        hovertemplate="<b>%{x}</b><br>Advisories: %{y}<extra></extra>",
    ))
    fig_month.update_layout(
        **PLOT_BASE,
        title=dict(text="Monthly Pattern", font=dict(color="#e0e0e0", size=13), x=0.5),
        xaxis={
            **AXIS_STYLE,
            "showgrid": False,
            "title": ""
        },
        yaxis=dict(**AXIS_STYLE, title=dict(text="Count", font=dict(size=11))),
        height=220,
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_month, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# ROW 2 — COUNTY CHOROPLETH + ADVISORY CATEGORY DONUT
# =============================================================================
st.markdown("<div class='section-label'>County Breakdown & Cause Distribution</div>",
            unsafe_allow_html=True)

col_choro, col_cat = st.columns([3, 2])

with col_choro:
    county_counts = (
        filtered.groupby("County")
        .agg(
            count=("Advisory_Duration", "count"),
            avg_duration=("Advisory_Duration", "mean"),
            total_pop=("Population_Served", "sum"),
            total_severity=("severity_index", "sum"),
        )
        .reset_index()
        .sort_values("count", ascending=False)
    )

    fig_bar = go.Figure(go.Bar(
        x=county_counts.head(20)["count"],
        y=county_counts.head(20)["County"].str.title(),
        orientation="h",
        marker=dict(
            color=county_counts.head(20)["count"],
            colorscale=[[0, BLUE], [0.5, ORANGE], [1, CORAL]],
            line=dict(color="#0e1117", width=1),
            cornerradius=4,
        ),
        text=county_counts.head(20)["count"],
        textposition="outside",
        textfont=dict(color="#e0e0e0", size=10),
        hovertemplate=(
            "<b>%{y} County</b><br>"
            "Advisories: %{x}<br>"
            "<extra></extra>"
        ),
        cliponaxis=False,
    ))
    fig_bar.update_layout(
        **{
            **PLOT_BASE,  # base styles
            "title": dict(
                text="Top 20 Counties by Advisory Count",
                font=dict(color="#e0e0e0", size=13),
                x=0.5
            ),
            "xaxis": dict(
                **AXIS_STYLE,
                title=dict(text="Number of Advisories", font=dict(size=11))
            ),
            "yaxis": {
                **AXIS_STYLE,
                "showgrid": False,
                "autorange": "reversed",
                "tickfont": {
                    **AXIS_STYLE.get("tickfont", {}),
                    "size": 10
                }
            },
            "height": 480,
            "margin": dict(l=10, r=50, t=45, b=10),  # safely override
        }
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_bar, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_cat:
    cat_counts = (
        filtered["Advisory_Category"]
        .value_counts()
        .reset_index()
    )
    cat_counts.columns = ["category", "count"]

    colors_donut = [CORAL, ORANGE, BLUE, TEAL, "#8B5CF6", "#EC4899", GRAY]

    fig_donut = go.Figure(go.Pie(
        labels=cat_counts["category"],
        values=cat_counts["count"],
        hole=0.62,
        marker=dict(
            colors=colors_donut[:len(cat_counts)],
            line=dict(color="#0e1117", width=2),
        ),
        textinfo="label+percent",
        textfont=dict(color="#e0e0e0", size=10),
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        pull=[0.03] + [0] * (len(cat_counts) - 1),
    ))
    fig_donut.add_annotation(
        text=f"<b>{len(filtered)}</b><br><span style='font-size:11px'>notices</span>",
        x=0.5, y=0.5,
        font=dict(size=18, color="#e0e0e0"),
        showarrow=False,
    )
    fig_donut.update_layout(
        **{
            **PLOT_BASE,  # base layout
            "title": dict(
                text="Advisory Category Breakdown",
                font=dict(color="#e0e0e0", size=13),
                x=0.5
            ),
            "showlegend": True,
            "legend": dict(
                orientation="v",
                font=dict(color="#e0e0e0", size=10),
                bgcolor="rgba(0,0,0,0)",
                x=1.02,
            ),
            "height": 480,
            "margin": dict(l=10, r=120, t=45, b=10),  # safely override PLOT_BASE margin
        }
    )
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# ROW 3 — DURATION vs POPULATION SCATTER + TOP SYSTEMS TABLE
# =============================================================================
st.markdown("<div class='section-label'>Severity & System-Level Detail</div>",
            unsafe_allow_html=True)

col_scatter, col_table = st.columns([3, 2])

with col_scatter:
    fig_scatter = px.scatter(
        filtered,
        x="Advisory_Duration",
        y="Population_Served",
        color="Advisory_Category",
        size="No._of_Violations",
        size_max=20,
        hover_name="PWS_Name",
        hover_data={
            "County": True,
            "Year": True,
            "Advisory_Duration": True,
            "Population_Served": ":,.0f",
            "No._of_Violations": True,
        },
        color_discrete_sequence=[CORAL, ORANGE, BLUE, TEAL, "#8B5CF6", "#EC4899"],
        log_y=True,
        height=380,
        labels={
            "Advisory_Duration": "Duration (days)",
            "Population_Served": "Population Served (log)",
            "Advisory_Category": "Category",
        }
    )
    fig_scatter.update_layout(
        **PLOT_BASE,
        title=dict(text="Duration vs Population (size = violations)",
                   font=dict(color="#e0e0e0", size=13), x=0.5),
        xaxis={
            **AXIS_STYLE,
            "title": dict(text="Duration (days)", font=dict(size=11))
        },
        yaxis={
            **AXIS_STYLE,
            "title": dict(text="Population Served (log scale)", font=dict(size=11))
        },
        legend=dict(
            title=dict(text="Category", font=dict(color="#8b949e", size=10)),
            font=dict(color="#e0e0e0", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    fig_scatter.update_traces(marker=dict(line=dict(color="#0e1117", width=0.5)))
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_scatter, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_table:
    st.markdown(
        "<div style='color:#e0e0e0;font-size:0.9rem;font-weight:600;"
        "margin-bottom:0.5rem'>Top 10 Systems by Severity</div>",
        unsafe_allow_html=True
    )
    top_systems = (
        filtered.groupby(["PWS_Name", "County"])
        .agg(
            notices=("Advisory_Duration", "count"),
            total_days=("Advisory_Duration", "sum"),
            avg_pop=("Population_Served", "mean"),
            severity=("severity_index", "sum"),
        )
        .reset_index()
        .sort_values("severity", ascending=False)
        .head(10)
    )
    top_systems["severity"] = top_systems["severity"].apply(lambda x: f"{x:,.0f}")
    top_systems["avg_pop"] = top_systems["avg_pop"].apply(lambda x: f"{x:,.0f}")
    top_systems.columns = ["System", "County", "Notices", "Days", "Avg Pop", "Severity"]

    st.dataframe(
        top_systems,
        width='stretch',
        height=360,
        hide_index=True,
        column_config={
            "System": st.column_config.TextColumn("System", width="medium"),
            "County": st.column_config.TextColumn("County", width="small"),
            "Notices": st.column_config.NumberColumn("Notices", format="%d"),
            "Days": st.column_config.NumberColumn("Days", format="%d"),
            "Avg Pop": st.column_config.TextColumn("Avg Pop"),
            "Severity": st.column_config.TextColumn("Severity ↓"),
        }
    )


# =============================================================================
# FOOTER
# =============================================================================
load_footer()