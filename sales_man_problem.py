import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import box, Polygon
import shapely
import contextily as ctx


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

def get_population_by_zoom_in_bounding_box(population_data : gpd.GeoDataFrame | None = None, 
                                           zoom_level: int | None = None, 
                                           bounding_box: list[tuple[float, float]] | None = None) -> gpd.GeoDataFrame:
    """
    args:
    ----
    
    `populaton_data` is a dataframe of census data 
    containing population column for each population center as a point geometry

    `zoom_level` is the level of the zoom that is present in the dataset

    `bounding box` is the list of lon lat pair to develope a shapely polygon


    return:
    ------

    DataFrame filtered using bounding box and zoom_level
    """
    population_data = gpd.GeoDataFrame(
          population_data, geometry=gpd.points_from_xy(population_data.longitude, 
                                                       population_data.latitude)
      )
    pop_by_zoom =  population_data.loc[population_data.zoom_level == zoom_level]
    city_boundary = define_boundary(bounding_box)
    pop_by_zoom = pop_by_zoom.loc[pop_by_zoom.within(city_boundary)]
    return pop_by_zoom


def get_income_by_zoom_in_bounding_box(income_data : gpd.GeoDataFrame | None = None, 
                                        zoom_level: int | None = None, 
                                        bounding_box: list[tuple[float, float]] | None = None) -> gpd.GeoDataFrame:
    """
    args:
    ----
    
    `income_data` is a dataframe of income data 

    `zoom_level` is the level of the zoom that is present in the dataset

    `bounding box` is the list of lon lat pair to develope a shapely polygon


    return:
    ------

    DataFrame filtered using bounding box and zoom_level
    """
    income_data = gpd.GeoDataFrame(
          income_data, geometry=gpd.points_from_xy(income_data.longitude, 
                                                   income_data.latitude)
      )
    inc_by_zoom =  income_data.loc[income_data.zoom_level == zoom_level]
    city_boundary = define_boundary(bounding_box)
    inc_by_zoom = inc_by_zoom.loc[inc_by_zoom.within(city_boundary)]
    return inc_by_zoom
    
def get_places_data(places_data : gpd.GeoDataFrame | None = None, 
                    bounding_box : list[tuple[float, float]] | None = None) -> gpd.GeoDataFrame:
    
    """
    args:
    ----

    `places_data` is the dataframe of destinations forexample supermarkets, pharmecies etc.
    `bounding box` is the list of lon lat pair to develope a shapely polygon

    return:
    ------

    DataFrame filtered using bounding box
    """

    places = places_data.data.map(lambda x: gpd.GeoDataFrame.from_features(x["features"])).values.tolist()
    places = pd.concat(places).reset_index()
    city_boundary = define_boundary(bounding_box)
    places = places.loc[places.within(city_boundary)]
    return places

def create_grid(population : gpd.GeoDataFrame | None = None, 
                grid_size : int | None = None) -> gpd.GeoDataFrame:
    
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

    minx, miny, maxx, maxy = population.total_bounds
    a_grid_size = (((maxx-minx) * (maxy-miny))/(population.shape[0]))**(0.5)
    if grid_size is None:
        grid_size = a_grid_size
    grid_cells = [
        box(x, y, x + grid_size, y + grid_size)
        for x in np.arange(minx, maxx, grid_size)
        for y in np.arange(miny, maxy, grid_size)
    ]
    grid = gpd.GeoDataFrame(geometry=grid_cells, crs=population.crs)
    return grid

def haversine(lat1_array : np.ndarray, 
              lon1_array : np.ndarray, 
              lat2_array : np.ndarray, 
              lon2_array : np.ndarray) -> np.ndarray:
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

    lat1_rad, lon1_rad = np.radians(lat1_array), np.radians(lon1_array)
    lat2_rad, lon2_rad = np.radians(lat2_array), np.radians(lon2_array)

    lat1_rad = lat1_rad[:, np.newaxis]  #  (M, 1)
    lon1_rad = lon1_rad[:, np.newaxis]  #  (M, 1)
    
    dlat = lat2_rad - lat1_rad  # (M, N)
    dlon = lon2_rad - lon1_rad  # (M, N)
    
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    R = 6371.0  
    distances = R * c  # (M, N)

    return distances


def get_grids_of_data(origins : gpd.GeoDataFrame, 
                      destinations : gpd.GeoDataFrame, 
                      weights : gpd.GeoDataFrame,
                      distanace_limit: float) -> gpd.GeoDataFrame:
    """
    args:
    ----
    `origins` are the population centers in a form if geodataframe
    `destinations` are the places geodataframe
    `weights` are the income dataframes in this context for each population center keep `None` if unavailable
    `distance_limit` is a max distance a person is willing to travel to reach destination

    return:
    ------
    a single geodataframe containing popygons (grids) for entire ROI and aggregated data for each grid
    cell (population, places counts)
    """
    matrix = haversine(origins.latitude.values, 
                        origins.longitude.values,
                        destinations.latitude.values,
                        destinations.longitude.values)

    od_cost_matrix = {k:[] for k in range(matrix.shape[0])}

    for i in range(matrix.shape[0]):
        od = matrix[i].tolist()
        while len(od_cost_matrix[i])<matrix.shape[1]:
            if np.min(od)<distanace_limit:
                amn = np.argmin(od)
                if np.isfinite(amn):
                    od_cost_matrix[i].append(amn)
                od[amn] = np.inf
            else:
                if len(od_cost_matrix[i])==0:
                    amn = np.argmin(od)
                    if np.isfinite(amn):
                        od_cost_matrix[i].append(amn)
                break

    origins["number_of_accessibile_markets"] = [len(i) for i in od_cost_matrix.values()]

    if weights is None:
        origins["effective_population"] = origins["population"]/origins["number_of_accessibile_markets"]
    else:
        origins["effective_population"] = (origins["population"].values*weights["income"].values)/origins["number_of_accessibile_markets"].values

    market = {k:[] for k in range(matrix.shape[1])}
    for i in range(matrix.shape[1]):
        for k, v in od_cost_matrix.items():
            if i in v:
                market[i].append(origins["effective_population"].iloc[k])

    destinations["market"] = [sum(v) for v in market.values()]

    grid = create_grid(origins, grid_size=None)

    poulation_grid = gpd.sjoin(origins, grid, how="left", predicate="within")
    places_grid = gpd.sjoin(destinations, grid, how="left", predicate="within")
    data = pd.concat([
            grid,
            poulation_grid.groupby("index_right")["population"].sum().rename("number_of_persons"),
            poulation_grid.groupby("index_right")["effective_population"].sum().rename("effective_population"),
            places_grid.groupby("index_right")["geometry"].count().rename("number_of_supermarkets"),
            places_grid.groupby("index_right")["market"].sum().rename("number_of_potential_customers"),
        ], axis=1)

    mask = ~data.iloc[:,1:].isna().all(axis=1)
    data = data.loc[mask].fillna(0.0).reset_index(drop=True)
    return data

def select_nbrs_with_sum(i : int, 
                         cost : np.ndarray, 
                         max_share : float, 
                         shares : dict, 
                         used : list[int]) -> list[int]:
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
    x = np.argsort(cost)
    value = 0
    nbrs = []
    for i in x:
        if i in used:
            continue
        value += shares[i]
        nbrs.append(i)
        if value>=max_share:
            break
    return nbrs

def get_clusters_for_sales_man(num_sales_man : int, 
                               population : gpd.GeoDataFrame, 
                               places : gpd.GeoDataFrame,
                               weights : gpd.GeoDataFrame,
                               bounding_box : list[tuple[float, float]], 
                               distance_limit : float = 2.5,
                               zoom_level : int = 5) -> gpd.GeoDataFrame:

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
    population = get_population_by_zoom_in_bounding_box(population_data=population, 
                                                        zoom_level=zoom_level,
                                                        bounding_box=bounding_box)

    places = get_places_data(places_data=places, 
                            bounding_box=bounding_box).assign(longitude=lambda x: x.geometry.x,
                                                                latitude=lambda x: x.geometry.y)
    if weights is not None:
        weights = get_income_by_zoom_in_bounding_box(income_data=weights,
                                                     zoom_level=zoom_level,
                                                     bounding_box=bounding_box)

    
    places = places.loc[places.geometry.drop_duplicates().index]
    
    origins = population[["geometry", "longitude", "latitude", "population"]].reset_index(drop=True)
    destinations = places[["geometry", "longitude", "latitude"]].reset_index(drop=True)
    
    grided_data = get_grids_of_data(origins, destinations, weights, distance_limit)
    mask = (grided_data.number_of_potential_customers>0)
    masked_grided_data = grided_data[mask].reset_index(drop=True)
    
    nbrs = masked_grided_data.geometry.map(shapely.centroid).to_frame().assign(longitude=lambda x: x.geometry.x, 
                                                                               latitude=lambda x: x.geometry.y)
    matrix = haversine(nbrs.latitude.values, 
                       nbrs.longitude.values,
                       nbrs.latitude.values,
                       nbrs.longitude.values)

    equitable_share = masked_grided_data["number_of_potential_customers"].sum().item()/num_sales_man

    used = []
    groups = {i:[] for i in range(num_sales_man)}

    j = 0
    for i in range(masked_grided_data.shape[0]):
        if i in used:
            continue
        else:
            nbrs = select_nbrs_with_sum(i, matrix[i], equitable_share, masked_grided_data["number_of_potential_customers"].values, used)
            groups[j].extend(nbrs)
            used.extend(nbrs)
            j += 1

        if j >= num_sales_man:
            break

    def return_group_number(index : int) -> int:
        """
        Returns back the class/group index for each grid cell based in the `groups` dict
        `groups` is the dict created in the `get_clusters_for_sales_man`
        `index`is the index of the gridcell in the `masked_grided_data`
        """
        for k, v in groups.items():
            if index in v:
                return k
            
    
    masked_grided_data = masked_grided_data.assign(group = lambda x: x.index)
    masked_grided_data["group"] = masked_grided_data["group"].map(return_group_number)
    return  masked_grided_data

def plot_results(grided_data : gpd.GeoDataFrame, 
                 n_cols :int, 
                 n_rows : int, 
                 colors : list[str], 
                 alpha : float  = 0.8, 
                 show_legends : bool = True, 
                 edge_color : str = "white", 
                 show_title : bool = True,
                 log_output : bool = True,
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
    """
    grid = grided_data.copy(deep=True)

    single_fig_width = 8
    single_fig_height = 8
    fig = plt.figure(figsize=(single_fig_width*n_cols + n_cols, single_fig_height*n_rows + n_rows))

    for i,column in enumerate(grid.columns[1:], 1):
      ax = plt.subplot(n_rows,n_cols,i)
      grid[f"log_{column}"] = np.log1p(grid[column])
      vmax = grid[f"log_{column}"].quantile(0.95) if log_output else grid[column].max()
      vmin = grid[f"log_{column}"].quantile(0.05) if log_output else grid[column].min()
      grid.set_crs(epsg=4326, inplace=True)
      grid.to_crs(epsg=3857).plot(
                column=f"log_{column}" if log_output else column,
                legend=show_legends,
                cmap=colors[i-1],
                edgecolor=edge_color,
                linewidth=0.1,
                vmin=vmin, vmax=vmax,
                alpha=alpha,
                ax=ax
            )
      ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
      ax.axis("off")
      if show_title:
        ax.set_title(f"{column} per Grid Cell", fontsize=14)
    plt.show()