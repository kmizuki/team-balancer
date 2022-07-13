import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage
from io import BytesIO
import pandas as pd

st.set_page_config(
    page_title="PlinCustom",
    page_icon="garen.jpeg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# st.title("試合記録")

# Create API client.
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = storage.Client(credentials=credentials)


def read_file(bucket_name, file_path):
    bucket = client.bucket(bucket_name)
    content = bucket.blob(file_path).download_as_bytes()
    return content


bucket_name = "custom-match-history"

blobs = client.list_blobs(bucket_name)
for blob in reversed(list(blobs)):
    st.write(blob.name)
    file_path = blob.name

    content = read_file(bucket_name, file_path)

    df = pd.read_csv(BytesIO(content))
    df = df.set_index("player", drop=False)
    df = df.rename(
        columns={
            "championsKilled": "kill",
            "assists": "assist",
            "goldEarned": "gold",
            "individualPosition": "position",
            "numDeaths": "death",
            "skin": "champion",
            "team": "side",
            "visionWardsBoughtInGame": "c_ward",
        }
    )
    df.loc[df["death"] == 0, "kda"] = df["kill"] + df["assist"]
    df.loc[~(df["death"] == 0), "kda"] = (df["kill"] + df["assist"]) / df["death"]
    df["cs"] = df["minionsKilled"] + df["neutralMinionsKilled"]
    df1 = df[0:5]
    df2 = df[5:10]
    pos_order = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    df1["order"] = df1["position"].apply(lambda x: pos_order.index(x) if x in pos_order else -1)
    df2["order"] = df2["position"].apply(lambda x: pos_order.index(x) if x in pos_order else -1)
    df1 = df1.sort_values("order")
    df2 = df2.sort_values("order")
    drop_col = ["player", "order", "minionsKilled", "neutralMinionsKilled", "position"]
    df1 = df1.drop(drop_col, axis=1)
    df2 = df2.drop(drop_col, axis=1)
    columns_order = [
        "champion",
        "kill",
        "death",
        "assist",
        "kda",
        "cs",
        "gold",
        "c_ward",
        "win",
        "side",
    ]
    df1 = df1.reindex(columns=columns_order)
    df2 = df2.reindex(columns=columns_order)
    df1 = df1.style.format(formatter={"kda": "{:.2f}"})
    df2 = df2.style.format(formatter={"kda": "{:.2f}"})
    st.table(df1)
    st.table(df2)
