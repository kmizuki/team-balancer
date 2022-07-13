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
beta = sigma / 2.0
tau = sigma / 100.0
draw_probability = 0.0
backend = None

env = trueskill.TrueSkill(mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=draw_probability, backend=backend)

env.make_as_global()
rate_dict = {}

# Create API client.
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = storage.Client(credentials=credentials)


@st.experimental_memo(ttl=600)
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
for blob in blobs:
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

st.write("勝率予測")

options3 = st.multiselect("チーム1", df_player_dict.keys(), [])
options4 = st.multiselect("チーム2", df_player_dict.keys(), [])

t1 = []
t2 = []
for player in options3:
    t1.append(rate_dict[player])
for player in options4:
    t2.append(rate_dict[player])
if t1 != [] or t2 != []:
    wp = win_probability(t1, t2, env=env)
    st.write(f"チーム1の勝率: {wp*100.0:.2f}%")
