import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import box, Polygon
import shapely
from all_types.request_dtypes import (
    ReqIntelligenceData,
    ReqFetchDataset,
    ReqClustersForSalesManData,
)
from storage import fetch_intelligence_by_viewport
from data_fetcher import fetch_country_city_data, fetch_dataset
import contextily as ctx
from typing import Tuple
import asyncio
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def define_boundary(bounding_box: list[tuple[float, float]]) -> Polygon:
    """
    args:
    ----
    A list of tuples containing containing lng, lat information.
    The length of the list must be [3,inf)

    return:
    ------
    A shapely polygon
    """
    boundary = Polygon([[p[0], p[1]] for p in bounding_box])
    return boundary


async def get_population_and_income(
    bounding_box: list[tuple[float, float]], zoom_level: int
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Fetch both population and income data for a specific bounding box and zoom level
    using the API endpoint, making two separate calls.

    Args:
        bounding_box: List of (longitude, latitude) tuples defining the area
        zoom_level: The zoom level to retrieve data for

    Returns:
        Tuple of (population_gdf, income_gdf) GeoDataFrames
    """
    # Calculate bounding box coordinates once
    min_lng = min(point[0] for point in bounding_box)
    max_lng = max(point[0] for point in bounding_box)
    min_lat = min(point[1] for point in bounding_box)
    max_lat = max(point[1] for point in bounding_box)

    # Create base request object with common parameters
    base_request = {
        "min_lng": min_lng,
        "min_lat": min_lat,
        "max_lng": max_lng,
        "max_lat": max_lat,
        "zoom_level": zoom_level,
        "user_id": "your_user_id",  # You'll need to provide this
    }

    # Create population-only request
    population_request = ReqIntelligenceData(
        **base_request, population=True, income=False
    )

    # Create combined population and income request
    income_request = ReqIntelligenceData(
        **base_request, population=True, income=True
    )

    # Fetch both datasets concurrently

    population_task = fetch_intelligence_by_viewport(population_request)
    income_task = fetch_intelligence_by_viewport(income_request)

    # Wait for both tasks to complete
    population_data, income_data = await asyncio.gather(
        population_task, income_task
    )

    # Process population data
    population_features = population_data.get("features", [])
    population_gdf = (
        gpd.GeoDataFrame.from_features(population_features)
        if population_features
        else gpd.GeoDataFrame()
    )

    # Process income data
    income_features = income_data.get("features", [])
    income_gdf = (
        gpd.GeoDataFrame.from_features(income_features)
        if income_features
        else gpd.GeoDataFrame()
    )

    return population_gdf, income_gdf


def filter_data_by_bounding_box(
    places_data: dict = None,
    bounding_box: list[tuple[float, float]] = None,
) -> gpd.GeoDataFrame:
    """
    Filter places data by a boundary polygon.
    args:
    ----
    `places_data` is the GeoJSON FeatureCollection object (e.g., supermarkets, pharmacies)
    `bounding_box` is the list of lon lat pairs to develop a shapely polygon
    return:
    ------
    GeoDataFrame filtered using bounding box
    """
    # Create GeoDataFrame directly from the GeoJSON FeatureCollection
    places = gpd.GeoDataFrame.from_features(places_data["features"])

    # Create boundary polygon
    city_boundary = define_boundary(bounding_box)

    # Filter by boundary
    places = places[places.within(city_boundary)]

    # Add longitude and latitude columns
    places["longitude"] = places.geometry.x
    places["latitude"] = places.geometry.y

    return places


def create_grid(
    population: gpd.GeoDataFrame | None = None, grid_size: int | None = None
) -> gpd.GeoDataFrame:
    """
    args:
    ----
    `pouplation` is the filtered data set from `get_population_by_zoom_in_bounding_box`
    `grid_size` is the size of the grid. if set None the grid size will be calculated based on the
    available data. donot set its value unless necessary

    return:
    ------
    A dataframe containing geometry column having polygon covering the ROI
    """

    logger.info(
        f"Starting grid creation with {len(population)} population data points"
    )

    population = population.set_crs("EPSG:4326")

    # Extract the minimum bounding rectangle (MBR) of all population data points
    # This follows cartographic principles of defining the spatial extent for tessellation
    # Example output: minx=-74.25, miny=40.47, maxx=-73.70, maxy=40.92 (NYC coordinates)
    minx, miny, maxx, maxy = population.total_bounds
    total_area = (maxx - minx) * (maxy - miny)

    logger.info(
        f"Study area bounds: [{minx:.4f}, {miny:.4f}] to [{maxx:.4f}, {maxy:.4f}]"
    )
    logger.info(
        f"Total study area: {total_area:.2f} square degrees ({total_area * 111.32**2:.2f} km²)"
    )

    # Calculate optimal grid size using spatial statistical theory
    # Formula: grid_size = √(total_area / number_of_points)
    # This ensures each grid cell represents approximately one data point on average
    # Based on uniform sampling theory and spatial aggregation principles
    # Example: For NYC with 1000 population points over 55km x 45km area:
    # a_grid_size = √((55 * 45) / 1000) = √2.475 ≈ 1.57 km per grid cell
    a_grid_size = (total_area / population.shape[0]) ** 0.5

    logger.info(
        f"Calculated optimal grid size: {a_grid_size:.6f} degrees ({a_grid_size * 111.32:.2f} km)"
    )
    logger.info("This means ~1 population data point per grid cell on average")

    # Use calculated optimal size if no manual override provided
    # Allows for adaptive grid resolution based on data density
    if grid_size is None:
        grid_size = a_grid_size
        logger.info("Using calculated optimal grid size")
    else:
        logger.info(
            f"Using manual override grid size: {grid_size:.6f} degrees ({grid_size * 111.32:.2f} km)"
        )

    # Calculate expected number of grid cells
    expected_x_cells = int(np.ceil((maxx - minx) / grid_size))
    expected_y_cells = int(np.ceil((maxy - miny) / grid_size))
    expected_total_cells = expected_x_cells * expected_y_cells

    logger.info(
        f"Expected grid dimensions: {expected_x_cells} × {expected_y_cells} = {expected_total_cells} total cells"
    )

    # Create regular tessellation using systematic sampling theory
    # Generates a fishnet grid of square polygons covering the entire study area
    # Each box(x, y, x+size, y+size) creates a square polygon geometry
    # Uses nested list comprehension for efficient vectorized grid generation
    # Example: For 55km x 45km area with 1.57km grid size = ~35 x 29 = ~1015 grid cells
    grid_cells = [
        box(
            x, y, x + grid_size, y + grid_size
        )  # Create square polygon for each grid position
        for x in np.arange(
            minx, maxx, grid_size
        )  # Iterate through x-coordinates
        for y in np.arange(
            miny, maxy, grid_size
        )  # Iterate through y-coordinates
    ]

    logger.info(
        f"Generated {len(grid_cells)} grid cells (expected {expected_total_cells})"
    )

    # Convert list of geometries to GeoDataFrame with proper coordinate reference system
    # Inherits CRS from population data to maintain spatial accuracy
    grid = gpd.GeoDataFrame(geometry=grid_cells, crs=population.crs)

    logger.info(f"Created grid GeoDataFrame with CRS: {grid.crs}")
    logger.info("Grid creation completed successfully")

    return grid


def haversine(
    lat1_array: np.ndarray,
    lon1_array: np.ndarray,
    lat2_array: np.ndarray,
    lon2_array: np.ndarray,
) -> np.ndarray:
    """
    args:
    `lat1_array, lon1_array, lat2_array, lon2_array` are the arrays of origins and destinations.
    lat1, lon1 are for the origins in degrres (population center)
    lat2, lon2 are for the destination in degrees (places)

    return:
    ------
    A numpy array for distance matrix calculated using haversine formula which takes inaccount the
    curvature of the earth. The returned distances are in km
    """

    logger.info(
        f"Computing Haversine distances: {len(lat1_array)} origins × {len(lat2_array)} destinations"
    )
    logger.info(
        f"Total distance calculations: {len(lat1_array) * len(lat2_array):,}"
    )

    # Convert decimal degrees to radians for trigonometric calculations
    # All trigonometric functions in numpy work with radians, not degrees
    # Example: 40.7589° → 0.7118 radians, -73.9851° → -1.2915 radians
    lat1_rad, lon1_rad = np.radians(lat1_array), np.radians(lon1_array)
    lat2_rad, lon2_rad = np.radians(lat2_array), np.radians(lon2_array)

    logger.debug("Converted coordinates to radians")
    logger.debug(
        f"Origin latitude range: {np.min(lat1_rad):.4f} to {np.max(lat1_rad):.4f} radians"
    )
    logger.debug(
        f"Origin longitude range: {np.min(lon1_rad):.4f} to {np.max(lon1_rad):.4f} radians"
    )

    # Reshape origin arrays to enable broadcasting for distance matrix computation
    # Creates column vectors (M, 1) for origins to broadcast against row vectors (N,) for destinations
    # This mathematical technique enables vectorized computation of all pairwise distances
    # Example: 500 origins × 200 destinations = 500×1 array broadcasts to 500×200 matrix
    lat1_rad = lat1_rad[
        :, np.newaxis
    ]  # (M, 1) - each origin latitude as column
    lon1_rad = lon1_rad[
        :, np.newaxis
    ]  # (M, 1) - each origin longitude as column

    logger.debug(
        f"Reshaped arrays for broadcasting: {lat1_rad.shape} × {lat2_rad.shape}"
    )

    # Calculate coordinate differences using broadcasting
    # Results in (M, N) matrices where each element [i,j] represents difference between origin i and destination j
    # Example: Manhattan to Brooklyn bridge = 40.7831-40.7589 = 0.0242° ≈ 0.0004 radians latitude difference
    dlat = lat2_rad - lat1_rad  # (M, N) - latitude differences
    dlon = lon2_rad - lon1_rad  # (M, N) - longitude differences

    logger.debug(f"Calculated coordinate differences with shape: {dlat.shape}")

    # Apply Haversine formula for great-circle distances on a sphere
    # Formula: a = sin²(Δφ/2) + cos φ₁ ⋅ cos φ₂ ⋅ sin²(Δλ/2)
    # This accounts for Earth's curvature and provides accurate distances
    # First term: handles latitudinal differences
    # Second term: handles longitudinal differences scaled by latitude cosines
    # Example: For 2.5km distance, a ≈ 0.000039 (very small for short distances)
    a = (
        np.sin(dlat / 2.0) ** 2  # Latitudinal component
        + np.cos(lat1_rad)
        * np.cos(lat2_rad)
        * np.sin(dlon / 2.0) ** 2  # Longitudinal component
    )

    # Complete Haversine formula: c = 2 ⋅ arctan2(√a, √(1−a))
    # arctan2 handles edge cases better than arcsin and provides numerical stability
    # Example: For a=0.000039, c ≈ 0.000395 radians (angular distance)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Earth's mean radius in kilometers (WGS84 approximation)
    # Multiply angular distance by radius to get linear distance
    # Example: 0.000395 radians × 6371 km = 2.52 km (final distance)
    R = 6371.0
    distances = R * c  # (M, N) - final distance matrix in kilometers

    logger.info(
        f"Haversine calculation completed. Distance matrix shape: {distances.shape}"
    )
    logger.info(
        f"Distance statistics: min={np.min(distances):.2f}km, max={np.max(distances):.2f}km, mean={np.mean(distances):.2f}km"
    )
    logger.info(
        "This represents realistic Earth-surface distances accounting for planetary curvature"
    )

    return distances


def get_grids_of_data(
    population_gdf: gpd.GeoDataFrame,
    places: gpd.GeoDataFrame,
    weights: gpd.GeoDataFrame,
    distanace_limit: float,
) -> gpd.GeoDataFrame:
    """
    Creates a grid representation of the area and aggregates population and places data within each grid cell,
    calculating accessibility and market potential.

    args:
    ----
    `population_gdf` are the population centers in a form if geodataframe
    `places` are the places geodataframe
    `weights` are the income dataframes in this context for each population center keep `None` if unavailable
    `distance_limit` is a max distance a person is willing to travel to reach destination

    return:
    ------
    a single geodataframe containing polygons (grids) for entire ROI and aggregated data for each grid
    cell (population, places counts)
    """

    logger.info(
        f"Starting grid data aggregation with {len(population_gdf)} population centers, {len(places)} places"
    )
    logger.info(
        f"Distance limit for accessibility: {distanace_limit:.1f}km (typical walking/driving threshold)"
    )
    logger.info(f"Income weights provided: {weights is not None}")

    # Ensure population data has proper CRS - coordinates look like lat/lon (EPSG:4326)
    population_gdf = population_gdf.set_crs("EPSG:4326")
    # Ensure places data has same CRS as population
    places = places.set_crs("EPSG:4326")

    # Standardize population data structure for consistent processing
    # Extract centroids as representative points for polygon data
    # This follows spatial analysis principles of point-in-polygon representation
    origins = population_gdf.copy()
    origins["longitude"] = (
        origins.geometry.centroid.x
    )  # X-coordinate of geometric center
    origins["latitude"] = (
        origins.geometry.centroid.y
    )  # Y-coordinate of geometric center
    origins["population"] = origins[
        "Population_Count"
    ]  # Standardize population column name

    total_population = origins["population"].sum()
    logger.info(f"Total population in study area: {total_population:,} people")
    logger.info(
        f"Population density: {total_population/len(origins):.0f} people per population center"
    )

    # Select only essential columns to optimize memory usage and processing speed
    # Follows data science best practices of working with minimal necessary data
    origins = origins[
        ["geometry", "longitude", "latitude", "population"]
    ].reset_index(drop=True)

    # Prepare destinations dataset with consistent structure
    # Assumes places already have longitude/latitude coordinates
    destinations = places[["geometry", "longitude", "latitude"]].reset_index(
        drop=True
    )

    logger.info(
        f"Prepared {len(origins)} origins and {len(destinations)} destinations for analysis"
    )

    # Compute full distance matrix between all origins and destinations
    # Uses Haversine formula to account for Earth's curvature
    # Results in M×N matrix where M=origins, N=destinations
    # This implements spatial interaction theory for accessibility analysis
    # Example: 500 population centers × 150 supermarkets = 500×150 matrix with distances 0.2-25.8 km
    matrix = haversine(
        origins.latitude.values,
        origins.longitude.values,
        destinations.latitude.values,
        destinations.longitude.values,
    )

    # Initialize accessibility mapping using origin-destination cost matrix
    # Dictionary stores lists of accessible destination indices for each origin
    # This implements the concept of service catchment areas in spatial analysis
    od_cost_matrix = {k: [] for k in range(matrix.shape[0])}

    logger.info("Calculating accessibility for each population center...")

    # Calculate accessibility for each population center (origin)
    # Implements distance-based accessibility measurement theory
    accessibility_counts = []

    for i in range(matrix.shape[0]):
        # Get distances from current origin to all destinations
        # Example: [1.2, 3.4, 0.8, 5.2, 2.1, 8.9, 1.5, 4.3] km to 8 supermarkets
        od = matrix[i].tolist()  # Convert to list for manipulation

        # Iteratively find accessible destinations within distance threshold
        # Continues until all destinations are evaluated or distance limit exceeded
        while len(od_cost_matrix[i]) < matrix.shape[1]:

            # Check if closest remaining destination is within travel threshold
            # Implements spatial accessibility theory with distance decay
            # Example: If distance_limit=5km, destinations at [1.2, 3.4, 0.8, 2.1, 1.5, 4.3] qualify
            if np.min(od) < distanace_limit:
                amn = np.argmin(od)  # Find index of closest destination

                # Validate that the index is finite (not NaN or infinite)
                if np.isfinite(amn):
                    od_cost_matrix[i].append(
                        amn
                    )  # Add to accessible destinations

                # Mark destination as processed by setting distance to infinity
                # Prevents re-selection in subsequent iterations
                od[amn] = np.inf
            else:
                # Fallback: if no destinations within limit, assign closest one
                # Ensures every origin has at least one accessible destination
                # Prevents zero-division errors in subsequent calculations
                if len(od_cost_matrix[i]) == 0:
                    amn = np.argmin(od)
                    if np.isfinite(amn):
                        od_cost_matrix[i].append(amn)
                break  # Exit loop when distance threshold exceeded

        accessibility_counts.append(len(od_cost_matrix[i]))

    # Calculate accessibility indicator for each population center
    # Counts number of services/facilities reachable within distance limit
    # Higher values indicate better accessibility/service availability
    # Example: Downtown areas might have 8-12 accessible supermarkets, suburban areas 2-4
    origins["number_of_accessibile_markets"] = accessibility_counts

    avg_accessibility = np.mean(accessibility_counts)
    max_accessibility = np.max(accessibility_counts)
    min_accessibility = np.min(accessibility_counts)

    logger.info("Accessibility analysis completed:")
    logger.info(
        f"  Average accessible places per population center: {avg_accessibility:.1f}"
    )
    logger.info(
        f"  Range: {min_accessibility} to {max_accessibility} accessible places"
    )
    logger.info(
        f"  {sum(1 for x in accessibility_counts if x == 1)} centers have only 1 accessible place (service deserts)"
    )
    logger.info(
        f"  {sum(1 for x in accessibility_counts if x >= 5)} centers have 5+ accessible places (well-served areas)"
    )

    # Compute effective population using accessibility-weighted demographics
    # Implements spatial equity theory: divides population by service availability
    # Areas with fewer accessible services get higher effective population weights
    if weights is None:
        # Simple accessibility weighting: population inversely proportional to service access
        # Population centers with fewer accessible markets carry more weight per person
        # Example: 5000 people with 2 markets = 2500 effective pop vs 3000 people with 6 markets = 500 effective pop
        origins["effective_population"] = (
            origins["population"] / origins["number_of_accessibile_markets"]
        )
        logger.info("Using simple accessibility weighting (no income data)")
    else:
        # ===== REPLACE YOUR ENTIRE else: BLOCK WITH THIS =====
        # Handle NaN values in income data - Enhanced debugging
        logger.info("=== INCOME PROCESSING DEBUG ===")
        original_income_values = weights["income"].values
        logger.info(
            f"STEP 1 - Original income sample: {original_income_values[:5]}"
        )
        logger.info(
            f"STEP 1 - Original income NaN count: {np.isnan(original_income_values).sum()}"
        )

        income_values = weights["income"].values.copy()  # Make a copy
        logger.info(f"STEP 2 - Copied income sample: {income_values[:5]}")

        # Log income data quality
        nan_count = np.isnan(income_values).sum()
        valid_count = len(income_values) - nan_count
        logger.info(
            f"STEP 3 - Income data quality: {valid_count}/{len(income_values)} valid values, {nan_count} NaN values"
        )

        if nan_count > 0:
            median_income = np.nanmedian(income_values)
            logger.info(
                f"STEP 4 - Calculated median income: ${median_income:,.0f}"
            )

            if np.isnan(median_income):
                logger.warning(
                    "STEP 5 - All income values are NaN, using neutral weight of 1.0"
                )
                income_values = np.ones_like(income_values)
            else:
                logger.info(
                    f"STEP 5 - Replacing {nan_count} NaN income values with median: ${median_income:,.0f}"
                )
                # CRITICAL: Use the CORRECTED income_values, not the original
                income_values = np.nan_to_num(income_values, nan=median_income)
                logger.info(
                    f"STEP 6 - After np.nan_to_num, income sample: {income_values[:5]}"
                )
                logger.info(
                    f"STEP 6 - After np.nan_to_num, NaN count: {np.isnan(income_values).sum()}"
                )

        # Check alignment
        if len(income_values) != len(origins):
            logger.error(
                f"MISMATCH: income ({len(income_values)}) vs origins ({len(origins)})"
            )
            income_values = income_values[: len(origins)]

        # CRITICAL FIX: Use the corrected income_values throughout
        population_values = origins["population"].values
        accessibility_values = origins["number_of_accessibile_markets"].values

        logger.info(f"STEP 7 - Final income values sample: {income_values[:5]}")
        logger.info(
            f"STEP 7 - Population values sample: {population_values[:5]}"
        )
        logger.info(
            f"STEP 7 - Accessibility values sample: {accessibility_values[:5]}"
        )

        # Calculate step by step using CORRECTED income_values
        step1 = population_values * income_values  # Use corrected values
        step2 = step1 / accessibility_values

        logger.info(
            f"STEP 8 - Step 1 (pop * corrected_income) sample: {step1[:5]}"
        )
        logger.info(
            f"STEP 8 - Step 2 (result / accessibility) sample: {step2[:5]}"
        )
        logger.info(
            f"STEP 8 - Final effective population NaN count: {np.isnan(step2).sum()}"
        )

        if np.isnan(step2).sum() > 0:
            logger.error("STILL HAVE NaN VALUES AFTER CORRECTION!")
            logger.error(
                f"  NaN positions in income: {np.where(np.isnan(income_values))[0][:5]}"
            )
            logger.error(
                f"  NaN positions in step1: {np.where(np.isnan(step1))[0][:5]}"
            )
            logger.error(
                f"  NaN positions in step2: {np.where(np.isnan(step2))[0][:5]}"
            )

        origins["effective_population"] = step2
        logger.info("Using income-weighted accessibility calculation")
        logger.info(f"Average income weight: ${np.mean(income_values):,.0f}")
        logger.info("=== END INCOME PROCESSING DEBUG ===")
        # ===== END ENHANCED INCOME DEBUGGING =====

    total_effective_pop = origins["effective_population"].sum()
    logger.info(f"Total effective population: {total_effective_pop:,.0f}")
    logger.info(
        "Effective population represents purchasing power adjusted for service access"
    )

    # Calculate market potential for each destination (place/facility)
    # Implements gravity model theory: sum of accessible effective populations
    # Each destination's market size = sum of all populations that can reach it
    market = {
        k: [] for k in range(matrix.shape[1])
    }  # Initialize market potential storage

    logger.info("Calculating market potential for each destination...")
    logger.info("Market calculation diagnostic:")
    logger.info(
        f"  Effective population range: {origins['effective_population'].min():.2f} to {origins['effective_population'].max():.2f}"
    )
    logger.info(
        f"  Effective population NaN count: {origins['effective_population'].isna().sum()}"
    )

    for i in range(matrix.shape[1]):  # Iterate through each destination
        for (
            k,
            v,
        ) in (
            od_cost_matrix.items()
        ):  # Check each origin's accessible destinations
            if i in v:  # If current destination is accessible from origin k
                # Add origin's effective population to destination's market potential
                # This implements cumulative accessibility/market catchment theory
                market[i].append(origins["effective_population"].iloc[k])

    # Aggregate market potential for each destination
    # Sum all effective populations that can access each destination
    # Results in total market size/customer base for each facility
    # Example: Downtown supermarket might have 25,000 total potential customers, suburban one has 8,500
    destinations["market"] = [sum(v) for v in market.values()]
    logger.info("Market calculation results:")
    logger.info(f"  Market values sample: {destinations['market'][:5]}")
    logger.info(f"  Market NaN count: {sum(np.isnan(destinations['market']))}")
    logger.info(
        f"  Market zero count: {sum(np.array(destinations['market']) == 0)}"
    )
    logger.info(
        f"  Non-zero market count: {sum(np.array(destinations['market']) > 0)}"
    )

    # ===== INSERT ENHANCED MARKET CALCULATION DEBUGGING HERE =====
    logger.info("=== MARKET CALCULATION DEBUG ===")
    logger.info(
        f"Total origins with valid effective_population: {sum(~np.isnan(origins['effective_population']))}"
    )
    logger.info(
        f"Total origins with zero effective_population: {sum(origins['effective_population'] == 0)}"
    )

    # Check each destination's market calculation
    for i in range(min(5, len(destinations))):
        dest_market_contributors = market[i]
        logger.info(f"Destination {i} market calculation:")
        logger.info(
            f"  Number of contributing origins: {len(dest_market_contributors)}"
        )
        if len(dest_market_contributors) > 0:
            logger.info(
                f"  Contributors sample: {dest_market_contributors[:3]}"
            )
            logger.info(f"  Contributors sum: {sum(dest_market_contributors)}")
            logger.info(
                f"  Any NaN contributors: {any(np.isnan(dest_market_contributors))}"
            )
        else:
            logger.info(f"  No origins can access this destination")

    # Check accessibility matrix
    accessible_destinations_per_origin = [
        len(v) for v in od_cost_matrix.values()
    ]
    logger.info(
        f"Origins with 0 accessible destinations: {sum(x == 0 for x in accessible_destinations_per_origin)}"
    )
    logger.info(
        f"Total accessible origin-destination pairs: {sum(accessible_destinations_per_origin)}"
    )
    logger.info("=== END MARKET CALCULATION DEBUG ===")
    # ===== END ENHANCED MARKET CALCULATION DEBUGGING =====

    market_stats = destinations["market"]
    logger.info("Market potential calculated:")
    logger.info(
        f"  Average market size per destination: {np.mean(market_stats):,.0f} potential customers"
    )
    logger.info(
        f"  Range: {np.min(market_stats):,.0f} to {np.max(market_stats):,.0f} potential customers"
    )
    logger.info(
        f"  Total market across all destinations: {np.sum(market_stats):,.0f}"
    )

    # Create spatial tessellation grid for aggregation analysis
    # Uses adaptive grid sizing based on population density
    grid = create_grid(origins, grid_size=None)

    # Perform spatial joins to assign data points to grid cells
    # Implements spatial aggregation theory for converting point data to areal units
    # "within" predicate ensures points are assigned to containing grid cells
    logger.info("Performing spatial joins to assign data to grid cells...")
    logger.info("Spatial join diagnostic:")
    logger.info(f"  Origins bounds: {origins.total_bounds}")
    logger.info(f"  Grid bounds: {grid.total_bounds}")
    logger.info(f"  Destinations bounds: {destinations.total_bounds}")

    # Check if bounds overlap
    o_minx, o_miny, o_maxx, o_maxy = origins.total_bounds
    g_minx, g_miny, g_maxx, g_maxy = grid.total_bounds

    overlap_x = max(0, min(o_maxx, g_maxx) - max(o_minx, g_minx))
    overlap_y = max(0, min(o_maxy, g_maxy) - max(o_miny, g_miny))

    logger.info(f"  Bounds overlap: {overlap_x:.6f} x {overlap_y:.6f} degrees")

    if overlap_x <= 0 or overlap_y <= 0:
        logger.error("  NO SPATIAL OVERLAP between origins and grid!")

    # Sample a few points to check spatial join manually
    # Sample a few points to check spatial join manually
    logger.info("Sample spatial join check:")
    for i in range(min(3, len(origins))):
        point = origins.iloc[i].geometry
        logger.info(f"  Origin {i}: {point}")

        # Check which grid cell this point should be in
        grid_matches = grid[grid.contains(point)]
        logger.info(f"    Matches {len(grid_matches)} grid cells")

    # ===== INSERT ENHANCED SPATIAL JOIN DEBUGGING HERE =====
    logger.info("=== SPATIAL JOIN DEBUG ===")
    logger.info(f"Origins bounds: {origins.total_bounds}")
    logger.info(f"Grid bounds: {grid.total_bounds}")

    # Check grid cell sizes
    first_grid_cell = grid.iloc[0].geometry
    grid_width = first_grid_cell.bounds[2] - first_grid_cell.bounds[0]
    grid_height = first_grid_cell.bounds[3] - first_grid_cell.bounds[1]
    logger.info(f"Grid cell size: {grid_width:.6f} x {grid_height:.6f} degrees")

    # Check population polygon sizes
    for i in range(min(5, len(origins))):
        pop_geom = origins.iloc[i].geometry
        pop_bounds = pop_geom.bounds
        pop_width = pop_bounds[2] - pop_bounds[0]
        pop_height = pop_bounds[3] - pop_bounds[1]
        logger.info(
            f"Population polygon {i} size: {pop_width:.6f} x {pop_height:.6f} degrees"
        )
        logger.info(
            f"  Bounds: [{pop_bounds[0]:.6f}, {pop_bounds[1]:.6f}, {pop_bounds[2]:.6f}, {pop_bounds[3]:.6f}]"
        )

        # Check which grid cells this polygon overlaps with
        overlapping_grids = grid[grid.geometry.intersects(pop_geom)]
        containing_grids = grid[grid.geometry.contains(pop_geom)]
        logger.info(f"  Overlaps with {len(overlapping_grids)} grid cells")
        logger.info(f"  Contained within {len(containing_grids)} grid cells")

        # Check centroid containment
        centroid = pop_geom.centroid
        centroid_containing_grids = grid[grid.geometry.contains(centroid)]
        logger.info(
            f"  Centroid contained in {len(centroid_containing_grids)} grid cells"
        )
        logger.info(f"  Centroid: {centroid}")

    # Test different spatial predicates
    logger.info("Testing different spatial predicates:")
    test_origins = origins.head(10)  # Test first 10

    within_join = gpd.sjoin(test_origins, grid, how="left", predicate="within")
    intersects_join = gpd.sjoin(
        test_origins, grid, how="left", predicate="intersects"
    )

    within_success = len(within_join[within_join["index_right"].notna()])
    intersects_success = len(
        intersects_join[intersects_join["index_right"].notna()]
    )

    logger.info(f"  'within' predicate: {within_success}/10 successful joins")
    logger.info(
        f"  'intersects' predicate: {intersects_success}/10 successful joins"
    )
    logger.info("=== END SPATIAL JOIN DEBUG ===")
    # ===== END ENHANCED SPATIAL JOIN DEBUGGING =====

    poulation_grid = gpd.sjoin(origins, grid, how="left", predicate="within")
    places_grid = gpd.sjoin(destinations, grid, how="left", predicate="within")

    logger.info("Spatial joins completed:")
    logger.info(
        f"  Population centers assigned to grid: {len(poulation_grid[poulation_grid['index_right'].notna()])}/{len(origins)}"
    )
    logger.info(
        f"  Places assigned to grid: {len(places_grid[places_grid['index_right'].notna()])}/{len(destinations)}"
    )
    # Detailed post-join analysis
    logger.info("Post spatial join analysis:")
    logger.info(f"  Population grid shape: {poulation_grid.shape}")
    logger.info(f"  Places grid shape: {places_grid.shape}")

    # Check which population centers failed to join
    failed_pop = poulation_grid[poulation_grid["index_right"].isna()]
    logger.info(f"  Failed population joins: {len(failed_pop)}")
    if len(failed_pop) > 0:
        logger.info(
            f"    Sample failed points: {failed_pop.geometry.iloc[:3].tolist()}"
        )

    # Check the actual aggregation data
    pop_aggregation = poulation_grid.groupby("index_right")[
        "effective_population"
    ].sum()
    places_aggregation = places_grid.groupby("index_right")["market"].sum()

    logger.info(f"  Population aggregation: {len(pop_aggregation)} grid cells")
    logger.info(f"  Places aggregation: {len(places_aggregation)} grid cells")
    logger.info(f"  Places aggregation sample: {places_aggregation.head()}")

    # Aggregate spatial data at grid cell level using groupby operations
    # Implements spatial data aggregation and statistical summarization
    # Combines multiple datasets into unified grid-based representation
    data = pd.concat(
        [
            grid,  # Base grid geometries as spatial framework
            # Population aggregation: sum raw population counts per grid cell
            # Provides demographic density distribution across space
            # Example: Grid cell might contain 12,500 people from 3 population centers
            poulation_grid.groupby("index_right")["population"]
            .sum()
            .rename("number_of_persons"),
            # Effective population aggregation: sum accessibility-weighted population
            # Accounts for service availability and economic factors
            # Example: Same grid cell has 8,200 effective population (lower due to good service access)
            poulation_grid.groupby("index_right")["effective_population"]
            .sum()
            .rename("effective_population"),
            # Facility count: number of destinations/places per grid cell
            # Measures service/facility density distribution
            # Example: Commercial grid cell might have 4 supermarkets, residential cell has 0-1
            places_grid.groupby("index_right")["geometry"]
            .count()
            .rename("number_of_supermarkets"),
            # Market potential aggregation: sum customer base for all facilities in grid cell
            # Represents total economic opportunity/demand within each spatial unit
            # Example: Commercial district grid cell has 89,500 potential customers across all its stores
            places_grid.groupby("index_right")["market"]
            .sum()
            .rename("number_of_potential_customers"),
        ],
        axis=1,  # Concatenate along columns (join datasets horizontally)
    )

    # Data cleaning: remove empty grid cells with no associated data
    # Creates boolean mask to identify cells with at least one non-null value
    # Improves computational efficiency by eliminating sparse spatial units
    mask = (
        ~data.iloc[:, 1:].isna().all(axis=1)
    )  # Check all columns except geometry
    data = (
        data.loc[mask].fillna(0.0).reset_index(drop=True)
    )  # Filter and clean data

    logger.info("Grid aggregation completed:")
    logger.info(f"  Total grid cells created: {len(grid)}")
    logger.info(
        f"  Grid cells with data: {len(data)} ({100*len(data)/len(grid):.1f}%)"
    )
    logger.info(
        f"  Grid cells with potential customers: {sum(data['number_of_potential_customers'] > 0)}"
    )

    return data


def select_nbrs_with_sum(
    i: int, cost: np.ndarray, max_share: float, shares: dict, used: list[int]
) -> list[int]:
    """
    A helper function for clustering funtionality. It makes sure that the cluster are formed by neighboring
    gridcells and calculates the sum of indicator value for each itteration.

    args:
    ----
    `i` is index of the origin
    `cost` is od distnace matrix
    `max_share` is the max share of the indicator each cluster can have
    `shares` is the assigned value to each destination
    `used` is the a list of gridcells that are taken

    return:
    ------
    a list of neighboring gridcells for origin i that will become of cluster
    """

    logger.debug(f"Building cluster starting from grid cell {i}")
    logger.debug(
        f"Target max share: {max_share:,.0f}, Available unused cells: {len(cost) - len(used)}"
    )

    # Sort grid cells by distance from origin i (nearest neighbor ordering)
    # Implements spatial contiguity constraint for cluster formation
    # Ensures clusters are geographically compact rather than spatially fragmented
    # Example: From grid cell 45, sorted neighbors might be [46, 44, 55, 35, 47, 43, 56, 34...]
    x = np.argsort(cost)  # Returns indices sorted by ascending distance

    logger.debug(f"Sorted {len(x)} neighbors by distance from seed cell {i}")

    # Initialize accumulator variables for greedy cluster building
    value = 0  # Running sum of indicator values (market potential)
    nbrs = []  # List of neighbor indices to include in cluster

    # Greedy nearest-neighbor selection with capacity constraint
    # Implements load-balancing principle: distribute total workload equally
    for idx, cell_idx in enumerate(
        x
    ):  # Iterate through grid cells in order of proximity

        # Skip grid cells already assigned to other clusters
        # Ensures each spatial unit belongs to exactly one cluster (partition constraint)
        if cell_idx in used:
            logger.debug(f"  Cell {cell_idx} already used, skipping")
            continue

        # Add current grid cell's indicator value to cluster total
        # Accumulates market potential/workload for current cluster
        # Example: Adding grid cells with 2500, 1800, 3200 customers → value = 7500
        cell_value = shares[cell_idx]
        value += cell_value
        nbrs.append(cell_idx)  # Include grid cell in current cluster

        logger.debug(
            f"  Added cell {cell_idx} with {cell_value:,.0f} customers. Cluster total: {value:,.0f}"
        )

        # Check if cluster has reached target capacity (load balancing)
        # Stops growing cluster when maximum share threshold is exceeded
        # Implements equitable distribution of total market potential across clusters
        # Example: If max_share=25000 and value=26300, stop adding cells to this cluster
        if value >= max_share:
            logger.debug(
                f"  Cluster reached target capacity ({value:,.0f} >= {max_share:,.0f})"
            )
            break

    logger.info(
        f"Cluster built from seed {i}: {len(nbrs)} cells, {value:,.0f} total customers"
    )
    logger.info(f"  Cells included: {nbrs}")
    logger.info(
        f"  Load balancing: {100*value/max_share:.1f}% of target capacity"
    )

    return nbrs


async def get_clusters_for_sales_man(
    req: ReqClustersForSalesManData,
) -> gpd.GeoDataFrame:
    """
    Main funtion to produce the clusters for the salesman problem
    args:
    ----
    `num_sales_man` is the number of cluster we want in the final output geodataframe
    `population` is the raw census dataframe
    `places` is the raw places dataframe containing responese column
    `weights` is the raw income data
    `bounding_box` is a list if longitude, latitude pair
    `distance_limit` is the max distace a cosumer is willing to travel to reach destination
    `zoom_level` is the zoom_level for the census data

    return:
    ------
    A geodataframe constaining gridcells (polygons) under geometry column
    each grid cell is classfied by cluster index under group column
    """

    default_zoom = 14
    logger.info(
        f"Starting sales territory clustering for {req.city_name}, {req.country_name}"
    )
    logger.info(f"Target number of sales territories: {req.num_sales_man}")
    logger.info(
        f"Distance limit: {req.distance_limit}km, Zoom level: {default_zoom}"
    )

    # Retrieve geographic boundary data for specified city
    all_cities = await fetch_country_city_data()

    # Search for target city within country's city database
    found_city = None
    for city in all_cities.get(req.country_name, []):
        if city["name"] == req.city_name:
            found_city = city
            break

    if found_city is None:
        logger.error(f"City {req.city_name} not found in {req.country_name}")
        raise ValueError(f"City not found: {req.city_name}")

    # Extract bounding box coordinates that define study area extent
    bounding_box = found_city.get("bounding_box", [])
    logger.info(f"City bounding box: {len(bounding_box)} coordinate pairs")

    # Load demographic and economic data for the study area
    # Zoom level controls resolution/granularity of population data
    logger.info("Loading population and income data...")
    population_gdf, income_gdf = await get_population_and_income(
        bounding_box, zoom_level=default_zoom
    )

    logger.info(
        f"Loaded {len(population_gdf)} population records, {len(income_gdf) if income_gdf is not None else 0} income records"
    )
    if income_gdf is not None and len(income_gdf) > 0:
        logger.info("Income data diagnostic:")
        for col in income_gdf.columns:
            if col != "geometry":
                values = income_gdf[col].values
                logger.info(
                    f"  Column '{col}': {len(values)} values, {np.isnan(values).sum()} NaN"
                )
                if not np.all(np.isnan(values)):
                    logger.info(
                        f"    Range: {np.nanmin(values):.2f} to {np.nanmax(values):.2f}"
                    )
    else:
        logger.warning("Income data is empty or None")
    # Retrieve businesses/facilities data for the entire city
    logger.info("Loading business/facility data...")
    page_token = ""
    data_load_req = ReqFetchDataset(
        boolean_query=req.boolean_query,  # Search criteria by types
        action="full data",
        page_token=page_token,
        city_name=req.city_name,
        country_name=req.country_name,
        user_id=req.user_id,
        full_load=req.full_load,
    )
    places = await fetch_dataset(data_load_req)
    places = places.get("full_load_geojson", {})

    # Filter facilities to study area boundaries
    places = filter_data_by_bounding_box(places, bounding_box)
    logger.info(f"Filtered to {len(places)} places within study area")

    # Remove duplicate facility locations (data quality control)
    original_count = len(places)
    places = places.loc[places.geometry.drop_duplicates().index]
    logger.info(
        f"Removed {original_count - len(places)} duplicate locations, {len(places)} unique places remain"
    )

    # Generate grid-based spatial aggregation with accessibility analysis
    # Implements spatial tessellation with market potential calculation
    # Combines population, facilities, income, and accessibility into unified spatial framework
    logger.info("Generating grid-based spatial aggregation...")
    grided_data = get_grids_of_data(
        population_gdf, places, income_gdf, req.distance_limit
    )

    # Filter to grid cells with actual market potential
    # Removes empty/irrelevant spatial units to focus clustering on viable areas
    mask = grided_data.number_of_potential_customers > 0
    masked_grided_data = grided_data[mask].reset_index(drop=True)
    if len(masked_grided_data) == 0:
        logger.error("No grid cells with market potential found!")
        logger.error("This usually means:")
        logger.error("  1. Income data contains only NaN values")
        logger.error(
            "  2. Spatial join failed to assign population to grid cells"
        )
        logger.error("  3. Distance limit is too restrictive")
    logger.info("Grid filtering results:")
    logger.info(f"  Total grid cells: {len(grided_data)}")
    logger.info(
        f"  Cells with market potential: {len(masked_grided_data)} ({100*len(masked_grided_data)/len(grided_data):.1f}%)"
    )
    logger.info(
        f"  Removed {len(grided_data) - len(masked_grided_data)} empty cells"
    )

    # Calculate geometric centroids for distance calculations
    # Converts polygon grid cells to representative point locations
    # Implements spatial geometry simplification for efficient distance computation
    centroids = masked_grided_data.geometry.map(shapely.centroid)

    # Convert centroids to coordinate DataFrame for distance matrix calculation
    nbrs = centroids.to_frame()
    nbrs["longitude"] = nbrs.geometry.x  # Extract longitude coordinates
    nbrs["latitude"] = nbrs.geometry.y  # Extract latitude coordinates

    logger.info(f"Calculated centroids for {len(nbrs)} grid cells")

    # Compute distance matrix between all grid cell centroids
    # Implements spatial proximity analysis for cluster contiguity constraints
    # Results in symmetric matrix of inter-centroid distances
    # Example: 450×450 matrix with distances ranging 0.8-28.5 km between grid centroids
    logger.info("Computing distance matrix between grid centroids...")
    matrix = haversine(
        nbrs.latitude.values,
        nbrs.longitude.values,
        nbrs.latitude.values,
        nbrs.longitude.values,
    )

    # Calculate target market share per salesperson
    # Implements equitable distribution principle: divide total market equally
    # Ensures balanced workload assignment across sales territories
    # Example: 180,000 total customers ÷ 8 salespeople = 22,500 customers per territory
    total_customers = masked_grided_data["number_of_potential_customers"].sum()
    equitable_share = total_customers / req.num_sales_man

    logger.info("Market distribution analysis:")
    logger.info(f"  Total potential customers: {total_customers:,.0f}")
    logger.info(f"  Target customers per territory: {equitable_share:,.0f}")
    logger.info(
        f"  This represents balanced workload distribution across {req.num_sales_man} salespeople"
    )

    # Initialize clustering data structures
    used = []  # Track assigned grid cells to prevent overlap
    groups = {
        i: [] for i in range(req.num_sales_man)
    }  # Store cluster assignments

    logger.info("Starting greedy spatial clustering algorithm...")

    # Greedy spatial clustering algorithm with load balancing
    # Implements modified k-means with spatial contiguity constraints
    j = 0  # Current cluster index
    clusters_created = 0

    for i in range(masked_grided_data.shape[0]):

        # Skip grid cells already assigned to clusters
        # Maintains partition constraint: each cell belongs to exactly one cluster
        if i in used:
            continue
        else:
            logger.info(f"Creating cluster {j} starting from grid cell {i}")

            # Find spatially contiguous neighbors within capacity limit
            # Implements greedy nearest-neighbor expansion with load balancing
            # Example: Starting from grid 25, might select [25, 26, 35, 24, 36, 15] totaling 23,100 customers
            nbrs = select_nbrs_with_sum(
                i,  # Current seed grid cell
                matrix[i],  # Distances from seed to all other cells
                equitable_share,  # Maximum market capacity per cluster
                masked_grided_data[
                    "number_of_potential_customers"
                ].values,  # Market values
                used,  # Already assigned cells to avoid
            )

            # Assign selected neighbors to current cluster
            groups[j].extend(nbrs)  # Add cells to cluster j
            used.extend(nbrs)  # Mark cells as assigned

            cluster_customers = sum(
                masked_grided_data["number_of_potential_customers"].iloc[idx]
                for idx in nbrs
            )
            logger.info(
                f"Cluster {j} completed: {len(nbrs)} cells, {cluster_customers:,.0f} customers"
            )

            j += 1  # Move to next cluster
            clusters_created += 1

        # Stop when all requested clusters are created
        # Implements termination condition for clustering algorithm
        if j >= req.num_sales_man:
            logger.info(
                f"Reached target number of clusters ({req.num_sales_man})"
            )
            break

    logger.info("Clustering completed:")
    logger.info(f"  Clusters created: {clusters_created}")
    logger.info(
        f"  Grid cells assigned: {len(used)}/{len(masked_grided_data)} ({100*len(used)/len(masked_grided_data):.1f}%)"
    )
    logger.info(f"  Unassigned cells: {len(masked_grided_data) - len(used)}")

    # Helper function to map grid cell indices to cluster labels
    # Implements reverse lookup for cluster assignment labeling
    def return_group_number(index: int) -> int:
        """
        Returns back the class/group index for each grid cell based in the `groups` dict
        `groups` is the dict created in the `get_clusters_for_sales_man`
        `index`is the index of the gridcell in the `masked_grided_data`
        """
        for k, v in groups.items():
            if index in v:
                return k
        return None  # Return None for unassigned cells

    # Apply cluster labels to grid data
    # Implements final data preparation with cluster identification
    # Creates new column indicating which sales territory each grid cell belongs to
    # Example: Final output has 'group' column with values 0-7 for 8 sales territories
    masked_grided_data = masked_grided_data.assign(group=lambda x: x.index)
    masked_grided_data["group"] = masked_grided_data["group"].map(
        return_group_number
    )

    # Log final cluster statistics
    cluster_stats = (
        masked_grided_data.groupby("group")
        .agg({"number_of_potential_customers": ["sum", "count"]})
        .round(0)
    )

    logger.info("Final cluster statistics:")
    for group_id in range(req.num_sales_man):
        if group_id in groups:
            cells = len(groups[group_id])
            customers = masked_grided_data[
                masked_grided_data["group"] == group_id
            ]["number_of_potential_customers"].sum()
            logger.info(
                f"  Cluster {group_id}: {cells} cells, {customers:,.0f} customers ({100*customers/total_customers:.1f}% of total)"
            )

    unassigned = len(masked_grided_data[masked_grided_data["group"].isna()])
    if unassigned > 0:
        logger.warning(f"  {unassigned} cells remain unassigned")

    logger.info("Sales territory clustering completed successfully")

    import matplotlib.pyplot as plt
    # 4 plots in a row, each subplot 3.5x3.5 inches = total ~18x5 inches
    plot_results(masked_grided_data.iloc[:,:-1], 4, 1, ["Greens", "Reds", "Blues", "Purples"],
                alpha=0.75, subplot_size=(3.5, 3.5))
    # Single plot, 6x6 inches
    plot_results(masked_grided_data[["geometry", "group"]], 1, 1, ["tab20c"],
                alpha=1, show_legends=False, edge_color=None, show_title=False,
                subplot_size=(6, 6))

    return masked_grided_data


def plot_results(
    grided_data: gpd.GeoDataFrame,
    n_cols: int,
    n_rows: int,
    colors: list[str],
    alpha: float = 0.8,
    show_legends: bool = True,
    edge_color: str = "white",
    show_title: bool = True,
    subplot_size: tuple = (8, 8),
) -> None:
    """
    args:
    ----
    `grided_data` is the geodataframe
    `n_cols` is the number of cols in th plot
    `n_rows` is the number of rows in th plot
    `colors` if the list of color maps for each plot
    `alpha` is the opacity of the colors
    `show_legends` flag to turn legeneds on or off
    `edge_color` to define the edge colors of the gridcells
    `show_title` flag to show or hide the title
    `subplot_size` is a tuple (width, height) for each individual subplot in inches
    """
    grid = grided_data.copy(deep=True)
    single_fig_width, single_fig_height = subplot_size

    fig = plt.figure(
        figsize=(
            single_fig_width * n_cols + n_cols,
            single_fig_height * n_rows + n_rows,
        )
    )

    for i, column in enumerate(grid.columns[1:], 1):
        ax = plt.subplot(n_rows, n_cols, i)
        grid[f"log_{column}"] = np.log1p(grid[column])
        vmax = grid[f"log_{column}"].quantile(0.95)
        vmin = grid[f"log_{column}"].quantile(0.05)
        grid.set_crs(epsg=4326, inplace=True)
        grid.to_crs(epsg=3857).plot(
            column=f"log_{column}",
            legend=show_legends,
            cmap=colors[i - 1],
            edgecolor=edge_color,
            linewidth=0.1,
            vmin=vmin,
            vmax=vmax,
            alpha=alpha,
            ax=ax,
        )
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
        ax.axis("off")
        if show_title:
            # Use shorter, cleaner titles and smaller font
            clean_title = (
                column.replace("_", " ").replace("number of", "Count:").title()
            )
            ax.set_title(
                clean_title, fontsize=10, pad=10
            )  # Smaller font + padding

    # Add proper spacing to prevent overlap
    plt.tight_layout(pad=2.0)  # Add padding between subplots
    plt.subplots_adjust(top=0.85, hspace=0.3, wspace=0.2)  # Manual adjustment
    plt.show()
