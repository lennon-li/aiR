import os
import time
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "global"

# 1. Create Data Store
def create_data_store(data_store_id):
    client = discoveryengine.DataStoreServiceClient()
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
    
    data_store = discoveryengine.DataStore(
        display_name="aiR Curated R Docs",
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
    )
    
    request = discoveryengine.CreateDataStoreRequest(
        parent=parent,
        data_store=data_store,
        data_store_id=data_store_id,
    )
    
    try:
        operation = client.create_data_store(request=request)
        print(f"Creating Data Store {data_store_id}...")
        result = operation.result()
        print(f"Data Store created: {result.name}")
        return result
    except Exception as e:
        if "already exists" in str(e):
            print(f"Data Store {data_store_id} already exists.")
            return True
        print(f"Data Store error: {e}")
        return False

# 2. Create Search App
def create_app(app_id, data_store_id):
    # Search apps are created via ControlServiceClient in v1beta
    client = discoveryengine.ControlServiceClient()
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
    
    # Actually, Engine is the term for App in the API
    # But often Search Apps are created via Console or EngineService
    # Let's try EngineServiceClient
    try:
        engine_client = discoveryengine.EngineServiceClient()
        engine = discoveryengine.Engine(
            display_name="aiR Curated Search App",
            industry_vertical=discoveryengine.IndustryVertical.GENERIC,
            solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
            data_store_ids=[data_store_id],
        )
        request = discoveryengine.CreateEngineRequest(
            parent=parent,
            engine=engine,
            engine_id=app_id,
        )
        operation = engine_client.create_engine(request=request)
        print(f"Creating Search App {app_id}...")
        result = operation.result()
        print(f"Search App created: {result.name}")
        return True
    except Exception as e:
        if "already exists" in str(e):
            print(f"Search App {app_id} already exists.")
            return True
        print(f"Search App error: {e}")
        return False

# 3. Import Documents
def import_documents(data_store_id, gcs_uri):
    client = discoveryengine.DocumentServiceClient()
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{data_store_id}/branches/default_branch"
    
    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[gcs_uri],
            data_schema="content"
        ),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    
    try:
        operation = client.import_documents(request=request)
        print(f"Importing documents from {gcs_uri}...")
        print("Import operation started.")
        return operation
    except Exception as e:
        print(f"Import error: {e}")
        return None

DATA_STORE_ID = "r-docs-curated"
APP_ID = "air-docs-curated"
GCS_URI = "gs://air-mvp-lennon-li-2026-rdocs/**"

if create_data_store(DATA_STORE_ID):
    print("Waiting for data store propagation...")
    time.sleep(15)
    create_app(APP_ID, DATA_STORE_ID)
    import_documents(DATA_STORE_ID, GCS_URI)
