/* Team 3 - DDL for NFL Management System
 * Tables used for NFL Management System: stadium,team,player,season,
 * game,offense_game_stats,defense_game_stats,special_game_stats

*/

/* If database tables need to be reset*/
DROP TABLE special_game_stats;
DROP TABLE defense_game_stats;
DROP TABLE offense_game_stats;
DROP TABLE game;
DROP TABLE season;
DROP TABLE player;
DROP TABLE team;
DROP TABLE stadium;

/* Attributes for stadium: name,city,state,address,capacity,turf_type 
 * Primary key -> city, state
 * Foreign Key -> none
*/
create table stadium(
  name varchar(50), 
  city varchar(50), 
  state char(2), 
  address varchar(50), 
  capacity int, 
  turf_type varchar(50), 
  primary key(city, state)
);
/* Attributes for team: mascot,location,coach,home_city,home_state,division,wins,losses,
					    standing
 * Primary key -> mascot
 * Foreign key -> home_city references stadium city,
 				  home_state references stadium state
*/
create table team (
  mascot varchar(50), 
  location varchar(50), 
  coach varchar(50), 
  home_city varchar(50),
  home_state char(2),
  division varchar(50),  
  wins int, 
  losses int, 
  standing int, 
  primary key(mascot),
  foreign key(home_city, home_state) references stadium(city,state)
);
/* Attributes for player: id,name,team,height,weight,age,position,
 * jersey,birth_date,years_played,college
 * Primary key -> id
 * Foreign key -> team references team's mascot
*/
create table player (
  id varchar(8), 
  name varchar(50), 
  team varchar(50), 
  height varchar(4), 
  weight numeric(3, 0), 
  age numeric(2, 0), 
  position varchar(3), 
  jersey numeric(2,0), 
  birth_date varchar(10), 
  years_played smallint, 
  college varchar(50), 
  primary key(id),
  foreign key(team) references team(mascot)
);
/* Attributes for season: year,start_date,end_date
 * Primary key -> year 
 * Foreign key -> none
*/
create table season(
  year numeric(4, 0), 
  start_date date, 
  end_date date, 
  primary key(year)
);
/* Attributes for game: game_id,season_year,week,game_date,
 * home_team,away_team,home_score,away_score
 * Primary key -> game_id
 * Foreign key -> season year references seasons's year,
 *                home team references team's mascot,
 *				  away team references team's mascot
*/
create table game(
  game_id varchar(12),
  season_year numeric(4, 0), 
  week varchar(9),
  game_date date, 
  home_team varchar(50), 
  away_team varchar(50), 
  home_score int, 
  away_score int, 
  primary key(game_id),
  foreign key(season_year) references season(year),
  foreign key(home_team) references team(mascot), 
  foreign key(away_team) references team(mascot)
);
/* Attrbiutes for offense_game_stats: player_id, game_id, passing_completions, passing_attempts,
 * passing yards, rushing attempts, rushing yards,fumbles
 * Primary key -> player id and game id
 * Foreign key -> player_id references player's id,
 *                game_id references game's game_id
*/
create table offense_game_stats(
  player_id varchar(8), 
  game_id varchar(12),
  passing_completions int, 
  passing_attempts int, 
  passing_yards int, 
  rushing_attempts int, 
  rushing_yards int, 
  fumbles int, 
  primary key(player_id, game_id),
  foreign key(player_id) references player(id),
  foreign key(game_id) references game(game_id)
);
/* Attributes for defense_game_stats: player_id, game_id, tackles,sacks,
 * fumbles_recovered,interceptions,passes defended
 * Primary key -> game_id and player_id
 * Foreign key -> player_id references player's id,
 *				  game_id references game's game_id
*/
create table defense_game_stats(
  player_id varchar(8),
  game_id varchar(12), 
  tackles int, 
  sacks int, 
  fumbles_recovered int, 
  interceptions int, 
  passes_defended int, 
  primary key(game_id, player_id), 
  foreign key(player_id) references player(id), 
  foreign key(game_id) references game(game_id)
);
/* Attrbiutes for special_game_stats: game_id, player_id, field_goals, fg_attempts,
 * extra_points, ep_attempts, punts, punt yards
 * Primary key -> game_id and player_id
 * Foreign key -> game_id references game's game_id
*/
create table special_game_stats(
  player_id varchar(8),
  game_id varchar(12),
  field_goals int, 
  fg_attempts int, 
  extra_points int, 
  ep_attempts int, 
  punts int, 
  punt_yards int, 
  primary key(game_id,player_id),
  foreign key(player_id) references player(id), 
  foreign key(game_id) references game(game_id)
);
