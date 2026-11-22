{% include-markdown "it/dbzero/dbops/manual/fn_crea_regime_fiscale_di_prova.md" %}
# ⚙️ Funzione `fn_crea_regime_fiscale_di_prova`

```sql
CREATE FUNCTION fn_crea_regime_fiscale_di_prova(p_codice_interno character varying, p_codice character varying, p_descrizione character varying, p_attivo boolean)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_crea_regime_fiscale_di_prova(p_codice_interno character varying, p_codice character varying, p_descrizione character varying, p_attivo boolean)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
    v_id       config.regimi_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Crea un regime fiscale DI PROVA, per i test e2e che
    --   devono costruire un regime acceso o spento. Solo in
    --   SVILUPPO, solo righe nuove, col segno in meta.
    --
    -- Regole:
    --   - fuori da SVILUPPO -> E_DATI_DI_SVILUPPO_IN_PRODUZIONE
    --     (la porta dei dati di sviluppo, stessa regola);
    --   - un codice_interno o un codice gia' presenti -> 23505
    --     dai due UNIQUE: una riga del catalogo non si tocca;
    --   - solo INSERT: il regime spento nasce spento.
    -- =========================================================

    -- 1. LA PORTA.
    v_ambiente := script.fn_ambiente_installazione();
    IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_crea_regime_fiscale_di_prova',
            'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
            jsonb_build_object('ambiente', v_ambiente),
            NULL::uuid,
            v_ambiente);
    END IF;

    -- 2. LA RIGA NUOVA, col segno di prova.
    INSERT INTO config.regimi_fiscali (codice_interno, codice, descrizione, attivo, meta)
    VALUES (p_codice_interno, p_codice, p_descrizione, p_attivo,
            jsonb_build_object('di_prova', true))
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_crea_regime_fiscale_di_prova(p_codice_interno character varying, p_codice character varying, p_descrizione character varying, p_attivo boolean)
IS 'Crea un regime fiscale DI PROVA in config.regimi_fiscali e ne restituisce l''id: la porta dei test e2e, perche'' l''app i regimi li legge e basta. Si apre solo in SVILUPPO (altrimenti E_DATI_DI_SVILUPPO_IN_PRODUZIONE, la regola della porta dei dati di sviluppo). Scrive solo righe nuove, con meta = {"di_prova": true}: un codice_interno o un codice gia'' presenti li rifiutano i due UNIQUE. Non modifica e non spegne: un regime spento nasce spento. SECURITY DEFINER: scrive come proprietario. Un regime di prova in un database PRODUZIONE lo vede dbops.vw_radici_di_prova_in_produzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
