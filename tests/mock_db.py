import copy

class MockFirestoreDB:
    def __init__(self, initial_data=None):
        """
        Initializes self.db_data.
        If initial_data is provided, it should populate self.db_data.
        """
        self.db_data = {}
        if initial_data:
            self.set_initial_data(initial_data)

    def set_initial_data(self, data: dict):
        """
        Clears self.db_data and sets it to a deep copy of the provided data.
        """
        self.db_data = copy.deepcopy(data)

    def get_document(self, collection_path: str, document_id: str) -> dict | None:
        """
        Returns a deep copy of the document if found.
        Returns None if the collection or document doesn't exist.
        """
        if collection_path in self.db_data and \
           document_id in self.db_data[collection_path]:
            return copy.deepcopy(self.db_data[collection_path][document_id])
        return None

    def update_document(self, collection_path: str, document_id: str, data_to_update: dict) -> bool:
        """
        Updates the document with data_to_update.
        Does not create if the path is invalid.
        Returns True if successful, False otherwise.
        """
        if collection_path in self.db_data and \
           document_id in self.db_data[collection_path]:
            # For simplicity, using dictionary update(). A deep merge might be needed for nested fields.
            self.db_data[collection_path][document_id].update(data_to_update)
            return True
        return False

    def add_document(self, collection_path: str, document_id: str, data: dict) -> bool:
        """
        Adds a new document to the specified collection.
        If the document already exists, it should not overwrite and return False.
        If the collection doesn't exist, it should create it.
        Returns True if successful, False otherwise.
        """
        if collection_path not in self.db_data:
            self.db_data[collection_path] = {}

        if document_id in self.db_data[collection_path]:
            return False  # Document already exists

        self.db_data[collection_path][document_id] = copy.deepcopy(data)
        return True

    def get_collection(self, collection_path: str) -> dict | None:
        """
        Returns a deep copy of the entire collection if found.
        Returns None if the collection doesn't exist.
        """
        if collection_path in self.db_data:
            return copy.deepcopy(self.db_data[collection_path])
        return None
