from geopy.distance import geodesic
import json
from collections import defaultdict
from geopy.distance import geodesic
import time
from datetime import timedelta

import itertools
import json
from collections import defaultdict
from multiprocessing import Pool

DEDUPLICATE_RULES_PATH = 'Backend/layer_category_country_city_matching/full_data_plans/duplicate_rules.json'

def parrallel_calculate_distances(args):
    circle1, circle2, distance_threshold = args
    point1 = (circle1['coords'][0], circle1['coords'][1])
    point2 = (circle2['coords'][0], circle2['coords'][1])
    distance = geodesic(point1, point2).meters

    if distance < distance_threshold:
        c1, c2 = sorted([circle1['circle'], circle2['circle']])
        return (f"{c2}", f"{c1}")
    return None


def parrallel_create_duplicate_rules(json_path, distance_threshold=200, num_processes=4):
    # Load the data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Separate circles by their level (unchanged)
    circles_by_level = defaultdict(list)
    for entry in data:
        circle = None
        for part in entry.split('_'):
            if part.startswith('circle='):
                circle = part.split('=')[1]
                break

        if circle:
            level = circle.count('.')
            coord_parts = entry.split('_')[:2]
            coords = [float(x) for x in coord_parts]
            circles_by_level[level].append({
                'circle': circle,
                'coords': coords,
                'full_string': entry
            })

    # Process each level in parallel
    potential_rules = {}
    with Pool(processes=num_processes) as pool:
        for level, circles in circles_by_level.items():
            # Create all possible pairs of circles
            circle_pairs = list(itertools.combinations(circles, 2))

            # Add distance_threshold to each pair for mapping
            args = [(c1, c2, distance_threshold) for c1, c2 in circle_pairs]

            # Process pairs in parallel
            results = pool.map(parrallel_calculate_distances, args)

            # Filter out None results and add to potential_rules
            valid_results = filter(None, results)
            potential_rules.update(dict(valid_results))

    # Save rules to JSON file
    with open(DEDUPLICATE_RULES_PATH, 'w') as file:
        json.dump(potential_rules, file, indent=4)

    return potential_rules


def create_duplicate_rules(json_path, distance_threshold=200):  # threshold in meters
    # Load the data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Separate circles by their level
    circles_by_level = defaultdict(list)
    for entry in data:
        circle = None
        for part in entry.split('_'):
            if part.startswith('circle='):
                circle = part.split('=')[1]
                break

        if circle:
            level = circle.count('.')
            coord_parts = entry.split('_')[:2]  # First two parts are lat, lon
            coords = [float(x) for x in coord_parts]
            circles_by_level[level].append({
                'circle': circle,
                'coords': coords,  # [lat, lon]
                'full_string': entry
            })

    # Find potential duplicates within each level
    potential_rules = {}
    total_start_time = time.time()
    # Calculate total comparisons needed
    total_comparisons = 0
    for circles in circles_by_level.values():
        n = len(circles)
        total_comparisons += (n * (n - 1)) // 2
    
    comparisons_done = 0
    for level, circles in circles_by_level.items():
        n_circles = len(circles)
        print(f"\nProcessing level {level} with {n_circles} circles")
        
        for i in range(len(circles)):
            for j in range(i + 1, len(circles)):
                comparisons_done += 1
                
                if comparisons_done % 10000 == 0:  # Update status every 1000 comparisons
                    elapsed_time = time.time() - total_start_time
                    avg_time_per_comparison = elapsed_time / comparisons_done
                    remaining_comparisons = total_comparisons - comparisons_done
                    estimated_remaining_time = remaining_comparisons * avg_time_per_comparison
                    
                    print(f"\rProgress: {comparisons_done}/{total_comparisons} comparisons "
                          f"({(comparisons_done/total_comparisons*100):.1f}%) "
                          f"Elapsed: {timedelta(seconds=int(elapsed_time))} "
                          f"Remaining: {timedelta(seconds=int(estimated_remaining_time))}", end='')
                
                circle1 = circles[i]
                circle2 = circles[j]
                
                point1 = (circle1['coords'][0], circle1['coords'][1])
                point2 = (circle2['coords'][0], circle2['coords'][1])
                distance = geodesic(point1, point2).meters
                
                if distance < distance_threshold:
                    c1, c2 = sorted([circle1['circle'], circle2['circle']])
                    rule_key = f"{c2}"
                    rule_value = f"{c1}"
                    potential_rules[rule_key] = rule_value

    print(f"\nProcessing complete. Total time: {timedelta(seconds=int(time.time() - total_start_time))}")
    
    # Save rules to JSON file
    with open(DEDUPLICATE_RULES_PATH, 'w') as file:
        json.dump(potential_rules, file, indent=4)


    return potential_rules
