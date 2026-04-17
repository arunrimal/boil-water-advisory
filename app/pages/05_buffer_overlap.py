import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import datetime
from pathlib import Path
from shapely.ops import unary_union
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

CRS_PROJECTED = "EPSG:32614"

# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown("<div class='hero-title' style='font-size:2rem'>Buffer Overlap Analysis</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div class='hero-subtitle' style='font-size:0.95rem'>"
    "Where did multiple water systems simultaneously issue advisories "
    "affecting the same geographic area? "
    "Each system has a 10 km impact buffer — overlaps reveal shared risk zones."
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
 
# -- Apply filters --
filtered = bwa.copy()
if selected_year != "All years":
    filtered = filtered[filtered["Year"] == int(selected_year)]
if selected_cats:
    filtered = filtered[filtered["Advisory_Category"].isin(selected_cats)]
 
filtered["severity_index"] = (
    filtered["Advisory_Duration"] *
    filtered["Population_Served"] *
    filtered["No._of_Violations"]
)
 
# =============================================================================
# COMPUTE BUFFER OVERLAPS — cached (O(n²) so runs once)
# =============================================================================
@st.cache_data(show_spinner="Computing cross-PWS buffer overlaps...")
def compute_overlaps(_bwa_df):
    """
    Find concurrent overlapping 10km buffers across different PWSs.
    Skips same-PWS comparisons — cross-system only.
    """
    bwa_proj    = _bwa_df.to_crs(CRS_PROJECTED).copy()
    bwa_buffers = bwa_proj.set_geometry("buffer_geometry")
    overlaps    = []
 
    rows = list(bwa_buffers.iterrows())
    for i, (idx1, row1) in enumerate(rows):
        for idx2, row2 in rows[i + 1:]:
            # Cross-PWS only — skip same system
            if row1["PWS_Name"] == row2["PWS_Name"]:
                continue
            if not row1["buffer_geometry"].intersects(row2["buffer_geometry"]):
                continue
            # Check concurrent advisory dates
            concurrent = (
                row1["Issues_Date"] <= row2["Rescinded_Date"] and
                row2["Issues_Date"] <= row1["Rescinded_Date"]
            )
            if not concurrent:
                continue
            intersection    = row1["buffer_geometry"].intersection(row2["buffer_geometry"])
            concurrent_days = (
                min(row1["Rescinded_Date"], row2["Rescinded_Date"]) -
                max(row1["Issues_Date"],    row2["Issues_Date"])
            ).days
 
            overlaps.append({
                "pws_1"           : row1["PWS_Name"],
                "pws_2"           : row2["PWS_Name"],
                "county_1"        : row1["County"],
                "county_2"        : row2["County"],
                "year_1"          : row1["Year"],
                "year_2"          : row2["Year"],
                "geometry"        : intersection,
                "overlap_area_km2": round(intersection.area / 1e6, 2),
                "concurrent_days" : concurrent_days,
                "cat_1"           : row1["Advisory_Category"],
                "cat_2"           : row2["Advisory_Category"],
            })
 
    if not overlaps:
        return None
 
    return gpd.GeoDataFrame(overlaps, geometry="geometry", crs=CRS_PROJECTED)
 
 
overlap_gdf = compute_overlaps(filtered)
 
# =============================================================================
# KPI ROW
# =============================================================================
st.markdown("<div class='section-label'>Overlap Summary</div>", unsafe_allow_html=True)
 
c1, c2, c3, c4 = st.columns(4)
 
if overlap_gdf is not None and len(overlap_gdf) > 0:
    total_pairs    = len(overlap_gdf)
    total_area     = overlap_gdf["overlap_area_km2"].sum()
    max_days       = int(overlap_gdf["concurrent_days"].max())
    counties_involved = set(
        overlap_gdf["county_1"].tolist() + overlap_gdf["county_2"].tolist()
    )
 
    c1.metric("Overlapping Pairs Found", total_pairs,
              delta="cross-PWS concurrent only")
    c2.metric("Total Overlap Area",      f"{total_area:.1f} km²")
    c3.metric("Max Concurrent Days",     f"{max_days} days")
    c4.metric("Counties Involved",       len(counties_involved),
              delta=", ".join([c.title() for c in counties_involved]))
else:
    c1.metric("Overlapping Pairs Found", 0)
    c2.metric("Total Overlap Area",      "0 km²")
    c3.metric("Max Concurrent Days",     "0 days")
    c4.metric("Counties Involved",       0)
    st.info(
        "No concurrent cross-PWS buffer overlaps found with current filters. "
        "Try selecting 'All years'.",
        icon="ℹ️"
    )
 
st.markdown("<br>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 1 — Main map: all buffers + overlap zones highlighted
# =============================================================================
st.markdown("<div class='section-label'>Spatial Overview — Buffers & Overlap Zones</div>",
            unsafe_allow_html=True)
st.markdown(
    "<div style='color:#6e7681;font-size:0.85rem;margin-bottom:0.8rem'>"
    "Gray circles = 10 km impact buffers for all systems · "
    "Coral zones = concurrent cross-PWS overlapping areas · "
    "Red dots = individual advisory locations."
    "</div>",
    unsafe_allow_html=True
)
 
fig_map = go.Figure()
 
# ── Layer 1: All buffer circles (light gray, transparent) ───────────────────
buf_wgs = filtered.copy().to_crs(epsg=4326).set_geometry("buffer_geometry")
for _, row in buf_wgs.iterrows():
    try:
        coords = list(row["buffer_geometry"].exterior.coords)
        lons   = [c[0] for c in coords]
        lats   = [c[1] for c in coords]
        fig_map.add_trace(go.Scattermapbox(
            lon=lons, lat=lats,
            mode="lines",
            line=dict(color="rgba(74,158,255,0.15)", width=0.8),
            fill="toself",
            fillcolor="rgba(74,158,255,0.04)",
            hoverinfo="skip",
            showlegend=False,
        ))
    except Exception:
        continue
 
# ── Layer 2: Overlap zones (coral fill) ─────────────────────────────────────
if overlap_gdf is not None and len(overlap_gdf) > 0:
    overlap_wgs = overlap_gdf.to_crs(epsg=4326)
    for _, row in overlap_wgs.iterrows():
        try:
            geom = row["geometry"]
            # Handle both Polygon and MultiPolygon
            polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
            for poly in polys:
                coords = list(poly.exterior.coords)
                lons   = [c[0] for c in coords]
                lats   = [c[1] for c in coords]
                fig_map.add_trace(go.Scattermapbox(
                    lon=lons, lat=lats,
                    mode="lines",
                    line=dict(color="rgba(255,107,107,0.8)", width=1.5),
                    fill="toself",
                    fillcolor="rgba(255,107,107,0.35)",
                    hoverinfo="text",
                    text=(
                        f"<b>Overlap Zone</b><br>"
                        f"{row['pws_1'].title()} ×<br>"
                        f"{row['pws_2'].title()}<br>"
                        f"Area: {row['overlap_area_km2']:.1f} km²<br>"
                        f"Concurrent: {row['concurrent_days']} days"
                    ),
                    showlegend=False,
                ))
        except Exception:
            continue
 
# ── Layer 3: Individual PWS points ──────────────────────────────────────────
fig_map.add_trace(go.Scattermapbox(
    lon=filtered["lon"].tolist(),
    lat=filtered["lat"].tolist(),
    mode="markers",
    marker=dict(size=6, color="#FF6B6B", opacity=0.7),
    text=filtered["PWS_Name"].str.title(),
    hovertemplate="<b>%{text}</b><extra></extra>",
    name="Advisory locations",
    showlegend=True,
))
 
fig_map.update_layout(
    mapbox=dict(
        style="carto-darkmatter",
        zoom=6,
        center={"lat": 38.5, "lon": -98.0},
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e0e0"),
    margin=dict(l=0, r=0, t=0, b=0),
    height=520,
    legend=dict(
        font=dict(color="#e0e0e0", size=11),
        bgcolor="rgba(22,27,34,0.85)",
        bordercolor="rgba(255,255,255,0.08)",
        borderwidth=1,
        x=0.01, y=0.99,
    ),
)
 
st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
st.plotly_chart(fig_map, width='stretch', config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)
 
# =============================================================================
# VIZ 2 + VIZ 3 — side by side (only if overlaps exist)
# =============================================================================
if overlap_gdf is not None and len(overlap_gdf) > 0:
 
    col_table, col_bar = st.columns([3, 2])
 
    # ── VIZ 2 — Overlap pairs detail table ──────────────────────────────────
    with col_table:
        st.markdown("<div class='section-label'>Overlapping Pairs — Detail</div>",
                    unsafe_allow_html=True)
 
        table_df = overlap_gdf[[
            "pws_1", "pws_2", "county_1", "county_2",
            "overlap_area_km2", "concurrent_days",
            "cat_1", "cat_2", "year_1", "year_2"
        ]].copy()
 
        table_df.columns = [
            "System 1", "System 2", "County 1", "County 2",
            "Overlap Area (km²)", "Concurrent Days",
            "Category 1", "Category 2", "Year 1", "Year 2"
        ]
        table_df["System 1"] = table_df["System 1"].str.title()
        table_df["System 2"] = table_df["System 2"].str.title()
        table_df["Category 1"] = table_df["Category 1"].str.replace("_", " ").str.title()
        table_df["Category 2"] = table_df["Category 2"].str.replace("_", " ").str.title()
        table_df = table_df.sort_values("Overlap Area (km²)", ascending=False)
 
        st.dataframe(
            table_df,
            width='stretch',
            hide_index=True,
            column_config={
                "System 1"         : st.column_config.TextColumn("System 1",  width="medium"),
                "System 2"         : st.column_config.TextColumn("System 2",  width="medium"),
                "County 1"         : st.column_config.TextColumn("County 1",  width="small"),
                "County 2"         : st.column_config.TextColumn("County 2",  width="small"),
                "Overlap Area (km²)": st.column_config.NumberColumn(
                    "Overlap Area (km²)", format="%.2f"),
                "Concurrent Days"  : st.column_config.NumberColumn(
                    "Concurrent Days", format="%d"),
                "Category 1"       : st.column_config.TextColumn("Category 1"),
                "Category 2"       : st.column_config.TextColumn("Category 2"),
                "Year 1"           : st.column_config.NumberColumn("Year 1",  format="%d"),
                "Year 2"           : st.column_config.NumberColumn("Year 2",  format="%d"),
            }
        )
 
    # ── VIZ 3 — Grouped bar: overlap area vs concurrent days per pair ────────
    with col_bar:
        st.markdown("<div class='section-label'>Overlap Area vs Concurrent Days</div>",
                    unsafe_allow_html=True)
 
        bar_df = overlap_gdf.copy()
        bar_df["pair_label"] = bar_df.apply(
            lambda r: (
                r["pws_1"].title().replace(", City Of", "") +
                " ×\n" +
                r["pws_2"].title().replace(", City Of", "")
            ),
            axis=1
        )
 
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Overlap Area (km²)",
            x=bar_df["pair_label"],
            y=bar_df["overlap_area_km2"],
            marker=dict(
                color="#FF6B6B",
                line=dict(color="#0e1117", width=1),
                cornerradius=4,
            ),
            yaxis="y",
            hovertemplate="<b>%{x}</b><br>Area: %{y:.2f} km²<extra></extra>",
        ))
        fig_bar.add_trace(go.Bar(
            name="Concurrent Days",
            x=bar_df["pair_label"],
            y=bar_df["concurrent_days"],
            marker=dict(
                color="#4A9EFF",
                line=dict(color="#0e1117", width=1),
                cornerradius=4,
            ),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Days: %{y}<extra></extra>",
        ))
 
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e0e0e0", family="Inter, sans-serif"),
            title=dict(text="Per-Pair Comparison",
                       font=dict(color="#e0e0e0", size=12), x=0.5),
            xaxis=dict(
                showgrid=False, color="#6e7681",
                tickfont=dict(size=9), tickangle=-10
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                color="#FF6B6B", title="Area (km²)",
                title_font=dict(color="#FF6B6B", size=11),
                zeroline=False,
            ),
            yaxis2=dict(
                overlaying="y", side="right",
                color="#4A9EFF", title="Concurrent Days",
                title_font=dict(color="#4A9EFF", size=11),
                showgrid=False, zeroline=False,
            ),
            barmode="group",
            bargap=0.2,
            legend=dict(
                font=dict(color="#e0e0e0", size=10),
                bgcolor="rgba(0,0,0,0)",
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1,
            ),
            margin=dict(l=10, r=50, t=60, b=10),
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