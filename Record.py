import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage
from io import BytesIO
import pandas as pd
import trueskill
import itertools
import math


def win_probability(team1, team2, env=None):
    env = env if env else trueskill.global_env()
    delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma = sum(r.sigma**2 for r in itertools.chain(team1, team2))
    size = len(team1) + len(team2)
    denom = math.sqrt(size * (env.beta * env.beta) + sum_sigma)
    return env.cdf(delta_mu / denom)


st.set_page_config(
    page_title="PlinCustom",
    page_icon="garen.jpeg",
    layout="wide",
    initial_sidebar_state="expanded",
)

mu = 25.0
sigma = mu / 3.0
beta = sigma / 1.5
tau = sigma / 100.0
draw_probability = 0.0
backend = None

env = trueskill.TrueSkill(mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=draw_probability, backend=backend)

env.make_as_global()
rate_dict = {}

# Create API client.
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
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
    rating=[0, 0, 0, 0, 0, 0],
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
df_player_dict = {}
df_champion_dict = {}
df_set_dict = {}

blobs = client.list_blobs(bucket_name)
for blob in reversed(list(blobs)):
    file_path = blob.name

    content = read_file(bucket_name, file_path)

    df = pd.read_csv(BytesIO(content))
    df["cs"] = df["minionsKilled"] + df["neutralMinionsKilled"]

    team1 = {}
    team2 = {}
    for data in df.itertuples():
        if data.player in name_dict:
            player_name = name_dict[data.player]
        else:
            player_name = data.player
        if player_name not in df_player_dict:
            df_player_dict[player_name] = df_personal.copy()
            rate_dict[player_name] = env.create_rating()
        if data.team == 100:
            team1[player_name] = rate_dict[player_name]
        else:
            team2[player_name] = rate_dict[player_name]
    wp = win_probability(team1.values(), team2.values(), env=env)

    team1, team2, = env.rate(
        (
            team1,
            team2,
        ),
        ranks=(
            0 + (data.win == "Win"),
            1 - (data.win == "Win"),
        ),
    )
    for r_key in team1.keys():
        rate_dict[r_key] = team1[r_key]
    for r_key in team2.keys():
        rate_dict[r_key] = team2[r_key]

    for data in df.itertuples():
        if data.player in name_dict:
            player_name = name_dict[data.player]
        else:
            player_name = data.player
        champion_name = data.skin
        if champion_name not in df_champion_dict:
            df_champion_dict[champion_name] = df_personal.copy()
        if (player_name, champion_name) not in df_set_dict:
            df_set_dict[(player_name, champion_name)] = df_personal.copy()

        # 全データ集計
        df_player_dict[player_name]["match_count"]["all"] += 1
        df_player_dict[player_name]["win_count"]["all"] += 1 if data.win == "Win" else 0
        df_player_dict[player_name]["kill"]["all"] += data.championsKilled
        df_player_dict[player_name]["death"]["all"] += data.numDeaths
        df_player_dict[player_name]["assist"]["all"] += data.assists
        df_player_dict[player_name]["cs"]["all"] += data.cs
        df_player_dict[player_name]["gold"]["all"] += data.goldEarned
        df_player_dict[player_name]["c_ward"]["all"] += data.visionWardsBoughtInGame
        df_player_dict[player_name]["rating"]["all"] = rate_dict[player_name].mu
        df_champion_dict[champion_name]["match_count"]["all"] += 1
        df_champion_dict[champion_name]["win_count"]["all"] += 1 if data.win == "Win" else 0
        df_champion_dict[champion_name]["kill"]["all"] += data.championsKilled
        df_champion_dict[champion_name]["death"]["all"] += data.numDeaths
        df_champion_dict[champion_name]["assist"]["all"] += data.assists
        df_champion_dict[champion_name]["cs"]["all"] += data.cs
        df_champion_dict[champion_name]["gold"]["all"] += data.goldEarned
        df_champion_dict[champion_name]["c_ward"]["all"] += data.visionWardsBoughtInGame
        df_set_dict[(player_name, champion_name)]["match_count"]["all"] += 1
        df_set_dict[(player_name, champion_name)]["win_count"]["all"] += 1 if data.win == "Win" else 0
        df_set_dict[(player_name, champion_name)]["kill"]["all"] += data.championsKilled
        df_set_dict[(player_name, champion_name)]["death"]["all"] += data.numDeaths
        df_set_dict[(player_name, champion_name)]["assist"]["all"] += data.assists
        df_set_dict[(player_name, champion_name)]["cs"]["all"] += data.cs
        df_set_dict[(player_name, champion_name)]["gold"]["all"] += data.goldEarned
        df_set_dict[(player_name, champion_name)]["c_ward"]["all"] += data.visionWardsBoughtInGame

        # ポジション毎データ集計
        df_player_dict[player_name]["match_count"][position_dict[data.individualPosition]] += 1
        df_player_dict[player_name]["win_count"][position_dict[data.individualPosition]] += (
            1 if data.win == "Win" else 0
        )
        df_player_dict[player_name]["kill"][position_dict[data.individualPosition]] += data.championsKilled
        df_player_dict[player_name]["death"][position_dict[data.individualPosition]] += data.numDeaths
        df_player_dict[player_name]["assist"][position_dict[data.individualPosition]] += data.assists
        df_player_dict[player_name]["cs"][position_dict[data.individualPosition]] += data.cs
        df_player_dict[player_name]["gold"][position_dict[data.individualPosition]] += data.goldEarned
        df_player_dict[player_name]["c_ward"][position_dict[data.individualPosition]] += data.visionWardsBoughtInGame
        df_champion_dict[champion_name]["match_count"][position_dict[data.individualPosition]] += 1
        df_champion_dict[champion_name]["win_count"][position_dict[data.individualPosition]] += (
            1 if data.win == "Win" else 0
        )
        df_champion_dict[champion_name]["kill"][position_dict[data.individualPosition]] += data.championsKilled
        df_champion_dict[champion_name]["death"][position_dict[data.individualPosition]] += data.numDeaths
        df_champion_dict[champion_name]["assist"][position_dict[data.individualPosition]] += data.assists
        df_champion_dict[champion_name]["cs"][position_dict[data.individualPosition]] += data.cs
        df_champion_dict[champion_name]["gold"][position_dict[data.individualPosition]] += data.goldEarned
        df_champion_dict[champion_name]["c_ward"][
            position_dict[data.individualPosition]
        ] += data.visionWardsBoughtInGame
        df_set_dict[(player_name, champion_name)]["match_count"][position_dict[data.individualPosition]] += 1
        df_set_dict[(player_name, champion_name)]["win_count"][position_dict[data.individualPosition]] += (
            1 if data.win == "Win" else 0
        )
        df_set_dict[(player_name, champion_name)]["kill"][
            position_dict[data.individualPosition]
        ] += data.championsKilled
        df_set_dict[(player_name, champion_name)]["death"][position_dict[data.individualPosition]] += data.numDeaths
        df_set_dict[(player_name, champion_name)]["assist"][position_dict[data.individualPosition]] += data.assists
        df_set_dict[(player_name, champion_name)]["cs"][position_dict[data.individualPosition]] += data.cs
        df_set_dict[(player_name, champion_name)]["gold"][position_dict[data.individualPosition]] += data.goldEarned
        df_set_dict[(player_name, champion_name)]["c_ward"][
            position_dict[data.individualPosition]
        ] += data.visionWardsBoughtInGame

# データ正規化
for player_name in df_player_dict.keys():
    df_player_dict[player_name]["win_rate"] = (
        df_player_dict[player_name]["win_count"] / df_player_dict[player_name]["match_count"]
    )
    df_player_dict[player_name]["kill"] /= df_player_dict[player_name]["match_count"]
    df_player_dict[player_name]["death"] /= df_player_dict[player_name]["match_count"]
    df_player_dict[player_name]["assist"] /= df_player_dict[player_name]["match_count"]
    df_player_dict[player_name]["kda"] = (
        df_player_dict[player_name]["kill"] + df_player_dict[player_name]["assist"]
    ) / df_player_dict[player_name]["death"]
    df_player_dict[player_name]["cs"] /= df_player_dict[player_name]["match_count"]
    df_player_dict[player_name]["gold"] /= df_player_dict[player_name]["match_count"]
    df_player_dict[player_name]["c_ward"] /= df_player_dict[player_name]["match_count"]
for champion_name in df_champion_dict.keys():
    df_champion_dict[champion_name]["win_rate"] = (
        df_champion_dict[champion_name]["win_count"] / df_champion_dict[champion_name]["match_count"]
    )
    df_champion_dict[champion_name]["kill"] /= df_champion_dict[champion_name]["match_count"]
    df_champion_dict[champion_name]["death"] /= df_champion_dict[champion_name]["match_count"]
    df_champion_dict[champion_name]["assist"] /= df_champion_dict[champion_name]["match_count"]
    df_champion_dict[champion_name]["kda"] = (
        df_champion_dict[champion_name]["kill"] + df_champion_dict[champion_name]["assist"]
    ) / df_champion_dict[champion_name]["death"]
    df_champion_dict[champion_name]["cs"] /= df_champion_dict[champion_name]["match_count"]
    df_champion_dict[champion_name]["gold"] /= df_champion_dict[champion_name]["match_count"]
    df_champion_dict[champion_name]["c_ward"] /= df_champion_dict[champion_name]["match_count"]
for (player_name, champion_name) in df_set_dict.keys():
    df_set_dict[(player_name, champion_name)]["win_rate"] = (
        df_set_dict[(player_name, champion_name)]["win_count"]
        / df_set_dict[(player_name, champion_name)]["match_count"]
    )
    df_set_dict[(player_name, champion_name)]["kill"] /= df_set_dict[(player_name, champion_name)]["match_count"]
    df_set_dict[(player_name, champion_name)]["death"] /= df_set_dict[(player_name, champion_name)]["match_count"]
    df_set_dict[(player_name, champion_name)]["assist"] /= df_set_dict[(player_name, champion_name)]["match_count"]
    df_set_dict[(player_name, champion_name)]["kda"] = (
        df_set_dict[(player_name, champion_name)]["kill"] + df_set_dict[(player_name, champion_name)]["assist"]
    ) / df_set_dict[(player_name, champion_name)]["death"]
    df_set_dict[(player_name, champion_name)]["cs"] /= df_set_dict[(player_name, champion_name)]["match_count"]
    df_set_dict[(player_name, champion_name)]["gold"] /= df_set_dict[(player_name, champion_name)]["match_count"]
    df_set_dict[(player_name, champion_name)]["c_ward"] /= df_set_dict[(player_name, champion_name)]["match_count"]

# 全体集計用データ作成
df_all_player = pd.DataFrame(index=[], columns=df_player_dict[next(iter(df_player_dict))].columns)
df_all_dict = {}
for player in df_player_dict.keys():
    for position in df_player_dict[player].iterrows():
        if position[0] not in df_all_dict:
            df_all_dict[position[0]] = df_all_player.copy()
        df_tmp = pd.DataFrame([position[1]], index={player})
        df_all_dict[position[0]] = pd.concat([df_all_dict[position[0]], df_tmp])

df_all_champion = pd.DataFrame(index=[], columns=df_champion_dict[next(iter(df_champion_dict))].columns)
df_all_champion_dict = {}
for champion in df_champion_dict.keys():
    for position in df_champion_dict[champion].iterrows():
        if position[0] not in df_all_champion_dict:
            df_all_champion_dict[position[0]] = df_all_champion.copy()
        df_tmp = pd.DataFrame([position[1]], index={champion})
        df_all_champion_dict[position[0]] = pd.concat([df_all_champion_dict[position[0]], df_tmp])

df_all_set = pd.DataFrame(index=[], columns=df_set_dict[next(iter(df_set_dict))].columns)
df_all_set_dict = {}
for (player, champion) in df_set_dict.keys():
    if player not in df_all_set_dict:
        df_all_set_dict[player] = df_all_set.copy()
    df_all_set_dict[player] = pd.concat(
        [df_all_set_dict[player], df_set_dict[(player, champion)][:1].rename(index={"all": champion})]
    )

for keys in df_all_dict.keys():
    df_all_dict[keys] = df_all_dict[keys].sort_values("rating", ascending=False)
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
                "c_ward": "{:.1f}",
                "rating": "{:.1f}",
            },
            na_rep="-",
        )
        .highlight_max(axis=0, subset="win_rate")
        .highlight_max(axis=0, subset="kill")
        .highlight_min(axis=0, subset="death")
        .highlight_max(axis=0, subset="assist")
        .highlight_max(axis=0, subset="kda")
        .highlight_max(axis=0, subset="cs")
        .highlight_max(axis=0, subset="gold")
        .highlight_max(axis=0, subset="rating")
    )
for keys in df_all_champion_dict.keys():
    df_all_champion_dict[keys] = df_all_champion_dict[keys].sort_values("match_count", ascending=False)
    df_all_champion_dict[keys] = (
        df_all_champion_dict[keys]
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
                "c_ward": "{:.1f}",
                "rating": "{:.1f}",
            },
            na_rep="-",
        )
        .highlight_max(axis=0, subset="win_rate")
        .highlight_max(axis=0, subset="kill")
        .highlight_min(axis=0, subset="death")
        .highlight_max(axis=0, subset="assist")
        .highlight_max(axis=0, subset="kda")
        .highlight_max(axis=0, subset="cs")
        .highlight_max(axis=0, subset="gold")
    )
for keys in df_all_set_dict.keys():
    df_all_set_dict[keys] = df_all_set_dict[keys].sort_values("match_count", ascending=False)
    df_all_set_dict[keys] = (
        df_all_set_dict[keys]
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
                "c_ward": "{:.1f}",
                "rating": "{:.1f}",
            },
            na_rep="-",
        )
        .highlight_max(axis=0, subset="win_rate")
        .highlight_max(axis=0, subset="kill")
        .highlight_min(axis=0, subset="death")
        .highlight_max(axis=0, subset="assist")
        .highlight_max(axis=0, subset="kda")
        .highlight_max(axis=0, subset="cs")
        .highlight_max(axis=0, subset="gold")
    )

st.write("総合戦績")
option1 = st.selectbox("ポジションの選択", df_all_dict.keys())
st.dataframe(df_all_dict[option1])
st.dataframe(df_all_champion_dict[option1])

# フォーマット
for keys in df_player_dict.keys():
    df_player_dict[keys] = df_player_dict[keys].style.format(
        formatter={
            "win_rate": "{:.2f}",
            "kill": "{:.1f}",
            "death": "{:.1f}",
            "assist": "{:.1f}",
            "kda": "{:.2f}",
            "cs": "{:.0f}",
            "gold": "{:.0f}",
            "c_ward": "{:.1f}",
            "rating": "{:.1f}",
        },
        na_rep="-",
    )
for keys in df_champion_dict.keys():
    df_champion_dict[keys] = df_champion_dict[keys].style.format(
        formatter={
            "win_rate": "{:.2f}",
            "kill": "{:.1f}",
            "death": "{:.1f}",
            "assist": "{:.1f}",
            "kda": "{:.2f}",
            "cs": "{:.0f}",
            "gold": "{:.0f}",
            "c_ward": "{:.1f}",
            "rating": "{:.1f}",
        },
        na_rep="-",
    )

st.write("個人戦績")
option2 = st.selectbox("プレイヤーの選択", df_player_dict.keys())

st.dataframe(df_player_dict[option2])
st.dataframe(df_all_set_dict[option2])

st.write("勝率予測")
st.write("チーム1")

column1, column2, column3, column4, column5 = st.columns(5)
p0 = column1.selectbox("1", df_player_dict.keys())
p1 = column2.selectbox("2", df_player_dict.keys())
p2 = column3.selectbox("3", df_player_dict.keys())
p3 = column4.selectbox("4", df_player_dict.keys())
p4 = column5.selectbox("5", df_player_dict.keys())
st.write("チーム2")
column6, column7, column8, column9, column10 = st.columns(5)
p5 = column6.selectbox("6", df_player_dict.keys())
p6 = column7.selectbox("7", df_player_dict.keys())
p7 = column8.selectbox("8", df_player_dict.keys())
p8 = column9.selectbox("9", df_player_dict.keys())
p9 = column10.selectbox("10", df_player_dict.keys())
t1 = [rate_dict[p0], rate_dict[p1], rate_dict[p2], rate_dict[p3], rate_dict[p4]]
t2 = [rate_dict[p5], rate_dict[p6], rate_dict[p7], rate_dict[p8], rate_dict[p9]]
wp = win_probability(t1, t2, env=env)

st.write(f"チーム1の勝率: {wp*100.0:.2f}%")
