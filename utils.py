from all_types.myapi_dtypes import ReqFetchDataset


def make_ggl_layer_filename(req: ReqFetchDataset) -> str:
    # type_string = make_include_exclude_name(req.includedTypes, req.excludedTypes)
    type_string = req.boolean_query.replace(" ", "_")
    tcc_string = f"{type_string}_{req.country_name}_{req.city_name}"
    return tcc_string