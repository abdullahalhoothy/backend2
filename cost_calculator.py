from all_types.myapi_dtypes import ReqFetchDataset
from all_types.response_dtypes import ResCostEstimate
from use_json import use_json
import logging
from backend_common.logging_wrapper import apply_decorator_to_module
from boolean_query_processor import optimize_query_sequence
import json
import math
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

COST_PER_1000_CALLS = 40
MAX_RESULTS_THRESHOLD = 20  # Stop subdividing if results < 20
# Global dictionary to store category popularity data for each city
CITY_CATEGORIES: Dict[str, Dict] = {}

def get_city_key(country_name: str, city_name: str) -> str:
    """Generate a unique key for each city"""
    return f"{country_name.lower()}_{city_name.lower()}"

def ensure_city_categories(country_name: str, city_name: str) -> Dict:
    """Load and return category data for a city, loading it if not already loaded"""
    city_key = get_city_key(country_name, city_name)
    
    if city_key not in CITY_CATEGORIES:
        file_path = f"Backend/country_info/{country_name.lower().replace(' ', '_')}/city_info/{city_name.lower().replace(' ', '_')}/ggl_categories.json"
        try:
            with open(file_path, 'r') as f:
                categories_data = json.load(f)
                # Flatten the categories
                CITY_CATEGORIES[city_key] = {
                    subcat: value
                    for cat in categories_data
                    for subcat, value in categories_data[cat].items()
                }
                logger.info(f"Loaded categories for {city_key}")
        except Exception as e:
            logger.error(f"Error loading categories for {city_key}: {str(e)}")
            CITY_CATEGORIES[city_key] = {}
    
    return CITY_CATEGORIES[city_key]

async def load_city_categories(country_name: str, city_name: str) -> None:
    """Load category popularity data for a specific city if not already loaded"""
    city_key = get_city_key(country_name, city_name)
    if city_key not in CITY_CATEGORIES:
        file_path = f"Backend/country_info/{country_name.lower().replace(' ', '_')}/city_info/{city_name.lower().replace(' ', '_')}/ggl_categories.json"
        try:
            with open(file_path, 'r') as f:
                categories_data = json.load(f)
                # Flatten the categories
                CITY_CATEGORIES[city_key] = {
                    subcat: value
                    for cat in categories_data
                    for subcat, value in categories_data[cat].items()
                }
        except Exception as e:
            print(f"Error loading categories for {city_key}: {str(e)}")
            CITY_CATEGORIES[city_key] = {}

def get_city_categories(country_name: str, city_name: str) -> Dict:
    """Get category popularity data for a specific city"""
    city_key = get_city_key(country_name, city_name)
    return CITY_CATEGORIES.get(city_key, {})

def estimate_active_circles(density_score: float, total_circles: int) -> int:
    """
    Estimate how many circles will actually be queried based on density score.
    
    Args:
        density_score: Combined popularity score for the requested categories (0-1)
        total_circles: Total number of circles from disk covering problem
    
    Returns:
        Estimated number of circles that will actually be queried
    """
    # Calculate levels in the circle hierarchy (each level has 7 subcircles)
    levels = math.floor(math.log(total_circles, 7)) + 1
    
    # Base number of circles we'll definitely query (level 1)
    active_circles = 7
    
    # For each additional level, estimate percentage of circles that will need querying
    # based on density score
    remaining_circles = total_circles - 7
    for level in range(2, levels + 1):
        circles_at_level = min(remaining_circles, 7 ** level)
        
        # Higher density means more circles will return >= 20 results
        # and thus need subcircle queries
        activation_rate = density_score * (1 / level)  # Decreases with each level
        active_at_level = math.ceil(circles_at_level * activation_rate)
        
        active_circles += active_at_level
        remaining_circles -= circles_at_level
        
        # If activation rate is very low, we can stop estimating
        if activation_rate < 0.1:
            break
            
    return min(active_circles, total_circles)

async def calculate_cost(req: ReqFetchDataset):
    # Get the flattened categories, loading if necessary
    flattened_categories = ensure_city_categories(req.country_name, req.city_name)

    #TODO adding it here just for an idea we can improve our accuracy by using information gotten from a plan file and seeing which data was skipped which wasn't
    # plan_file = f"plan_{req.boolean_query}_{req.country_name}_{req.city_name}.json"
    # with open(plan_file, 'r') as f:
    #     plan = json.load(f)
    #     total_circles = len([x for x in plan if x != "end of search plan"])

    total_circles = 500  # Example default

    if "default" in req.search_type or "category_search" in req.search_type:
        total_api_calls = 0
        optimized_queries = optimize_query_sequence(req.boolean_query, flattened_categories)
        
        for included_types, excluded_types in optimized_queries:
            # Calculate density score for this query combination
            density_score = min(1.0, sum(
                flattened_categories.get(cat, 0.1) 
                for cat in included_types
            ) / len(included_types))
            
            # Estimate actually active circles based on density
            active_circles = estimate_active_circles(density_score, total_circles)            
            total_api_calls += active_circles

    if "keyword_search" in req.search_type:
        total_api_calls = 500 *0.5 # arbtrary discount
        
    cost = (total_api_calls / 1000) * COST_PER_1000_CALLS
        
    return ResCostEstimate(cost=cost, api_calls=total_api_calls)