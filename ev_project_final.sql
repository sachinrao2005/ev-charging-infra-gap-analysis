-- ============================================================
-- EV CHARGING INFRASTRUCTURE GAP ANALYSIS — FULL PIPELINE
-- ============================================================
-- Story in one line: identify which Indian states have the
-- biggest gap between EV adoption and charging infrastructure,
-- and rank them by investment priority.
--
-- Data sources:
--   1. Vahan (Ministry of Road Transport) - EV registrations
--   2. OpenChargeMap (OCM)  - crowd-sourced charging stations
--   3. Ministry of Heavy Industries / PIB - OFFICIAL charging
--      station counts (used because OCM turned out to badly
--      undercount real stations - see Stage 4)
-- ============================================================


-- ============================================================
-- STAGE 1: LOAD RAW EV REGISTRATION DATA
-- ============================================================

CREATE DATABASE IF NOT EXISTS ev_project;
USE ev_project;

CREATE TABLE raw_registrations (
    id              INT PRIMARY KEY,
    reg_date        DATE,
    state_name      VARCHAR(100),
    state_code      INT,
    office_name     VARCHAR(150),
    office_code     VARCHAR(20),
    fuel_type       VARCHAR(50),
    category        VARCHAR(20),
    registrations   INT
);

-- clev.csv = the CLEANED Vahan export (corrupted rows already
-- removed - see clean_vahan_registrations.py). A handful of rows
-- in the original file had implausible values (a single local
-- RTO office reporting 200,000+ EV registrations in one month -
-- clearly a scraping error) which was inflating some state totals
-- by up to 87%. Those rows were filtered out before this load.



LOAD DATA LOCAL INFILE '/Users/sachin_rao/Downloads/clev.csv'
INTO TABLE raw_registrations
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(id, reg_date, state_name, state_code, office_name, office_code, fuel_type, category, registrations);


-- ============================================================
-- STAGE 2: CLEAN STATE NAMES + TAG EV ROWS
-- ============================================================

-- Only real spelling/format fixes needed - not every state, just
-- the ones that actually appeared inconsistently in the raw data.



CREATE TABLE state_name_mapping (
    raw_name    VARCHAR(150) PRIMARY KEY,
    clean_name  VARCHAR(100)
);

INSERT INTO state_name_mapping VALUES
('Andaman And Nicobar Islands', 'Andaman and Nicobar Islands'),
('Jammu And Kashmir', 'Jammu and Kashmir'),
('The Dadra And Nagar Haveli And Daman And Diu', 'Dadra and Nagar Haveli and Daman and Diu');



-- One view everything downstream builds on: clean state names,
-- split date into year/month, and flag which rows are actually EVs.
-- (fuel_type = "Strong Hybrid Ev" is excluded on purpose - it still
-- runs mainly on petrol/diesel, not a plug-in EV.)



CREATE VIEW clean_registrations AS
SELECT
    r.id,
    r.reg_date,
    YEAR(r.reg_date)  AS reg_year,
    MONTH(r.reg_date) AS reg_month,
    COALESCE(m.clean_name, r.state_name) AS state_name,
    r.office_name,
    r.fuel_type,
    r.registrations,
    CASE
        WHEN r.fuel_type IN ('Electric(Bov)', 'Pure Ev', 'Plug-In Hybrid Ev') THEN 1
        ELSE 0
    END AS is_ev
FROM raw_registrations r
LEFT JOIN state_name_mapping m ON r.state_name = m.raw_name;


-- ============================================================
-- STAGE 3: AGGREGATE TO STATE-YEAR LEVEL
-- ============================================================

-- Core table: one row per state per year. Everything else joins to this.

CREATE TABLE state_yearly_ev_registrations AS
SELECT
    state_name,
    reg_year,
    SUM(CASE WHEN is_ev = 1 THEN registrations ELSE 0 END) AS total_ev_registrations,
    SUM(registrations) AS total_registrations,
    ROUND(
        SUM(CASE WHEN is_ev = 1 THEN registrations ELSE 0 END) * 100.0
        / NULLIF(SUM(registrations), 0), 2
    ) AS ev_share_pct
FROM clean_registrations
WHERE state_name != 'Telangana'   -- Telangana wasn't in the original Vahan export
GROUP BY state_name, reg_year
ORDER BY state_name, reg_year;


-- Year-over-year growth, using a window function (LAG) to compare
-- each state against its own prior year.
-- NOTE: 2024 in this data only covers Jan-May (partial year), so
-- comparing 2024 vs 2023 would falsely show every state "declining".
-- Growth is calculated for 2023 vs 2022 instead, since both are full years.


CREATE VIEW state_yoy_growth AS
SELECT
    state_name,
    reg_year,
    total_ev_registrations,
    LAG(total_ev_registrations) OVER (PARTITION BY state_name ORDER BY reg_year) AS prev_year_ev,
    ROUND(
        (total_ev_registrations - LAG(total_ev_registrations) OVER (PARTITION BY state_name ORDER BY reg_year))
        * 100.0 / NULLIF(LAG(total_ev_registrations) OVER (PARTITION BY state_name ORDER BY reg_year), 0), 2
    ) AS yoy_growth_pct
FROM state_yearly_ev_registrations;



-- OPTIONAL - only needed for the dashboard's time-series chart,


CREATE TABLE state_monthly_trend AS
SELECT
    state_name,
    reg_year,
    reg_month,
    SUM(CASE WHEN is_ev = 1 THEN registrations ELSE 0 END) AS ev_registrations,
    SUM(registrations) AS total_registrations
FROM clean_registrations
GROUP BY state_name, reg_year, reg_month
ORDER BY state_name, reg_year, reg_month;


-- ============================================================
-- STAGE 4: CHARGING STATION DATA (TWO SOURCES)
-- ============================================================

-- Source A: OpenChargeMap (crowd-sourced, point-level detail -
-- lat/long, operator, connector power). Kept for map visuals only.


CREATE TABLE charging_stations (
    station_id       INT PRIMARY KEY,
    title             VARCHAR(255),
    address_line      VARCHAR(255),
    town              VARCHAR(100),
    state_clean       VARCHAR(100),
    postcode          VARCHAR(20),
    latitude          DECIMAL(9,6),
    longitude         DECIMAL(9,6),
    operator_name     VARCHAR(100),
    num_connections   INT,
    max_power_kw      DECIMAL(10,2),
    date_created      DATETIME
);

LOAD DATA LOCAL INFILE '/Users/sachin_rao/Downloads/clevs.csv'
INTO TABLE charging_stations
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(station_id, title, address_line, town, @dummy_state, postcode, latitude, longitude,
 operator_name, num_connections, max_power_kw, date_created, @dummy_status, @dummy_qstate, state_clean);
 
 

-- Source B: Official Ministry of Heavy Industries / PIB figures.
-- Used for the ACTUAL analysis below, because OCM only covers
-- ~7% of real stations nationally, with heavy South-India bias
-- (proven in the comparison view right after this table).



CREATE TABLE official_charging_stations (
    state                     VARCHAR(100) PRIMARY KEY,
    official_total_stations   INT,
    fast_chargers             INT,
    slow_chargers             INT
);

LOAD DATA LOCAL INFILE '/Users/sachin_rao/Downloads/official_ev_charging_stations.csv'
INTO TABLE official_charging_stations
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(state, official_total_stations, fast_chargers, slow_chargers);




-- Proves the OCM bias claim above with numbers - keep this, it's
-- a real finding, not just a sanity check.


CREATE VIEW ocm_coverage_analysis AS
SELECT
    o.state,
    o.official_total_stations,
    COALESCE(c.ocm_station_count, 0) AS ocm_station_count,
    ROUND(COALESCE(c.ocm_station_count, 0) * 100.0 / o.official_total_stations, 1) AS ocm_coverage_pct
FROM official_charging_stations o
LEFT JOIN (
    SELECT state_clean, COUNT(*) AS ocm_station_count
    FROM charging_stations
    GROUP BY state_clean
) c ON o.state = c.state_clean
ORDER BY ocm_coverage_pct ASC;


-- ============================================================
-- STAGE 5: THE CORE ANALYSIS
-- ============================================================

-- Key metric: charging stations per 1,000 EVs, by state.
-- Lower = more underserved = higher priority.
-- Filtered to states with >=1000 EVs so tiny markets (e.g. 3 EVs
-- total) don't produce a meaningless, noisy ratio.



CREATE VIEW state_ev_infra_gap AS
SELECT
    v.state_name,
    v.total_ev_registrations,
    o.official_total_stations,
    o.fast_chargers,
    ROUND(o.official_total_stations * 1000.0 / NULLIF(v.total_ev_registrations, 0), 2) AS stations_per_1000_ev
FROM state_yearly_ev_registrations v
JOIN official_charging_stations o ON v.state_name = o.state
WHERE v.reg_year = 2024
  AND v.total_ev_registrations >= 1000
ORDER BY stations_per_1000_ev ASC;



-- Final output: priority score combining three signals into one
-- ranked list. This is the number to present as recommendation.
--   - gap_score    (50%): how underserved the state is (the core story)
--   - scale_score  (30%): size of the market (don't prioritize tiny markets)
--   - growth_score (20%): momentum (fast-growing = becomes urgent soon)
-- All three are normalized to 0-1 first since they're on different scales.



CREATE VIEW state_priority_score AS
WITH normalized AS (
    SELECT
        g.state_name,
        g.total_ev_registrations,
        g.stations_per_1000_ev,
        y.yoy_growth_pct,
        (MAX(g.stations_per_1000_ev) OVER () - g.stations_per_1000_ev)
            / NULLIF(MAX(g.stations_per_1000_ev) OVER () - MIN(g.stations_per_1000_ev) OVER (), 0) AS gap_score,
        (g.total_ev_registrations - MIN(g.total_ev_registrations) OVER ())
            / NULLIF(MAX(g.total_ev_registrations) OVER () - MIN(g.total_ev_registrations) OVER (), 0) AS scale_score,
        (y.yoy_growth_pct - MIN(y.yoy_growth_pct) OVER ())
            / NULLIF(MAX(y.yoy_growth_pct) OVER () - MIN(y.yoy_growth_pct) OVER (), 0) AS growth_score
    FROM state_ev_infra_gap g
    -- NOTE: g uses 2024 EV totals (most recent), y uses 2023 growth
    -- (last full year) - intentional, not a mismatch. See Stage 3 note.
    JOIN state_yoy_growth y ON g.state_name = y.state_name AND y.reg_year = 2023
)
SELECT
    state_name,
    total_ev_registrations,
    stations_per_1000_ev,
    yoy_growth_pct,
    ROUND(0.5 * gap_score + 0.3 * scale_score + 0.2 * growth_score, 3) AS priority_score
FROM normalized
ORDER BY priority_score DESC;