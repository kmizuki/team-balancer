import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage
from io import BytesIO
import pandas as pd
import trueskill
import itertools
import math
from PIL import Image
import random
import statistics


def win_probability(team1, team2, env=None):
    env = env if env else trueskill.global_env()
    delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma = sum(r.sigma**2 for r in itertools.chain(team1, team2))
    size = len(team1) + len(team2)
    denom = math.sqrt(size * (env.beta * env.beta) + sum_sigma)
    return env.cdf(delta_mu / denom)


def get_blobs(bucket_name, client):
    blobs = client.list_blobs(bucket_name)
    return blobs


def read_file(bucket_name, file_path, client):
    bucket = client.bucket(bucket_name)
    content = bucket.blob(file_path).download_as_bytes()
    return content


def get_dataframe(_blobs, bucket_name, _client):
    df_list = []
    for blob in _blobs:
        file_path = blob.name

        content = read_file(bucket_name, file_path, _client)

        df = pd.read_csv(BytesIO(content))
        df["cs"] = df["minionsKilled"] + df["neutralMinionsKilled"]
        df_list.append(df)
    return df_list


st.set_page_config(
    page_title="PlinCustom",
    page_icon="garen.jpeg",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.experimental_memo(ttl=600)
def get_all_record():
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = storage.Client(credentials=credentials)

    bucket_name = "custom-match-history"
    blobs = get_blobs(bucket_name, client)

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
    st.session_state.df_list = get_dataframe(blobs, bucket_name, client)
    for df in st.session_state.df_list:
        team1 = {}
        team2 = {}
        for data in df.itertuples():
            if data.player in name_dict:
                player_name = name_dict[data.player]
            else:
                player_name = data.player
            if player_name not in st.session_state.df_player_dict:
                st.session_state.df_player_dict[player_name] = df_personal.copy()
                st.session_state.rate_dict[player_name] = [st.session_state.env.create_rating()]
            if data.team == 100:
                team1[player_name] = st.session_state.rate_dict[player_name][0]
            else:
                team2[player_name] = st.session_state.rate_dict[player_name][0]

        team1, team2, = st.session_state.env.rate(
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
            st.session_state.rate_dict[r_key].insert(0, team1[r_key])
        for r_key in team2.keys():
            st.session_state.rate_dict[r_key].insert(0, team2[r_key])

        for data in df.itertuples():
            if data.player in name_dict:
                player_name = name_dict[data.player]
            else:
                player_name = data.player
            champion_name = data.skin
            if champion_name not in st.session_state.df_champion_dict:
                st.session_state.df_champion_dict[champion_name] = df_personal.copy()
            if (player_name, champion_name) not in st.session_state.df_set_dict:
                st.session_state.df_set_dict[(player_name, champion_name)] = df_personal.copy()

            # 全データ集計
            st.session_state.df_player_dict[player_name]["match_count"]["all"] += 1
            st.session_state.df_player_dict[player_name]["win_count"]["all"] += 1 if data.win == "Win" else 0
            st.session_state.df_player_dict[player_name]["kill"]["all"] += data.championsKilled
            st.session_state.df_player_dict[player_name]["death"]["all"] += data.numDeaths
            st.session_state.df_player_dict[player_name]["assist"]["all"] += data.assists
            st.session_state.df_player_dict[player_name]["cs"]["all"] += data.cs
            st.session_state.df_player_dict[player_name]["gold"]["all"] += data.goldEarned
            st.session_state.df_player_dict[player_name]["c_ward"]["all"] += data.visionWardsBoughtInGame
            st.session_state.df_player_dict[player_name]["rating"]["all"] = st.session_state.rate_dict[player_name][
                0
            ].mu
            st.session_state.df_champion_dict[champion_name]["match_count"]["all"] += 1
            st.session_state.df_champion_dict[champion_name]["win_count"]["all"] += 1 if data.win == "Win" else 0
            st.session_state.df_champion_dict[champion_name]["kill"]["all"] += data.championsKilled
            st.session_state.df_champion_dict[champion_name]["death"]["all"] += data.numDeaths
            st.session_state.df_champion_dict[champion_name]["assist"]["all"] += data.assists
            st.session_state.df_champion_dict[champion_name]["cs"]["all"] += data.cs
            st.session_state.df_champion_dict[champion_name]["gold"]["all"] += data.goldEarned
            st.session_state.df_champion_dict[champion_name]["c_ward"]["all"] += data.visionWardsBoughtInGame
            st.session_state.df_set_dict[(player_name, champion_name)]["match_count"]["all"] += 1
            st.session_state.df_set_dict[(player_name, champion_name)]["win_count"]["all"] += (
                1 if data.win == "Win" else 0
            )
            st.session_state.df_set_dict[(player_name, champion_name)]["kill"]["all"] += data.championsKilled
            st.session_state.df_set_dict[(player_name, champion_name)]["death"]["all"] += data.numDeaths
            st.session_state.df_set_dict[(player_name, champion_name)]["assist"]["all"] += data.assists
            st.session_state.df_set_dict[(player_name, champion_name)]["cs"]["all"] += data.cs
            st.session_state.df_set_dict[(player_name, champion_name)]["gold"]["all"] += data.goldEarned
            st.session_state.df_set_dict[(player_name, champion_name)]["c_ward"]["all"] += data.visionWardsBoughtInGame

            # ポジション毎データ集計
            st.session_state.df_player_dict[player_name]["match_count"][position_dict[data.individualPosition]] += 1
            st.session_state.df_player_dict[player_name]["win_count"][position_dict[data.individualPosition]] += (
                1 if data.win == "Win" else 0
            )
            st.session_state.df_player_dict[player_name]["kill"][
                position_dict[data.individualPosition]
            ] += data.championsKilled
            st.session_state.df_player_dict[player_name]["death"][
                position_dict[data.individualPosition]
            ] += data.numDeaths
            st.session_state.df_player_dict[player_name]["assist"][
                position_dict[data.individualPosition]
            ] += data.assists
            st.session_state.df_player_dict[player_name]["cs"][position_dict[data.individualPosition]] += data.cs
            st.session_state.df_player_dict[player_name]["gold"][
                position_dict[data.individualPosition]
            ] += data.goldEarned
            st.session_state.df_player_dict[player_name]["c_ward"][
                position_dict[data.individualPosition]
            ] += data.visionWardsBoughtInGame
            st.session_state.df_champion_dict[champion_name]["match_count"][
                position_dict[data.individualPosition]
            ] += 1
            st.session_state.df_champion_dict[champion_name]["win_count"][position_dict[data.individualPosition]] += (
                1 if data.win == "Win" else 0
            )
            st.session_state.df_champion_dict[champion_name]["kill"][
                position_dict[data.individualPosition]
            ] += data.championsKilled
            st.session_state.df_champion_dict[champion_name]["death"][
                position_dict[data.individualPosition]
            ] += data.numDeaths
            st.session_state.df_champion_dict[champion_name]["assist"][
                position_dict[data.individualPosition]
            ] += data.assists
            st.session_state.df_champion_dict[champion_name]["cs"][position_dict[data.individualPosition]] += data.cs
            st.session_state.df_champion_dict[champion_name]["gold"][
                position_dict[data.individualPosition]
            ] += data.goldEarned
            st.session_state.df_champion_dict[champion_name]["c_ward"][
                position_dict[data.individualPosition]
            ] += data.visionWardsBoughtInGame
            st.session_state.df_set_dict[(player_name, champion_name)]["match_count"][
                position_dict[data.individualPosition]
            ] += 1
            st.session_state.df_set_dict[(player_name, champion_name)]["win_count"][
                position_dict[data.individualPosition]
            ] += (1 if data.win == "Win" else 0)
            st.session_state.df_set_dict[(player_name, champion_name)]["kill"][
                position_dict[data.individualPosition]
            ] += data.championsKilled
            st.session_state.df_set_dict[(player_name, champion_name)]["death"][
                position_dict[data.individualPosition]
            ] += data.numDeaths
            st.session_state.df_set_dict[(player_name, champion_name)]["assist"][
                position_dict[data.individualPosition]
            ] += data.assists
            st.session_state.df_set_dict[(player_name, champion_name)]["cs"][
                position_dict[data.individualPosition]
            ] += data.cs
            st.session_state.df_set_dict[(player_name, champion_name)]["gold"][
                position_dict[data.individualPosition]
            ] += data.goldEarned
            st.session_state.df_set_dict[(player_name, champion_name)]["c_ward"][
                position_dict[data.individualPosition]
            ] += data.visionWardsBoughtInGame

    # データ正規化
    for player_name in st.session_state.df_player_dict.keys():
        st.session_state.df_player_dict[player_name]["win_rate"] = (
            st.session_state.df_player_dict[player_name]["win_count"]
            / st.session_state.df_player_dict[player_name]["match_count"]
        )
        st.session_state.df_player_dict[player_name]["kill"] /= st.session_state.df_player_dict[player_name][
            "match_count"
        ]
        st.session_state.df_player_dict[player_name]["death"] /= st.session_state.df_player_dict[player_name][
            "match_count"
        ]
        st.session_state.df_player_dict[player_name]["assist"] /= st.session_state.df_player_dict[player_name][
            "match_count"
        ]
        st.session_state.df_player_dict[player_name]["kda"] = (
            st.session_state.df_player_dict[player_name]["kill"]
            + st.session_state.df_player_dict[player_name]["assist"]
        ) / st.session_state.df_player_dict[player_name]["death"]
        st.session_state.df_player_dict[player_name]["cs"] /= st.session_state.df_player_dict[player_name][
            "match_count"
        ]
        st.session_state.df_player_dict[player_name]["gold"] /= st.session_state.df_player_dict[player_name][
            "match_count"
        ]
        st.session_state.df_player_dict[player_name]["c_ward"] /= st.session_state.df_player_dict[player_name][
            "match_count"
        ]
    for champion_name in st.session_state.df_champion_dict.keys():
        st.session_state.df_champion_dict[champion_name]["win_rate"] = (
            st.session_state.df_champion_dict[champion_name]["win_count"]
            / st.session_state.df_champion_dict[champion_name]["match_count"]
        )
        st.session_state.df_champion_dict[champion_name]["kill"] /= st.session_state.df_champion_dict[champion_name][
            "match_count"
        ]
        st.session_state.df_champion_dict[champion_name]["death"] /= st.session_state.df_champion_dict[champion_name][
            "match_count"
        ]
        st.session_state.df_champion_dict[champion_name]["assist"] /= st.session_state.df_champion_dict[champion_name][
            "match_count"
        ]
        st.session_state.df_champion_dict[champion_name]["kda"] = (
            st.session_state.df_champion_dict[champion_name]["kill"]
            + st.session_state.df_champion_dict[champion_name]["assist"]
        ) / st.session_state.df_champion_dict[champion_name]["death"]
        st.session_state.df_champion_dict[champion_name]["cs"] /= st.session_state.df_champion_dict[champion_name][
            "match_count"
        ]
        st.session_state.df_champion_dict[champion_name]["gold"] /= st.session_state.df_champion_dict[champion_name][
            "match_count"
        ]
        st.session_state.df_champion_dict[champion_name]["c_ward"] /= st.session_state.df_champion_dict[champion_name][
            "match_count"
        ]
    for (player_name, champion_name) in st.session_state.df_set_dict.keys():
        st.session_state.df_set_dict[(player_name, champion_name)]["win_rate"] = (
            st.session_state.df_set_dict[(player_name, champion_name)]["win_count"]
            / st.session_state.df_set_dict[(player_name, champion_name)]["match_count"]
        )
        st.session_state.df_set_dict[(player_name, champion_name)]["kill"] /= st.session_state.df_set_dict[
            (player_name, champion_name)
        ]["match_count"]
        st.session_state.df_set_dict[(player_name, champion_name)]["death"] /= st.session_state.df_set_dict[
            (player_name, champion_name)
        ]["match_count"]
        st.session_state.df_set_dict[(player_name, champion_name)]["assist"] /= st.session_state.df_set_dict[
            (player_name, champion_name)
        ]["match_count"]
        st.session_state.df_set_dict[(player_name, champion_name)]["kda"] = (
            st.session_state.df_set_dict[(player_name, champion_name)]["kill"]
            + st.session_state.df_set_dict[(player_name, champion_name)]["assist"]
        ) / st.session_state.df_set_dict[(player_name, champion_name)]["death"]
        st.session_state.df_set_dict[(player_name, champion_name)]["cs"] /= st.session_state.df_set_dict[
            (player_name, champion_name)
        ]["match_count"]
        st.session_state.df_set_dict[(player_name, champion_name)]["gold"] /= st.session_state.df_set_dict[
            (player_name, champion_name)
        ]["match_count"]
        st.session_state.df_set_dict[(player_name, champion_name)]["c_ward"] /= st.session_state.df_set_dict[
            (player_name, champion_name)
        ]["match_count"]

    # 全体集計用データ作成
    df_all_player = pd.DataFrame(
        index=[], columns=st.session_state.df_player_dict[next(iter(st.session_state.df_player_dict))].columns
    )
    for player in st.session_state.df_player_dict.keys():
        for position in st.session_state.df_player_dict[player].iterrows():
            if position[0] not in st.session_state.df_all_dict:
                st.session_state.df_all_dict[position[0]] = df_all_player.copy()
            df_tmp = pd.DataFrame([position[1]], index={player})
            st.session_state.df_all_dict[position[0]] = pd.concat([st.session_state.df_all_dict[position[0]], df_tmp])

    df_all_champion = pd.DataFrame(
        index=[], columns=st.session_state.df_champion_dict[next(iter(st.session_state.df_champion_dict))].columns
    )
    for champion in st.session_state.df_champion_dict.keys():
        for position in st.session_state.df_champion_dict[champion].iterrows():
            if position[0] not in st.session_state.df_all_champion_dict:
                st.session_state.df_all_champion_dict[position[0]] = df_all_champion.copy()
            df_tmp = pd.DataFrame([position[1]], index={champion})
            st.session_state.df_all_champion_dict[position[0]] = pd.concat(
                [st.session_state.df_all_champion_dict[position[0]], df_tmp]
            )

    df_all_set = pd.DataFrame(
        index=[], columns=st.session_state.df_set_dict[next(iter(st.session_state.df_set_dict))].columns
    )
    for (player, champion) in st.session_state.df_set_dict.keys():
        if player not in st.session_state.df_all_set_dict:
            st.session_state.df_all_set_dict[player] = df_all_set.copy()
        st.session_state.df_all_set_dict[player] = pd.concat(
            [
                st.session_state.df_all_set_dict[player],
                st.session_state.df_set_dict[(player, champion)][:1].rename(index={"all": champion}),
            ]
        )
    return (
        st.session_state.rate_dict,
        st.session_state.df_player_dict,
        st.session_state.df_champion_dict,
        st.session_state.df_set_dict,
        st.session_state.df_all_champion_dict,
        st.session_state.df_all_set_dict,
        st.session_state.df_all_dict,
        st.session_state.df_list,
    )


def page_record():
    st.session_state.env = trueskill.TrueSkill(draw_probability=0.0)
    st.session_state.env.make_as_global()
    st.session_state.rate_dict = {}
    st.session_state.df_player_dict = {}
    st.session_state.df_champion_dict = {}
    st.session_state.df_set_dict = {}
    st.session_state.df_all_champion_dict = {}
    st.session_state.df_all_set_dict = {}
    st.session_state.df_all_dict = {}
    st.session_state.df_list = []
    (
        st.session_state.rate_dict,
        st.session_state.df_player_dict,
        st.session_state.df_champion_dict,
        st.session_state.df_set_dict,
        st.session_state.df_all_champion_dict,
        st.session_state.df_all_set_dict,
        st.session_state.df_all_dict,
        st.session_state.df_list,
    ) = get_all_record()

    for keys in st.session_state.df_all_dict.keys():
        st.session_state.df_all_dict[keys] = st.session_state.df_all_dict[keys].sort_values(
            "win_rate", ascending=False
        )
        st.session_state.df_all_dict[keys] = (
            st.session_state.df_all_dict[keys]
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
    for keys in st.session_state.df_all_champion_dict.keys():
        st.session_state.df_all_champion_dict[keys] = st.session_state.df_all_champion_dict[keys].sort_values(
            "match_count", ascending=False
        )
        st.session_state.df_all_champion_dict[keys] = (
            st.session_state.df_all_champion_dict[keys]
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
    for keys in st.session_state.df_all_set_dict.keys():
        st.session_state.df_all_set_dict[keys] = st.session_state.df_all_set_dict[keys].sort_values(
            "match_count", ascending=False
        )
        st.session_state.df_all_set_dict[keys] = (
            st.session_state.df_all_set_dict[keys]
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

    # フォーマット
    df_player_dict_styler = {}
    for keys in st.session_state.df_player_dict.keys():
        df_player_dict_styler[keys] = st.session_state.df_player_dict[keys].style.format(
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
    for keys in st.session_state.df_champion_dict.keys():
        st.session_state.df_champion_dict[keys] = st.session_state.df_champion_dict[keys].style.format(
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

    if st.session_state.df_all_dict != {}:
        st.write("総合戦績")
        option1 = st.selectbox("ポジションの選択", st.session_state.df_all_dict.keys())
        st.dataframe(st.session_state.df_all_dict[option1])
        st.dataframe(st.session_state.df_all_champion_dict[option1])

    if df_player_dict_styler != {}:
        st.write("個人戦績")
        option2 = st.selectbox("プレイヤーの選択", df_player_dict_styler.keys())

        st.dataframe(df_player_dict_styler[option2])
        st.dataframe(st.session_state.df_all_set_dict[option2])

        st.write("レート変動")
        chart_data = pd.DataFrame(st.session_state.rate_dict[option2][::-1], columns=["期待値", "標準偏差"])
        st.line_chart(chart_data)


def page_history():
    for i, df in enumerate(reversed(list(st.session_state.df_list))):
        st.write(f"match {i+1}")
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


def page_balancer():
    # st.write("勝率予測")

    # options3 = st.multiselect("チームA", st.session_state.df_player_dict.keys(), [])
    # options4 = st.multiselect("チームB", st.session_state.df_player_dict.keys(), [])

    # t1 = []
    # t2 = []
    # for player in options3:
    #     t1.append(st.session_state.rate_dict[player])
    # for player in options4:
    #     t2.append(st.session_state.rate_dict[player])
    # if t1 != [] or t2 != []:
    #     wp = win_probability(t1, t2, env=st.session_state.env)
    #     st.write(f"チーム1の勝率: {wp*100.0:.0f}%")
    #     my_bar = st.progress(0)
    #     my_bar.progress(wp)

    # st.write("")
    st.write("自動チーム編成")

    options5 = st.multiselect("参加者", st.session_state.df_player_dict.keys(), [])
    if len(options5) == 10:
        wp = 0.0
        wp_min = 0.4
        wp_max = 0.6
        cnt = 0
        while wp < wp_min or wp > wp_max:
            options5 = random.sample(options5, 10)
            a = options5[:5]
            b = options5[5:]
            t3 = []
            t4 = []
            for player in a:
                t3.append(st.session_state.rate_dict[player][0])
            for player in b:
                t4.append(st.session_state.rate_dict[player][0])
            wp = win_probability(t3, t4, env=st.session_state.env)
            cnt += 1
            if cnt % 10 == 0:
                wp_min -= 0.01
                wp_max += 0.01

        a_rate = []
        for player in a:
            a_rate.append(st.session_state.rate_dict[player][0].mu)
        a = [i for _, i in sorted(zip(a_rate, a))]
        a_ave_rate = statistics.mean(a_rate)
        a_team_list = ["", "", "", "", ""]
        a_team = {}
        for player in a:
            tmp_list = [0, 1, 2, 3, 4]
            role_weight = list(st.session_state.df_player_dict[player]["match_count"][:])
            weight_list = []
            for i in range(5):
                weight_list.append(role_weight[i + 1] / role_weight[0])
            weight_list = [i for _, i in sorted(zip(weight_list, tmp_list), reverse=True)]
            for i in range(5):
                if a_team_list[weight_list[i]] == "":
                    a_team_list[weight_list[i]] = player
                    break
        a_team["top"] = a_team_list[0]
        a_team["jg"] = a_team_list[1]
        a_team["mid"] = a_team_list[2]
        a_team["bot"] = a_team_list[3]
        a_team["supp"] = a_team_list[4]
        b_rate = []
        for player in b:
            b_rate.append(st.session_state.rate_dict[player][0].mu)
        b = [i for _, i in sorted(zip(b_rate, b))]
        b_ave_rate = statistics.mean(b_rate)
        b_team_list = ["", "", "", "", ""]
        b_team = {}
        for player in b:
            tmp_list = [0, 1, 2, 3, 4]
            role_weight = list(st.session_state.df_player_dict[player]["match_count"][:])
            weight_list = []
            for i in range(5):
                weight_list.append(role_weight[i + 1] / role_weight[0])
            weight_list = [i for _, i in sorted(zip(weight_list, tmp_list), reverse=True)]
            for i in range(5):
                if b_team_list[weight_list[i]] == "":
                    b_team_list[weight_list[i]] = player
                    break
        b_team["top"] = b_team_list[0]
        b_team["jg"] = b_team_list[1]
        b_team["mid"] = b_team_list[2]
        b_team["bot"] = b_team_list[3]
        b_team["supp"] = b_team_list[4]

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"チームA平均レート: {a_ave_rate:.1f}")
            st.write(a_team)
        with col2:
            st.write(f"チームB平均レート: {b_ave_rate:.1f}")
            st.write(b_team)
        st.write(f"勝利予測: {wp*100.0:.0f}%")
        my_bar = st.progress(0)
        my_bar.progress(wp)


def page_benzaiten():
    st.title("今日の弁財天")

    img = Image.open("zeniarai.jpeg")
    st.image(img, use_column_width=True)


selected_page = st.sidebar.radio("Menu", ["Record", "History", "Balancer", "Benzaiten"])

if selected_page == "Record":
    page_record()
elif selected_page == "History":
    if st.session_state.df_list != []:
        page_history()
elif selected_page == "Balancer":
    if st.session_state.df_player_dict != {}:
        page_balancer()
elif selected_page == "Benzaiten":
    page_benzaiten()
else:
    pass
