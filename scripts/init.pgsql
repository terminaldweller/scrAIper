CREATE TABLE IF NOT EXISTS toll_facilities (
		id SERIAL PRIMARY KEY,
		state_or_province VARCHAR(255) NOT NULL,
		facility_label VARCHAR(255) NOT NULL,
		toll_operator VARCHAR(255) NOT NULL,
		facility_type VARCHAR(255) NOT NULL,
		road_type VARCHAR(255) NOT NULL,
		interstate boolean NOT NULL,
		facility_open_date VARCHAR(255) NOT NULL,
		revenue_lane_miles float NOT NULL,
		revenue float NOT NULL,
		length_miles float NOT NULL,
		lane float NOT NULL,
		source_type VARCHAR(255) NOT NULL,
		reference VARCHAR(255) NOT NULL,
		year integer NOT NULL
);

/* SELECT 'CREATE DATABASE tolls' */
/* WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'irc')\gexec */
