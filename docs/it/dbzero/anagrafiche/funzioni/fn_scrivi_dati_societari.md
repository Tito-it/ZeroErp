# ⚙️ Funzione `fn_scrivi_dati_societari`

```sql
CREATE FUNCTION fn_scrivi_dati_societari(p_soggetto_id uuid, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_data_costituzione date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_scrivi_dati_societari(p_soggetto_id uuid, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_data_costituzione date)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: crea o aggiorna i dati societari di un soggetto (stato intero).
--   Aggiunge solo il controllo del soggetto (obbligatorio, poi esistente):
--   le regole (forma, natura,
--   REA, capitale, canale FE) sono nei trigger.
-- ⛔ SECURITY DEFINER: dal 20261011-04 l'app non scrive la tabella, e
--   questa e' la porta. Nessun guard di livello: il permesso resta al
--   backend, come per anagrafiche.soggetti (decisione di Tid, 2026-10-10).
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (B-1..B-5).
-- =========================================================
DECLARE
    v_id           anagrafiche.dati_societari.id%TYPE;
    v_socio_unico  anagrafiche.dati_societari.socio_unico%TYPE;
    v_liquidazione anagrafiche.dati_societari.liquidazione%TYPE;
BEGIN
    -- Due rami, due codici: il soggetto non passato e' un chiamante rotto
    -- (PARAMETRO), quello passato e inesistente e' «non trovato».
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_scrivi_dati_societari', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
            NULL::uuid,
            'il soggetto e'' obbligatorio');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti s WHERE s.id = p_soggetto_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_scrivi_dati_societari',
            'E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            p_soggetto_id::text);
    END IF;

    -- I due enum NOT NULL: NULL vale il valore PROPOSTO dal parametro,
    -- con la cascata della sessione (override per emittente, D-2-bis).
    -- Parametro assente: la cascata solleva (nessun valore di riserva).
    v_socio_unico := COALESCE(
        p_socio_unico,
        script.fn_get_parameter_di_sessione(
            'dati_societari_default_socio_unico',
            'anagrafiche.fn_scrivi_dati_societari')::anagrafiche.socio_unico_enum);
    v_liquidazione := COALESCE(
        p_liquidazione,
        script.fn_get_parameter_di_sessione(
            'dati_societari_default_liquidazione',
            'anagrafiche.fn_scrivi_dati_societari')::anagrafiche.liquidazione_enum);

    UPDATE anagrafiche.dati_societari ds
       SET forma_giuridica_id = p_forma_giuridica_id,
           id_prov_iscri_rea  = p_id_prov_iscri_rea,
           iscrizione_rea     = NULLIF(btrim(p_iscrizione_rea), ''),
           capitale_sociale   = p_capitale_sociale,
           socio_unico        = v_socio_unico,
           liquidazione       = v_liquidazione,
           destinatario_fe    = NULLIF(btrim(p_destinatario_fe), ''),
           pec_fatturazione   = NULLIF(btrim(p_pec_fatturazione), ''),
           codice_sdi         = NULLIF(btrim(p_codice_sdi), ''),
           data_costituzione  = p_data_costituzione
     WHERE ds.soggetto_id = p_soggetto_id
    RETURNING ds.id INTO v_id;

    IF v_id IS NULL THEN
        INSERT INTO anagrafiche.dati_societari (
            soggetto_id, forma_giuridica_id, id_prov_iscri_rea, iscrizione_rea,
            capitale_sociale, socio_unico, liquidazione,
            destinatario_fe, pec_fatturazione, codice_sdi, data_costituzione
        )
        VALUES (
            p_soggetto_id, p_forma_giuridica_id, p_id_prov_iscri_rea,
            NULLIF(btrim(p_iscrizione_rea), ''),
            p_capitale_sociale, v_socio_unico, v_liquidazione,
            NULLIF(btrim(p_destinatario_fe), ''),
            NULLIF(btrim(p_pec_fatturazione), ''),
            NULLIF(btrim(p_codice_sdi), ''),
            p_data_costituzione
        )
        RETURNING id INTO v_id;
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_scrivi_dati_societari(p_soggetto_id uuid, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_data_costituzione date)
IS 'Il verbo di scrittura dei dati societari: crea o aggiorna la riga del soggetto (una per soggetto), STATO INTERO (NULL scrive NULL dove la colonna lo ammette; testi ripuliti, vuoto = NULL). socio_unico e liquidazione NULL valgono il valore proposto dai parametri dati_societari_default_socio_unico / _liquidazione, letto con script.fn_get_parameter_di_sessione: la cascata col contesto della sessione, quindi con l''override dell''emittente attivo (D-2-bis e D-4 di brief-db-parametri-senza-override); parametro assente = errore, nessun valore di riserva. Aggiunge solo il controllo del soggetto: NULL solleva E_PARAMETRO_INVALIDO, inesistente E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO; forma, natura, REA, capitale e canale FE restano ai trigger della tabella. SECURITY DEFINER: dal 20261011-04 l''applicazione non scrive anagrafiche.dati_societari direttamente, e questa e'' la porta (B-5); nessun guard di livello, il permesso resta al backend come per anagrafiche.soggetti. Se nella stessa scrittura cambia la natura del soggetto, si aggiorna prima il soggetto e poi si chiama il verbo. Lo chiamano anagrafiche.fn_scrivi_dati_societari_alla_nascita, il backend in modifica e le fixture pgTAP. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (B-1..B-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
