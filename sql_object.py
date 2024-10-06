
from dataclasses import dataclass

@dataclass
class SqlObject:
    insert_user_profile_query: str = """  INSERT INTO user_data
      (user_id, user_name, email, prdcer_dataset, prdcer_lyrs, prdcer_ctlgs, draft_ctlgs)
            VALUES ($1, $2, $3, $4, $5, $6, $7);
            """
    update_user_profile_query: str = """  
    UPDATE user_data SET user_name = $2, 
        email = $3, 
        prdcer_dataset = $4, 
        prdcer_lyrs = $5, 
        prdcer_ctlgs = $6, 
        draft_ctlgs = $7 
    WHERE user_id = $1;
        """
    load_user_profile_query: str = """SELECT * FROM user_data WHERE user_id = $1;"""

    fetch_user_layers_query: str = """SELECT prdcer_lyrs FROM user_data WHERE user_id = $1;"""

    fetch_user_ctlg_query:str = """SELECT prdcer_ctlgs FROM user_data WHERE user_id = $1;"""
