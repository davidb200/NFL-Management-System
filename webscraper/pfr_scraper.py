import requests
import re
from bs4 import BeautifulSoup
from time import sleep

import webaddress 
from teams_data import nfl_teams
from stadiums_data import nfl_stadiums
import football_cfg as football
import sql_cfg


HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15', 
           'Accept-language': 'bg', 
           'Accept-encoding': 'identit', 
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 
           'Referer': 'http://diri.bg'
          }

# TODO:      Completely scrape 2023 pre and post seasons
# TODO:      Completely scrape 2022 pre, regular, and post seasons
# TODO:      Completely scrape 2021 pre, regular, and post seasons
# TODO:      Scrape all previous seasons' post-season (Will allow for querying how many times a team has made it to the playoffs/super bowl or won the super bowl.
# TODO: DONE Fix formatting for dates to be in single quotes.
# TODO: DONE Fix VALUE to VALUES
# TODO: DONE Capitalize Regular, Pre, Post season values. 
# TODO:      Handle duplicate player ID values (player traded mid-season?)
# TODO:      Handle players with multiple positions (esp if both offense and defense, handle adding both offense_plays and defense_plays values
# TODO: DONE Fix a few stadium names not matching between Stadiums and Teams

# Get the URL's HTML. If HTTP reqeust fails, keep trying until it succeeds.
def get_html(url):  

  html_doc = None
  attempt_count = 0
  
  while (html_doc is None):
    attempt_count += 1
    
    try:
      html_doc = requests.get(url, headers = HEADERS)
    
    except requests.exceptions.ConnectionError:
      print(f'   Attempt {attempt_count}: Failed to retrieve page. Retrying in 3 seconds.')
      sleep(3.1)
    
    else:
      print(f'   Attempt {attempt_count}: HTTP request successful!')
  
  return html_doc

# Get the player data from the teams' rosters.
def get_player_data(teams):
  player_ids = [] # List to fill and return for player gamelog URLs
  
  with open('NFL_DML_Insert_File.sql', 'a') as dml_file:
    dml_file.write(f'DELETE FROM {sql_cfg.player_table};\n')

    for team in teams:
      team_name = "'"+ team +"'"

      for year in football.years:
        # Get team roster page HTML
        print(f'Retrieving {team} roster.')
        url = webaddress.domain+'/teams/'+teams[team]['abbv']+'/'+str(year)+'_roster.htm'
        html_doc = get_html(url)
        html_doc = html_doc.text

        # Get the table out of a comment
        start = re.search(r'<div class="table_container"', html_doc).span()[0]
        data = html_doc[start:]
        end = re.search(r'</div>', data).span()[1]
        data = data[:end]
          
        # Get table rows <tr>...< /tr>
        soup = BeautifulSoup(data, 'html.parser')
        tr_tags = soup.find_all('tr')
        tr_tags = tr_tags[1:-1]   # First row is column labels, last row is column sums, remove them
        
        for i in range(len(tr_tags)):  
          jersey = tr_tags[i].find('th', {'data-stat' : 'uniform_number'})
          jersey = 'NULL' if jersey is None or jersey.string is None else int(jersey.string)
          
          id = tr_tags[i].find('td', {'data-stat' : 'player'})['data-append-csv'] # Player ID is a tag attribute
          player_ids.append(id)
          id = "'" + id + "'"
          
          name_td = tr_tags[i].find('td', {'data-stat' : 'player'})
          name = name_td.find('a').string     # <td ...><a href...>name</a></td>
          name = "'" + name.string.replace("'", "''") + "'"    # Sanitize '

          age = tr_tags[i].find('td', {'data-stat' : "age"})
          age = 'NULL' if age is None or age.string is None else int(age.string)

          position = tr_tags[i].find('td', {'data-stat' : "pos"})
          position = 'NULL' if position is None or position.string is None else "'" + position.string + "'"

          weight = tr_tags[i].find('td', {'data-stat' : 'weight'})
          weight = 'NULL' if weight is None or weight.string is None else int(weight.string)

          height = tr_tags[i].find('td', {'data-stat' : 'height'})
          height = 'NULL' if height is None or height.string is None else "'" + height.string + "'"

          college = tr_tags[i].find('td', {'data-stat' : 'college_id'})
          college = 'NULL' if college is None or college.string is None else college.string
          college = "'" + college.replace("'", "''") + "'"

          try:
            birth_date = "'"+ tr_tags[i].find('td', {'data-stat' : 'birth_date_mod'})['csk'] +"'" # YYYY-MM-DD format is a tag attribute
          except KeyError:
            birth_date = 'NULL'

          years_played = tr_tags[i].find('td', {'data-stat' : 'experience'})
          years_played = 0 if years_played.string == 'Rook' else years_played.string
          
          dml_file.write(f'INSERT INTO {sql_cfg.player_table} VALUES ({id}, {name}, {team_name}, {height}, {weight}, {age}, {position}, {jersey}, {birth_date}, {years_played}, {college});\n')
          

        sleep(3.2)

    dml_file.write('\n')
    print()
  return player_ids

# Get the game data from a player's game log.
def get_stats_data(players):
  with open('NFL_DML_Insert_File.sql', 'a') as dml_file:

    dml_file.write(f'DELETE FROM {sql_cfg.op_game_data};\n')
    dml_file.write(f'DELETE FROM {sql_cfg.dp_game_data};\n')
    dml_file.write(f'DELETE FROM {sql_cfg.sp_game_data};\n')
    
    for player in players:
      for year in football.years:
        print(f'Retrieving {player} gamelogs.')
        url = webaddress.domain+'/players/'+player[:1]+'/'+player+'/gamelog/'+str(year)
        
        html_doc = html_doc = get_html(url)

        # find the player's position on the page and use it to set the table we will use in SQL (offense/defense/special teams)
        player_position = re.search(r'(?<=Position</strong>: )(.*?)(?=[\n\r])', html_doc.text)
        player_position = 'NULL' if player_position == None else player_position.group(0)
        if player_position in football.offense_positions:
          table = sql_cfg.op_game_data
        elif player_position in football.defense_positions:
          table = sql_cfg.dp_game_data
        elif player_position in football.special_positions:
          table = sql_cfg.sp_game_data
        elif player_position == 'NULL':
          table = 'NULL'
        else:
          table = 'UNKNOWN POSITION: ' + player_position
          with open('unknown_position_log.txt', 'a') as logfile:
            logfile.write(f'{player} : {player_position}\n')

        soup = BeautifulSoup(html_doc.text, 'html.parser')
        gamelog_div = soup.find('div', class_= 'table_container')

        if gamelog_div != None:        # Player has a 2023 game log table
          player_id = "'" + player + "'"

          tr_tags = gamelog_div.find_all('tr')

          for i in range(2, len(tr_tags)-1):    # First 2 rows are column headers, last is column sum
            missed_game = tr_tags[i].find('td', {'data-stat' : 'reason'})   #check if played in game
            if missed_game == None:
              
              game_id = f"'{tr_tags[i].find('a').get('href')[11:23]}'"

              if table == sql_cfg.op_game_data:
                pass_cmp = tr_tags[i].find('td', {'data-stat' : 'pass_cmp'})
                pass_cmp = 0 if pass_cmp is None or pass_cmp.string is None else int(pass_cmp.string)

                pass_att = tr_tags[i].find('td', {'data-stat' : 'pass_att'})
                pass_att = 0 if pass_att is None or pass_att.string is None else int(pass_att.string)

                pass_yds = tr_tags[i].find('td', {'data-stat' : 'pass_yds'})
                pass_yds = 0 if pass_yds is None or pass_yds.string is None else int(pass_yds.string)

                rush_att = tr_tags[i].find('td', {'data-stat' : 'rush_att'})
                rush_att = 0 if rush_att is None or rush_att.string is None else int(rush_att.string)

                rush_yds = tr_tags[i].find('td', {'data-stat' : 'rush_yds'})
                rush_yds = 0 if rush_yds is None or rush_yds.string is None else int(rush_yds.string)

                fumbles_lost = tr_tags[i].find('td', {'data-stat' : 'fumbles_lost'})
                fumbles_lost = 0 if fumbles_lost is None or fumbles_lost.string is None else int(fumbles_lost.string)

                dml_file.write(f'INSERT INTO {table} VALUES ({player_id}, {game_id}, {pass_cmp}, {pass_att}, {pass_yds}, {rush_att}, {rush_yds}, {fumbles_lost});\n')

              elif table == sql_cfg.dp_game_data:
                tackles = tr_tags[i].find('td', {'data-stat' : 'tackles_combined'})
                tackles = 0 if tackles is None or tackles.string is None else int(tackles.string)

                sacks = tr_tags[i].find('td', {'data-stat' : 'sacks'})
                sacks = 0 if sacks is None or sacks.string is None else int(float(sacks.string))

                fumbles_rec = tr_tags[i].find('td', {'data-stat' : 'fumbles_rec'})
                fumbles_rec = 0 if fumbles_rec is None or fumbles_rec.string is None else int(fumbles_rec.string)

                def_int = tr_tags[i].find('td', {'data-stat' : 'def_int'})
                def_int = 0 if def_int is None or def_int.string is None else int(def_int.string)

                pass_defended = tr_tags[i].find('td', {'data-stat' : 'pass_defended'})
                pass_defended = 0 if pass_defended is None or pass_defended.string is None else int(pass_defended.string)

                dml_file.write(f"INSERT INTO {table} VALUES ({player_id}, {game_id}, {tackles}, {sacks}, {fumbles_rec}, {def_int}, {pass_defended});\n")

              elif table == sql_cfg.sp_game_data:
                fg_made = tr_tags[i].find('td', {'data-stat' : 'fgm'})
                fg_made = 0 if fg_made is None or fg_made.string is None else int(fg_made.string)

                fg_att = tr_tags[i].find('td', {'data-stat' : 'fga'})
                fg_att = 0 if fg_att is None or fg_att.string is None else int(fg_att.string)

                ep_made = tr_tags[i].find('td', {'data-stat' : 'epm'})
                ep_made = 0 if ep_made is None or ep_made.string is None else int(ep_made.string)

                ep_att = tr_tags[i].find('td', {'data-stat' : 'epa'})
                ep_att = 0 if ep_att is None or ep_att.string is None else int(ep_att.string)

                punts = tr_tags[i].find('td', {'data-stat' : 'kickoff'})
                punts = 0 if punts is None or punts.string.string is None else int(punts.string)

                punt_yds = tr_tags[i].find('td', {'data-stat' : 'kickoff_yds'})
                punt_yds = 0 if punt_yds is None or punt_yds.string is None else int(punt_yds.string)

                dml_file.write(f'INSERT INTO {table} VALUES ({player_id}, {game_id}, {fg_made}, {fg_att}, {ep_made}, {ep_att}, {punts}, {punt_yds});\n')

        sleep(3.1)  # Avoid bot detection (> 20 requests / minute)
    
    dml_file.write('\n')
    print()

# Get the game data from the season's schedule page.
def get_game_data():
  with open('NFL_DML_Insert_File.sql', 'a') as dml_file:

    dml_file.write(f'DELETE FROM {sql_cfg.game_table};\n')
    
    for year in football.years:
      url = webaddress.domain+'/years/'+str(year)+'/games.htm'

      print(f'Retreiving {year} schedule.')
      html_doc = get_html(url)
      
      soup = BeautifulSoup(html_doc.text, 'html.parser')
      schedule_div = soup.find('div', id='div_games')

      tr_tags = schedule_div.find_all('tr')
      tr_tags = tr_tags[1:]
      
      for i in range(len(tr_tags)):
        week = tr_tags[i].find('th', {'data-stat' : 'week_num'})
        if week.string in football.weeks:

          id = f"'{tr_tags[i].find_all('a')[2].get('href')[11:23]}'"

          date = "'" + tr_tags[i].find('td', {'data-stat' : 'game_date'})['csk'] + "'"
      
          winner = tr_tags[i].find('td', {'data-stat' : 'winner'})
          winner = "'" + winner.string.split(' ')[-1] + "'"

          win_score = tr_tags[i].find('td', {'data-stat' : 'pts_win'})
          win_score = int(win_score.string)

          at = tr_tags[i].find('td', {'data-stat' : 'game_location'})
        
          loser = tr_tags[i].find('td', {'data-stat' : 'loser'})
          loser = "'" + loser.string.split(' ')[-1] + "'"

          lose_score = tr_tags[i].find('td', {'data-stat' : 'pts_lose'})
          lose_score = int(lose_score.string)

          if at.string is None:    # Home team won
            dml_file.write(f"INSERT INTO {sql_cfg.game_table} VALUES ({id}, 2023, 'Regular', {week.string}, {date}, {winner}, {loser}, {win_score}, {lose_score});\n")
          else:     # Away team won
            dml_file.write(f"INSERT INTO {sql_cfg.game_table} VALUES ({id}, 2023, 'Regular', {week.string}, {date}, {loser}, {winner}, {lose_score}, {win_score});\n")
      
      sleep(3.2)

    dml_file.write('\n')
    print()


def get_stadium_data():
  with open('NFL_DML_Insert_File.sql', 'a') as dml_file:
    
    dml_file.write(f'DELETE FROM {sql_cfg.stadium_table};\n')

    for stadium in nfl_stadiums:
      name = "'"+ stadium +"'"
      city = "'"+ nfl_stadiums[stadium]['city'] +"'"
      state = "'"+ nfl_stadiums[stadium]['state'] +"'"
      address = "'"+ nfl_stadiums[stadium]['address'] +"'"
      capacity = nfl_stadiums[stadium]['capacity']
      turf_type = "'"+ nfl_stadiums[stadium]['turf'] +"'"

      dml_file.write(f'INSERT INTO {sql_cfg.stadium_table} VALUES ({name}, {city}, {state}, {address}, {capacity}, {turf_type});\n')
    
    dml_file.write('\n')

def get_team_data():
  with open('NFL_DML_Insert_File.sql', 'a') as dml_file:
  
    dml_file.write(f'DELETE FROM {sql_cfg.team_table};\n')

    for team in nfl_teams:
      mascot = "'"+ team +"'"
      location = "'"+ nfl_teams[team]['location'] +"'"
      coach = "'"+ nfl_teams[team]['coach'] +"'"
      home_stadium = "'"+ nfl_teams[team]['stadium'] +"'"
      division = "'"+ nfl_teams[team]['division'] +"'"

      dml_file.write(f'INSERT INTO {sql_cfg.team_table} VALUES ({mascot}, {location}, {coach}, {home_stadium}, {division});\n')

    dml_file.write('\n')

def get_season_data():
    with open('NFL_DML_Insert_File.sql', 'a') as dml_file:
      dml_file.write(f'DELETE FROM {sql_cfg.season_table};\n')
      for year in football.years:
        season_type = "'Regular'"
        start_date = '2023-09-10'
        end_date = '2024-01-07'
        dml_file.write(f'INSERT INTO {sql_cfg.season_table} VALUES ({year}, {season_type}, {start_date}, {end_date});\n')
      
      dml_file.write('\n')


if __name__ == '__main__':
  '''
  f = open('NFL_DML_Insert_File.sql','w')   # Clear old file contents
  f.close()

  get_stadium_data()

  get_team_data()

  player_ids = get_player_data(nfl_teams)

  with open('player_id.txt', 'w') as file:
    for id in player_ids:
      file.write(id + " ")
  
  get_season_data()
  
  get_game_data()
  
  with open('player_id.txt', 'r') as file:
    player_ids = file.read().split()

  get_plays_data(player_ids)
  '''