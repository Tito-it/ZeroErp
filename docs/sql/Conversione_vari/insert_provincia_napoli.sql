
INSERT INTO config.province (
    id, descrizione, sigla, regione_id, data_insert, user_insert, data_update, user_update, extra_country
) VALUES (
    55,
    'Napoli',
    'NA',
    17,
    CURRENT_TIMESTAMP,
    CURRENT_USER,
    CURRENT_TIMESTAMP,
    CURRENT_USER,
    '{"stato_utilizzo": "ITA", "codice_istat": "063"}'
);
