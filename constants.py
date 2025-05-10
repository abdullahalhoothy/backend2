def load_country_city():
    data = {
        "United Arab Emirates": [
            {
                "name": "Dubai",
                "lat": 25.2048,
                "lng": 55.2708,
                "bounding_box": [
                    25.1053471,
                    25.4253471,
                    55.1324914,
                    55.4524914,
                ],
                "borders": {
                    "northeast": {"lat": 25.3960, "lng": 55.5643},
                    "southwest": {"lat": 24.7921, "lng": 54.8911},
                },
            },
            {
                "name": "Abu Dhabi",
                "lat": 24.4539,
                "lng": 54.3773,
                "bounding_box": [
                    24.2810331,
                    24.6018540,
                    54.2971553,
                    54.7659108,
                ],
                "borders": {
                    "northeast": {"lat": 24.5649, "lng": 54.5485},
                    "southwest": {"lat": 24.3294, "lng": 54.2783},
                },
            },
            {
                "name": "Sharjah",
                "lat": 25.3573,
                "lng": 55.4033,
                "bounding_box": [
                    24.7572612,
                    25.6989797,
                    53.9777051,
                    56.6024458,
                ],
                "borders": {
                    "northeast": {"lat": 25.4283, "lng": 55.5843},
                    "southwest": {"lat": 25.2865, "lng": 55.2723},
                },
            },
        ],
        "Saudi Arabia": [
            {
                "name": "Riyadh",
                "lat": 24.7136,
                "lng": 46.6753,
                "bounding_box": [
                    19.2083336,
                    27.7020999,
                    41.6811300,
                    48.2582000,
                ],
                "borders": {
                    "northeast": {"lat": 24.9182, "lng": 46.8482},
                    "southwest": {"lat": 24.5634, "lng": 46.5023},
                },
            },
            {
                "name": "Jeddah",
                "lat": 21.5433,
                "lng": 39.1728,
                "bounding_box": [
                    21.3904432,
                    21.7104432,
                    39.0142363,
                    39.3342363,
                ],
                "borders": {
                    "northeast": {"lat": 21.7432, "lng": 39.2745},
                    "southwest": {"lat": 21.3234, "lng": 39.0728},
                },
            },
            {
                "name": "Mecca",
                "lat": 21.4225,
                "lng": 39.8262,
                "bounding_box": [
                    21.1198192,
                    21.8480401,
                    39.5058552,
                    40.4756100,
                ],
                "borders": {
                    "northeast": {"lat": 21.5432, "lng": 39.9283},
                    "southwest": {"lat": 21.3218, "lng": 39.7241},
                },
            },
        ],
        "Canada": [
            {
                "name": "Toronto",
                "lat": 43.6532,
                "lng": -79.3832,
                "bounding_box": [
                    43.5796082,
                    43.8554425,
                    -79.6392832,
                    -79.1132193,
                ],
                "borders": {
                    "northeast": {"lat": 43.8554, "lng": -79.1168},
                    "southwest": {"lat": 43.5810, "lng": -79.6396},
                },
            },
            {
                "name": "Vancouver",
                "lat": 49.2827,
                "lng": -123.1207,
                "bounding_box": [
                    49.1989306,
                    49.3161714,
                    -123.2249611,
                    -123.0232419,
                ],
                "borders": {
                    "northeast": {"lat": 49.3932, "lng": -122.9856},
                    "southwest": {"lat": 49.1986, "lng": -123.2642},
                },
            },
            {
                "name": "Montreal",
                "lat": 45.5017,
                "lng": -73.5673,
                "bounding_box": [
                    45.4100756,
                    45.7047897,
                    -73.9741567,
                    -73.4742952,
                ],
                "borders": {
                    "northeast": {"lat": 45.7058, "lng": -73.4734},
                    "southwest": {"lat": 45.4139, "lng": -73.7089},
                },
            },
        ],
    }
    return data