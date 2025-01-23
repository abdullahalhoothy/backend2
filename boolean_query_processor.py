import logging
import json
import re
from sympy import parse_expr
from sympy.logic.boolalg import to_dnf
from typing import Dict, List, Tuple
from backend_common.logging_wrapper import apply_decorator_to_module
from string import ascii_lowercase
from typing import Tuple, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def replace_boolean_operators(query: str) -> str:
    """
    Replaces boolean operators in a query string with their textual equivalents.
    """
    return (
        query.lower()
        .replace(" and ", " & ")
        .replace(" or ", " | ")
        .replace(" not ", " ~ ")
    )

def map_boolean_words(
    query: str, reverse: bool = False, mapping: Dict[str, str] = None
) -> Tuple[str, Dict[str, str]]:
    """
    Maps words in a boolean query to/from single letters to prevent operator conflicts.

    Args:
        query: The boolean query string
        reverse: If True, maps letters back to words using provided mapping
        mapping: Required when reverse=True, the mapping dictionary to use

    Returns:
        Tuple of (processed_query, mapping_dictionary)
    """
    if reverse and mapping is None:
        raise ValueError("Mapping dictionary required when reverse=True")

    query = query.lower()

    if reverse:
        # Replace letters with original words all at once using a single regex
        result = query
        pattern = '|'.join(re.escape(letter) for letter in mapping.keys())
        result = re.sub(pattern, lambda m: mapping[m.group()], result)
        return result, mapping
    else:
        # Create new mapping of words to letters
        words = []
        current_word = ""
        in_word = False

        # Split into words while preserving operators
        for char in query:
            if char.isalnum() or char in ["_", "-"]:
                current_word += char
                in_word = True
            else:
                if in_word:
                    words.append(current_word)
                    current_word = ""
                    in_word = False
                words.append(char)
        if in_word:
            words.append(current_word)

        # Filter out operators and empty strings
        unique_words = []
        operators = {"and", "or", "not", "&", "|", "~", "(", ")", " "}
        for word in words:
            word = word.strip()
            if word and word.lower() not in operators:
                if word not in unique_words:
                    unique_words.append(word)

        if len(unique_words) > 26:
            raise ValueError("Query contains more than 26 unique terms")

        # Create mapping
        mapping = {ascii_lowercase[i]: word for i, word in enumerate(unique_words)}

        # Replace words with letters
        result = query
        for letter, word in mapping.items():
            result = result.replace(word, letter)

        logger.debug(f"Created mapping: {mapping}")
        return result, mapping


def optimize_query_sequence(
    boolean_query, popularity_data: Dict[str, float]
) -> List[Tuple[List[str], List[str]]]:
    """
    Optimize the query sequence based on set theory and popularity data
    Returns: List of (included_types, excluded_types) tuples
    """
    # Convert to sympy syntax
    query = replace_boolean_operators(boolean_query)
    logger.info(f"Processing query: {query}")

    # First map words to letters
    mapped_query, mapping = map_boolean_words(query)
    logger.info(f"Mapped query: {mapped_query}")

    # Parse and convert to DNF
    expr = parse_expr(mapped_query)
    dnf_expr = to_dnf(expr)
    logger.info(f"DNF Expression: {dnf_expr}")
    # Map back to original terms
    original_expr, _ = map_boolean_words(str(dnf_expr), reverse=True, mapping=mapping)
    logger.info(f"DNF Expression: {original_expr}")

    terms = original_expr.split(" | ")
    queries = []
    processed_terms = set()

    logger.info(f"DNF Expression: {dnf_expr}")

    # First handle simple terms (no AND conditions)
    if popularity_data:
        simple_terms = [
            (term, popularity_data.get(term.lower(), 0.0))
            for term in terms
            if "&" not in term
        ]
        # Sort by complexity score (DESCENDING)
        simple_terms.sort(key=lambda x: x[1], reverse=True)
        logger.info("Sorted terms by popularity:")
    else:
        # If no popularity data, treat all terms equally with score 1.0
        simple_terms = [(term, 1.0) for term in terms if "&" not in term]
        logger.info("No popularity data provided, treating all terms equally")

    for term, score in simple_terms:
        logger.info(f"  {term}: {score}")

    # Process simple terms first
    for term, score in simple_terms:
        included = []
        excluded = list(processed_terms)

        if term.startswith("~"):
            excluded.append(term[1:])
        else:
            included.append(term)
            processed_terms.add(term)

        if included or excluded:
            queries.append((included, excluded))
            logger.info(
                f"Added query - Include: {included}, Exclude: {excluded}, Popularity: {score}"
            )

    # Then handle compound terms
    compound_terms = [term for term in terms if "&" in term]
    for term in compound_terms:
        included = []
        excluded = list(processed_terms)

        parts = term.replace("(", "").replace(")", "").split(" & ")
        for part in parts:
            if part.startswith("~"):
                excluded.append(part[1:])
            else:
                included.append(part)

        if included or excluded:
            queries.append((included, excluded))
            logger.info(
                f"Added compound query - Include: {included}, Exclude: {excluded}"
            )
            processed_terms.update(included)

    return queries


def reduce_to_single_query(boolean_query: str) -> Tuple[List[str], List[str]]:
    """
    Reduces a boolean query to a single set of included and excluded types.
    Returns: Tuple[included_types: List[str], excluded_types: List[str]]
    """
    try:
        # First map words to letters
        mapped_query, mapping = map_boolean_words(boolean_query)
        logger.debug(f"Mapped query: {mapped_query}")

        # Convert query to sympy syntax and parse
        query = (
        mapped_query
        .replace(" and ", " & ")
        .replace(" or ", " | ")
        .replace(" not ", " ~ ")
    )
        expr = parse_expr(query)
        dnf_expr = to_dnf(expr)

        # Map back to original terms
        original_expr, _ = map_boolean_words(
            str(dnf_expr), reverse=True, mapping=mapping
        )
        logger.info(f"DNF Expression: {original_expr}")

        # Extract all terms
        included_types = set()
        excluded_types = set()

        # Convert to string and split by OR
        terms = original_expr.split(" | ")

        # Process each term
        for term in terms:
            # Split by AND if compound term
            parts = term.replace("(", "").replace(")", "").split(" & ")
            for part in parts:
                if part.startswith("~"):
                    excluded_types.add(part[1:])
                else:
                    included_types.add(part)

        # Remove any type that appears in both sets (resolve conflicts)
        conflicting_types = included_types.intersection(excluded_types)
        if conflicting_types:
            logger.warning(f"Found conflicting types: {conflicting_types}")
            included_types = included_types - conflicting_types
            excluded_types = excluded_types - conflicting_types

        logger.info(
            f"Reduced query - Include: {list(included_types)}, Exclude: {list(excluded_types)}"
        )

        return list(included_types), list(excluded_types)

    except Exception as e:
        logger.error(f"Error reducing boolean query: {str(e)}")
        return [], []


def test_optimized_queries():
    test_cases = [
        "((Brunch AND (coffee OR tea)) OR (Breakfast OR (bakery AND dessert))) AND NOT fast_food",
        "coffee AND tea",
        "restaurant OR cafe OR tea",
        "NOT fast_food",
        "(pizza_restaurant OR hamburger_restaurant) AND NOT vegan_restaurant",
        "((cafe AND wifi) OR (library AND quiet)) AND NOT construction",
    ]

    for i, query in enumerate(test_cases, 1):
        try:
            print(f"\nTest Case {i}:")


            # Get optimized query sequence using global POPULARITY_DATA
            # Load and flatten the popularity data
            with open("Backend/ggl_categories_poi_estimate.json", "r") as f:
                raw_popularity_data = json.load(f)

            # Flatten the nested dictionary - we only care about subkeys
            POPULARITY_DATA = {}
            for category in raw_popularity_data.values():
                POPULARITY_DATA.update(category)

            optimized_queries = optimize_query_sequence(query, POPULARITY_DATA)


            for j, (included, excluded) in enumerate(optimized_queries, 1):
                print(f"\nCall {j}:")
                print(f"  Include: {included}")
                print(f"  Exclude: {excluded}")
                print(f"  Popularity Scores:")
                for inc in included:
                    score = POPULARITY_DATA.get(inc, 0.0)
                    print(f"    {inc}: {score}")

            print("\n" + "=" * 50)

        except Exception as e:
            print(f"Error processing query: {str(e)}")


# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
