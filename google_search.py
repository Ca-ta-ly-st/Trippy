import os
import requests
class GoogleSearch:
    def __init__(self):
        self.google_search_api_key = os.getenv("GOOGLE_SEARCH_API")
        self.google_search_engine_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.google_search_api_endpoint = os.getenv("GOOGLE_API_ENDPOINT")
        self.query_result = None

    def search(self, query):
        # print("GOOGLE SEARCH")
        params = {
            "key": self.google_search_api_key,
            "cx": self.google_search_engine_ID,
            "q": query
        }
        try:
            # print("Searching in Google...")
            response = requests.get(self.google_search_api_endpoint, params=params)
            # response.raise_for_status()
            self.query_result = response.json()
        except Exception as error:
            return error

    def get_first_link(self):
        item = ""
        try:
            if 'items' in self.query_result:
                item = self.query_result['items'][0]['link']
            return item
        except Exception as error:
            print(error)
            return ""
    
    def get_first_non_pdf_link(self):
        item = ""
        try:
            if 'items' in self.query_result:
                for item in self.query_result['items']:
                    if not item['link'].endswith(".pdf"):
                        return item["link"]
            return item
        except Exception as error:
            print(error)
            return ""