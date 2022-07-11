import streamlit as st
import pandas as pd
import requests
import plotly.express as px

BASE_URL = 'https://d1fodqbtqsx6d3.cloudfront.net'
st.set_page_config(page_title="Challenger Queue Data", layout='wide')
player_name = '100 Abbedagge'


# Look for a player in team data, if found then gives it his team result and return
def get_player_data(teams_data, player_name):
    for team in teams_data:
        for player in team['players']:
            if player['name'] == player_name:
                player['win'] = team['winner']
                return player
    return None

# Instead of whitelisting a single player, whitelist the whole team if
# the player is in there


def get_player_team(teams_data, player_name):
    for team in teams_data:
        is_team = False
        for player in team['players']:
            player['win'] = 1 if team['winner'] else 0
            if player['name'] == player_name:
                is_team = True

        if is_team:
            return team['players']
    return None


url = BASE_URL + '/matches.json'
r = requests.get(url, verify=False)
matches = r.json()

matches_df = pd.DataFrame(matches['matches'])

# go look into each match if the player was present
matches_df['player_data'] = matches_df['teams'].apply(
    lambda match_teams: get_player_data(match_teams, player_name))
player_matches = matches_df[matches_df['player_data'].notnull()]

# gather all of the other players that were in the same team
player_matches['teammates'] = player_matches['teams'].apply(
    lambda team: get_player_team(team, player_name))

# reorganize the teammates to have a list of their names
teammates_list = [element for sublist in player_matches['teammates'].tolist()
                  for element in sublist]
teammates = pd.DataFrame(teammates_list)
teammates = teammates[teammates['name'] != player_name]
teammates['team'] = teammates['name'].apply(
    lambda player_name: player_name.split()[0])

st.write("All teammates")
st.write(teammates)

# let's only return top 10 most played with for more readability
most_played_with_names = teammates['name'].value_counts().head(
    10).index.tolist()
most_played_with = teammates[teammates['name'].isin(
    most_played_with_names)]

# separating my layout in 2 columns
col1, col2 = st.columns(2)

with col1:
    fig = px.pie(most_played_with, names='name', title="Played with")
    fig.update_traces(textinfo='value')
    st.plotly_chart(fig)

with col2:
    fig = px.histogram(most_played_with, x="name", color="team", y="win",
                       histfunc="avg", title="Average winrate with")
    fig.update_layout(barmode='stack', xaxis={
                      'categoryorder': 'category ascending'})
    st.plotly_chart(fig)
