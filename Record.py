import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage
from io import BytesIO
import pandas as pd

st.title("今日の弁財天")

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = storage.Client(credentials=credentials)


def read_file(bucket_name, file_path):
    bucket = client.bucket(bucket_name)
    content = bucket.blob(file_path).download_as_bytes()
    return content


bucket_name = "custom-match-history"

# player_dict = {}
# player_df = []
# blobs = client.list_blobs(bucket_name)
# for blob in blobs:
#     file_path = blob.name

#     content = read_file(bucket_name, file_path)

#     df = pd.read_csv(BytesIO(content))
#     df["cs"] = df["minionsKilled"] + df["neutralMinionsKilled"]

#     for column_name in df:
#         if column_name == "player":

