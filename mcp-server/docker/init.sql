CREATE TABLE IF NOT EXISTS animals_types (
    id BIGSERIAL PRIMARY KEY,
    animal_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS animals_breeds (
    id BIGSERIAL PRIMARY KEY,
    animal_breed TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pets_info (
    id BIGSERIAL PRIMARY KEY,
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
    pet_is_sterylyzed BOOLEAN DEFAULT FALSE,
    pet_weight NUMERIC,
    pet_special_notes TEXT
);

CREATE TABLE IF NOT EXISTS documents_types (
    document_type_id BIGSERIAL PRIMARY KEY,
    document_type TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pet_documents (
    document_id BIGSERIAL PRIMARY KEY,
    pet_id BIGINT NOT NULL REFERENCES pets_info(id) ON DELETE CASCADE,
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

Индексы
CREATE INDEX IF NOT EXISTS idx_pets_info_user_pet ON pets_info(user_id, id);
CREATE INDEX IF NOT EXISTS idx_pet_documents_pet_uploaded ON pet_documents(pet_id, uploaded_at);
CREATE INDEX IF NOT EXISTS idx_vet_clinics_active_city ON vet_clinics(vet_status, LOWER(vet_city));

СПРАВОЧНИКИ

INSERT INTO animals_types (id, animal_name) VALUES
    (1, 'Собака'),
    (2, 'Кошка')
ON CONFLICT DO NOTHING;

INSERT INTO animals_breeds (id, animal_breed) VALUES
    (1, 'Немецкая овчарка'),
    (2, 'Бордер-колли'),
    (3, 'Золотистый ретривер'),
    (4, 'Такса'),
    (5, 'Лабрадор'),
    (6, 'Дворняга'),
    (7, 'Британская короткошёрстная'),
    (8, 'Мейн-кун'),
    (9, 'Шотландская вислоухая')
ON CONFLICT DO NOTHING;

INSERT INTO documents_types (document_type_id, document_type) VALUES
    (1, 'Ветеринарный паспорт'),
    (2, 'Справка о прививках'),
    (3, 'Результаты анализов'),
    (4, 'Выписка из клиники'),
    (5, 'Справка для выезда за границу')
ON CONFLICT DO NOTHING;

#ПИТОМЦЫ
#user_id — строковый, совпадает с user_id в JWT
#Lогин: {"user_id": "1", "password": "petcare-demo-password"}

INSERT INTO pets_info (
    id, user_id, pet_name, pet_sex,
    animal_type_id, animal_breed_id,
    pet_date_of_birth, pedigree,
    pet_neck_girth, pet_breast_girth, pet_length,
    pet_is_sterylyzed, pet_weight, pet_special_notes
) VALUES
(
    1, '1', 'Барни', 'male',
    1, 3,
    '2021-04-12', true,
    38, 72, 64,
    false, 24.50,
    'Активный, любит долгие прогулки. Есть склонность тянуть поводок.'
),
(
    2, '1', 'Мия', 'female',
    2, 7,
    '2020-09-05', false,
    22, 36, 41,
    true, 4.80,
    'Спокойная, плохо переносит шумные места.'
),
(
    3, '2', 'Рич', 'male',
    1, 5,
    '2019-01-28', true,
    44, 85, 78,
    null, 33.20,
    'Нуждается в контроле веса. Рекомендуются умеренные нагрузки.'
),
(
    4, '3', 'Луна', 'female',
    1, 2,
    '2022-06-17', false,
    31, 58, 55,
    false, 14.70,
    'Пугливая при контакте с крупными собаками.'
),
(
    5, null, 'Симба', 'male',
    2, 9,
    '2023-11-03', false,
    19, 32, 37,
    false, 3.60,
    null
)
ON CONFLICT DO NOTHING;

#Сброс sequence после ручной вставки id
SELECT setval('pets_info_id_seq', (SELECT MAX(id) FROM pets_info));

#ВЕТЕРИНАРНЫЕ КЛИНИКИ (реальные, Ростов-на-Дону)

INSERT INTO vet_clinics (
    vet_name, vet_city, vet_street, vet_building_number,
    vet_lat, vet_lon,
    vet_working_hours, vet_is_24_7,
    vet_phone, vet_website, vet_status
) VALUES
(
    'Вита', 'Ростов-на-Дону', 'Улица Мадояна', '198/125',
    47.2321, 39.7012,
    '09:00-22:00', false,
    '+7-863-303-08-65', 'https://rostovvet.ru/', 'active'
),
(
    'заВЕТный Друг', 'Ростов-на-Дону', 'Улица Еляна', '68',
    47.2489, 39.7234,
    '00:00-24:00', true,
    '+7-900-122-14-20', 'https://zoovetdrug.ru/', 'active'
),
(
    'заВЕТный Друг', 'Ростов-на-Дону', 'Улица Вересаева', '105/2',
    47.2198, 39.6891,
    '00:00-24:00', true,
    '+7-900-122-14-20', 'https://zoovetdrug.ru/', 'active'
),
(
    'Ветеринарная клиника доктора Зарубина', 'Ростов-на-Дону', 'Улица Добровольского', '32',
    47.2567, 39.7445,
    '09:00-21:00', false,
    '+7-863-297-66-44', 'https://vetzarubin.ru/', 'active'
),
(
    'Доктор Фламинго', 'Ростов-на-Дону', 'Ректорская улица', '13',
    47.2412, 39.7156,
    '10:00-20:00', false,
    '+7-961-426-26-36', null, 'active'
)
ON CONFLICT DO NOTHING;


# МЕТАДАННЫЕ ДОКУМЕНТОВ
файлы не загружены в MinIO, но список документов работает

INSERT INTO pet_documents (
    pet_id, custom_name, object_key,
    content_type, size_bytes,
    uploaded_at, document_type_id
) VALUES
(
    1, 'Справка для выезда за границу №1',
    'pets/1/1636528371_spravka_1.pdf',
    'application/pdf', 128589,
    '2025-11-10 10:23:00+00', 5
),
(
    1, 'Справка для выезда за границу №2',
    'pets/1/1636528417_spravka_2.pdf',
    'application/pdf', 174941,
    '2025-11-10 10:24:00+00', 5
),
(
    3, 'Справка для выезда за границу №3',
    'pets/3/1636528423_spravka_3.pdf',
    'application/pdf', 211869,
    '2025-11-10 10:25:00+00', 5
),
(
    3, 'Справка для выезда за границу №4',
    'pets/3/1636528434_spravka_4.pdf',
    'application/pdf', 61433,
    '2025-11-10 10:26:00+00', 5
)
ON CONFLICT DO NOTHING;
