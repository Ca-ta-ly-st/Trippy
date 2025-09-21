import os
from datetime import datetime
from langchain_openai import AzureChatOpenAI
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv
load_dotenv()

class LLM:
    _access_token = None
    _expires_on = None
    _instance = None
    def __init__(self, base, deployment, version, callback = None, name = None):
        if not LLM._access_token or self.is_token_expired():
            self.update_access_token()
        os.environ["AZURE_OPENAI_API_KEY"] = LLM._access_token
        os.environ["AZURE_OPENAI_ENDPOINT"] = base
        self._name = name
        retries = 0
        max_retries = 5
        err = True
        while err and retries < max_retries:
            try:
                self.client = AzureChatOpenAI(
                    name=self._name,
                    azure_deployment=deployment,
                    openai_api_version=version,
                    callbacks=callback
                )
                self.conversation = []
                err = False
            except Exception as e:
                print(f"Error initializing Azure client: {e}")
                retries += 1
        
    @classmethod
    def is_token_expired(cls):
        if not cls._expires_on:
            return True
        return datetime.now() > datetime.fromtimestamp(int(cls._expires_on))
    
    @classmethod
    def get_access_token(cls):
        client_id = os.getenv("client_id")
        tenant_id = os.getenv("tenant_id")
        client_secret = os.getenv("client_secret")

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        access_token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return access_token
    
    @classmethod
    def update_access_token(cls):
        retries = 0
        max_retries = 5
        err = True
        while err and retries < max_retries:
            try:
                access_token = cls.get_access_token()
                err = False
            except:
                print("Error getting access token, retrying...")
                retries += 1
        cls._access_token = access_token.token
        cls._expires_on = str(access_token.expires_on - 300)
    # def __new__(cls):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #         retries = 0
    #         err = True
    #         while err and retries < 5:
    #             try:
    #                 cls._instance.client = cls._instance.create_client()
    #                 err = False
    #             except Exception as e:
    #                 print(f"Error initializing Azure client: {e}")
    #                 retries += 1
    #     return cls._instance
    
    # def create_client(self):
    #     """
    #     Creates an AzureChatOpenAI client using the access token.
    #     """
    #     print("Creating Azure client...")
    #     access_token = self.get_access_token()
    #     os.environ["AZURE_OPENAI_API_KEY"] = access_token.token
    #     os.environ["EXPIRES_ON"] = str(access_token.expires_on - 300) # 5 minutes buffer
    #     os.environ["AZURE_OPENAI_ENDPOINT"] = os.getenv("api_base_o3")
    #     print(os.environ["AZURE_OPENAI_ENDPOINT"])
    #     client = AzureChatOpenAI(
    #         azure_deployment=os.getenv("deployment_name_41"),
    #         openai_api_version=os.getenv("api_version_o3"),
    #         # temperature=0,
    #     )
    #     return client
    # def get_access_token(self):
    #     client_id = os.getenv("client_id")
    #     tenant_id = os.getenv("tenant_id")
    #     client_secret = os.getenv("client_secret")

    #     credential = ClientSecretCredential(
    #         tenant_id=tenant_id,
    #         client_id=client_id,
    #         client_secret=client_secret
    #     )
    #     access_token = credential.get_token("https://cognitiveservices.azure.com/.default")
    #     return access_token
    
    def inference(self, prompt) -> str:
        err = True
        max_retries = 5
        retries = 0
        while err and retries < max_retries:
            try:
                # Check if the access token is expired
                # current_time = datetime.now()
                # if current_time > datetime.fromtimestamp(int(os.environ["EXPIRES_ON"])):
                #     print("***************************")
                #     print("Generating new Access Token")
                #     print("***************************")
                #     self.client = self.create_client()
                if self.is_token_expired():
                    print("***************************")
                    print("Generating new Access Token")
                    print("***************************")
                    self.update_access_token()
                if isinstance(prompt, str):
                    prompt = prompt.strip()
                response = self.client.invoke(prompt, timeout = 150)
                self.conversation.append({"role": "user", "content": prompt})
                self.conversation.append({"role": "agent", "content": response.content})
                err = False
            except Exception as e:
                print(f"Error: {e}")
                print("Retrying...")
                retries += 1
        return response.content