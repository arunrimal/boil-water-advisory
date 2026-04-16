"""
BWA Dashboard — Shared Styles
Imported by all pages via:
    from utils.styles import load_css, PLOT_BASE, AXIS_STYLE, CORAL, ORANGE, BLUE, TEAL, GRAY
"""

import streamlit as st

# =============================================================================
# COLOR CONSTANTS — single source of truth for all pages
# =============================================================================
CORAL  = "#FF6B6B"
ORANGE = "#FF8E53"
BLUE   = "#4A9EFF"
TEAL   = "#00D4AA"
GRAY   = "#6e7681"
BG     = "#0e1117"
BG2    = "#161b22"
BG3    = "#1c2333"
TEXT   = "#e0e0e0"
TEXT2  = "#8b949e"
TEXT3  = "#6e7681"
BORDER = "rgba(255, 255, 255, 0.05)"
BORDER2= "rgba(255, 107, 107, 0.15)"

# =============================================================================
# PLOTLY SHARED LAYOUT — used by every chart in every page
# =============================================================================
PLOT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, family="Inter, sans-serif"),
    margin=dict(l=10, r=10, t=45, b=10),
)

AXIS_STYLE = dict(
    showgrid=True,
    gridcolor="rgba(255,255,255,0.05)",
    color=GRAY,
    tickfont=dict(size=11),
    zeroline=False,
)

# styles.py — add after PLOT_BASE and AXIS_STYLE definitions
def apply_layout(fig, **overrides):
    layout = {**PLOT_BASE}

    if "margin" in overrides:
        layout["margin"] = {
            **PLOT_BASE.get("margin", {}),
            **overrides.pop("margin")
        }

    layout.update(overrides)
    fig.update_layout(**layout)

# Colorscale used across severity/intensity charts
SEVERITY_COLORSCALE = [
    [0.0, BLUE],
    [0.5, ORANGE],
    [1.0, CORAL],
]

# =============================================================================
# CSS — injected into every page via load_css()
# =============================================================================
CSS = """
<style>
    /* ── Base dark theme ── */
    .stApp { background-color: #0e1117; }

    /* ── Hero title ── */
    .hero-title {
        font-size: 3.2rem;
        font-weight: 900;
        line-height: 1.15;
        letter-spacing: -1px;
        background: linear-gradient(90deg, #FF6B6B 0%, #FF8E53 60%, #FFC85A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
    }

    .hero-subtitle {
        font-size: 1.15rem;
        color: #8b949e;
        margin-bottom: 2.5rem;
        line-height: 1.6;
    }

    /* ── Section label ── */
    .section-label {
        color: #FF6B6B;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.8rem;
        margin-top: 2rem;
    }

    /* ── Metric cards ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg,
            rgba(28, 35, 48, 0.95) 0%,
            rgba(20, 25, 38, 0.98) 100%);
        border: 1px solid rgba(255, 107, 107, 0.15);
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
        transition: border-color 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(255, 107, 107, 0.4);
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.1rem !important;
        font-weight: 700 !important;
        color: #FF6B6B !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        color: #8b949e !important;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    div[data-testid="stMetricDelta"] { font-size: 0.85rem !important; }

    /* ── Chart card wrapper ── */
    .chart-card {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 14px;
        padding: 1rem;
        margin-bottom: 1rem;
        width: 100%; 
        box-sizing: border-box;
        overflow: visible;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stSlider label {
        color: #8b949e !important;
        font-size: 0.83rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ── Sidebar Navigation Links ── */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {
        # color: #8b949e !important;
        color: #e0e0e0 !important;
    }
    
    /* ── Sidebar Collapse Arrow ── */
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] span {
        color: #8b949e !important;
    }

    /* ── Map Toggle ── */
    .map-panel {
    background: linear-gradient(145deg, #1e1e1e, #2a2a2a);
    padding: 12px 16px;
    border-radius: 14px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
    }
    
    /* ── Map Toggle Hover ── */
    .map-panel:hover {
        transform: translateY(-2px);
    }

    /* ── Info banner ── */
    .info-banner {
        background: linear-gradient(90deg,
            rgba(255, 107, 107, 0.08) 0%,
            rgba(255, 142, 83, 0.05) 100%);
        border-left: 3px solid #FF6B6B;
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        color: #c9d1d9;
        font-size: 0.92rem;
        margin-bottom: 1.5rem;
    }

    /* ── Styled divider ── */
    .styled-divider {
        height: 1px;
        background: linear-gradient(90deg,
            rgba(255,107,107,0.4) 0%,
            rgba(255,142,83,0.2) 50%,
            rgba(0,0,0,0) 100%);
        margin: 2rem 0;
        border: none;
    }

    /* ── About box ── */
    .about-box {
        background: linear-gradient(135deg,
            rgba(28, 35, 48, 0.8) 0%,
            rgba(20, 25, 38, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 14px;
        padding: 1.6rem 2rem;
        color: #8b949e;
        font-size: 0.92rem;
        line-height: 1.8;
    }
    .about-box b { color: #e0e0e0; }

    /* ── Tech badges ── */
    .badge {
        display: inline-block;
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.25);
        color: #FF8E53;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        margin: 3px 4px;
        letter-spacing: 0.3px;
    }

    /* ── Pipeline status ── */
    .status-ok {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(0, 212, 170, 0.1);
        border: 1px solid rgba(0, 212, 170, 0.3);
        color: #00D4AA;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 20px;
    }
    .status-err {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.3);
        color: #FF6B6B;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 20px;
    }
    .dot-ok {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #00D4AA;
        display: inline-block;
        animation: pulse-ok 2s infinite;
    }
    .dot-err {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #FF6B6B;
        display: inline-block;
    }
    @keyframes pulse-ok {
        0%,100% { box-shadow: 0 0 0 0 rgba(0,212,170,0.4); }
        50%      { box-shadow: 0 0 0 5px rgba(0,212,170,0); }
    }

    /* ── Landing page metric cards ── */
    .metric-card {
        background: linear-gradient(135deg,
            rgba(28, 35, 48, 0.95) 0%,
            rgba(20, 25, 38, 0.98) 100%);
        border: 1px solid rgba(255, 107, 107, 0.15);
        border-radius: 16px;
        padding: 1.8rem 1.4rem;
        text-align: center;
        transition: border-color 0.25s, transform 0.2s;
    }
    .metric-card:hover {
        border-color: rgba(255, 107, 107, 0.5);
        transform: translateY(-2px);
    }
    .metric-number {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF6B6B, #FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
        margin-bottom: 0.3rem;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #6e7681;
        margin-top: 0.2rem;
    }

    /* ── Page navigation cards (main.py) ── */
    .page-card {
        background: linear-gradient(135deg,
            rgba(28, 35, 48, 0.9) 0%,
            rgba(20, 25, 38, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 1.4rem;
        height: 100%;
        transition: border-color 0.25s, transform 0.2s, background 0.25s;
        cursor: pointer;
    }
    .page-card:hover {
        border-color: rgba(255, 107, 107, 0.4);
        transform: translateY(-3px);
    }
    .page-icon  { font-size: 2rem; margin-bottom: 0.6rem; display: block; }
    .page-title { font-size: 1rem; font-weight: 700; color: #e0e0e0; margin-bottom: 0.4rem; }
    .page-desc  { font-size: 0.82rem; color: #6e7681; line-height: 1.5; }
    .page-tag   {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 20px;
        margin-top: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ── Footer ── */
    .footer {
        text-align: center;
        color: #6e7681;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* ── Headings ── */
    h2, h3 { color: #e0e0e0; font-weight: 600; margin-top: 1.5rem; }
</style>
"""


# =============================================================================
# FOOTER HTML — shared across all pages
# =============================================================================
def get_footer(author: str = "Arun Rimal",
               email: str = "aarunrimal@gmail.com") -> str:
    from datetime import datetime
    return (
        f"<div class='footer'>"
        f"💧 Kansas Boil Water Advisory Geospatial Dashboard · "
        f"Data: KDHE Disruption in Water Service · "
        f"{author} · {email} · "
        f"{datetime.now().year}"
        f"</div>"
    )


# =============================================================================
# LOAD FUNCTION — called at top of every page
# =============================================================================
def load_css():
    """Inject shared CSS into the current page."""
    st.markdown(CSS, unsafe_allow_html=True)


def load_footer():
    """Render shared footer on the current page."""
    st.markdown("---")
    st.markdown(get_footer(), unsafe_allow_html=True)