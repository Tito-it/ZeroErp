CREATE OR REPLACE FUNCTION dbops.fn_create_gestore(p_codice text, p_ragione_sociale text, p_partita_iva character, p_codice_fiscale character, p_tipo_soggetto character, p_forma_giuridica text, p_capitale_sociale numeric, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_destinatario_fe character, p_cd_software text, p_valuta_id integer, p_iban character, p_cd_int_utility text, p_cd_int_ruolo_funzionale text)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_soggetto_id            UUID;
    v_soggetto_ruolo_id      INTEGER;
    v_gestore_id             INTEGER;
BEGIN
-- ====================================================================
-- Funzione factory per creare un Gestore “end‑to‑end” con assegnazione utility/ruolo
--   • Inserisce in anagrafiche.soggetti (tipo_soggetto = 'G')
--   • Popola anagrafiche.dati_societari
--   • Assegna il ruolo GE in anagrafiche.soggetti_ruoli
--   • Inserisce il record in anagrafiche.gestori
--   • Associa il gestore a utility specifica e ruolo funzionale
-- Restituisce il UUID del soggetto creato.
-- Schema: dbops
-- ====================================================================

/* 
esempio di chiamata
19/04/2025 la funzione non è stata testata  al momento di questa 
data sviluppo. Quando si genererrano i dati si prega di aggiornarla e
indicare un esempio funzionante


SELECT dbops.create_gestore(
  -- 1. p_codice
  NULL,
  -- 2. p_ragione_sociale
  'Zero ERP Srl',
  -- 3. p_partita_iva
  '01234567890',
  -- 4. p_codice_fiscale
  'RSSMRA85M01H501U',
  -- 5. p_tipo_soggetto
  'G',
  -- 6. p_forma_giuridica
  'SRL',
  -- 7. p_capitale_sociale
  100000.00,
  -- 8. p_id_prov_iscri_rea
  1,
  -- 9. p_iscrizione_rea
  'REA123456',
  -- 10. p_destinatario_fe
  'ABC123XYZ',
  -- 11. p_cd_software
  'ZEROERP',
  -- 12. p_valuta_id
  (SELECT id_valuta FROM config.pa_valute WHERE iso_code = 'EUR'),
  -- 13. p_iban
  'IT60X0542811101000000123456',
  -- 14. p_cd_int_utility
  'GAS',
  -- 15. p_cd_int_ruolo_funzionale
  'GAS_DIST'
);


*/

    -- 1) Creo il soggetto
    INSERT INTO anagrafiche.soggetti (
        id, codice, ragione_sociale, tipo_soggetto,
        partita_iva, codice_fiscale
    ) VALUES (
        gen_random_uuid(), p_codice, p_ragione_sociale, p_tipo_soggetto,
        p_partita_iva, p_codice_fiscale
    )
    RETURNING id INTO v_soggetto_id;

    -- 2) Popolo i dati societari
    INSERT INTO anagrafiche.dati_societari (
        soggetto_id, forma_giuridica, capitale_sociale,
        id_prov_iscri_rea, iscrizione_rea, destinatario_fe
    ) VALUES (
        v_soggetto_id, p_forma_giuridica, p_capitale_sociale,
        p_id_prov_iscri_rea, p_iscrizione_rea, p_destinatario_fe
    );

    -- 3) Assegno il ruolo “GE” (Gestore) in soggetti_ruoli
    INSERT INTO anagrafiche.soggetti_ruoli (
        soggetto_id, ruolo_id
    ) VALUES (
        v_soggetto_id,
        (SELECT id FROM config.tipi_ruoli WHERE cd_int_ruolo = 'GE')
    )
    RETURNING id_soggetto_ruolo INTO v_soggetto_ruolo_id;

    -- 4) Inserisco il record in gestori
    INSERT INTO anagrafiche.gestori (
        soggetto_id, soggetto_ruolo_id,
        descrizione, cd_prod_software, valuta_id, iban
    ) VALUES (
        v_soggetto_id, v_soggetto_ruolo_id,
        p_ragione_sociale, p_cd_software, p_valuta_id, p_iban
    )
    RETURNING id INTO v_gestore_id;

    -- 5) Associo il gestore a utility e ruolo funzionale
    INSERT INTO anagrafiche.gestori_utilities_ruoli (
        gestore_id, utility_id, ruolo_id, extra
    ) VALUES (
        v_gestore_id,
        (SELECT id_utility FROM config.utilities WHERE cd_int_utility = p_cd_int_utility),
        (SELECT id FROM config.tipi_ruoli WHERE cd_int_ruolo = p_cd_int_ruolo_funzionale),
        '{}'::jsonb
    );

    RETURN v_soggetto_id;
END;
$function$
