-- #1 -------------------------------------------------------
/*
A Colt’s fan wants to learn more about the subtotals and grand
totals of the offensive player’s yards run on the Colt’s team. 
Using rollup, list how many yards (rush yards and pass yards) 
each offensive player has gained on a team in a given year, 
and then how many rush yards and pass yards they have gained 
by each position in the 2023 season. 
*/
SELECT NAME,
       position,
       Sum(passing_yards) AS pass_yards,
       Sum(rushing_yards) AS rush_yards
FROM   player,
       offense_game_stats ogs,
       game
WHERE  player.id = ogs.player_id
       AND ogs.game_id = game.game_id
       AND player.team = 'Colts'
       AND game.season_year = 2023
GROUP  BY rollup( position, NAME )
ORDER  BY position,
          NAME; 


-- #2 -------------------------------------------------------
/*
A sport’s analyst wants to create a report about quarterbacks rank 
based on the number of yards thrown. List the rankings of the 
quarterback's names in ascending order (Having the rank 1 quarterback 
at the top) along with the total number of yards thrown for each quarterback.
*/
SELECT NAME,
       Rank()
         OVER (
           ORDER BY passing_yards DESC) AS rank,
       passing_yards
FROM   (SELECT NAME,
               Sum(passing_yards) AS passing_yards
        FROM   player,
               offense_game_stats ogs
        WHERE  ogs.player_id = player.id
               AND player.position = 'QB'
        GROUP  BY NAME) AS qb_yards; 

	 
-- #3 -------------------------------------------------------
/*
NFL defensive coaches want to analyze the key defensive player positions
(linebacker, safety/defensive backs) on their opponents’ teams. Create
a query that shows the total number of tackles performed by these 
positions by pivoting about the position names. Include the name of 
the team as well.
*/
SELECT   team,
         Sum(tackles) filter (WHERE position LIKE '%LB') AS line_backers,
         sum(tackles) filter (WHERE position LIKE '%S'
OR       position = 'DB') AS safetys
FROM     player
JOIN     defense_game_stats
ON       (
                  player.id = defense_game_stats.player_id)
GROUP BY team
ORDER BY team;

-- #4 -------------------------------------------------------
/*
NFL fans want to know about old players (above the age of 30) in 
the NFL league who play on key special teams positions (kicker, 
punter, kick returner, punt returner). Find players that play in 
the current season as a kicker (K), punter (P), kick returner (KR) 
or punt returner (PR) and who are over the age of 30. Include the 
age of these player’s as well.
*/
SELECT DISTINCT NAME,
                age
FROM   (SELECT NAME,
               age,
               position
        FROM   player
               JOIN special_game_stats
                 ON player.id = special_game_stats.player_id
        WHERE  age > 30) AS special_player_age
WHERE  position IN ( 'K', 'P', 'KR', 'PR' )
ORDER  BY age; 

-- #5 -------------------------------------------------------
/*
A Colts fan wants to know what teams the Colts have won against 
in the 2023 season. Write a query that lists every team the Colts 
have won against and the date their game occurred.
*/
SELECT DISTINCT game_date,
                CASE
                  WHEN home_team = 'Colts'
                       AND home_score > away_score THEN away_team
                  WHEN away_team = 'Colts'
                       AND away_score > home_score THEN home_team
                END AS wins
FROM   game
WHERE  ( ( home_team = 'Colts'
           AND home_score > away_score )
          OR ( away_team = 'Colts'
               AND away_score > home_score ) )
       AND season_year = 2023; 

-- #6 -------------------------------------------------------
/*
AA sports analyst regularly needs to access the data from previous 
year’s SuperBowls for comparison. Create a function that accepts a 
season year as input and outputs the data for that season’s 
superbowl including: Superbowl number, participating teams, and 
each team’s score. 
*/
CREATE OR REPLACE FUNCTION superbowl_info (input_year numeric(4,0))
	RETURNS TABLE(SuperBowl_Num int,
				 team1 varchar(50), team2 varchar(50), 
				  team1_score int, team2_score int)
				  AS $$
	BEGIN
		RETURN QUERY
		SELECT (input_year::int - 1965) as SuperBowl_Num,
				home_team, away_team, home_score, away_score
		FROM game
		WHERE season_year = input_year
		AND week = 'SuperBowl';
	END;
	$$ LANGUAGE plpgsql;
-- Calling the function (2023 is an example input year)
Select *
From superbowl_info(2023);

-- #7 -------------------------------------------------------
/*
An offensive NFL coach wants to know more about the quarterback 
Patrick Mahomes' progress in cumulative passing yards. Create a 
window showing the progress of Patrick Mahomes by cumulative 
passing yards thrown each game date he plays in the current 
regular season.
*/
SELECT name,
       game_date,
       SUM(passing_yards)
         over (
           PARTITION BY name
           ORDER BY game_date ROWS BETWEEN unbounded preceding AND CURRENT ROW)
       AS
       cumulative_passing_yards
FROM   (SELECT p.name AS name,
               g.game_date,
               o.passing_yards
        FROM   player p
               join offense_game_stats o
                 ON p.id = o.player_id
               join game g
                 ON o.game_id = g.game_id
        WHERE  p.name = 'Patrick Mahomes') AS player_stats
ORDER  BY name,
          game_date; 

-- #8 -------------------------------------------------------
/* 
A new fan wants to choose a favorite team. 
He wants a team that frequently makes it to the AFC or NFC 
conference championship game, meaning they frequently have good seasons. 
Create a view that will display the home and away teams for the conference 
championship games, organized by year and which championship they belonged to.
*/

CREATE OR replace VIEW final_four_teams_by_year
AS
  SELECT season_year,
         home_team,
         away_team,
         Substring(division, 1, 3) AS conference
  FROM   game
         join team
           ON ( game.home_team = team.mascot )
  WHERE  game.week = 'ConfChamp'
  ORDER  BY season_year DESC,
            conference ASC;

-- Querying view			
SELECT *
FROM   final_four_teams_by_year; 

			
-- #9 -------------------------------------------------------
/*
The fan from the above question now wants to move to the location of 
the stadium that has hosted the most conference championship games. 
Rank the stadiums by the number of conference championship games they 
have hosted. Include their city and state.
*/
SELECT Rank()
         OVER (
           ORDER BY Count(*) DESC) AS stadium_rank,
       stadium.NAME,
       Count(*)                    AS playoff_count,
       stadium.city,
       stadium.state
FROM   final_four_teams_by_year
       JOIN team
         ON ( home_team = mascot )
       JOIN stadium
         ON ( home_city = stadium.city
              AND home_state = stadium.state )
GROUP  BY stadium.NAME,
          stadium.city,
          stadium.state; 


-- #10 ------------------------------------------------------
/* 
A common point of pride for an NFL team is how many Super Bowl 
championship games they have won throughout their history. Create 
a query that ranks teams by Super Bowl wins, excluding teams that 
have not won a SuperBowl. 
*/
SELECT Rank()
         OVER (
           ORDER BY Count(*) DESC ) AS team_rank,
       mascot,
       Count(*)                     AS super_bowl_championships
FROM   ((SELECT *
         FROM   game
                JOIN team
                  ON ( team.mascot = game.home_team )
         WHERE  game.home_score > game.away_score)
        UNION
        (SELECT *
         FROM   game
                JOIN team
                  ON ( team.mascot = game.away_team )
         WHERE  game.away_score > game.home_score)) AS all_team_games
WHERE  week = 'SuperBowl'
GROUP  BY mascot; 


