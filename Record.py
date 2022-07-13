import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage
from io import BytesIO
import pandas as pd

# st.title("個人戦績")

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

name_dict = {"弁天町5520001": "弁財天", "弁天魚のムニエル": "弁財天", "ナウナヤングマン": "ヤングマン"}

match_dict = dict(
    match_count=[0, 0, 0, 0, 0, 0],
    win_count=[0, 0, 0, 0, 0, 0],
    win_rate=[0, 0, 0, 0, 0, 0],
    kill=[0, 0, 0, 0, 0, 0],
    death=[0, 0, 0, 0, 0, 0],
    assist=[0, 0, 0, 0, 0, 0],
    kda=[0, 0, 0, 0, 0, 0],
    cs=[0, 0, 0, 0, 0, 0],
    gold=[0, 0, 0, 0, 0, 0],
    c_ward=[0, 0, 0, 0, 0, 0],
)
position_dict = {
    "TOP": "top",
    "JUNGLE": "jg",
    "MIDDLE": "mid",
    "BOTTOM": "bot",
    "UTILITY": "supp",
}
position_idx = ["all", "top", "jg", "mid", "bot", "supp"]
df_personal = pd.DataFrame(data=match_dict, index=position_idx)
df_dict = {}

blobs = client.list_blobs(bucket_name)
for blob in reversed(list(blobs)):
    file_path = blob.name

    content = read_file(bucket_name, file_path)

    df = pd.read_csv(BytesIO(content))
    df["cs"] = df["minionsKilled"] + df["neutralMinionsKilled"]

    for data in df.itertuples():
        if data.player in name_dict:
            name = name_dict[data.player]
        else:
            name = data.player
        if name not in df_dict:
            df_dict[name] = df_personal.copy()

        # 全データ集計
        df_dict[name]["match_count"]["all"] += 1
        df_dict[name]["win_count"]["all"] += 1 if data.win == "Win" else 0
        df_dict[name]["kill"]["all"] += data.championsKilled
        df_dict[name]["death"]["all"] += data.numDeaths
        df_dict[name]["assist"]["all"] += data.assists
        df_dict[name]["cs"]["all"] += data.cs
        df_dict[name]["gold"]["all"] += data.goldEarned
        df_dict[name]["c_ward"]["all"] += data.visionWardsBoughtInGame

        # ポジション毎データ集計
        df_dict[name]["match_count"][position_dict[data.individualPosition]] += 1
        df_dict[name]["win_count"][position_dict[data.individualPosition]] += (
            1 if data.win == "Win" else 0
        )
        df_dict[name]["kill"][
            position_dict[data.individualPosition]
        ] += data.championsKilled
        df_dict[name]["death"][position_dict[data.individualPosition]] += data.numDeaths
        df_dict[name]["assist"][position_dict[data.individualPosition]] += data.assists
        df_dict[name]["cs"][position_dict[data.individualPosition]] += data.cs
        df_dict[name]["gold"][position_dict[data.individualPosition]] += data.goldEarned
        df_dict[name]["c_ward"][
            position_dict[data.individualPosition]
        ] += data.visionWardsBoughtInGame

# データ正規化
for name in df_dict.keys():
    df_dict[name]["win_rate"] = (
        df_dict[name]["win_count"] / df_dict[name]["match_count"]
    )
    df_dict[name]["kill"] /= df_dict[name]["match_count"]
    df_dict[name]["death"] /= df_dict[name]["match_count"]
    df_dict[name]["assist"] /= df_dict[name]["match_count"]
    df_dict[name]["kda"] = (df_dict[name]["kill"] + df_dict[name]["assist"]) / df_dict[
        name
    ]["death"]
    df_dict[name]["cs"] /= df_dict[name]["match_count"]
    df_dict[name]["gold"] /= df_dict[name]["match_count"]
    df_dict[name]["c_ward"] /= df_dict[name]["match_count"]

# 全体集計用データ作成
df_all_player = pd.DataFrame(index=[], columns=df_dict[next(iter(df_dict))].columns)
df_all_dict = {}
for player in df_dict.keys():
    for position in df_dict[player].iterrows():
        if position[0] not in df_all_dict:
            df_all_dict[position[0]] = df_all_player.copy()
        df_tmp = pd.DataFrame([position[1]], index={player})
        df_all_dict[position[0]] = pd.concat([df_all_dict[position[0]], df_tmp])

for keys in df_all_dict.keys():
    df_all_dict[keys] = df_all_dict[keys].sort_values("win_rate", ascending=False)
    df_all_dict[keys] = (
        df_all_dict[keys]
        .style.format(
            formatter={
                "match_count": "{:.0f}",
                "win_count": "{:.0f}",
                "win_rate": "{:.2f}",
                "kill": "{:.1f}",
                "death": "{:.1f}",
                "assist": "{:.1f}",
                "kda": "{:.2f}",
                "cs": "{:.0f}",
                "gold": "{:.0f}",
            }
        )
        .highlight_max(axis=0, subset="win_rate")
        .highlight_max(axis=0, subset="kill")
        .highlight_min(axis=0, subset="death")
        .highlight_max(axis=0, subset="assist")
        .highlight_max(axis=0, subset="kda")
        .highlight_max(axis=0, subset="cs")
        .highlight_max(axis=0, subset="gold")
        .highlight_max(axis=0, subset="c_ward")
    )

st.write("総合戦績")
option1 = st.selectbox("ポジションの選択", df_all_dict.keys())
st.dataframe(df_all_dict[option1])

# フォーマット
for keys in df_dict.keys():
    df_dict[keys] = df_dict[keys].style.format(
        formatter={
            "win_rate": "{:.2f}",
            "kill": "{:.1f}",
            "death": "{:.1f}",
            "assist": "{:.1f}",
            "kda": "{:.2f}",
            "cs": "{:.0f}",
            "gold": "{:.0f}",
            "c_ward": "{:.1f}",
        }
    )

st.write("個人戦績")
option2 = st.selectbox("プレイヤーの選択", df_dict.keys())

st.table(df_dict[option2])
