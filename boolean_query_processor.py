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


def preserve_space_for_text_search_items(query: str, reverse: bool = False) -> str:
    # Regex to find text search items: @content@
    # The content is captured in group 1.
    # Content is defined as zero or more characters that are not '@'.
    # This robustly handles '@' symbols that might appear outside of our
    # intended search item delimiters (e.g., in an email address test@example.com).
    pattern = r'@([^@]*)@'

    # Determine the source and target substrings for replacement based on the 'reverse' flag.
    if reverse:
        # Backward transformation: Replace "wxyz" with spaces.
        # This applies only to "wxyz" sequences within the content of @...@ items.
        source_substring = 'wxyz'
        replacement_substring = ' '

        return query.replace(source_substring, replacement_substring)

    else:
        # Forward transformation: Replace spaces with "wxyz".
        # This applies only to spaces within the content of @...@ items.
        source_substring = ' '
        replacement_substring = 'wxyz'
        def replacer_callback(match_obj: re.Match) -> str:
            # Extract the content found between the '@' symbols (captured by group 1).
            content_inside_ats = match_obj.group(1)
            
            # Perform the specified substring replacement within this extracted content.
            modified_content = content_inside_ats.replace(source_substring, replacement_substring)
            
            return f'{modified_content}'
        
        # Use re.sub() with the replacer_callback to find all text search items
        # and apply the transformation to their content.
        # Parts of the query string that do not match the pattern remain unchanged.
        return re.sub(pattern, replacer_callback, query)


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
        # Sort mapping items by length of word (value) in descending order
        # item[0] is the letter (key), item[1] is the word (value)
        sorted_mapping_items = sorted(mapping.items(), key=lambda item: len(item[1]), reverse=True)
        
        for letter, word in sorted_mapping_items:
            result = result.replace(word, letter)
        
        logger.info(f"Sorted mapping items for replacement: {sorted_mapping_items}")
        return result, mapping

def text_search_query_sequence(boolean_query: str) -> List[Tuple[List[str], List[str]]]:
    """
    Converts a boolean query string into a list of (included_terms, excluded_terms) tuples,
    representing the Disjunctive Normal Form (DNF) of the query.
    Terms originally like "@text with space@" are processed to handle spaces correctly
    and restored in the output.
    """

    # 1. Preserve spaces in @...@ terms (e.g., "@auto parts@" -> "autowxyzparts")
    #    and remove @ wrappers. Other parts of query are unchanged.
    preserved_query = preserve_space_for_text_search_items(boolean_query, reverse=False)
    logger.info(f"Query after space preservation: {preserved_query}")

    # 2. Convert textual boolean operators (AND, OR, NOT) to sympy's format (&, |, ~)
    #    and convert to lowercase.
    query_sympy_syntax = replace_boolean_operators(preserved_query)
    logger.info(f"Query with sympy operators: {query_sympy_syntax}")

    # 3. Map terms to single letters for sympy processing
    mapped_query, mapping = map_boolean_words(query_sympy_syntax)
    logger.info(f"Mapped query to letters: '{mapped_query}', Mapping: {mapping}")

    # 4. Parse with sympy and convert to DNF
    expr = parse_expr(mapped_query)
    dnf_expr_sympy = to_dnf(expr, simplify=True) # simplify=True is default
    logger.info(f"DNF expression (sympy object): {dnf_expr_sympy}")

    # 6. Convert DNF sympy object back to string, then map letters back to original (wxyz-preserved) terms
    dnf_expr_str = str(dnf_expr_sympy)
    original_expr_dnf, _ = map_boolean_words(dnf_expr_str, reverse=True, mapping=mapping)
    logger.info(f"DNF expression (original terms, wxyz format): {original_expr_dnf}")

    # 7. Parse the DNF string into include/exclude lists for each clause
    # Example DNF string from sympy: "termA_wxyz & ~termB_wxyz | termC_wxyz"
    dnf_clauses_str = original_expr_dnf.split(" | ")
    
    intermediate_queries = [] # Stores ( [include_wxyz], [exclude_wxyz] ) tuples
    for clause_str in dnf_clauses_str:
        clause_str = clause_str.strip()
        if not clause_str: # Should not happen with valid DNF from sympy unless original_expr_dnf was empty
            continue

        # Literals within a clause are separated by " & "
        # .replace("(", "").replace(")", "") handles cases like "(termA & termB)" if sympy adds them around ANDed parts
        literals_str_list = clause_str.replace("(", "").replace(")", "").split(" & ")
        
        included_terms_in_clause = []
        excluded_terms_in_clause = []
        
        for literal_str in literals_str_list:
            literal_str = literal_str.strip()
            if not literal_str: # Skip empty strings from split (e.g. if "&&" occurred)
                continue
            
            if literal_str.startswith("~"):
                term = literal_str[1:].strip() # Remove "~" and strip whitespace
                if term: # Ensure term is not empty after stripping "~" and whitespace
                    excluded_terms_in_clause.append(term)
            else:
                if literal_str: # Ensure term is not empty
                    included_terms_in_clause.append(literal_str)
        
        # Add clause if it has any terms (either included or excluded)
        if included_terms_in_clause or excluded_terms_in_clause:
             intermediate_queries.append((included_terms_in_clause, excluded_terms_in_clause))

    # 8. Final postprocessing: revert "wxyz" to spaces in term names using the user's provided loop structure.
    final_processed_queries = []
    for included_list, excluded_list in intermediate_queries:
        new_included_list = [
            preserve_space_for_text_search_items(item_str, reverse=True)
            for item_str in included_list
        ]
        new_excluded_list = [
            preserve_space_for_text_search_items(item_str, reverse=True)
            for item_str in excluded_list
        ]
        final_processed_queries.append((new_included_list, new_excluded_list))
        
    logger.info(f"Generated {len(final_processed_queries)} query sequences from DNF.")
    return final_processed_queries

def optimize_query_sequence(
    boolean_query, popularity_data: Dict[str, float] = None
) -> List[Tuple[List[str], List[str]]]:
    """
    Optimize the query sequence based on set theory and popularity data
    Returns: List of (included_types, excluded_types) tuples
    """
    # boolean_query = preserve_space_for_text_search_items(boolean_query)
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
        logger.info(f"Mapped query: {mapped_query}")

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


def separate_boolean_queries(boolean_string:str):
    """
    Separates a boolean query string into category-only and keyword-only queries.

    Keywords are enclosed in @...@.
    Categories are alphanumeric + underscore, not enclosed in @.
    """

    # 1. Define a token pattern to capture all parts of the query
    # Order matters: keywords first, then operators, then category-like words, then parentheses.
    token_pattern = re.compile(
        r'(@[^@]+@)'              # Keywords like @auto parts@
        r'|(\b(?:AND|OR|NOT)\b)'  # Operators AND, OR, NOT (case-insensitive matching later)
        r'|([a-zA-Z0-9_]+)'       # Categories like auto_parts_store
        r'|(\()|(\))'             # Parentheses
    )

    tokens = [match.group(0) for match in token_pattern.finditer(boolean_string)]

    # Placeholder for terms that will be removed
    REMOVED_TERM_PLACEHOLDER = "__REMOVED_TERM__"

    def build_specific_query(keep_type):
        """
        Builds a query string keeping only 'category' or 'keyword' terms.
        Other terms are replaced by REMOVED_TERM_PLACEHOLDER.
        """
        specific_tokens = []
        for token in tokens:
            is_keyword = token.startswith('@') and token.endswith('@')
            is_operator_or_paren = token in ['(', ')'] or \
                                   re.fullmatch(r'AND|OR|NOT', token, re.IGNORECASE)
            # A category is what's left, assuming valid input structure
            is_category = not is_keyword and not is_operator_or_paren

            if is_operator_or_paren:
                specific_tokens.append(token)
            elif is_keyword:
                if keep_type == 'keyword':
                    specific_tokens.append(token)
                else:
                    specific_tokens.append(REMOVED_TERM_PLACEHOLDER)
            elif is_category: # Must be a category term
                if keep_type == 'category':
                    specific_tokens.append(token)
                else:
                    specific_tokens.append(REMOVED_TERM_PLACEHOLDER)
            # else: this case should not happen if tokenization is correct
        return " ".join(specific_tokens)

    def cleanup_query_string(s):
        """
        Cleans up a query string containing REMOVED_TERM_PLACEHOLDER.
        Removes placeholders and fixes syntax.
        """
        if not s: # Handle empty initial string
            return ""

        # Use a loop to apply rules iteratively until the string stabilizes
        last_s = None
        while s != last_s:
            last_s = s

            # Normalize whitespace
            s = re.sub(r'\s+', ' ', s).strip()

            # Rule 1: (X AND/OR REMOVED) -> (X), (REMOVED AND/OR X) -> (X)
            # This handles cases where a placeholder is one of the operands inside parentheses
            s = re.sub(r'\(\s*([^\s()]+)\s+(AND|OR)\s+' + REMOVED_TERM_PLACEHOLDER + r'\s*\)', r'(\1)', s, flags=re.IGNORECASE)
            s = re.sub(r'\(\s*' + REMOVED_TERM_PLACEHOLDER + r'\s+(AND|OR)\s+([^\s()]+)\s*\)', r'(\2)', s, flags=re.IGNORECASE)
            
            # Rule 2: NOT REMOVED_TERM -> REMOVED_TERM (it effectively removes the NOT clause)
            s = re.sub(r'\bNOT\s+' + REMOVED_TERM_PLACEHOLDER + r'\b', REMOVED_TERM_PLACEHOLDER, s, flags=re.IGNORECASE)

            # Rule 3: (REMOVED_TERM) -> REMOVED_TERM
            s = re.sub(r'\(\s*' + REMOVED_TERM_PLACEHOLDER + r'\s*\)', REMOVED_TERM_PLACEHOLDER, s, flags=re.IGNORECASE)
            
            # Rule 4: REMOVED_TERM AND/OR X -> X (if REMOVED_TERM is the left operand)
            # Needs to be careful not to remove X if X is also REMOVED_TERM yet
            # This regex looks for a placeholder followed by an operator and then a non-placeholder, non-operator, non-paren term
            s = re.sub(r'\b' + REMOVED_TERM_PLACEHOLDER + r'\s+(AND|OR)\s+(?![()]|\b(?:AND|OR|NOT|' + REMOVED_TERM_PLACEHOLDER + r')\b)([^\s()]+)\b', r'\2', s, flags=re.IGNORECASE)
            # Or if X is a parenthesized expression
            s = re.sub(r'\b' + REMOVED_TERM_PLACEHOLDER + r'\s+(AND|OR)\s+(\([^\)]+\))', r'\2', s, flags=re.IGNORECASE)


            # Rule 5: X AND/OR REMOVED_TERM -> X (if REMOVED_TERM is the right operand)
            s = re.sub(r'\b(?![()]|\b(?:AND|OR|NOT|' + REMOVED_TERM_PLACEHOLDER + r')\b)([^\s()]+)\s+(AND|OR)\s+' + REMOVED_TERM_PLACEHOLDER + r'\b', r'\1', s, flags=re.IGNORECASE)
            # Or if X is a parenthesized expression
            s = re.sub(r'(\([^\)]+\))\s+(AND|OR)\s+' + REMOVED_TERM_PLACEHOLDER + r'\b', r'\1', s, flags=re.IGNORECASE)

            # Rule 6: Handle cases like REMOVED_TERM AND REMOVED_TERM -> REMOVED_TERM
            s = re.sub(r'\b' + REMOVED_TERM_PLACEHOLDER + r'\s+(?:AND|OR)\s+' + REMOVED_TERM_PLACEHOLDER + r'\b', REMOVED_TERM_PLACEHOLDER, s, flags=re.IGNORECASE)

            # Rule 7: If the entire string is just the placeholder, make it empty
            if s == REMOVED_TERM_PLACEHOLDER:
                s = ""
                break # No more processing needed

            # Rule 8: Clean up dangling operators
            # Inside parentheses
            s = re.sub(r'\(\s*(AND|OR)\s+', '(', s, flags=re.IGNORECASE)
            s = re.sub(r'\s*(AND|OR)\s*\)', ')', s, flags=re.IGNORECASE)
            # At the beginning/end of string
            s = re.sub(r'^\s*(AND|OR)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'\s*(AND|OR)\s*$', '', s, flags=re.IGNORECASE)
            
            # Rule 9: Clean up empty parentheses ()
            # If () is part of a larger expression like X AND ()
            s = re.sub(r'([^\s()]+)\s+(AND|OR)\s+\(\s*\)', r'\1', s, flags=re.IGNORECASE)
            s = re.sub(r'\(\s*\)\s+(AND|OR)\s+([^\s()]+)', r'\2', s, flags=re.IGNORECASE)
            s = re.sub(r'(\([^\)]+\))\s+(AND|OR)\s+\(\s*\)', r'\1', s, flags=re.IGNORECASE) # (X) AND () -> (X)
            s = re.sub(r'\(\s*\)\s+(AND|OR)\s+(\([^\)]+\))', r'\2', s, flags=re.IGNORECASE) # () AND (X) -> (X)
            s = re.sub(r'\bNOT\s+\(\s*\)', '', s, flags=re.IGNORECASE) # NOT () -> empty

            # If the string is just "()", make it empty
            if s == "()":
                s = ""
                break
            
            # Remove any remaining standalone empty parentheses from the string
            s = re.sub(r'\s*\(\s*\)\s*', ' ', s).strip() # Replace with space then strip

            # Final whitespace normalization
            s = re.sub(r'\s+', ' ', s).strip()
            
        # One last pass for specific cases if placeholder is still there
        # This helps if placeholder was left alone e.g. (X AND Y) AND __REMOVED_TERM__
        s = re.sub(r'\s+(AND|OR)\s+' + REMOVED_TERM_PLACEHOLDER + r'$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^' + REMOVED_TERM_PLACEHOLDER + r'\s+(AND|OR)\s+', '', s, flags=re.IGNORECASE)
        if s == REMOVED_TERM_PLACEHOLDER: s = ""

        # Ensure a completely empty string if all terms were removed
        if not re.search(r'[a-zA-Z0-9@_]', s): # if only operators/parens left
             return ""
        return s

    # Build category query
    raw_category_query = build_specific_query('category')
    category_boolean = cleanup_query_string(raw_category_query)

    # Build keyword query
    raw_keyword_query = build_specific_query('keyword')
    keyword_boolean = cleanup_query_string(raw_keyword_query)


# # Example usage:
# boolean1 = """(auto_parts_store OR @auto parts@ OR @car repair@ OR @car parts@ OR @car repair parts@ OR @قطع غيار السيارات@) AND NOT @بنشر@"""
# cat_query1, kw_query1 = separate_boolean_queries(boolean1)
# print(f"Original: {boolean1}")
# print(f"Category Boolean: \"{cat_query1}\"")
# print(f"Keyword Boolean: \"{kw_query1}\"")
# print("-" * 30)

# boolean2 = """@keyword1@ AND (category1 OR @keyword2@) AND NOT category2"""
# cat_query2, kw_query2 = separate_boolean_queries(boolean2)
# print(f"Original: {boolean2}")
# print(f"Category Boolean: \"{cat_query2}\"")
# print(f"Keyword Boolean: \"{kw_query2}\"")
# print("-" * 30)

# boolean3 = """@k1@ OR @k2@"""
# cat_query3, kw_query3 = separate_boolean_queries(boolean3)
# print(f"Original: {boolean3}")
# print(f"Category Boolean: \"{cat_query3}\"")
# print(f"Keyword Boolean: \"{kw_query3}\"")
# print("-" * 30)

# boolean4 = """category1 AND category2"""
# cat_query4, kw_query4 = separate_boolean_queries(boolean4)
# print(f"Original: {boolean4}")
# print(f"Category Boolean: \"{cat_query4}\"")
# print(f"Keyword Boolean: \"{kw_query4}\"")
# print("-" * 30)

# boolean5 = """(category1)"""
# cat_query5, kw_query5 = separate_boolean_queries(boolean5)
# print(f"Original: {boolean5}")
# print(f"Category Boolean: \"{cat_query5}\"")
# print(f"Keyword Boolean: \"{kw_query5}\"")
# print("-" * 30)

# boolean6 = """(@keyword1@)"""
# cat_query6, kw_query6 = separate_boolean_queries(boolean6)
# print(f"Original: {boolean6}")
# print(f"Category Boolean: \"{cat_query6}\"")
# print(f"Keyword Boolean: \"{kw_query6}\"")
# print("-" * 30)

# boolean7 = """NOT category1 AND (@k1@ OR category2)"""
# cat_query7, kw_query7 = separate_boolean_queries(boolean7)
# print(f"Original: {boolean7}")
# print(f"Category Boolean: \"{cat_query7}\"") # Expected: NOT category1 AND (category2)
# print(f"Keyword Boolean: \"{kw_query7}\"")   # Expected: (@k1@)
# print("-" * 30)

# boolean8 = """( @k1@ ) AND ( @k2@ OR cat1 )"""
# cat_query8, kw_query8 = separate_boolean_queries(boolean8)
# print(f"Original: {boolean8}")
# print(f"Category Boolean: \"{cat_query8}\"") # Expected: (cat1)
# print(f"Keyword Boolean: \"{kw_query8}\"")   # Expected: ( @k1@ ) AND ( @k2@ )
# print("-" * 30)


    return category_boolean, keyword_boolean



# Apply the decorator to all functions in this module
apply_decorator_to_module(logger)(__name__)
