import json
import firebase_admin
from firebase_admin import credentials, auth, firestore
from backend_common.common_config import CommonApiConfig
from backend_common.dtypes.auth_dtypes import UserProfileSettings
import asyncio
from typing import Dict, Any
from rich import print_json

# Please double check the updated user profile data before writing to firestore
WRITE_TO_FIRESTORE = False 


def get_default_settings() -> Dict[str, Any]:
    temp_settings = UserProfileSettings(user_id="temp")
    settings = {
        "settings": temp_settings.model_dump(exclude={'user_id'})
    }
    return settings

async def update_all_user_profiles():
    if not firebase_admin._apps:
        conf = CommonApiConfig.get_common_conf()
        cred = credentials.Certificate(conf.firebase_sp_path)
        firebase_admin.initialize_app(cred)

    db = firestore.Client.from_service_account_json(conf.firebase_sp_path)
    
    try:
        users = auth.list_users().iterate_all()
        
        default_settings = get_default_settings()
        print("\nDefault Settings Template:")
        print_json(json.dumps(default_settings))
        
        for user in users:
            try:
                user_ref = db.collection('all_user_profiles').document(user.uid)
                
                profile = user_ref.get()
                if not profile.exists:
                    continue

                print(f"{'='*80}")
                print(f"User: {user.email}")
                print(f"{'='*80}")

                current_data = profile.to_dict()
                
                print("Current Profile Data:")
                print_json(json.dumps(current_data))
                
                updated_data = current_data.copy()
                if 'settings' not in updated_data:
                    updated_data['settings'] = {}
                
                for key, value in default_settings['settings'].items():
                    if key not in updated_data['settings']:
                        updated_data['settings'][key] = value
                
                print("\nUpdated Profile Data:")
                print_json(json.dumps(updated_data))
                print()
                
                if WRITE_TO_FIRESTORE:
                    user_ref.set(updated_data, merge=True)
                
            except Exception as e:
                print(f"Error updating user {user.email}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error listing users: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(update_all_user_profiles()) 