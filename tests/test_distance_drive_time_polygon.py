import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_distance_drive_time_polygon(async_client, res_route_info , req_route_info):
    with(patch("data_fetcher.calculate_distance_traffic_route" , new_callable=AsyncMock) as get_route_info):
        get_route_info.return_value = res_route_info
        response = await async_client.post("/fastapi/distance_drive_time_polygon" , json=req_route_info)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_distance_drive_time_polygon_noroute(async_client, res_route_info_duplicate , req_route_info):
    with(patch("data_fetcher.calculate_distance_traffic_route" , new_callable=AsyncMock) as get_route_info):
        get_route_info.return_value = res_route_info_duplicate
        response = await async_client.post("/fastapi/distance_drive_time_polygon" , json=req_route_info)
        assert response.status_code == 400
