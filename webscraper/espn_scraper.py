import requests
import re
import json

from teams_data import roster_URLs, nfl_teams


# TODO: 0)       Change any camelCase to snake_case as found
# TODO: 1)  DONE Sanitize player.names for ' characters (i.e. change any ' to \' )    ?? Maybe already sanitized?
# TODO: 2a) DONE Change create_player_table_dml() and print_roster() output from printing to terminal to generating a DML file
# TODO: 2b) DONE Consider merging print_roster() into create_player_table_dml()
# TODO: 3a)      Create functions for creating offense_game_stats, defense_game_stats, and special_game_stats DML data
# TODO: 3b)      Output 3a to file
# TODO: 4)       Scrape game data
# TODO: 5)       Output game data to DML file
# TODO: 6)       Output team data to DML file
# TODO: 7)       Create and output stadium data to DML file


def get_roster(url_end):
  url_start = 'https://www.espn.com/nfl/team/roster/_/name/'
  HTML = requests.get(url_start+url_end, headers = {'User-Agent':'...'})
  
  start = re.search(r'"groups":', HTML.text).span()[0]   # Find where the groups key starts
  end = re.search(r'},"subType":', HTML.text).span()[0]  # Find where the groups key values end
  
  data = '{' + HTML.text[start:end]  # Slice out the groups
  roster_json = json.loads(data)  # Build JSON from string
  
  return roster_json['groups']

def export_json_to_file(json_data, file_name):
  with open(file_name, "w") as file:
    json.dump(json_data, file, indent=4)

def import_json_from_file(filename):
  with open(filename, "r") as file:
    data = json.load(file)
  return data

def create_player_table_dml(player_json):
  file = open("NFL_DML_Insert_File.sql", "w")   # w to empty the file before writing
  file.write('DELETE FROM player;\n')

  for team in player_json:

    for group in player_json[team]:    # group 0 = Offense, 1 = defense, 2 = special teams
      file.write(f"# {team.upper()} : {group['name'].upper()}\n")

      for player in group['athletes']:
        file.write("INSERT INTO player VALUES (")
        file.write(f"{player['id']}, ")          # id
        sanitized_name = player['name'].replace("'", "''")
        file.write(f"'{sanitized_name}', ")      # name
        file.write(f"'{team}', ")           # team_name
        sanitized_height = player['height'].replace("'", "''")
        file.write(f"'{sanitized_height}', ")    # height
        file.write(f"{player['weight'][:-4]}, ") # weight  # slicing to remove ' lbs'
        try:
          file.write(f"{player['age']}, ")       # age
        except:
          file.write(f"NULL, ")
        file.write(f"'{player['position']}', ")  # position
        try:
          file.write(f"{player['jersey']}, ")    # jersey
        except:
          file.write(f"NULL, ")
        file.write(f"'{player['birthDate']}', ") # birth_date
        if player['experience'] == 'R':             # years_played    # R = rookie
          file.write(f"0, ")  
        else:
          file.write(f"{player['experience']}, ")
        try:
          sanitized_college = player['college'].replace("'", "''")
          file.write(f"'{sanitized_college}'")   # college
        except:
          file.write(f"NULL")
        file.write(");\n")

  file.close()


def get_player_stats(url):
  url = url[:31] + 'gamelog/' + url[31:]  # Convert from player page URL to player gamelog URL
  HTML = requests.get(url, headers = {'User-Agent' : '...'})

  try:
    start = re.search(r'"groups":', HTML.text).span()[0]   # Find where the groups key starts
  except:
    return 'Null' # Player has no game data (ex: recent acquisition, unused backup, snapper)
  
  end = re.search(r',"hasAllStar":', HTML.text).span()[0]  # Find where the groups key values end

  data = '{' + HTML.text[start:end] +'}'  # Slice out the groups
  stats_json = json.loads(data)  # Build JSON from string
  
  return stats_json['groups']


def export_player_game_stats(player_stats, player_game_stats):
  file = open("NFL_DML_Insert_File.sql", "a")   # a to append to file
  hasGames = False

  if player_stats['position'] in ['QB', 'RB', 'FB', 'WR', 'TE', 'C', 'G', 'OT']:
    table_name = 'offense_plays'
  elif player_stats['position'] in ['DE', 'DT', 'LB', 'CB', 'S']:
    table_name = 'defense_plays'
  elif player_stats['position'] in ['PK', 'P', 'LS']:
    table_name = 'special_teams_plays'

  for season in player_game_stats:
    try:
      season['name']
    except:
      print(f"{player_stats['name']}: No season data?")
    else:
      if season['name'] == '2023 Regular Season':
        hasGames = True
        # print(json.dumps(season, indent=4))

        for table in season['tbls']:
          for event in table['events']:
            file.write(f"INSERT INTO {table_name} VALUES (")
            file.write(f"{player_stats['id']}, ")
            file.write(f"{event['dt'][:10]}, ")
            if player_stats['position'] == 'QB':
              file.write(f"{event['stats'][0]}, {event['stats'][1]}, {event['stats'][2]}, {event['stats'][11]}, {event['stats'][12]}, NULL")

            elif player_stats['position'] in ['RB', 'FB']:
              file.write(f"{event['stats'][5]}, {event['stats'][6]}, {event['stats'][7]}, {event['stats'][0]}, {event['stats'][1]}, {event['stats'][11]}")

            elif player_stats['position'] in ['WR', 'TE']:
              file.write(f"{event['stats'][0]}, {event['stats'][1]}, {event['stats'][2]}, {event['stats'][6]}, {event['stats'][7]}, {event['stats'][11]}")

            elif player_stats['position'] in ['C', 'G', 'OT']:
              file.write(f"NULL, NULL, NULL, NULL, NULL, NULL")

            elif player_stats['position'] in ['DE', 'DT', 'LB', 'CB', 'S']:
              file.write(f"{event['stats'][0]}, {event['stats'][3]}, {event['stats'][9]}, {event['stats'][11]}, {event['stats'][16]}")
            
            elif player_stats['position'] == 'PK':
              file.write(f"{event['stats'][7][:1]}, {event['stats'][7][1:]}, {event['stats'][10][:1]}, {event['stats'][10][1:]}, NULL, NULL")

            elif player_stats['position'] == 'P':
              file.write(f"NULL, NULL, NULL, NULL, {event['stats'][0]}, {event['stats'][3]}")

            elif player_stats['position'] == 'S':
              file.write(f"NULL, NULL, NULL, NULL, NULL, NULL")

            file.write(f");\n")
  
    if hasGames == False:
      print(f"{player_stats['name']}: No 20203 Regular Season")
  file.close()


if (__name__ == "__main__"):
  rosters = {}
  '''
  # Get roster tuples
  for team in roster_URLs:
    print(f'Retrieving {team} roster.')
    rosters.update({team : get_roster(roster_URLs[team])})
  
  # Export raw data to file
  export_json_to_file(rosters, "rosters.json")
  '''
  
  # Input player data from json
  rosters = import_json_from_file("rosters.json")

  # Output to file
  create_player_table_dml(rosters)
  
  # rosters heirarchy: rosters['Teamname'][#group#]['athletes'][#athlete#]['attribute']
  for team in rosters:
    for group in rosters[team]:
      for player in group['athletes']:
        print(f"Retrieving {player['name']} game stats. ({team} : {group['name']})")
        player_game_stats = get_player_stats(player['href'])  # Get stats JSON from HTML
        export_player_game_stats(player, player_game_stats)   # Reformat to DML and export to SQL
        

    # export_offense_dml_to_file(offense_player_game_stats)
    