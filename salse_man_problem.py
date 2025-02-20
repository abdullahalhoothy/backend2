import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import geopandas as gpd
from shapely.geometry import box, Polygon
import shapely
import contextily as ctx


def define_boundary(bounding_box):
    boundary = Polygon([[p[0], p[1]] for p in bounding_box])
    return boundary

def get_population_by_zoom_in_bounding_box(population_data=None, 
                                           zoom_level=None, 
                                           bounding_box=None):
    population_data = gpd.GeoDataFrame(
          population_data, geometry=gpd.points_from_xy(population_data.longitude, 
                                                       population_data.latitude)
      )
    pop_by_zoom =  population_data.loc[population_data.zoom_level == zoom_level]
    city_boundary = define_boundary(bounding_box)
    pop_by_zoom = pop_by_zoom.loc[pop_by_zoom.within(city_boundary)]
    return pop_by_zoom
    
def get_places_data_old(places_data=None, 
                    place=None, 
                    bounding_box=None):
    places = places_data.loc[places_data.filename.str.contains(place)].response_data.map(json.loads).map(lambda x: gpd.GeoDataFrame.from_features(x["features"])).values.tolist()
    places = pd.concat(places).reset_index()
    city_boundary = define_boundary(bounding_box)
    places = places.loc[places.within(city_boundary)]
    return places

def get_places_data(places_data=None, 
                    bounding_box=None):
    places = places_data.data.map(lambda x: gpd.GeoDataFrame.from_features(x["features"])).values.tolist()
    places = pd.concat(places).reset_index()
    city_boundary = define_boundary(bounding_box)
    places = places.loc[places.within(city_boundary)]
    return places

def create_grid(population=None, 
                grid_size=None):
    
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


def haversine(lat1_array, lon1_array, lat2_array, lon2_array):
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


def get_grids_of_data(origins, destinations, distnace_limit):
    matrix = haversine(origins.latitude.values, 
                        origins.longitude.values,
                        destinations.latitude.values,
                        destinations.longitude.values)

    od_cost_matrix = {k:[] for k in range(matrix.shape[0])}

    for i in range(matrix.shape[0]):
        od = matrix[i].tolist()
        while len(od_cost_matrix[i])<matrix.shape[1]:
            if np.min(od)<distnace_limit:
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
    origins["effective_population"] = origins["population"]/origins["number_of_accessibile_markets"]

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

def select_nbrs_with_sum(i, cost, max_share, shares, used):
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

def get_clusters_for_sales_man(num_sales_man, population, places, bounding_box, distance_limit=2.5, zoom_level=5):

    population = get_population_by_zoom_in_bounding_box(population_data=population, 
                                                        zoom_level=zoom_level, 
                                                        bounding_box=bounding_box)

    places = get_places_data(places_data=places, 
                            bounding_box=bounding_box).assign(longitude=lambda x: x.geometry.x,
                                                                latitude=lambda x: x.geometry.y)
    
    places = places.loc[places.geometry.drop_duplicates().index]
    
    origins = population[["geometry", "longitude", "latitude", "population"]].reset_index(drop=True)
    destinations = places[["geometry", "longitude", "latitude"]].reset_index(drop=True)
    
    grided_data = get_grids_of_data(origins, destinations, distance_limit)
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

    def return_group_number(index):
        for k, v in groups.items():
            if index in v:
                return k
            
    
    masked_grided_data = masked_grided_data.assign(group = lambda x: x.index)
    masked_grided_data["group"] = masked_grided_data["group"].map(return_group_number)
    return  masked_grided_data

def plot_results(grided_data, n_cols, n_rows, colors, alpha=0.8, show_legends=True, edge_color="white", show_title=True):
    grid = grided_data.copy(deep=True)

    single_fig_width = 8
    single_fig_height = 8
    fig = plt.figure(figsize=(single_fig_width*n_cols + n_cols, single_fig_height*n_rows + n_rows))

    for i,column in enumerate(grid.columns[1:], 1):
      ax = plt.subplot(n_rows,n_cols,i)
      grid[f"log_{column}"] = np.log1p(grid[column])
      vmax = grid[f"log_{column}"].quantile(0.95)
      vmin = grid[f"log_{column}"].quantile(0.05)
      grid.set_crs(epsg=4326, inplace=True)
      grid.to_crs(epsg=3857).plot(
                column=f"log_{column}",
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
        ax.set_title(f"{column} per Grid Cell (Log scaled)", fontsize=14)
    plt.show()