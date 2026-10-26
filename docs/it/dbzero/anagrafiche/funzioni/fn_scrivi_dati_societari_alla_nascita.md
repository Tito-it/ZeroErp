{% include-markdown "it/dbzero/anagrafiche/manual/fn_scrivi_dati_societari_alla_nascita.md" %}
# ⚙️ Funzione `fn_scrivi_dati_societari_alla_nascita`

```sql
CREATE FUNCTION fn_scrivi_dati_societari_alla_nascita(p_soggetto_id uuid, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_data_costituzione date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_scrivi_dati_societari_alla_nascita(p_soggetto_id uuid, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_data_costituzione date)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: alla nascita di un soggetto, scrive i suoi dati societari
--   se vanno scritti, e solo col verbo (stato intero). Restituisce
--   l'id della riga, o NULL se la sezione non c'e' e la natura non
--   la pretende.
-- Lo chiamano le due porte di creazione, fn_crea_soggetto_pg e
--   fn_crea_soggetto_pf (regola del 2, 20261020-01).
-- Brief: brief-db-dati-societari-in-creazione §3.1.
-- =========================================================
DECLARE
    v_policy  config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
BEGIN
    -- Due rami, due codici, come nel verbo: il soggetto non passato e' un
    -- chiamante rotto (PARAMETRO), quello passato e inesistente e' «non trovato».
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_scrivi_dati_societari_alla_nascita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
            NULL::uuid,
            'il soggetto e'' obbligatorio');
    END IF;

    SELECT tsd.dati_societari_policy
      INTO v_policy
      FROM anagrafiche.soggetti s
      LEFT JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
     WHERE s.id = p_soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_scrivi_dati_societari_alla_nascita',
            'E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            p_soggetto_id::text);
    END IF;

    -- La sezione «c'e'» se almeno un campo ha un valore. Socio unico e
    -- liquidazione non contano: hanno sempre un valore, anche a sezione vuota.
    -- Una natura NONE con la sezione passa al verbo, e la rifiuta il guard
    -- della natura: niente scarto silenzioso.
    IF v_policy IS DISTINCT FROM 'REQUIRED'
       AND p_forma_giuridica_id IS NULL
       AND p_id_prov_iscri_rea IS NULL
       AND NULLIF(btrim(p_iscrizione_rea), '') IS NULL
       AND p_capitale_sociale IS NULL
       AND NULLIF(btrim(p_destinatario_fe), '') IS NULL
       AND NULLIF(btrim(p_pec_fatturazione), '') IS NULL
       AND NULLIF(btrim(p_codice_sdi), '') IS NULL
       AND p_data_costituzione IS NULL
    THEN
        RETURN NULL;
    END IF;

    RETURN anagrafiche.fn_scrivi_dati_societari(
        p_soggetto_id        := p_soggetto_id,
        p_forma_giuridica_id := p_forma_giuridica_id,
        p_id_prov_iscri_rea  := p_id_prov_iscri_rea,
        p_iscrizione_rea     := p_iscrizione_rea,
        p_capitale_sociale   := p_capitale_sociale,
        p_socio_unico        := p_socio_unico,
        p_liquidazione       := p_liquidazione,
        p_destinatario_fe    := p_destinatario_fe,
        p_pec_fatturazione   := p_pec_fatturazione,
        p_codice_sdi         := p_codice_sdi,
        p_data_costituzione  := p_data_costituzione
    );
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_scrivi_dati_societari_alla_nascita(p_soggetto_id uuid, p_forma_giuridica_id bigint, p_id_prov_iscri_rea integer, p_iscrizione_rea character varying, p_capitale_sociale numeric, p_socio_unico anagrafiche.socio_unico_enum, p_liquidazione anagrafiche.liquidazione_enum, p_destinatario_fe character varying, p_pec_fatturazione character varying, p_codice_sdi character varying, p_data_costituzione date)
IS 'Alla nascita di un soggetto decide se i suoi dati societari vanno scritti, e li scrive col verbo anagrafiche.fn_scrivi_dati_societari (stato intero). Si scrivono se la natura li pretende (dati_societari_policy REQUIRED) o se la sezione c''e'': almeno un campo con un valore fra forma, provincia e numero REA, capitale, canale FE, PEC, codice SDI e data di costituzione (testi vuoti esclusi; socio unico e liquidazione da soli non contano, hanno sempre un valore). Una sezione passata a una natura NONE va al verbo e la rifiuta il guard della natura (E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO), mai scartata in silenzio. Restituisce l''id dei dati societari, o NULL se non c''era niente da scrivere. Soggetto NULL: E_PARAMETRO_INVALIDO; inesistente: E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO. SECURITY INVOKER: la porta di scrittura resta il verbo. Lo chiamano anagrafiche.fn_crea_soggetto_pg e anagrafiche.fn_crea_soggetto_pf (regola del 2, 20261020-01). Brief: brief-db-dati-societari-in-creazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
