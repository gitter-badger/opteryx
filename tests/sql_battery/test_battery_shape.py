"""
The best way to test a SQL engine is to throw queries at it.

We have three in-memory tables, one of natural satellite data, one of planet data and
one of astronaut data. These are both small to allow us to test the SQL engine quickly
and is guaranteed to be available whereever the tests are run.

These tests only test the shape of the response, more specific tests wil test values.
The point of these tests is that we can throw many variations of queries, such as
different whitespace and capitalization and ensure we get a sensible looking response.

We test the shape in this battery because if the shape isn't right, the response isn't
going to be right, and testing shape of an in-memory dataset is quick, we can test 100s
of queries in a few seconds.

Testing the shape doesn't mean the response is right though.
"""
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], "../.."))

import opteryx

import pyarrow
import pytest

from opteryx.utils.arrow import fetchmany
from opteryx.utils.display import ascii_table
from opteryx.storage.adapters import DiskStorage


# fmt:off
STATEMENTS = [
        ("SELECT * FROM $satellites", 177, 8),
        ("SELECT * FROM $satellites;", 177, 8),
        ("SELECT * FROM $satellites\n;", 177, 8),
        ("select * from $satellites", 177, 8),
        ("Select * From $satellites", 177, 8),
        ("SELECT   *   FROM   $satellites", 177, 8),
        ("SELECT\n\t*\n  FROM\n\t$satellites", 177, 8),
        ("\n\n\n\tSELECT * FROM $satellites", 177, 8),
        ("SELECT $satellites.* FROM $satellites", 177, 8),
        ("SELECT s.* FROM $satellites AS s", 177, 8),
        ("SELECT * FROM $satellites WHERE name = 'Calypso'", 1, 8),
        ("SELECT * FROM $satellites WHERE (name = 'Calypso')", 1, 8),
        ("SELECT * FROM $satellites WHERE NOT name = 'Calypso'", 176, 8),
        ("SELECT * FROM $satellites WHERE NOT (name = 'Calypso')", 176, 8),
        ("SELECT * FROM $satellites WHERE `name` = 'Calypso'", 1, 8),
        ("select * from $satellites where name = 'Calypso'", 1, 8),
        ("SELECT * FROM $satellites WHERE name <> 'Calypso'", 176, 8),
        ("SELECT * FROM $satellites WHERE name = '********'", 0, 8),
        ("SELECT * FROM $satellites WHERE name LIKE '_a_y_s_'", 1, 8),
        ("SELECT * FROM $satellites WHERE name LIKE 'Cal%'", 4, 8),
        ("SELECT * FROM $satellites WHERE name like 'Cal%'", 4, 8),
        ("SELECT * FROM $satellites WHERE `name` = 'Calypso'", 1, 8),
        ("SELECT * FROM `$satellites` WHERE name = 'Calypso'", 1, 8),
        ("SELECT * FROM `$satellites` WHERE `name` = 'Calypso'", 1, 8),
        ("SELECT * FROM $satellites WITH (NO_CACHE)", 177, 8),

        ("/* comment */ SELECT * FROM $satellites WHERE name = 'Calypso'", 1, 8),
        ("SELECT * FROM $satellites /* comment */ WHERE name = 'Calypso'", 1, 8),
        ("SELECT * FROM $satellites /* WHERE name = 'Calypso' */", 177, 8),
        ("SELECT * FROM $satellites -- WHERE name = 'Calypso'", 177, 8),
        ("SELECT * FROM $satellites -- WHERE name = 'Calypso' \n WHERE id = 1", 1, 8),
        ("-- comment\nSELECT * --comment\n FROM $satellites -- WHERE name = 'Calypso' \n WHERE id = 1", 1, 8),
        ("/* comment */ SELECT * FROM $satellites /* comment */  WHERE name = 'Calypso'", 1, 8),
        ("/* comment */ SELECT * FROM $satellites /* comment */  WHERE name = 'Calypso'  /* comment */ ", 1, 8),
        ("/* comment --inner */ SELECT * FROM $satellites WHERE name = 'Calypso'", 1, 8),
        ("SELECT * FROM $satellites -- comment\n FOR TODAY", 177, 8),
        ("SELECT * FROM $satellites /* comment */ FOR TODAY /* comment */", 177, 8),

        ("SELECT name, id, planetId FROM $satellites", 177, 3),
        ("SELECT name, name FROM $satellites", 177, 1),
        ("SELECT name, id, name, id FROM $satellites", 177, 2),

        ("SELECT DISTINCT name FROM $astronauts", 357, 1),
        ("SELECT DISTINCT * FROM $astronauts", 357, 19),
        ("SELECT DISTINCT birth_date FROM $astronauts", 348, 1),
        ("SELECT DISTINCT birth_place FROM $astronauts", 272, 1),
        ("SELECT DISTINCT death_date FROM $astronauts", 39, 1),
        ("SELECT DISTINCT missions FROM $astronauts", 305, 1),
        ("SELECT DISTINCT group FROM $astronauts", 21, 1),
        ("SELECT DISTINCT name, birth_date, missions, birth_place, group FROM $astronauts", 357, 5),

        ("SELECT name as Name FROM $satellites", 177, 1),
        ("SELECT name as Name, id as Identifier FROM $satellites", 177, 2),
        ("SELECT name as NAME FROM $satellites WHERE name = 'Calypso'", 1, 1),
        ("SELECT name as NAME FROM $satellites GROUP BY name", 177, 1),

        ("SELECT * FROM $satellites WHERE id = 5", 1, 8),
        ("SELECT * FROM $satellites WHERE name = 'Cal' || 'ypso'", 1, 8),
        ("SELECT * FROM $satellites WHERE name = 'C' || 'a' || 'l' || 'y' || 'p' || 's' || 'o'", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 5 * 1 AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 10 / 2 AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 3 + 2 AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE id + 2 = 7 AND name = 'Europa'", 1, 8),

        ("SELECT * FROM $satellites WHERE magnitude = 5.29", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 5 AND magnitude = 5.29", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 5 AND magnitude = 1", 0, 8),
        ("SELECT * FROM $satellites WHERE id = 5 AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE (id = 5) AND (name = 'Europa')", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 5 OR name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE id = 5 OR name = 'Moon'", 2, 8),
        ("SELECT * FROM $satellites WHERE id < 3 AND (name = 'Europa' OR name = 'Moon')", 1, 8),
        ("SELECT * FROM $satellites WHERE id BETWEEN 5 AND 8", 4, 8),
        ("SELECT * FROM $satellites WHERE id NOT BETWEEN 5 AND 8", 173, 8),
        ("SELECT * FROM $satellites WHERE ((id BETWEEN 5 AND 10) AND (id BETWEEN 10 AND 12)) OR name = 'Moon'", 2, 8),
        ("SELECT * FROM $satellites WHERE id BETWEEN 5 AND 8 OR name = 'Moon'", 5, 8),
        ("SELECT * FROM $satellites WHERE id IN (5,6,7,8)", 4, 8),
        ("SELECT * FROM $satellites WHERE id IN (5,6,7,8) AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE (id IN (5,6,7,8)) AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE (id IN (5,6,7,8) AND name = 'Europa')", 1, 8),
        ("SELECT * FROM $satellites WHERE id IN (5,6,7,8) OR name = 'Moon'", 5, 8),
        ("SELECT * FROM $satellites WHERE (id = 5 OR id = 6 OR id = 7 OR id = 8) AND name = 'Europa'", 1, 8),
        ("SELECT * FROM $satellites WHERE (id = 6 OR id = 7 OR id = 8) OR name = 'Europa'", 4, 8),
        ("SELECT * FROM $satellites WHERE id = 5 OR id = 6 OR id = 7 OR id = 8 OR name = 'Moon'", 5, 8),
        ("SELECT * FROM $satellites WHERE planetId = id", 1, 8),
        ("SELECT * FROM $satellites WHERE planetId > 8", 5, 8),
        ("SELECT * FROM $satellites WHERE planetId >= 8", 19, 8),
        ("SELECT * FROM $satellites WHERE planetId < 5", 3, 8),
        ("SELECT * FROM $satellites WHERE planetId <= 5", 70, 8),
        ("SELECT * FROM $satellites WHERE planetId <> 5", 110, 8),
        ("SELECT * FROM $satellites WHERE name LIKE 'C%'", 12, 8),
        ("SELECT * FROM $satellites WHERE name LIKE 'M__n'", 1, 8),
        ("SELECT * FROM $satellites WHERE name LIKE '%c%'", 11, 8),
        ("SELECT * FROM $satellites WHERE name ILIKE '%c%'", 23, 8),
        ("SELECT * FROM $satellites WHERE name NOT LIKE '%c%'", 166, 8),
        ("SELECT * FROM $satellites WHERE name NOT ILIKE '%c%'", 154, 8),
        ("SELECT * FROM $satellites WHERE name ~ '^C.'", 12, 8),
        ("SELECT * FROM $satellites WHERE name SIMILAR TO '^C.'", 12, 8),
        ("SELECT * FROM $satellites WHERE name !~ '^C.'", 165, 8),
        ("SELECT * FROM $satellites WHERE name NOT SIMILAR TO '^C.'", 165, 8),
        ("SELECT * FROM $satellites WHERE name ~* '^c.'", 12, 8),
        ("SELECT * FROM $satellites WHERE name !~* '^c.'", 165, 8),

        ("SELECT COUNT(*) FROM $satellites", 1, 1),
        ("SELECT count(*) FROM $satellites", 1, 1),
        ("SELECT COUNT (*) FROM $satellites", 1, 1),
        ("SELECT\nCOUNT\n(*)\nFROM\n$satellites", 1, 1),
        ("SELECT Count(*) FROM $satellites", 1, 1),
        ("SELECT Count(*) FROM $satellites WHERE name = 'sputnik'", 1, 1),
        ("SELECT COUNT(name) FROM $satellites", 1, 1),
        ("SELECT COUNT(*) FROM $satellites GROUP BY name", 177, 1),
        ("SELECT COUNT(*) FROM $satellites GROUP BY planetId", 7, 1),
        ("SELECT COUNT(*) FROM $satellites GROUP\nBY planetId", 7, 1),
        ("SELECT COUNT(*) FROM $satellites GROUP     BY planetId", 7, 1),
        ("SELECT COUNT(*), planetId FROM $satellites GROUP BY planetId", 7, 2),
        ("SELECT COUNT(*), planetId FROM $satellites WHERE planetId < 6 GROUP BY planetId", 3, 2),        
        ("SELECT COUNT(*), planetId FROM $satellites WHERE planetId <= 6 GROUP BY planetId", 4, 2),
        ("SELECT COUNT(*), planetId FROM $satellites WHERE name LIKE 'Cal%' GROUP BY planetId", 3, 2),
        
        ("SELECT DISTINCT planetId FROM $satellites", 7, 1),
        ("SELECT * FROM $satellites LIMIT 50", 50, 8),
        ("SELECT * FROM $satellites LIMIT 0", 0, 8),
        ("SELECT * FROM $satellites OFFSET 150", 27, 8),
        ("SELECT * FROM $satellites LIMIT 50 OFFSET 150", 27, 8),
        ("SELECT * FROM $satellites LIMIT 50 OFFSET 170", 7, 8),
        ("SELECT * FROM $satellites ORDER BY name", 177, 8),
        ("SELECT * FROM $satellites ORDER BY 1", 177, 8),
        ("SELECT * FROM $satellites ORDER BY 1 DESC", 177, 8),
        ("SELECT * FROM $satellites ORDER BY 2", 177, 8),
        ("SELECT * FROM $satellites ORDER BY 1, 2", 177, 8),
        ("SELECT * FROM $satellites ORDER BY 1 ASC", 177, 8),
        ("SELECT * FROM $satellites ORDER BY RANDOM()", 177, 8),

        ("SELECT MAX(planetId) FROM $satellites", 1, 1),
        ("SELECT MIN(planetId) FROM $satellites", 1, 1),
        ("SELECT SUM(planetId) FROM $satellites", 1, 1),
        ("SELECT MAX(id), planetId FROM $satellites GROUP BY planetId", 7, 2),
        ("SELECT MIN(id), planetId FROM $satellites GROUP BY planetId", 7, 2),
        ("SELECT SUM(id), planetId FROM $satellites GROUP BY planetId", 7, 2),
        ("SELECT MIN(id), MAX(id), SUM(planetId), planetId FROM $satellites GROUP BY planetId", 7, 4),
        ("SELECT planetId, LIST(name) FROM $satellites GROUP BY planetId", 7, 2),

        ("SELECT BOOLEAN(planetId) FROM $satellites GROUP BY planetId, BOOLEAN(planetId)", 7, 1),
        ("SELECT VARCHAR(planetId) FROM $satellites GROUP BY planetId, VARCHAR(planetId)", 7, 1),
        ("SELECT TIMESTAMP(planetId) FROM $satellites GROUP BY planetId, TIMESTAMP(planetId)", 7, 1),
        ("SELECT NUMERIC(planetId) FROM $satellites GROUP BY planetId, NUMERIC(planetId)", 7, 1),
        ("SELECT CAST(planetId AS BOOLEAN) FROM $satellites", 177, 1),
        ("SELECT CAST(planetId AS VARCHAR) FROM $satellites", 177, 1),
        ("SELECT CAST(planetId AS TIMESTAMP) FROM $satellites", 177, 1),
        ("SELECT CAST(planetId AS NUMERIC) FROM $satellites", 177, 1),
        ("SELECT TRY_CAST(planetId AS BOOLEAN) FROM $satellites", 177, 1),
        ("SELECT TRY_CAST(planetId AS VARCHAR) FROM $satellites", 177, 1),
        ("SELECT TRY_CAST(planetId AS TIMESTAMP) FROM $satellites", 177, 1),
        ("SELECT TRY_CAST(planetId AS NUMERIC) FROM $satellites", 177, 1),

        ("SELECT PI()", 1, 1),
        ("SELECT GET(name, 1) FROM $satellites GROUP BY planetId, GET(name, 1)", 56, 1),
        ("SELECT COUNT(*), ROUND(magnitude) FROM $satellites group by ROUND(magnitude)", 22, 2),
        ("SELECT ROUND(magnitude) FROM $satellites group by ROUND(magnitude)", 22, 1),
        ("SELECT ROUND(magnitude, 1) FROM $satellites group by ROUND(magnitude, 1)", 88, 1),
        ("SELECT VARCHAR(planetId), COUNT(*) FROM $satellites GROUP BY 1", 7, 2),
        ("SELECT LEFT(name, 1), COUNT(*) FROM $satellites GROUP BY 1 ORDER BY 2 DESC", 21, 2),
        ("SELECT LEFT(name, 2) as le, COUNT(*) FROM $satellites GROUP BY 1 ORDER BY 2 DESC", 87, 2),
        ("SELECT RIGHT(name, 10), COUNT(*) FROM $satellites GROUP BY 1 ORDER BY 2 DESC", 177, 2),
        ("SELECT RIGHT(name, 2) as le, COUNT(*) FROM $satellites GROUP BY 1 ORDER BY 2 DESC", 30, 2),
        ("SELECT round(magnitude) FROM $satellites group by round(magnitude)", 22, 1),
        ("SELECT upper(name) as NAME, id as Identifier FROM $satellites", 177, 2),
        ("SELECT upper(name), lower(name), id as Identifier FROM $satellites", 177, 3),

        ("SELECT planetId, Count(*) FROM $satellites group by planetId having count(*) > 5", 4, 2),
        ("SELECT planetId, min(magnitude) FROM $satellites group by planetId having min(magnitude) > 5", 5, 2),
        ("SELECT planetId, min(magnitude) FROM $satellites group by planetId having min(magnitude) > 5 limit 2 offset 1", 2, 2),
        ("SELECT planetId, count(*) FROM $satellites group by planetId order by count(*) desc", 7, 2),
        ("SELECT planetId, count(*) FROM $satellites group by planetId order by planetId desc", 7, 2),
        ("SELECT planetId, count(*) FROM $satellites group by planetId order by planetId, count(*) desc", 7, 2),
        ("SELECT planetId, count(*) FROM $satellites group by planetId order by count(*), planetId desc", 7, 2),

        ("SELECT * FROM $satellites order by name", 177, 8),
        ("SELECT * FROM $satellites order by name desc", 177, 8),
        ("SELECT name FROM $satellites order by name", 177, 1),
        ("SELECT * FROM $satellites order by magnitude, name", 177, 8),

        ("SELECT planetId as pid FROM $satellites", 177, 1),
        ("SELECT planetId as pid, round(magnitude) FROM $satellites", 177, 2),
        ("SELECT planetId as pid, round(magnitude) as minmag FROM $satellites", 177, 2),
        ("SELECT planetId as pid, round(magnitude) as roundmag FROM $satellites", 177, 2),

        ("SELECT GET(birth_place, 'town') FROM $astronauts", 357, 1),
        ("SELECT GET(missions, 0) FROM $astronauts", 357, 1),
        ("SELECT GET(birth_place, 'town') FROM $astronauts WHERE GET(birth_place, 'town') = 'Warsaw'", 1, 1),
        ("SELECT COUNT(*), GET(birth_place, 'town') FROM $astronauts GROUP BY GET(birth_place, 'town')", 264, 2),
        ("SELECT birth_place['town'] FROM $astronauts", 357, 1),
        ("SELECT missions[0] FROM $astronauts", 357, 1),

        ("SELECT birth_place['town'] FROM $astronauts WHERE birth_place['town'] = 'Warsaw'", 1, 1),
        ("SELECT birth_place['town'] AS TOWN FROM $astronauts WHERE birth_place['town'] = 'Warsaw'", 1, 1),
        ("SELECT COUNT(*), birth_place['town'] FROM $astronauts GROUP BY birth_place['town']", 264, 2),
        ('SELECT LENGTH(missions) FROM $astronauts', 357, 1),
        ('SELECT LENGTH(missions) FROM $astronauts WHERE LENGTH(missions) > 6', 2, 1),

        ("SELECT birth_date FROM $astronauts", 357, 1),
        ("SELECT YEAR(birth_date) FROM $astronauts", 357, 1),
        ("SELECT YEAR(birth_date) FROM $astronauts WHERE YEAR(birth_date) < 1930", 14, 1),

        ("SELECT RANDOM() FROM $planets", 9, 1),
        ("SELECT NOW() FROM $planets", 9, 1),
        ("SELECT TODAY() FROM $planets", 9, 1),
        ("SELECT CURRENT_DATE", 1, 1),
        ("SELECT CURRENT_DATE()", 1, 1),
        ("SELECT CURRENT_TIME", 1, 1),
        ("SELECT CURRENT_TIME()", 1, 1),
        ("SELECT YEAR(birth_date), COUNT(*) FROM $astronauts GROUP BY YEAR(birth_date)", 54, 2),
        ("SELECT MONTH(birth_date), COUNT(*) FROM $astronauts GROUP BY MONTH(birth_date)", 12, 2),

        ("SELECT DATE_FORMAT(birth_date, '%d-%Y') FROM $astronauts", 357, 1),
        ("SELECT DATE_FORMAT(birth_date, 'dddd') FROM $astronauts", 357, 1),
        ("SELECT DATE_FORMAT(death_date, '%Y') FROM $astronauts", 357, 1),

        ("SELECT count(*), VARCHAR(year) FROM $astronauts GROUP BY VARCHAR(year)", 21, 2),
        ("SELECT count(*), CAST(year AS VARCHAR) FROM $astronauts GROUP BY CAST(year AS VARCHAR)", 21, 2),

        ("SELECT RANDOM()", 1, 1),
        ("SELECT NOW()", 1, 1),
        ("SELECT NOW() from $planets", 9, 1),
        ("SELECT TODAY()", 1, 1),
        ("SELECT HASH('hello')", 1, 1),
        ("SELECT MD5('hello')", 1, 1),
        ("SELECT UPPER('upper'), LOWER('LOWER')", 1, 2),

        ("SELECT HASH(name), name from $astronauts", 357, 2),
        ("SELECT HASH(death_date), death_date from $astronauts", 357, 2),
        ("SELECT HASH(birth_place), birth_place from $astronauts", 357, 2),
        ("SELECT HASH(missions), missions from $astronauts", 357, 2),

        ("SELECT * FROM (VALUES ('High', 3),('Medium', 2),('Low', 1)) AS ratings(name, rating)", 3, 2),
        ("SELECT * FROM (VALUES ('High', 3),('Medium', 2),('Low', 1)) AS ratings(name, rating) WHERE rating = 3", 1, 2),

        ("SELECT * FROM UNNEST(('foo', 'bar', 'baz', 'qux', 'corge', 'garply', 'waldo', 'fred')) AS element", 8, 1),
        ("SELECT * FROM UNNEST(('foo', 'bar', 'baz', 'qux', 'corge', 'garply', 'waldo', 'fred')) AS element WHERE element LIKE '%e%'", 2, 1),
        ("SELECT * FROM UNNEST(('foo', 'bar', 'baz', 'qux', 'corge', 'garply', 'waldo', 'fred'))", 8, 1),
        ("SELECT * FROM UNNEST(('foo', 'bar', 'baz', 'qux', 'corge', 'garply', 'waldo', 'fred')) WHERE unnest LIKE '%e%'", 2, 1),

        ("SELECT * FROM generate_series(10)", 10, 1),
        ("SELECT * FROM generate_series(-10,10)", 21, 1),
        ("SELECT * FROM generate_series(2,10,2)", 5, 1),
        ("SELECT * FROM generate_series(0.5,10,0.5)", 20, 1),
        ("SELECT * FROM generate_series(2,11,2)", 5, 1),
        ("SELECT * FROM generate_series(2,10,2) AS nums", 5, 1),
        ("SELECT * FROM generate_series(2,10,2) WHERE generate_series > 5", 3, 1),
        ("SELECT * FROM generate_series(2,10,2) AS nums WHERE nums < 5", 2, 1),
        ("SELECT * FROM generate_series(2) WITH (NO_CACHE)", 2, 1),

        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1 month')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1 mon')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1mon')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1mo')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1mth')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1 months')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '1 day')", 365, 1),
        ("SELECT * FROM generate_series('2020-01-01', '2020-12-31', '1day')", 366, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-12-31', '7 days')", 53, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-01-02', '1 hour')", 25, 1),
        ("SELECT * FROM generate_series('2022-01-01', '2022-01-01 23:59', '1 hour')", 24, 1),
        ("SELECT * FROM generate_series('2022-01-01 12:00', '2022-01-01 23:59', '1 hour')", 12, 1),
        ("SELECT * FROM generate_series('2022-01-01 12:00', '2022-01-01 12:15', '1 minute')", 16, 1),
        ("SELECT * FROM generate_series('2022-01-01 12:00', '2022-01-01 12:15', '1m30s')", 11, 1),
        ("SELECT * FROM generate_series(1,10) LEFT JOIN $planets ON id = generate_series", 10, 21),
        ("SELECT * FROM generate_series(1,5) JOIN $planets ON id = generate_series", 5, 21),
        ("SELECT * FROM (SELECT * FROM generate_series(1,10,2) AS gs) INNER JOIN $planets on gs = id", 5, 21),

        ("SELECT * FROM generate_series('192.168.1.0/28')", 16, 1),
        ("SELECT * FROM generate_series('192.168.1.100/29')", 8, 1),

        ("SELECT * FROM tests.data.dated WITH (NO_CACHE) FOR '2020-02-03'", 25, 8),
        ("SELECT * FROM tests.data.dated FOR '2020-02-03'", 25, 8),
        ("SELECT * FROM tests.data.dated FOR '2020-02-04'", 25, 8),
        ("SELECT * FROM tests.data.dated FOR DATES BETWEEN '2020-02-01' AND '2020-02-28'", 50, 8),
        ("SELECT * FROM tests.data.dated FOR '2020-02-03' OFFSET 1", 24, 8),
        ("SELECT * FROM tests.data.dated FOR DATES BETWEEN '2020-02-01' AND '2020-02-28' OFFSET 1", 49, 8),
        ("SELECT * FROM $satellites FOR YESTERDAY ORDER BY planetId OFFSET 10", 167, 8),

        ("SELECT * FROM tests.data.segmented FOR '2020-02-03'", 25, 8),

        ("SELECT * FROM $astronauts WHERE death_date IS NULL", 305, 19),
        ("SELECT * FROM $astronauts WHERE death_date IS NOT NULL", 52, 19),
        ("SELECT * FROM tests.data.formats.parquet WITH(NO_PARTITION) WHERE user_verified IS TRUE", 711, 13),
        ("SELECT * FROM tests.data.formats.parquet WITH(NO_PARTITION) WHERE user_verified IS FALSE", 99289, 13),

        ("SELECT * FROM $satellites FOR DATES IN LAST_MONTH ORDER BY planetId OFFSET 10", 167, 8),
        ("SELECT * FROM $satellites FOR DATES IN LAST_CYCLE ORDER BY planetId OFFSET 10", 167, 8),
        ("SELECT * FROM $satellites FOR DATES IN THIS_MONTH ORDER BY planetId OFFSET 10", 167, 8),
        ("SELECT * FROM $satellites FOR DATES IN THIS_CYCLE ORDER BY planetId OFFSET 10", 167, 8),

        ("SELECT missions FROM $astronauts WHERE LIST_CONTAINS(missions, 'Apollo 8')", 3, 1),
        ("SELECT missions FROM $astronauts WHERE LIST_CONTAINS_ANY(missions, ('Apollo 8', 'Apollo 13'))", 5, 1),
        ("SELECT missions FROM $astronauts WHERE LIST_CONTAINS_ALL(missions, ('Apollo 8', 'Gemini 7'))", 2, 1),
        ("SELECT missions FROM $astronauts WHERE LIST_CONTAINS_ALL(missions, ('Gemini 7', 'Apollo 8'))", 2, 1),

        ("SELECT * FROM $satellites WHERE planetId IN (SELECT id FROM $planets WHERE name = 'Earth')", 1, 8),
        ("SELECT * FROM $planets WHERE id NOT IN (SELECT DISTINCT planetId FROM $satellites)", 2, 20),
        ("SELECT name FROM $planets WHERE id IN (SELECT * FROM UNNEST((1,2,3)) as id)", 3, 1),
#        ("SELECT count(planetId) FROM (SELECT DISTINCT planetId FROM $satellites)", 1, 1),
        ("SELECT COUNT(*) FROM (SELECT planetId FROM $satellites WHERE planetId < 7) GROUP BY planetId", 4, 1),

        ("EXPLAIN SELECT * FROM $satellites", 1, 3),
        ("EXPLAIN SELECT * FROM $satellites WHERE id = 8", 2, 3),

        ("SHOW COLUMNS FROM $satellites", 8, 2),
        ("SHOW FULL COLUMNS FROM $satellites", 8, 6),
        ("SHOW EXTENDED COLUMNS FROM $satellites", 8, 12),
        ("SHOW EXTENDED COLUMNS FROM $planets", 20, 12),
        ("SHOW EXTENDED COLUMNS FROM $astronauts", 19, 12),
        ("SHOW COLUMNS FROM $satellites WHERE column_name ILIKE '%id'", 2, 2),
        ("SHOW COLUMNS FROM $satellites LIKE '%id'", 1, 2),
        ("SHOW COLUMNS FROM tests.data.dated FOR '2020-02-03'", 8, 2),

        ("SELECT * FROM $satellites CROSS JOIN $astronauts", 63189, 27),
        ("SELECT * FROM $satellites WITH (NO_CACHE) CROSS JOIN $astronauts WITH (NO_CACHE)", 63189, 27),
        ("SELECT * FROM $satellites, $planets", 1593, 28),
        ("SELECT * FROM $satellites INNER JOIN $planets USING (id)", 9, 28),
        ("SELECT * FROM $satellites WITH (NO_CACHE) INNER JOIN $planets USING (id)", 9, 28),
        ("SELECT * FROM $satellites WITH (NO_CACHE) INNER JOIN $planets WITH (NO_CACHE) USING (id)", 9, 28),
        ("SELECT * FROM $satellites INNER JOIN $planets WITH (NO_CACHE) USING (id)", 9, 28),
        ("SELECT * FROM $satellites JOIN $planets USING (id)", 9, 28),
        ("SELECT * FROM $astronauts CROSS JOIN UNNEST(missions) AS mission WHERE mission = 'Apollo 11'", 3, 20),
        ("SELECT * FROM $astronauts CROSS JOIN UNNEST(missions)", 869, 20),
        ("SELECT * FROM $planets INNER JOIN $satellites ON $planets.id = $satellites.planetId", 177, 28),
        ("SELECT DISTINCT planetId FROM $satellites LEFT OUTER JOIN $planets ON $satellites.planetId = $planets.id", 7, 1),
        ("SELECT DISTINCT planetId FROM $satellites LEFT JOIN $planets ON $satellites.planetId = $planets.id", 7, 1),
        ("SELECT DISTINCT $planets.id, $satellites.id FROM $planets LEFT OUTER JOIN $satellites ON $satellites.planetId = $planets.id", 179, 2),
        ("SELECT DISTINCT $planets.id, $satellites.id FROM $planets LEFT JOIN $satellites ON $satellites.planetId = $planets.id", 179, 2),
        ("SELECT planetId FROM $satellites LEFT JOIN $planets ON $satellites.planetId = $planets.id", 177, 1),

        ("SELECT DISTINCT planetId FROM $satellites RIGHT OUTER JOIN $planets ON $satellites.planetId = $planets.id", 8, 1),
        ("SELECT DISTINCT planetId FROM $satellites RIGHT JOIN $planets ON $satellites.planetId = $planets.id", 8, 1),
        ("SELECT planetId FROM $satellites RIGHT JOIN $planets ON $satellites.planetId = $planets.id", 179, 1),
        ("SELECT DISTINCT planetId FROM $satellites FULL OUTER JOIN $planets ON $satellites.planetId = $planets.id", 8, 1),
        ("SELECT DISTINCT planetId FROM $satellites FULL JOIN $planets ON $satellites.planetId = $planets.id", 8, 1),
        ("SELECT planetId FROM $satellites FULL JOIN $planets ON $satellites.planetId = $planets.id", 179, 1),

        ("SELECT pid FROM ( SELECT id AS pid FROM $planets) WHERE pid > 5", 4, 1),
        ("SELECT * FROM ( SELECT id AS pid FROM $planets) WHERE pid > 5", 4, 1),
        ("SELECT * FROM ( SELECT COUNT(planetId) AS moons, planetId FROM $satellites GROUP BY planetId ) WHERE moons > 10", 4, 2),

        ("SELECT * FROM $planets WHERE id = -1", 0, 20),
        ("SELECT COUNT(*) FROM (SELECT DISTINCT a FROM $astronauts CROSS JOIN UNNEST(alma_mater) AS a ORDER BY a)", 1, 1),

        ("SELECT a.id, b.id, c.id FROM $planets AS a INNER JOIN $planets AS b ON a.id = b.id INNER JOIN $planets AS c ON c.id = b.id", 9, 3),
        ("SELECT * FROM $planets AS a INNER JOIN $planets AS b ON a.id = b.id RIGHT OUTER JOIN $satellites AS c ON c.planetId = b.id", 177, 48),

        ("SELECT $planets.* FROM $satellites INNER JOIN $planets USING (id)", 9, 20),
        ("SELECT $satellites.* FROM $satellites INNER JOIN $planets USING (id)", 9, 8),
        ("SELECT $planets.* FROM $satellites INNER JOIN $planets AS p USING (id)", 9, 20),
        ("SELECT p.* FROM $satellites INNER JOIN $planets AS p USING (id)", 9, 20),
        ("SELECT s.* FROM $satellites AS s INNER JOIN $planets USING (id)", 9, 8),
        ("SELECT $satellites.* FROM $satellites AS s INNER JOIN $planets USING (id)", 9, 8),
        ("SELECT $satellites.* FROM $satellites AS s INNER JOIN $planets AS p USING (id)", 9, 8),
        ("SELECT s.* FROM $satellites AS s INNER JOIN $planets AS p USING (id)", 9, 8),

        ("SELECT DATE_TRUNC('month', birth_date) FROM $astronauts", 357, 1),
        ("SELECT DISTINCT * FROM (SELECT DATE_TRUNC('year', birth_date) AS BIRTH_YEAR FROM $astronauts)", 54, 1),
        ("SELECT DISTINCT * FROM (SELECT DATE_TRUNC('month', birth_date) AS BIRTH_YEAR_MONTH FROM $astronauts)", 247, 1),
        ("SELECT time_bucket(birth_date, 10, 'year') AS decade, count(*) from $astronauts GROUP BY time_bucket(birth_date, 10, 'year')", 6, 2),
        ("SELECT time_bucket(birth_date, 6, 'month') AS half, count(*) from $astronauts GROUP BY time_bucket(birth_date, 6, 'month')", 97, 2),
    
        ("SELECT graduate_major, undergraduate_major FROM $astronauts WHERE COALESCE(graduate_major, undergraduate_major, 'high school') = 'high school'", 4, 2),
        ("SELECT graduate_major, undergraduate_major FROM $astronauts WHERE COALESCE(graduate_major, undergraduate_major) = 'Aeronautical Engineering'", 41, 2),
        ("SELECT COALESCE(death_date, '2030-01-01') FROM $astronauts", 357, 1),

        ("SELECT SEARCH(name, 'al'), name FROM $satellites", 177, 2),
        ("SELECT name FROM $satellites WHERE SEARCH(name, 'al')", 18, 1),
        ("SELECT SEARCH(missions, 'Apollo 11'), missions FROM $astronauts", 357, 2),
        ("SELECT name FROM $astronauts WHERE SEARCH(missions, 'Apollo 11')", 3, 1),
        ("SELECT name, SEARCH(birth_place, 'Italy') FROM $astronauts", 357, 2),
        ("SELECT name, birth_place FROM $astronauts WHERE SEARCH(birth_place, 'Italy')", 1, 2),
        ("SELECT name, birth_place FROM $astronauts WHERE SEARCH(birth_place, 'Rome')", 1, 2),

        ("SELECT birth_date FROM $astronauts WHERE EXTRACT(year FROM birth_date) < 1930;", 14, 1),
        ("SELECT EXTRACT(month FROM birth_date) FROM $astronauts", 357, 1),
        ("SELECT EXTRACT(day FROM birth_date) FROM $astronauts", 357, 1),
        ("SELECT birth_date FROM $astronauts WHERE EXTRACT(year FROM birth_date) < 1930;", 14, 1),
        ("SELECT EXTRACT(doy FROM birth_date) FROM $astronauts", 357, 1),
        ("SELECT EXTRACT(DOY FROM birth_date) FROM $astronauts", 357, 1),
        ("SELECT EXTRACT(dow FROM birth_date) FROM $astronauts", 357, 1),
        ("SELECT EXTRACT(DOW FROM birth_date) FROM $astronauts", 357, 1),
        ("SELECT EXTRACT(YEAR FROM '2022-02-02')", 1, 1),
        ("SELECT DATE_FORMAT(birth_date, '%m-%y') FROM $astronauts", 357, 1),
        ("SELECT DATEDIFF('year', '2017-08-25', '2011-08-25') AS DateDiff;", 1, 1),
        ("SELECT DATEDIFF('days', '2022-07-07', birth_date) FROM $astronauts", 357, 1),
        ("SELECT DATEDIFF('minutes', birth_date, '2022-07-07') FROM $astronauts", 357, 1),
        ("SELECT EXTRACT(DOW FROM birth_date) AS DOW, COUNT(*) FROM $astronauts GROUP BY EXTRACT(DOW FROM birth_date) ORDER BY COUNT(*) DESC", 7, 2),


        ("SELECT * FROM tests.data.schema WITH(NO_PARTITION) ORDER BY 1", 2, 4),
        ("SELECT * FROM tests.data.schema WITH(NO_PARTITION, NO_PUSH_PROJECTION) ORDER BY 1", 2, 4),
        ("SELECT * FROM $planets WITH(NO_PARTITION) ORDER BY 1", 9, 20),
        ("SELECT * FROM $planets WITH(NO_PUSH_PROJECTION) ORDER BY 1", 9, 20),
        ("SELECT * FROM $planets WITH(NO_PARTITION, NO_PUSH_PROJECTION) ORDER BY 1", 9, 20),

        ("SELECT APPROXIMATE_MEDIAN(radius) AS AM FROM $satellites GROUP BY planetId HAVING APPROXIMATE_MEDIAN(radius) > 5;", 5, 1),
        ("SELECT APPROXIMATE_MEDIAN(radius) AS AM FROM $satellites GROUP BY planetId HAVING AM > 5;", 5, 1),
        ("SELECT COUNT(planetId) FROM $satellites", 1, 1),
        ("SELECT COUNT_DISTINCT(planetId) FROM $satellites", 1, 1),
        ("SELECT LIST(name), planetId FROM $satellites GROUP BY planetId", 7, 2),
        ("SELECT ONE(name), planetId FROM $satellites GROUP BY planetId", 7, 2),
        ("SELECT MAX(planetId) FROM $satellites", 1, 1),
        ("SELECT MAXIMUM(planetId) FROM $satellites", 1, 1),
        ("SELECT MEAN(planetId) FROM $satellites", 1, 1),
        ("SELECT AVG(planetId) FROM $satellites", 1, 1),
        ("SELECT AVERAGE(planetId) FROM $satellites", 1, 1),
        ("SELECT MIN(planetId) FROM $satellites", 1, 1),
        ("SELECT MIN_MAX(planetId) FROM $satellites", 1, 1),
#        ("SELECT MODE(planetId) FROM $satellites", 1, 1),
        ("SELECT PRODUCT(planetId) FROM $satellites", 1, 1),
        ("SELECT STDDEV(planetId) FROM $satellites", 1, 1),
        ("SELECT SUM(planetId) FROM $satellites", 1, 1),
#        ("SELECT QUANTILES(planetId) FROM $satellites", 1, 1),
        ("SELECT VARIANCE(planetId) FROM $satellites", 1, 1),

        ("SELECT name || ' ' || name FROM $planets", 9, 1),
        ("SELECT 32 * 12", 1, 1),
        ("SELECT 9 / 12", 1, 1),
        ("SELECT 3 + 3", 1, 1),
        ("SELECT 12 % 2", 1, 1),
        ("SELECT 10 - 10", 1, 1),
        ("SELECT * FROM $satellites WHERE planetId = 2 + 5", 27, 8),
        ("SELECT * FROM $satellites WHERE planetId = round(density)", 1, 8),
        ("SELECT * FROM $satellites WHERE planetId * 1 = round(density * 1)", 1, 8),
        ("SELECT ABSOLUTE(ROUND(gravity) * density * density) FROM $planets", 9, 1),
        ("SELECT COUNT(*), ROUND(gm) FROM $satellites GROUP BY ROUND(gm)", 22, 2),
        ("SELECT COALESCE(death_date, '1900-01-01') FROM $astronauts", 357, 1),

        # These are queries which have been found to return the wrong result or not run correctly
        # FILTERING ON FUNCTIONS
        ("SELECT DATE(birth_date) FROM $astronauts FOR TODAY WHERE DATE(birth_date) < '1930-01-01'", 14, 1),
        # ORDER OF CLAUSES
        ("SELECT * FROM $planets FOR '2022-03-03' INNER JOIN $satellites ON $planets.id = $satellites.planetId", 177, 28),
        # ZERO RECORD RESULT SETS
        ("SELECT * FROM $planets WHERE id = -1 ORDER BY id", 0, 20),
        ("SELECT * FROM $planets WHERE id = -1 LIMIT 10", 0, 20),
        # LEFT JOIN THEN FILTER ON NULLS
        ("SELECT * FROM $planets LEFT JOIN $satellites ON $satellites.planetId = $planets.id WHERE $satellites.id IS NULL", 2, 28),
        ("SELECT * FROM $planets LEFT JOIN $satellites ON $satellites.planetId = $planets.id WHERE $satellites.name IS NULL", 2, 28),
        # SORT BROKEN
        ("SELECT * FROM (SELECT * FROM $planets ORDER BY id DESC LIMIT 5) WHERE id > 7", 2, 20),
        # ORDER OF JOIN CONDITION
        ("SELECT * FROM $planets INNER JOIN $satellites ON $satellites.planetId = $planets.id", 177, 28),
        # ORDER BY QUALIFIED IDENTIFIER
        ("SELECT * FROM $planets LEFT JOIN $satellites ON $satellites.planetId = $planets.id ORDER BY $planets.name", 179, 28),
        # NAMED SUBQUERIES
        ("SELECT P.name FROM ( SELECT * FROM $planets ) AS P", 9, 1),
        # UNNEST
        ("SELECT * FROM tests.data.unnest_test CROSS JOIN UNNEST (values) AS value FOR '2000-01-01'", 15, 3),
        # FRAME HANDLING
        ("SELECT * FROM tests.data.framed FOR '2021-03-28'", 100000, 1),
        ("SELECT * FROM tests.data.framed FOR '2021-03-29'", 100000, 1),
        ("SELECT * FROM tests.data.framed FOR DATES BETWEEN '2021-03-28' AND '2021-03-29'", 200000, 1),
        ("SELECT * FROM tests.data.framed FOR DATES BETWEEN '2021-03-29' AND '2021-03-30'", 100000, 1),
        ("SELECT * FROM tests.data.framed FOR DATES BETWEEN '2021-03-28' AND '2021-03-30'", 200000, 1),
        # DOESN'T WORK WITH LARGE DATASETS (#179)
        ("SELECT * FROM (SELECT COUNT(*), column_1 FROM FAKE(5000,2) GROUP BY column_1 ORDER BY COUNT(*)) LIMIT 5", 5, 2),
        # FILTER CREATION FOR 3 OR MORE ANDED PREDICATES FAILS (#182)
        ("SELECT * FROM $astronauts WHERE name LIKE '%o%' AND `year` > 1900 AND gender ILIKE '%ale%' AND group IN (1,2,3,4,5,6)", 41, 19),
        # LIKE-ING NULL
        ("SELECT * FROM tests.data.nulls WHERE username LIKE 'BBC%' FOR '2000-01-01'", 3, 5),
        ("SELECT * FROM tests.data.nulls WHERE username ILIKE 'BBC%' FOR '2000-01-01'", 3, 5),
        ("SELECT * FROM tests.data.nulls WHERE username NOT LIKE 'BBC%' FOR '2000-01-01'", 21, 5),
        ("SELECT * FROM tests.data.nulls WHERE NOT username LIKE 'BBC%' FOR '2000-01-01'", 22, 5),
        ("SELECT * FROM tests.data.nulls WHERE username NOT ILIKE 'BBC%' FOR '2000-01-01'", 21, 5),
        ("SELECT * FROM tests.data.nulls WHERE username ~ 'BBC.+' FOR '2000-01-01'", 3, 5),
        ("SELECT * FROM tests.data.nulls WHERE tweet ILIKE '%Trump%' FOR '2000-01-01'", 0, 5),
        # BYTE-ARRAY FAILS #252
        (b"SELECT * FROM $satellites", 177, 8),
        # DISTINCT on null values #285
        ("SELECT DISTINCT name FROM (VALUES (null),(null),('apple')) AS booleans (name)", 2, 1),
        # empty aggregates with other columns, loose the other columns #281
# [#358]       ("SELECT name, COUNT(*) FROM $astronauts WHERE name = 'Jim' GROUP BY name", 1, 2),
        # JOIN from subquery regressed #291
        ("SELECT * FROM (SELECT id from $planets) AS ONE LEFT JOIN (SELECT id from $planets) AS TWO ON id = id", 9, 2),
        # JOIN on UNNEST #382
        ("SELECT name FROM $planets INNER JOIN UNNEST(('Earth')) AS n on name = n ", 1, 1),
        ("SELECT name FROM $planets INNER JOIN UNNEST(('Earth', 'Mars')) AS n on name = n", 2, 1),
    ]
# fmt:on


@pytest.mark.parametrize("statement, rows, columns", STATEMENTS)
def test_sql_battery(statement, rows, columns):
    """
    Test an battery of statements
    """

    opteryx.storage.register_prefix("tests", DiskStorage)

    conn = opteryx.connect()
    cursor = conn.cursor()
    cursor.execute(statement)

    cursor._results = list(cursor._results)
    if cursor._results:
        result = pyarrow.concat_tables(cursor._results, promote=True)
        actual_rows, actual_columns = result.shape
    else:  # pragma: no cover
        result = None
        actual_rows, actual_columns = 0, 0

    assert (
        rows == actual_rows
    ), f"Query returned {actual_rows} rows but {rows} were expected, {statement}\n{ascii_table(fetchmany(result, limit=10), limit=10)}"
    assert (
        columns == actual_columns
    ), f"Query returned {actual_columns} cols but {columns} were expected, {statement}\n{ascii_table(fetchmany(result, limit=10), limit=10)}"


if __name__ == "__main__":  # pragma: no cover

    print(f"RUNNING BATTERY OF {len(STATEMENTS)} SHAPE TESTS")
    for index, (statement, rows, cols) in enumerate(STATEMENTS):
        print(f"{index:04}", statement)
        test_sql_battery(statement, rows, cols)

    print("✅ okay")
