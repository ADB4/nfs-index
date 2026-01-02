-- NFS Index Database Schema
-- Drop existing tables if they exist
DROP TABLE IF EXISTS listings CASCADE;
DROP TABLE IF EXISTS variants CASCADE;
DROP TABLE IF EXISTS models CASCADE;
DROP TABLE IF EXISTS makes CASCADE;

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

CREATE TABLE variants (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_id, name)
);

CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    vin VARCHAR(17),
    year INTEGER NOT NULL,
    make_id INTEGER REFERENCES makes(id),
    model_id INTEGER REFERENCES models(id),
    variant_id INTEGER REFERENCES variants(id),
    mileage INTEGER,
    sale_price INTEGER,
    sale_date DATE NOT NULL,
    reserve_met BOOLEAN,
    number_of_bids INTEGER,
    location VARCHAR(200),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_listings_make_id ON listings(make_id);
CREATE INDEX idx_listings_model_id ON listings(model_id);
CREATE INDEX idx_listings_variant_id ON listings(variant_id);
CREATE INDEX idx_listings_year ON listings(year);
CREATE INDEX idx_listings_sale_date ON listings(sale_date);
CREATE INDEX idx_listings_vin ON listings(vin);

-- Insert initial data
INSERT INTO makes (name) VALUES ('MERCEDES-BENZ');

INSERT INTO models (make_id, name) 
SELECT id, 'SLR MCLAREN' FROM makes WHERE name = 'MERCEDES-BENZ';

INSERT INTO variants (model_id, name)
SELECT m.id, 'COUPE' FROM models m
JOIN makes mk ON m.make_id = mk.id
WHERE mk.name = 'MERCEDES-BENZ' AND m.name = 'SLR MCLAREN';

INSERT INTO variants (model_id, name)
SELECT m.id, 'ROADSTER' FROM models m
JOIN makes mk ON m.make_id = mk.id
WHERE mk.name = 'MERCEDES-BENZ' AND m.name = 'SLR MCLAREN';

INSERT INTO variants (model_id, name)
SELECT m.id, '722' FROM models m
JOIN makes mk ON m.make_id = mk.id
WHERE mk.name = 'MERCEDES-BENZ' AND m.name = 'SLR MCLAREN';

INSERT INTO variants (model_id, name)
SELECT m.id, 'STANDARD' FROM models m
JOIN makes mk ON m.make_id = mk.id
WHERE mk.name = 'MERCEDES-BENZ' AND m.name = 'SLR MCLAREN';

-- Create a view for easier querying with all names included
CREATE VIEW listings_with_details AS
SELECT 
    l.id,
    l.url,
    l.source,
    l.title,
    l.vin,
    l.year,
    mk.name AS make,
    m.name AS model,
    v.name AS variant,
    l.mileage,
    l.sale_price,
    l.sale_date,
    l.reserve_met,
    l.number_of_bids,
    l.location,
    l.scraped_at
FROM listings l
JOIN makes mk ON l.make_id = mk.id
JOIN models m ON l.model_id = m.id
LEFT JOIN variants v ON l.variant_id = v.id
ORDER BY l.sale_date DESC;