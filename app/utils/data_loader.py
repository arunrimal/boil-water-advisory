"""
BWA Data Loader Utility
Updated based on notebook geospatial analysis patterns
"""

import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from shapely import wkt
from datetime import datetime
import os
import gcsfs
import warnings

warnings.filterwarnings('ignore', category=UserWarning)



# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

ENV = os.getenv("ENV", "local")
GCP_BUCKET = "bwa-streamlit-app-data"

CREDENTIALS_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    Path(__file__).resolve().parent.parent / "credentials.json"
)

def get_gcs_filesystem():
    """Get authenticated GCS filesystem"""
    if ENV == "cloud":
        return gcsfs.GCSFileSystem(token=str(CREDENTIALS_PATH))
    return None


# =============================================================================
# PATH CONFIGURATION (from notebook pattern)
# =============================================================================

def get_project_root() -> Path:
    """Get project root directory (2 levels up from this file)"""
    return Path(__file__).resolve().parents[2]

def get_data_path() -> Path:
    """Get path to geocoded output geopackage"""
    if ENV == "cloud":
        return f"gs://{GCP_BUCKET}/outputs/geocoded_output.gpkg"
    return get_project_root() / "outputs" / "geocoded_output.gpkg"

def get_county_shapefile_path() -> Optional[Path]:
    """Get path to US counties shapefile if it exists"""
    if ENV == "cloud":
        return f"gs://{GCP_BUCKET}/tl_2024_us_county/tl_2024_us_county.shp"
    shp_path = get_project_root() / "tl_2024_us_county" / "tl_2024_us_county.shp"
    return shp_path if shp_path.exists() else None


# =============================================================================
# CORE DATA LOADING (based on notebook patterns)
# =============================================================================

@st.cache_data(show_spinner=False, ttl=3600, max_entries=1)
def load_bwa_data(
    apply_preprocessing: bool = True,
    validate: bool = True
) -> Optional[gpd.GeoDataFrame]:
    """Load BWA data from geocoded_output.gpkg with caching."""
    data_path = get_data_path()

    # Check existence for local only
    if ENV == "local" and not Path(str(data_path)).exists():
        st.error(f"❌ Data file not found: {data_path}")
        return None

    try:
        # Use GCS filesystem for cloud
        if ENV == "cloud":
            fs = get_gcs_filesystem()
            with fs.open(str(data_path), "rb") as f:
                gdf = gpd.read_file(f)
        else:
            gdf = gpd.read_file(data_path)

        gdf = gdf.to_crs(epsg=4326)

        if apply_preprocessing:
            gdf = _preprocess_data(gdf)

        if validate:
            _validate_data(gdf)

        return gdf

    except Exception as e:
        st.error(f"❌ Error loading BWA data: {str(e)}")
        import traceback
        st.sidebar.expander("🔧 Error Details").code(traceback.format_exc())
        return None


def _preprocess_data(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Preprocess data following notebook patterns exactly.
    """
    gdf = gdf.copy()
    
    # ---- YEAR HANDLING (notebook: Year used directly, but ensure numeric) ----
    if "Year" in gdf.columns:
        # Robust conversion: string "2023" -> int 2023
        gdf["Year"] = pd.to_numeric(gdf["Year"], errors='coerce')
        # Remove rows with invalid years
        invalid_years = gdf["Year"].isna().sum()
        if invalid_years > 0:
            st.sidebar.warning(f"⚠️ {invalid_years} rows with invalid Year removed")
            gdf = gdf.dropna(subset=["Year"])
        gdf["Year"] = gdf["Year"].astype(int)
    
    # ---- BUFFER GEOMETRY (notebook pattern) ----
    if "buffer_geometry" in gdf.columns:
        try:
            # Step 1: Parse WKT to Shapely geometries (notebook)
            gdf["buffer_geometry"] = gdf["buffer_geometry"].apply(
                lambda x: wkt.loads(x) if isinstance(x, str) else x
            )
            # Step 2: Convert to GeoSeries with proper CRS (notebook: EPSG:32614)
            gdf["buffer_geometry"] = gpd.GeoSeries(
                gdf["buffer_geometry"], 
                crs="EPSG:32614"
            )
        except Exception as e:
            st.warning(f"Could not parse buffer_geometry: {e}")
    
    # ---- POPULATION CLEANING (notebook pattern) ----
    if "Population_Served" in gdf.columns:
        gdf["Population_Served"] = (
            gdf["Population_Served"]
            .astype(str)
            .str.replace(",", "", regex=False)   # Remove commas
            .str.replace(" ", "", regex=False)   # Remove spaces
            .replace('', '0')                      # Empty -> 0
            .astype(float)
            .fillna(0)
        )
    
    # ---- COORDINATE FIELDS (notebook pattern) ----
    for col in ["lat", "lon"]:
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors='coerce')
    
    # ---- DATE PARSING (notebook pattern) ----
    date_cols = ["Issues_Date", "Lifted_Date", "Rescinded_Date", "Compliance_Date"]
    for col in date_cols:
        if col in gdf.columns:
            gdf[col] = pd.to_datetime(gdf[col], errors='coerce')
    
    # ---- SEVERITY INDEX (notebook pattern: Duration × Population × Violations) ----
    gdf = _compute_severity_metrics(gdf)
    
    # ---- COUNTY NAME CLEANING (notebook shows county names have variations) ----
    if "County" in gdf.columns:
        # Store original for reference
        gdf["County_Original"] = gdf["County"]
        # Clean: title case for display
        gdf["County"] = gdf["County"].str.title()
    
    # ---- STANDARDIZE COLUMN NAMES ----
    column_mapping = {
        'pws_name': 'PWS_Name',
        'pws_id': 'Federal_ID',
        'county_name': 'County',
        'advisory_type': 'Advisory_Category',
        'duration_days': 'Advisory_Duration',
        'violations': 'No._of_Violations',
    }
    
    for old, new in column_mapping.items():
        if old in gdf.columns and new not in gdf.columns:
            gdf.rename(columns={old: new}, inplace=True)
    
    return gdf


def _compute_severity_metrics(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Compute severity metrics following notebook pattern exactly.
    Notebook: severity_index = Duration × Population × Violations
    """
    # Check required columns (notebook uses these three)
    required = ["Advisory_Duration", "Population_Served", "No._of_Violations"]
    available = [col for col in required if col in gdf.columns]
    
    if len(available) == 3:
        # Raw severity index (notebook pattern)
        gdf["severity_index"] = (
            gdf["Advisory_Duration"] * 
            gdf["Population_Served"] * 
            gdf["No._of_Violations"]
        )
        
        # Log-transformed for visualization (notebook pattern)
        gdf["severity_log"] = np.log1p(gdf["severity_index"])
        
        # Normalized 0-1 score for color mapping
        min_sev = gdf["severity_index"].min()
        max_sev = gdf["severity_index"].max()
        if max_sev > min_sev:
            gdf["severity_score"] = (gdf["severity_index"] - min_sev) / (max_sev - min_sev)
        else:
            gdf["severity_score"] = 0.5
            
        # Severity categories (for analysis)
        gdf["severity_level"] = pd.cut(
            gdf["severity_score"],
            bins=[0, 0.25, 0.5, 0.75, 1.0],
            labels=["Low", "Medium", "High", "Critical"],
            include_lowest=True
        )
        
        # Additional: has_district flag (notebook pattern for rural/urban)
        if "District" in gdf.columns:
            gdf["has_district"] = gdf["District"].notna()
    
    return gdf


def _validate_data(gdf: gpd.GeoDataFrame) -> None:
    """Run validation checks based on notebook expectations"""
    issues = []
    
    if len(gdf) == 0:
        issues.append("Dataset is empty")
    
    # Check for required columns (based on notebook usage)
    required_cols = ["PWS_Name", "County", "Year", "Advisory_Duration", 
                     "Population_Served", "No._of_Violations", "lat", "lon"]
    missing = [col for col in required_cols if col not in gdf.columns]
    if missing:
        issues.append(f"Missing columns: {missing}")
        issues.append(f"Available: {list(gdf.columns)}")
    
    # Check geometry validity
    if gdf.geometry.isna().any():
        null_count = gdf.geometry.isna().sum()
        issues.append(f"{null_count} records with missing geometry")
    
    # Check coordinate bounds (Kansas approximate from notebook)
    if 'lat' in gdf.columns and 'lon' in gdf.columns:
        out_of_bounds = (
            (gdf['lat'] < 37) | (gdf['lat'] > 40) |
            (gdf['lon'] < -102) | (gdf['lon'] > -95)
        ).sum()
        if out_of_bounds > 0:
            issues.append(f"{out_of_bounds} records outside Kansas bounds")
    
    # Check for negative or zero durations
    if "Advisory_Duration" in gdf.columns:
        invalid_dur = (gdf["Advisory_Duration"] <= 0).sum()
        if invalid_dur > 0:
            issues.append(f"{invalid_dur} records with invalid duration")
    
    if issues:
        for issue in issues:
            st.warning(f"⚠️ {issue}")


# =============================================================================
# COUNTY DATA LOADING (notebook pattern)
# =============================================================================

@st.cache_data(show_spinner=False, ttl=3600)
def load_kansas_counties() -> Optional[gpd.GeoDataFrame]:
    """Load Kansas county boundaries from shapefile."""
    shp_path = get_county_shapefile_path()

    if not shp_path:
        st.sidebar.info("County shapefile not found - county maps disabled")
        return None

    try:
        if ENV == "cloud":
            fs = get_gcs_filesystem()
            with fs.open(str(shp_path), "rb") as f:
                us_counties = gpd.read_file(f)
        else:
            us_counties = gpd.read_file(shp_path)

        us_counties = us_counties.to_crs(epsg=4326)
        ks_counties = us_counties[us_counties["STATEFP"] == "20"].copy()
        return ks_counties

    except Exception as e:
        st.sidebar.warning(f"Could not load counties: {e}")
        return None


# =============================================================================
# FILTERING UTILITIES
# =============================================================================

def get_filter_options(
    gdf: gpd.GeoDataFrame,
    column: str,
    sort: bool = True,
    include_all: bool = True
) -> List[Any]:
    """Get unique values for filter dropdowns"""
    if column not in gdf.columns:
        return ["All"] if include_all else []
    
    values = gdf[column].dropna().unique().tolist()
    
    if sort:
        try:
            # Numeric sort for years, etc.
            values = sorted(values, key=lambda x: float(x))
        except (ValueError, TypeError):
            values = sorted(values, key=str)
    
    if include_all:
        if pd.api.types.is_numeric_dtype(gdf[column]):
            return values
        return ["All"] + values
    
    return values


def apply_filters(
    gdf: gpd.GeoDataFrame,
    year: Optional[str] = None,
    categories: Optional[List[str]] = None,
    duration_range: Optional[Tuple[int, int]] = None,
    pws_types: Optional[List[str]] = None,
    counties: Optional[List[str]] = None,
    severity_threshold: Optional[float] = None
) -> gpd.GeoDataFrame:
    """
    Apply multiple filters to dataset.
    Robust error handling for production use.
    """
    filtered = gdf.copy()
    
    # Year filter with type safety
    if year and year not in ["All", "All years"]:
        if "Year" not in filtered.columns:
            st.error("❌ 'Year' column not found for filtering")
            return filtered
        
        try:
            year_int = int(float(year))  # Handles "2023.0" or "2023"
            filtered = filtered[filtered["Year"] == year_int]
        except (ValueError, TypeError) as e:
            st.error(f"❌ Invalid year value '{year}': {e}")
            return filtered
    
    # Category filter
    if categories and "Advisory_Category" in filtered.columns:
        filtered = filtered[filtered["Advisory_Category"].isin(categories)]
    
    # Duration filter
    if duration_range and "Advisory_Duration" in filtered.columns:
        min_dur, max_dur = duration_range
        filtered = filtered[
            (filtered["Advisory_Duration"] >= min_dur) &
            (filtered["Advisory_Duration"] <= max_dur)
        ]
    
    # PWS Type filter
    if pws_types and "PWS_Type" in filtered.columns:
        filtered = filtered[filtered["PWS_Type"].isin(pws_types)]
    
    # County filter
    if counties and "County" in filtered.columns:
        filtered = filtered[filtered["County"].isin(counties)]
    
    # Severity threshold
    if severity_threshold is not None and "severity_score" in filtered.columns:
        filtered = filtered[filtered["severity_score"] >= severity_threshold]
    
    return filtered


# =============================================================================
# METRIC COMPUTATIONS (based on notebook analysis patterns)
# =============================================================================

def compute_metrics(
    gdf: gpd.GeoDataFrame,
    compare_gdf: Optional[gpd.GeoDataFrame] = None
) -> Dict[str, Any]:
    """
    Compute key metrics following notebook patterns.
    """
    metrics = {}
    
    # Basic counts
    metrics["total_advisories"] = len(gdf)
    metrics["unique_systems"] = gdf["Federal_ID"].nunique() if "Federal_ID" in gdf.columns else 0
    metrics["counties_affected"] = gdf["County"].nunique() if "County" in gdf.columns else 0
    
    # Population metrics (notebook pattern)
    if "Population_Served" in gdf.columns:
        pop = gdf["Population_Served"]
        metrics["total_population"] = int(pop.sum())
        metrics["avg_population"] = pop.mean()
        metrics["median_population"] = pop.median()
    else:
        metrics["total_population"] = 0
        metrics["avg_population"] = 0
        metrics["median_population"] = 0
    
    # Duration metrics (notebook pattern)
    if "Advisory_Duration" in gdf.columns:
        dur = gdf["Advisory_Duration"]
        metrics["avg_duration"] = dur.mean()
        metrics["median_duration"] = dur.median()
        metrics["max_duration"] = dur.max()
        metrics["total_duration_days"] = dur.sum()
    else:
        metrics["avg_duration"] = 0
        metrics["median_duration"] = 0
        metrics["max_duration"] = 0
        metrics["total_duration_days"] = 0
    
    # Severity metrics (notebook pattern)
    if "severity_index" in gdf.columns:
        sev = gdf["severity_index"]
        metrics["avg_severity"] = sev.mean()
        metrics["max_severity"] = sev.max()
        metrics["total_severity"] = sev.sum()
        metrics["high_severity_count"] = len(gdf[gdf["severity_score"] > 0.7])
    else:
        metrics["avg_severity"] = 0
        metrics["max_severity"] = 0
        metrics["total_severity"] = 0
        metrics["high_severity_count"] = 0
    
    # Violations
    if "No._of_Violations" in gdf.columns:
        metrics["total_violations"] = gdf["No._of_Violations"].sum()
        metrics["avg_violations"] = gdf["No._of_Violations"].mean()
    else:
        metrics["total_violations"] = 0
        metrics["avg_violations"] = 0
    
    # Deltas if comparison data provided
    if compare_gdf is not None:
        compare_metrics = compute_metrics(compare_gdf)
        metrics["delta_advisories"] = metrics["total_advisories"] - compare_metrics["total_advisories"]
        metrics["delta_duration"] = metrics["avg_duration"] - compare_metrics["avg_duration"]
        metrics["delta_population"] = metrics["total_population"] - compare_metrics["total_population"]
    
    return metrics


def compute_yearly_trends(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Compute yearly aggregation (notebook pattern).
    Notebook: year_counts = bwa_gdf["Year"].value_counts().sort_index()
    """
    if "Year" not in gdf.columns:
        return pd.DataFrame()
    
    # Match notebook pattern exactly
    yearly = gdf.groupby("Year").agg(
        count=("Advisory_Duration", "count"),
        avg_duration=("Advisory_Duration", "mean"),
        total_population=("Population_Served", "sum"),
        total_violations=("No._of_Violations", "sum"),
        unique_systems=("Federal_ID", "nunique"),
        avg_severity=("severity_score", "mean"),
        total_severity=("severity_index", "sum")
    ).reset_index()
    
    return yearly


def compute_monthly_patterns(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Compute monthly aggregation (notebook pattern).
    Notebook extracts month from Issues_Date.
    """
    if "Issues_Date" not in gdf.columns:
        return pd.DataFrame()
    
    gdf = gdf.copy()
    gdf["month"] = pd.to_datetime(gdf["Issues_Date"]).dt.month
    
    monthly = gdf.groupby("month").agg(
        count=("Advisory_Duration", "count"),
        avg_duration=("Advisory_Duration", "mean"),
        total_population=("Population_Served", "sum"),
        total_violations=("No._of_Violations", "sum")
    ).reset_index()
    
    # Add month names (notebook pattern)
    month_names = {i: datetime(2000, i, 1).strftime("%b") for i in range(1, 13)}
    monthly["month_name"] = monthly["month"].map(month_names)
    
    return monthly


def compute_county_aggregation(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    County-level aggregation (notebook pattern).
    Notebook: county_severity = bwa_gdf.groupby('County').agg({...})
    """
    if "County" not in gdf.columns:
        return pd.DataFrame()
    
    county_agg = gdf.groupby("County").agg(
        systems=("Federal_ID", "nunique"),
        notice_count=("Advisory_Duration", "count"),
        total_days=("Advisory_Duration", "sum"),
        avg_days=("Advisory_Duration", "mean"),
        total_pop=("Population_Served", "sum"),
        avg_pop=("Population_Served", "mean"),
        total_violations=("No._of_Violations", "sum"),
        total_severity=("severity_index", "sum"),
        avg_severity=("severity_index", "mean")
    ).reset_index()
    
    return county_agg


def compute_repeat_offenders(gdf: gpd.GeoDataFrame, min_notices: int = 2) -> pd.DataFrame:
    """
    Identify repeat offender systems (notebook pattern).
    Notebook: repeat = bwa_gdf.groupby(["Federal_ID", "PWS_Name", "County"]).agg(...)
    """
    if "Federal_ID" not in gdf.columns:
        return pd.DataFrame()
    
    repeat = (
        gdf.groupby(["Federal_ID", "PWS_Name", "County"])
        .agg(
            notice_count=("Advisory_Duration", "count"),
            total_duration=("Advisory_Duration", "sum"),
            avg_duration=("Advisory_Duration", "mean"),
            total_violations=("No._of_Violations", "sum"),
            total_severity=("severity_index", "sum"),
            first_advisory=("Issues_Date", "min"),
            last_advisory=("Issues_Date", "max")
        )
        .reset_index()
        .sort_values("notice_count", ascending=False)
    )
    
    # Filter to actual repeat offenders
    repeat = repeat[repeat["notice_count"] >= min_notices]
    
    return repeat


# =============================================================================
# INSIGHTS GENERATION (based on notebook analysis)
# =============================================================================

def generate_insights(
    gdf: gpd.GeoDataFrame, 
    historical_gdf: Optional[gpd.GeoDataFrame] = None
) -> Dict[str, Any]:
    """
    Generate insights following notebook analysis patterns.
    """
    insights = {}
    
    if len(gdf) == 0:
        insights["summary"] = "No data matches current filters."
        return insights
    
    # Top county (notebook pattern)
    if "County" in gdf.columns:
        county_counts = gdf["County"].value_counts()
        insights["top_county"] = county_counts.index[0]
        insights["top_county_count"] = county_counts.iloc[0]
        insights["county_count"] = gdf["County"].nunique()
    
    # Duration trend (notebook pattern)
    if "Advisory_Duration" in gdf.columns and historical_gdf is not None:
        current_avg = gdf["Advisory_Duration"].mean()
        hist_avg = historical_gdf["Advisory_Duration"].mean()
        dur_diff = current_avg - hist_avg
        insights["duration_delta"] = dur_diff
        insights["duration_trend"] = "increasing" if dur_diff > 0 else "decreasing"
        insights["duration_pct_change"] = (dur_diff / hist_avg * 100) if hist_avg != 0 else 0
    
    # Top cause (notebook pattern)
    if "Advisory_Category" in gdf.columns:
        cause_counts = gdf["Advisory_Category"].value_counts()
        insights["top_cause"] = cause_counts.index[0]
        insights["top_cause_count"] = cause_counts.iloc[0]
        insights["top_cause_pct"] = (cause_counts.iloc[0] / len(gdf)) * 100
        insights["cause_count"] = gdf["Advisory_Category"].nunique()
    
    # High severity (notebook pattern: severity_index > threshold)
    if "severity_score" in gdf.columns:
        high_sev = len(gdf[gdf["severity_score"] > 0.7])
        insights["high_severity_count"] = high_sev
        insights["high_severity_pct"] = (high_sev / len(gdf)) * 100
    
    # Repeat offenders count (notebook pattern)
    if "Federal_ID" in gdf.columns:
        system_counts = gdf["Federal_ID"].value_counts()
        repeat_offenders = len(system_counts[system_counts > 1])
        insights["repeat_offenders"] = repeat_offenders
        insights["repeat_offender_pct"] = (repeat_offenders / gdf["Federal_ID"].nunique()) * 100
    
    # Rural vs Urban (notebook pattern: has_district flag)
    if "has_district" in gdf.columns:
        rural_count = (~gdf["has_district"]).sum()
        urban_count = gdf["has_district"].sum()
        insights["rural_count"] = rural_count
        insights["urban_count"] = urban_count
    
    # Population insights (notebook pattern)
    if "Population_Served" in gdf.columns:
        pop = gdf["Population_Served"]
        insights["population_median"] = pop.median()
        insights["population_max"] = pop.max()
        insights["large_systems"] = len(gdf[pop > 5000])  # Notebook threshold
    
    return insights


# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================

def init_session_state_defaults():
    """Initialize all session state variables with defaults"""
    defaults = {
        "selected_year": "All years",
        "selected_cats": [],
        "dur_range": (1, 365),
        "selected_pws": [],
        "selected_counties": [],
        "severity_threshold": 0.0,
        "filtered_data": None,
        "all_data": None,
        "last_page": None,
        "data_loaded": False,
        "filters_reset": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_filters_to_session(
    year: str,
    categories: List[str],
    duration_range: Tuple[int, int],
    pws_types: List[str]
):
    """Save current filter selections to session state"""
    st.session_state.selected_year = year
    st.session_state.selected_cats = categories
    st.session_state.dur_range = duration_range
    st.session_state.selected_pws = pws_types


def load_filters_from_session() -> Dict[str, Any]:
    """Load filter selections from session state"""
    return {
        "year": st.session_state.get("selected_year", "All years"),
        "categories": st.session_state.get("selected_cats", []),
        "duration_range": st.session_state.get("dur_range", (1, 365)),
        "pws_types": st.session_state.get("selected_pws", [])
    }


# =============================================================================
# EXPORT UTILITIES (notebook pattern)
# =============================================================================

def export_data_summary(gdf: gpd.GeoDataFrame, format: str = "csv") -> bytes:
    """
    Export filtered data for download.
    Drops geometry columns for tabular export.
    """
    # Drop geometry columns (notebook pattern)
    cols_to_drop = ['geometry', 'buffer_geometry', 'buffer_geometry_wkt']
    df_export = pd.DataFrame(gdf.drop(columns=cols_to_drop, errors='ignore'))
    
    if format == "csv":
        return df_export.to_csv(index=False).encode('utf-8')
    elif format == "excel":
        import io
        buffer = io.BytesIO()
        df_export.to_excel(buffer, index=False, engine='openpyxl')
        return buffer.getvalue()
    else:
        raise ValueError(f"Unsupported format: {format}")


# =============================================================================
# DEBUGGING UTILITIES
# =============================================================================

def log_data_info(gdf: gpd.GeoDataFrame, label: str = "Data"):
    """Log data info to sidebar for debugging"""
    with st.sidebar:
        with st.expander(f"🔧 {label} Info", expanded=False):
            st.write(f"**Records:** {len(gdf):,}")
            st.write(f"**Columns:** {len(gdf.columns)}")
            st.write(f"**CRS:** {gdf.crs}")
            
            if 'Year' in gdf.columns:
                st.write(f"**Year range:** {gdf['Year'].min()} - {gdf['Year'].max()}")
            
            if st.checkbox("Show columns", key=f"cols_{label}"):
                st.write(list(gdf.columns))
            
            if st.checkbox("Show sample", key=f"sample_{label}"):
                st.dataframe(gdf.head(3))


# Make module runnable for testing
if __name__ == "__main__":
    st.title("Data Loader Test")
    st.write("Testing data loading utilities...")
    
    # Test load
    gdf = load_bwa_data()
    
    if gdf is not None:
        st.success(f"✅ Loaded {len(gdf):,} records")
        
        # Show sample metrics
        metrics = compute_metrics(gdf)
        st.subheader("Sample Metrics")
        st.json({k: v for k, v in metrics.items() if 'delta' not in k})
        
        # Show sample insights
        insights = generate_insights(gdf)
        st.subheader("Sample Insights")
        st.json(insights)
        
        # Test yearly trends
        yearly = compute_yearly_trends(gdf)
        if not yearly.empty:
            st.subheader("Yearly Trends (first 5)")
            st.dataframe(yearly.head())
    else:
        st.error("❌ Failed to load data")

