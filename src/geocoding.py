"""
Phase 7: This Phase Geocoding
Geocodes city locations from the final geospatial dataset,
creates point geometries, applies buffers, and saves as GeoPackage.
"""

import time
import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from logger_config import setup_logger

# -------- Configuration --------

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE   = ROOT / "data" / "geospatial_ready" / "final_for_geospatial.xlsx"
OUTPUT_FILE  = ROOT / "data" / "geocoded_output" / "geocoded_output.gpkg"

# Geocoding settings
GEOCODER_USER_AGENT  = "kansas_bwa_analysis"
GEOCODE_DELAY        = 1.5        # seconds between requests to respect API limits
GEOCODE_LOG_INTERVAL = 50       # log progress every N rows

# Projection settings
CRS_GEOGRAPHIC = "EPSG:4326"    # standard lat/lon
CRS_PROJECTED  = "EPSG:32614"   # UTM Zone 14N — appropriate for Kansas

# Buffer settings
BUFFER_METERS = 10_000          # 10km buffer around each point

# -------- Logger --------

logger = logging.getLogger("kdhe_pipeline")

# -------- Helper Functions --------

def load_data(path):
    """
    This Function loads the final geospatial Excel file.
    """
    logger.info(f"Loading data from: {path}")
    df = pd.read_excel(path)
    logger.info(f"Loaded {len(df)} records")
    return df


def geocode_city(geolocator, city, county):
    """
    This Function geocodes a single city + county combination using Nominatim.
    Returns (lat, lon) or (None, None) if geocoding fails.
    """
    try:
        query = f"{city}, {county}, Kansas, USA"
        location = geolocator.geocode(query)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        logger.warning(f"Geocoding failed for '{city}, {county}': {e}")
        return None, None


def geocode_all(df):
    """
    This Function geocodes all rows using the 'Cities Served' and 'county_clean' columns.
    Adds 'lat' and 'lon' columns to the dataframe.
    Respects API rate limits with a configurable delay between requests.
    """
    logger.info("Starting geocoding...")

    # Prepare county_clean column for geocoding query
    df["county_clean"] = (
        df["County"]
        .str.split(",")
        .str[0]
        .str.strip()
        .str.upper()
    )

    geolocator = Nominatim(user_agent=GEOCODER_USER_AGENT, timeout=10)

    df["lat"] = None
    df["lon"] = None

    for idx, row in df.iterrows():
        lat, lon = geocode_city(geolocator, row["City"], row["county_clean"])
        df.at[idx, "lat"] = lat
        df.at[idx, "lon"] = lon
        time.sleep(GEOCODE_DELAY)

        if idx % GEOCODE_LOG_INTERVAL == 0:
            logger.info(f"Geocoded {idx}/{len(df)} rows")

    success = df["lat"].notna().sum()
    failed  = df["lat"].isna().sum()

    logger.info(f"Geocoding complete — Success: {success} | Failed: {failed}")

    if failed > 0:
        failed_rows = df[df["lat"].isna()][["City", "county_clean"]].drop_duplicates()
        logger.warning(f"Failed geocoding rows:\n{failed_rows.to_string()}")

    return df


def filter_valid_coordinates(df):
    """
    This Function keeps only rows with valid, non-null, non-zero coordinates.
    """
    valid = df[
        df["lat"].notnull() & df["lon"].notnull() &
        (df["lat"] != 0)    & (df["lon"] != 0)
    ].copy()

    logger.info(f"Valid coordinates : {len(valid)} / {len(df)} rows")
    return valid


def create_geodataframe(df):
    """
    This Function creates a GeoDataFrame from lat/lon columns,
    projects to UTM Zone 14N, and adds a buffer geometry column.
    """
    logger.info("Creating point geometries...")
    geometry = [Point(lon, lat) for lon, lat in zip(df["lon"], df["lat"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=CRS_GEOGRAPHIC)

    logger.info(f"Projecting to {CRS_PROJECTED}...")
    gdf = gdf.to_crs(CRS_PROJECTED)

    logger.info(f"Applying {BUFFER_METERS}m buffer...")
    gdf["buffer_geometry"] = gdf.geometry.buffer(BUFFER_METERS)
    gdf["buffer_geometry"] = gdf["buffer_geometry"].to_wkt()

    return gdf


def save_geodataframe(gdf, path):
    """
    This Function saves the GeoDataFrame to a GeoPackage file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG")
    logger.info(f"Saved GeoDataFrame to: {path}")


# -------- Main --------

def main():
    logger.info("=" * 60)
    logger.info("KDHE BOIL WATER ADVISORY - GEOCODING")
    logger.info("Phase 7: Geocoding city locations")
    logger.info("=" * 60)

    # Step 1: To Load data
    df = load_data(INPUT_FILE)

    # Step 2: To geocode all rows
    df = geocode_all(df)

    # Step 3: To filter to valid coordinates only
    df_valid = filter_valid_coordinates(df)

    if df_valid.empty:
        logger.error("No valid coordinates found — aborting.")
        return

    # Step 4: To create GeoDataFrame with point geometry and buffers
    gdf = create_geodataframe(df_valid)

    # Step 5: To save to GeoPackage
    save_geodataframe(gdf, OUTPUT_FILE)

    logger.info("=" * 60)
    logger.info("Phase 7 Complete.")
    logger.info(f"Records geocoded : {len(df_valid)}")
    logger.info(f"Output file      : {OUTPUT_FILE}")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":
    setup_logger()
    main()