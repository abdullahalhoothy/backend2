from backend_common.database import Database


# teams functions
async def create_team(team_name: str, owner_id: str) -> dict:
    sql = "INSERT INTO teams (team_name, owner_id) VALUES ($1, $2) RETURNING *"
    team = await Database.fetchrow(sql, team_name, owner_id)
    return team


async def add_user_to_team(team_id: str, user_id: str) -> dict:
    sql = "INSERT INTO team_members (team_id, user_id) VALUES ($1, $2) RETURNING *"
    team_member = await Database.fetchrow(sql, team_id, user_id)
    return team_member


async def remove_user_from_team(team_id: str, user_id: str) -> dict:
    sql = "DELETE FROM team_members WHERE team_id = $1 AND user_id = $2"
    await Database.execute(sql, team_id, user_id)
    return {"message": "User removed from team"}


async def delete_team(team_id: str) -> dict:
    sql = "DELETE FROM teams WHERE team_id = $1"
    await Database.execute(sql, team_id)
    return {"message": "Team deleted"}


async def list_teams() -> dict:
    sql = "SELECT * FROM teams"
    teams = await Database.fetch(sql)
    return teams
