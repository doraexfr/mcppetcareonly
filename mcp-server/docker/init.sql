CREATE TABLE IF NOT EXISTS animals_types (
    id BIGSERIAL PRIMARY KEY,
    animal_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS animals_breeds (
    id BIGSERIAL PRIMARY KEY,
    animal_breed TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pets_info (
    pet_id BIGSERIAL PRIMARY KEY,
    user_id TEXT,
    pet_name TEXT NOT NULL,
    pet_sex TEXT,
    animal_type_id BIGINT REFERENCES animals_types(id),
    animal_breed_id BIGINT REFERENCES animals_breeds(id),
    pet_date_of_birth DATE,
    pedigree BOOLEAN,
    pet_neck_girth NUMERIC,
    pet_breast_girth NUMERIC,
    pet_length NUMERIC,
    pet_is_sterylyzed BOOLEAN NOT NULL DEFAULT FALSE,
    pet_weight NUMERIC
    pet_special_notes TEXT
);

CREATE TABLE IF NOT EXISTS documents_types (
    document_type_id BIGSERIAL PRIMARY KEY,
    document_type TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pet_documents (
    document_id BIGSERIAL PRIMARY KEY,
    pet_id BIGINT NOT NULL REFERENCES pets_info(pet_id) ON DELETE CASCADE,
    custom_name TEXT NOT NULL,
    object_key TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    etag TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    document_type_id BIGINT REFERENCES documents_types(document_type_id),
    UNIQUE (pet_id, custom_name)
);

CREATE TABLE IF NOT EXISTS vet_clinics (
    vet_id BIGSERIAL PRIMARY KEY,
    vet_name TEXT NOT NULL,
    vet_city TEXT NOT NULL,
    vet_street TEXT NOT NULL,
    vet_building_number TEXT NOT NULL,
    vet_lat DOUBLE PRECISION,
    vet_lon DOUBLE PRECISION,
    vet_working_hours TEXT,
    vet_is_24_7 BOOLEAN NOT NULL DEFAULT FALSE,
    vet_phone TEXT,
    vet_website TEXT,
    vet_status TEXT NOT NULL DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_pets_info_user_pet ON pets_info(user_id, pet_id);
CREATE INDEX IF NOT EXISTS idx_pet_documents_pet_uploaded ON pet_documents(pet_id, uploaded_at);
CREATE INDEX IF NOT EXISTS idx_vet_clinics_active_city ON vet_clinics(vet_status, LOWER(vet_city));
CREATE INDEX IF NOT EXISTS idx_vet_clinics_active_name_city ON vet_clinics(vet_status, LOWER(vet_name), LOWER(vet_city));
