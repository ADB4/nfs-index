CREATE TABLE makes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    make_id INTEGER REFERENCES makes(id),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(make_id, name)
);

CREATE TABLE trims (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_id, name)
);

CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    listing_url VARCHAR(500) NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    make_id INTEGER REFERENCES makes(id),
    model_id INTEGER REFERENCES models(id),
    year INTEGER NOT NULL,
    trim_id INTEGER REFERENCES trims(id),
    sale_price INTEGER,
    sale_date DATE NOT NULL,
    reserve_met BOOLEAN,
    number_of_bids INTEGER,
    mileage INTEGER,
    location VARCHAR(200),
    vin VARCHAR(17),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO makes (name) VALUES ('Mercedes-Benz');

INSERT INTO models (make_id, name) 
SELECT id, 'SLR McLaren' FROM makes WHERE name = 'Mercedes-Benz';

INSERT INTO trims (model_id, name)
SELECT m.id, 'Coupe' FROM models m
JOIN makes mk ON m.make_id = mk.id
WHERE mk.name = 'Mercedes-Benz' AND m.name = 'SLR McLaren';

INSERT INTO trims (model_id, name)
SELECT m.id, 'Roadster' FROM models m
JOIN makes mk ON m.make_id = mk.id
WHERE mk.name = 'Mercedes-Benz' AND m.name = 'SLR McLaren';