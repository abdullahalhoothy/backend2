from typing import List, Dict, Any, Tuple
from all_types.response_dtypes import (
    ResGradientColorBasedOnZone,
    NearestPointRouteResponse,
)

from google_api_connector import calculate_distance_traffic_route
from geo_std_utils import calculate_distance
from all_types.myapi_dtypes import *
from data_fetcher import given_layer_fetch_dataset

from geopy.distance import geodesic
import numpy as np
import uuid


from all_types.response_dtypes import (
    ResGradientColorBasedOnZone,
    NearestPointRouteResponse,
)
from agents import *
from data_fetcher import given_layer_fetch_dataset, fetch_user_layers


def assign_point_properties(point):
    return {
        "type": "Feature",
        "geometry": point["geometry"],
        "properties": point.get("properties", {}),
    }


async def filter_for_nearest_points(
    category_coordinates: List[Dict[str, float]],
    bussiness_target_coordinates: List[Dict[str, float]],
    num_points_per_target=3,
) -> List[Dict[str, Any]]:
    nearest_locations = []
    for target in bussiness_target_coordinates:
        distances = []
        for loc in category_coordinates:
            dist = calculate_distance(target, loc) / 1000  # to km
            distances.append(
                {
                    "latitude": loc["latitude"],
                    "longitude": loc["longitude"],
                    "distance": dist,
                }
            )

        # Sort distances and get the nearest 3
        nearest = sorted(distances, key=lambda x: x["distance"])[
            :num_points_per_target
        ]
        nearest_locations.append(
            {
                "target": target,
                "nearest_coordinates": [
                    (loc["latitude"], loc["longitude"]) for loc in nearest
                ],
            }
        )

    return nearest_locations


async def calculate_nearest_points_drive_time(
    nearest_locations: List[Dict[str, Any]],
) -> List[NearestPointRouteResponse]:
    results = []
    for item in nearest_locations:
        target = item["target"]
        target_routes = NearestPointRouteResponse(target=target, routes=[])

        for nearest in item["nearest_coordinates"]:
            origin = f"{target['latitude']},{target['longitude']}"
            destination = f"{nearest[0]},{nearest[1]}"

            # Fetch route information between target and nearest location
            if origin != destination:
                route_info = await calculate_distance_traffic_route(
                    origin, destination
                )
                target_routes.routes.append(route_info)

        results.append(target_routes)

    return results


def average_metric_of_surrounding_points(
    color_based_on, point, based_on_dataset, radius
):
    lat, lon = (
        point["geometry"]["coordinates"][1],
        point["geometry"]["coordinates"][0],
    )

    nearby_metric_value = []

    for point_2 in based_on_dataset["features"]:
        if color_based_on not in point_2["properties"]:
            continue

        distance = geodesic(
            (lat, lon),
            (
                point_2["geometry"]["coordinates"][1],
                point_2["geometry"]["coordinates"][0],
            ),
        ).meters

        if distance <= radius:
            nearby_metric_value.append(point_2["properties"][color_based_on])

    if nearby_metric_value:
        cleaned_list = [
            float(x)
            for x in nearby_metric_value
            if str(x).strip() and not isinstance(x, bool)
        ]
        return np.mean(cleaned_list)
    else:
        return None


def filter_locations_by_drive_time(
    nearest_locations: List[Dict[str, Any]], coverage_minutes: float
) -> List[Dict[str, Any]]:
    """
    Filter coordinates near target locations based on estimated driving distance.

    Args:
        nearest_locations: List of dicts containing targets and their nearest coordinates
        coverage_minutes: Desired drive time in minutes

    Returns:
        List of filtered locations with coordinates within estimated driving distance
    """
    AVERAGE_SPEED_MPS = 11.11  # Average urban speed of 40 km/h = 11.11 m/s
    desired_time_seconds = coverage_minutes * 60  # Convert minutes to seconds
    estimated_distance_meters = AVERAGE_SPEED_MPS * desired_time_seconds

    filtered_nearest_locations: List[Dict[str, Any]] = []
    for location in nearest_locations:
        target = location["target"]
        filtered_coords: List[Tuple[float, float]] = []
        for nearest_coord in location["nearest_coordinates"]:
            actual_distance = geodesic(
                (target["latitude"], target["longitude"]), nearest_coord
            ).meters
            if actual_distance <= estimated_distance_meters:
                filtered_coords.append(nearest_coord)

        filtered_nearest_locations.append(
            {
                "target": target,
                "nearest_coordinates": filtered_coords,  # This might be empty
            }
        )

    return filtered_nearest_locations


# filter by name
def filter_by_name(
    change_layer_dataset: Dict[str, Any], list_names: List[str]
) -> Dict[str, List[Dict]]:
    """
    Filter geographic points based on name matching.

    Args:
        change_layer_dataset: Dataset containing features to be filtered
        list_names: List of names to match against

    Returns:
        Dictionary containing two categories of features:
        - matched: Features with names matching the search criteria
        - unmatched: Features that don't match the search criteria
    """
    # Normalize names for case-insensitive comparison
    list_names_lower = [name.strip().lower() for name in list_names]

    # Initialize result categories
    matched_features = []
    unmatched_features = []

    # Categorize features based on name matching
    for feature in change_layer_dataset["features"]:
        feature_name = feature["properties"].get("name", "").strip().lower()

        # Check for partial substring matches
        if any(search_name in feature_name for search_name in list_names_lower):
            matched_features.append(assign_point_properties(feature))
        else:
            unmatched_features.append(assign_point_properties(feature))

    return {"matched": matched_features, "unmatched": unmatched_features}


#### Create name based layers
def create_name_based_layers(
    filtered_features: Dict[str, List[Dict]],
    req: Any,
    change_layer_metadata: Dict[str, Any],
) -> List[ResGradientColorBasedOnZone]:
    """
    Create layers based on name filtering results.

    Args:
        filtered_features: Dictionary containing categorized features
        req: Request object containing layer configuration
        change_layer_metadata: Metadata for the change layer

    Returns:
        List of ResGradientColorBasedOnZone objects representing different layers
    """
    new_layers = []
    base_layer_name = f"{req.change_lyr_name} - Name Match"

    layer_configs = [
        {
            "features": filtered_features["matched_within_radius"],
            "category": "matched",
            "name_suffix": "Matched",
            "color": req.change_lyr_new_color,
            "legend": f"Contains: {', '.join(req.list_names)}",
            "description": f"Features matching names: {', '.join(req.list_names)}",
        },
        {
            "features": filtered_features["unmatched_outside_radius"],
            "category": "unmatched",
            "name_suffix": "Unmatched",
            "color": req.change_lyr_orginal_color,
            "legend": "No name match",
            "description": "Features without matching names",
        },
    ]

    for config in layer_configs:
        if config["features"]:
            new_layers.append(
                ResGradientColorBasedOnZone(
                    type="FeatureCollection",
                    features=config["features"],
                    properties=list(
                        config["features"][0].get("properties", {}).keys()
                    ),
                    prdcer_layer_name=f"{base_layer_name} ({config['name_suffix']})",
                    prdcer_lyr_id=str(uuid.uuid4()),
                    sub_lyr_id=f"{req.change_lyr_id}_{config['category']}",
                    bknd_dataset_id=req.change_lyr_id,
                    points_color=config["color"],
                    layer_legend=config["legend"],
                    layer_description=config["description"],
                    records_count=len(config["features"]),
                    city_name=change_layer_metadata.get("city_name", ""),
                    is_zone_lyr="true",
                    progress=0,
                )
            )

    return new_layers


# filter by drive time
async def filter_by_drive_time(
    change_layer_dataset: Dict[str, Any],
    based_on_coordinates: List[Dict[str, float]],
    to_be_changed_coordinates: List[Dict[str, float]],
    coverage_minutes: float,
    num_points_per_target: int = 2,
) -> Dict[str, List[Dict]]:
    """
    Filter geographic points based on drive time calculations using existing helper functions.

    Args:
        change_layer_dataset: Dataset containing features to be filtered
        based_on_coordinates: List of reference point coordinates
        to_be_changed_coordinates: List of target point coordinates
        coverage_minutes: Maximum allowed drive time in minutes
        num_points_per_target: Number of nearest points to consider per target

    Returns:
        Dictionary containing three categories of features:
        - within_time: Features within the specified drive time
        - outside_time: Features exceeding the specified drive time
        - unallocated: Features with no valid route information
    """
    # Get nearest points using existing function
    nearest_locations = await filter_for_nearest_points(
        based_on_coordinates,
        to_be_changed_coordinates,
        num_points_per_target=num_points_per_target,
    )

    # Filter locations by estimated drive time
    filtered_nearest_locations = filter_locations_by_drive_time(
        nearest_locations, coverage_minutes
    )

    # Calculate actual routes with Google Maps
    route_results = await calculate_nearest_points_drive_time(
        filtered_nearest_locations
    )

    # Initialize result categories
    within_time_features = []
    outside_time_features = []
    unallocated_features = []

    # Process routes and categorize features
    for target_routes in route_results:
        min_static_time = float("inf")

        # Get minimum static drive time from routes
        for route in target_routes.routes:
            try:
                if route.route and route.route[0].static_duration:
                    static_time = int(
                        route.route[0].static_duration.replace("s", "")
                    )
                    min_static_time = min(min_static_time, static_time)
            except:
                continue

        # Find matching point and categorize
        for change_point in change_layer_dataset["features"]:
            if (
                change_point["geometry"]["coordinates"][1]
                == target_routes.target["latitude"]
                and change_point["geometry"]["coordinates"][0]
                == target_routes.target["longitude"]
            ):
                feature = assign_point_properties(change_point)

                if min_static_time != float("inf"):
                    drive_time_minutes = min_static_time / 60
                    if drive_time_minutes <= coverage_minutes:
                        within_time_features.append(feature)
                    else:
                        outside_time_features.append(feature)
                else:
                    unallocated_features.append(feature)
                break

    return {
        "within_time": within_time_features,
        "outside_time": outside_time_features,
        "unallocated": unallocated_features,
    }


### create drive time layers
def create_drive_time_layers(
    filtered_features: Dict[str, List[Dict]],
    req: Any,
    change_layer_metadata: Dict[str, Any],
) -> List[ResGradientColorBasedOnZone]:
    """
    Create gradient color layers based on drive time filtering results.

    Args:
        filtered_features: Dictionary containing categorized features
        req: Request object containing layer configuration
        change_layer_metadata: Metadata for the change layer

    Returns:
        List of ResGradientColorBasedOnZone objects representing different layers
    """
    new_layers = []
    base_layer_name = f"{req.change_lyr_name} based on {req.based_on_lyr_name}"

    layer_configs = [
        {
            "features": filtered_features["within_time"],
            "category": "within_drivetime",
            "name_suffix": "Within Drive Time",
            "color": req.color_grid_choice[0],
            "legend": f"Drive Time ≤ {req.coverage_value} m",
            "description": f"Points within {req.coverage_value} minutes drive time",
        },
        {
            "features": filtered_features["outside_time"],
            "category": "outside_drivetime",
            "name_suffix": "Outside Drive Time",
            "color": req.color_grid_choice[-1],
            "legend": f"Drive Time > {req.coverage_value} m",
            "description": f"Points outside {req.coverage_value} minutes drive time",
        },
        {
            "features": filtered_features["unallocated"],
            "category": "unallocated_drivetime",
            "name_suffix": "Unallocated Drive Time",
            "color": "#FFFFFF",
            "legend": "No route available",
            "description": "Points with no available route information",
        },
    ]

    for config in layer_configs:
        if config["features"]:
            new_layers.append(
                ResGradientColorBasedOnZone(
                    type="FeatureCollection",
                    features=config["features"],
                    properties=list(
                        config["features"][0].get("properties", {}).keys()
                    ),
                    prdcer_layer_name=f"{base_layer_name} ({config['name_suffix']})",
                    prdcer_lyr_id=str(uuid.uuid4()),
                    sub_lyr_id=f"{req.change_lyr_id}_{config['category']}_{req.based_on_lyr_id}",
                    bknd_dataset_id=req.change_lyr_id,
                    points_color=config["color"],
                    layer_legend=config["legend"],
                    layer_description=f"{config['description']}. Layer {req.change_lyr_id} based on {req.based_on_lyr_id}",
                    records_count=len(config["features"]),
                    city_name=change_layer_metadata.get("city_name", ""),
                    is_zone_lyr="true",
                    progress=0,
                )
            )

    return new_layers


# filter by property
def filter_by_property(
    change_layer_dataset: Dict[str, Any],
    property_name: str,
    property_value: Any,
) -> Dict[str, List[Dict]]:
    """
    Filter geographic points based on a specific property value.

    Args:
        change_layer_dataset: Dataset containing features to be filtered
        property_name: The name of the property to filter by
        property_value: The value of the property to match against

    Returns:
        Dictionary containing two categories of features:
        - matched: Features with the specified property value
        - unmatched: Features that don't match the specified property value
    """
    matched_features = []
    unmatched_features = []

    for feature in change_layer_dataset["features"]:
        feature_property = feature["properties"]
        feature_property_value = feature_property.get(property_name)

        if property_name in [
            "rating",
            "popularity_score",
            "user_ratings_total",
            "heatmap_weight",
        ]:
            feature_property_value = float(feature_property_value)
            if feature_property_value <= property_value:
                matched_features.append(assign_point_properties(feature))
            else:
                unmatched_features.append(assign_point_properties(feature))
        else:
            if property_name == "types":
                if property_value in feature_property_value:
                    matched_features.append(assign_point_properties(feature))
                else:
                    unmatched_features.append(assign_point_properties(feature))
            else:
                if feature_property_value == property_value:
                    matched_features.append(assign_point_properties(feature))
                else:
                    unmatched_features.append(assign_point_properties(feature))

    return {"matched": matched_features, "unmatched": unmatched_features}


# filet by distance (radius)
def filter_cl_distance_property_from_bol(
    change_layer_dataset: Dict[str, Any],
    based_on_coordinates,
    to_be_changed_coordinates,
    radius: float,
    color_based_on="",
    threshold=0,
) -> Dict[str, List[Dict]]:
    filtred_cl_coord = []
    for cl_feature in change_layer_dataset["features"]:
        changed_coord = cl_feature["geometry"]["coordinates"]
        prop_value = cl_feature["properties"][color_based_on]
    for changed_coord in to_be_changed_coordinates:
        for basedon_coord in based_on_coordinates:
            if changed_coord != basedon_coord:
                distance = calculate_distance(basedon_coord, changed_coord)
                if distance <= radius:
                    filtred_cl_coord.append(changed_coord)

    matched_within_radius = []
    unmatched_outside_radius = []

    for cl_feature in change_layer_dataset["features"]:
        feature_coordinates = {
            "latitude": cl_feature["geometry"]["coordinates"][1],
            "longitude": cl_feature["geometry"]["coordinates"][0],
        }
        if feature_coordinates in filtred_cl_coord:
            matched_within_radius.append(assign_point_properties(cl_feature))
        else:
            unmatched_outside_radius.append(assign_point_properties(cl_feature))

    return {
        "matched_within_radius": matched_within_radius,
        "unmatched_outside_radius": unmatched_outside_radius,
    }


# filter by property & drive time
async def filter_by_property_and_drive_time(
    change_layer_dataset,
    based_on_coordinates,
    to_be_changed_coordinates,
    req: ReqGradientColorBasedOnZone,
) -> Dict[str, List[Dict]]:
    # filter by drive time
    filtered_features_dt = await filter_by_drive_time(
        change_layer_dataset=change_layer_dataset,
        based_on_coordinates=based_on_coordinates,
        to_be_changed_coordinates=to_be_changed_coordinates,
        coverage_minutes=req.coverage_value,
    )["within_time"]

    # filter by name
    if req.color_based_on == "name":
        filtered_features_name = filter_by_name(
            change_layer_dataset=change_layer_dataset, list_names=req.list_names
        )["matched"]
        return [
            feature
            for feature in filtered_features_name
            if feature in filtered_features_dt
        ]
    else:
        property_name = req.color_based_on
        property_value = req.coverage_value
        # filter by property
        filtered_features_prop = filter_by_property(
            change_layer_dataset, property_name, property_value
        )["matched"]
        return [
            feature
            for feature in filtered_features_prop
            if feature in filtered_features_dt
        ]


async def filter_by_property_and_coverage_property(
    change_layer_dataset,
    based_on_coordinates,
    to_be_changed_coordinates,
    req: ReqFilter,
) -> Dict[str, List[Dict]]:
    # filter by drive time
    filtered_features_cp = []
    if req.coverage_property == "drive_time":
        filtered_features_cp = (
            await filter_by_drive_time(
                change_layer_dataset=change_layer_dataset,
                based_on_coordinates=based_on_coordinates,
                to_be_changed_coordinates=to_be_changed_coordinates,
                coverage_minutes=req.coverage_value,
            )
        )["within_time"]
    elif req.coverage_property == "radius":
        filtered_features_cp = filter_cl_distance_property_from_bol(
            change_layer_dataset=change_layer_dataset,
            based_on_coordinates=based_on_coordinates,
            to_be_changed_coordinates=to_be_changed_coordinates,
            radius=req.coverage_value,
        )["matched_within_radius"]

    if req.color_based_on:
        if req.color_based_on == "name":
            filtered_features = filter_by_name(
                change_layer_dataset=change_layer_dataset,
                list_names=req.list_names,
            )["matched"]
        else:
            property_name = req.color_based_on
            property_value = req.threshold
            # filter by property
            filtered_features = filter_by_property(
                change_layer_dataset, property_name, property_value
            )["matched"]
        filtered_features_intersection = (
            [
                feature
                for feature in filtered_features
                if feature in filtered_features_cp
            ]
            if req.coverage_property
            else filtered_features
        )
        return filtered_features_intersection
    return filtered_features_cp


async def coverage_filter_layers(req: ReqGradientColorBasedOnZone):
    change_layer_dataset, change_layer_metadata = (
        await given_layer_fetch_dataset(req.change_lyr_id)
    )
    based_on_layer_dataset, based_on_layer_metadata = (
        await given_layer_fetch_dataset(req.based_on_lyr_id)
    )
    based_on_coordinates = [
        {
            "latitude": point["geometry"]["coordinates"][1],
            "longitude": point["geometry"]["coordinates"][0],
        }
        for point in based_on_layer_dataset["features"]
    ]

    to_be_changed_coordinates = [
        {
            "latitude": point["geometry"]["coordinates"][1],
            "longitude": point["geometry"]["coordinates"][0],
        }
        for point in change_layer_dataset["features"]
    ]
    if (
        req.coverage_property == "drive_time"
    ):  # currently drive does not take into account ANY based on property
        # filter by drive time
        filtered_features = await filter_by_drive_time(
            change_layer_dataset=change_layer_dataset,
            based_on_coordinates=based_on_coordinates,
            to_be_changed_coordinates=to_be_changed_coordinates,
            coverage_minutes=req.coverage_value,
        )  # -> this function will return dict has {within_time_features,outside_time_features,unallocated_features}

        # Main function to create new layers
        new_layers = create_drive_time_layers(
            filtered_features=filtered_features,
            req=req,
            change_layer_metadata=change_layer_metadata,
        )

    elif req.coverage_property == "radius":
        # filter by drive time
        filtered_features = filter_cl_distance_property_from_bol(
            change_layer_dataset=change_layer_dataset,
            based_on_coordinates=based_on_coordinates,
            to_be_changed_coordinates=to_be_changed_coordinates,
            radius=req.coverage_value,
        )  # -> this function will return dict has {within_time_features,outside_time_features,unallocated_features}

        # Main function to create new layers
        new_layers = create_name_based_layers(
            filtered_features=filtered_features,
            req=req,
            change_layer_metadata=change_layer_metadata,
        )

    return (
        new_layers,
        change_layer_dataset,
        change_layer_metadata,
        based_on_layer_dataset,
        based_on_layer_metadata,
    )


# process_based on
async def process_color_based_on(
    req: ReqGradientColorBasedOnZone,
) -> List[ResGradientColorBasedOnZone]:
    (
        new_layers,
        change_layer_dataset,
        change_layer_metadata,
        based_on_layer_dataset,
        based_on_layer_metadata,
    ) = await coverage_filter_layers(req=req)
    if req.color_based_on == "name":
        # Validate input conditions
        if not req.list_names:
            raise ValueError(
                "list_names must be provided when color_based_on is 'name'."
            )
        if req.based_on_lyr_id != req.change_lyr_id:
            raise ValueError(
                "based_on_lyr_id and change_lyr_id must not be the same")

        # use filter by name function
        filtered_features = filter_by_name(
            change_layer_dataset=change_layer_dataset, list_names=req.list_names
        )  # return matched, unmatched layers
        # create new layers
        new_layers = create_name_based_layers(
            filtered_features=filtered_features,
            req=req,
            change_layer_metadata=change_layer_metadata,
        )

        return new_layers
    else:

        # Calculate influence scores for change_layer_dataset and store them
        influence_scores = []
        point_influence_map = {}
        for change_point in change_layer_dataset["features"]:
            change_point["id"] = str(uuid.uuid4())
            surrounding_metric_avg = average_metric_of_surrounding_points(
                req.color_based_on,
                change_point,
                based_on_layer_dataset,
                req.coverage_value,
            )
            if surrounding_metric_avg is not None:
                influence_scores.append(surrounding_metric_avg)
                point_influence_map[change_point["id"]] = surrounding_metric_avg

        # Create layers
        new_layers = []

        # Calculate thresholds based on influence scores
        percentiles = [16.67, 33.33, 50, 66.67, 83.33]

        # Initialize layer data
        if not influence_scores:
            # If no scores, create single layer of unallocated points
            layer_data = [[]] * (len(percentiles) + 1) + [
                [
                    assign_point_properties(point)
                    for point in change_layer_dataset["features"]
                ]
            ]
            thresholds = []  # Empty thresholds since we have no scores
        else:
            # Calculate thresholds if we have influence scores
            thresholds = np.percentile(influence_scores, percentiles)
            layer_data = [[] for _ in range(len(thresholds) + 2)]

            # Assign points to layers
            for change_point in change_layer_dataset["features"]:
                surrounding_metric_avg = point_influence_map.get(
                    change_point["id"]
                )
                feature = assign_point_properties(change_point)

                if surrounding_metric_avg is None:
                    layer_index = -1  # Last layer (unallocated)
                    feature["properties"]["influence_score"] = None
                else:
                    layer_index = next(
                        (
                            i
                            for i, threshold in enumerate(thresholds)
                            if surrounding_metric_avg <= threshold
                        ),
                        len(thresholds),
                    )
                    feature["properties"][
                        "influence_score"
                    ] = surrounding_metric_avg

                layer_data[layer_index].append(feature)

        # Create layers only for non-empty data
        for i, data in enumerate(layer_data):
            if data:
                color = (
                    req.color_grid_choice[i]
                    if i < len(req.color_grid_choice)
                    else "#FFFFFF"
                )
                if i == len(layer_data) - 1:
                    layer_name = "Unallocated Points"
                    layer_legend = "No nearby points"
                elif i == 0:
                    layer_name = f"Gradient Layer {i+1}"
                    layer_legend = f"Influence Score < {thresholds[0]:.2f}"
                elif i == len(thresholds):
                    layer_name = f"Gradient Layer {i+1}"
                    layer_legend = f"Influence Score > {thresholds[-1]:.2f}"
                else:
                    layer_name = f"Gradient Layer {i+1}"
                    layer_legend = f"Influence Score {thresholds[i-1]:.2f} - {thresholds[i]:.2f}"

                # Extract properties from first feature if available
                properties = []
                if data and len(data) > 0:
                    first_feature = data[0]
                    properties = list(
                        first_feature.get("properties", {}).keys()
                    )

                new_layers.append(
                    ResGradientColorBasedOnZone(
                        type="FeatureCollection",
                        features=data,
                        properties=properties,  # Add the properties list here
                        prdcer_layer_name=layer_name,
                        prdcer_lyr_id=req.change_lyr_id,
                        sub_lyr_id=f"{req.change_lyr_id}_gradient_{i+1}",
                        bknd_dataset_id=req.change_lyr_id,
                        points_color=color,
                        layer_legend=layer_legend,
                        layer_description=f"Gradient layer based on nearby {req.color_based_on} influence",
                        records_count=len(data),
                        city_name=change_layer_metadata.get("city_name", ""),
                        is_zone_lyr="true",
                        progress=0,
                    )
                )

        return new_layers


# filter based on
async def filter_based_on(req: ReqFilter):
    change_layer_dataset, change_layer_metadata = (
        await given_layer_fetch_dataset(req.change_lyr_id)
    )
    based_on_layer_dataset, based_on_layer_metadata = (
        await given_layer_fetch_dataset(req.based_on_lyr_id)
    )

    based_on_coordinates = [
        {
            "latitude": point["geometry"]["coordinates"][1],
            "longitude": point["geometry"]["coordinates"][0],
        }
        for point in based_on_layer_dataset["features"]
    ]

    to_be_changed_coordinates = [
        {
            "latitude": point["geometry"]["coordinates"][1],
            "longitude": point["geometry"]["coordinates"][0],
        }
        for point in change_layer_dataset["features"]
    ]

    filtred_property = await filter_by_property_and_coverage_property(
        change_layer_dataset=change_layer_dataset,
        based_on_coordinates=based_on_coordinates,
        to_be_changed_coordinates=to_be_changed_coordinates,
        req=req,
    )
    result_layers = []
    for feature in filtred_property:
        layer = ResGradientColorBasedOnZone(
            prdcer_layer_name=(
                f"{req.change_lyr_name} - Drive Time Match"
                if req.coverage_property == "drive_time"
                else f"{req.change_lyr_name} - Radius Match"
            ),
            prdcer_lyr_id=str(uuid.uuid4()),
            bknd_dataset_id=req.change_lyr_id,
            points_color=req.change_lyr_new_color,
            layer_legend=(
                f"Drive Time ≤ {req.coverage_value} m"
                if req.coverage_property == "drive_time"
                else f"Radius ≤ {req.coverage_value} m"
            ),
            is_zone_lyr="true",
            type="FeatureCollection",
            features=[feature],
            properties=list(feature.get("properties", {}).keys()),
            sub_lyr_id=(
                f"{req.change_lyr_id}_drive_time_match"
                if req.coverage_property == "drive_time"
                else f"{req.change_lyr_id}_radius_match"
            ),
            layer_description="",
            records_count=1,
            city_name=change_layer_metadata.get("city_name", ""),
            progress=0,
        )
        result_layers.append(layer)

    if len(result_layers) > 0:
        return result_layers
    else:
        raise ValueError("No features found based on the given criteria.")


async def process_color_based_on_agent(req: ReqPrompt) -> ValidationResult:
    prompt = req.prompt
    user_id = req.user_id
    user_layers = req.layers
    if not user_layers:
        user_layers = await fetch_user_layers(user_id)

    # validate the prompt'
    prompt_validation_agent = PromptValidationAgent()
    prompt_validation_result = prompt_validation_agent(prompt, user_layers)

    if prompt_validation_result.is_valid:
        recolor_agent = ReqGradientColorBasedOnZoneAgent()
        output_validation_agent = OutputValidationAgent()

        recolor_object = recolor_agent(prompt, user_layers)
        validation_recolor_object = output_validation_agent(
            prompt, recolor_object, user_layers
        )

        if validation_recolor_object.is_valid:
            validation_recolor_object.endpoint = "gradient_color_based_on_zone"
            validation_recolor_object.body = recolor_object

        return validation_recolor_object
    return prompt_validation_result
