{% include-markdown "it/dbzero/vendite/manual/fn_chiudi_preventivi_scaduti.md" %}
# ⚙️ Funzione `fn_chiudi_preventivi_scaduti`

```sql
CREATE FUNCTION fn_chiudi_preventivi_scaduti()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_chiudi_preventivi_scaduti()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_emesso_id   config.stati_doc_preventivi.id%TYPE;
    v_scaduto_id  config.stati_doc_preventivi.id%TYPE;
    v_id          vendite.preventivi.id%TYPE;
    -- CONTEGGIO dei preventivi portati allo stato di scadenza.
    v_n           integer := 0;
BEGIN
    -- ==========================================================
    -- Scopo: portare allo stato di scadenza i preventivi emessi
    --   con la validita' finita, nel perimetro della sessione.
    --   Vedi l'intestazione del changeSet 20261031-66.
    -- Ritorna: quanti preventivi sono scaduti.
    -- ==========================================================
    v_utente     := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    v_emesso_id  := script.fn_stato_emissione_id('vendite.preventivi'::regclass);
    v_scaduto_id := script.fn_stato_scadenza_id('vendite.preventivi'::regclass);

    IF v_emesso_id IS NULL OR v_scaduto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_chiudi_preventivi_scaduti',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_preventivi',
                               'emesso_id', v_emesso_id, 'scaduto_id', v_scaduto_id),
            NULL::uuid, 'stato di emissione e di scadenza (config.stati_doc_preventivi)');
    END IF;

    FOR v_id IN
        SELECT p.id
          FROM vendite.preventivi p
         WHERE p.stato_doc_preventivo_id = v_emesso_id
           AND p.validita_al IS NOT NULL
           AND p.validita_al < (SELECT script.fn_data_operativa())
           AND script.fn_scope_ef_whitelist_via_preventivo(v_utente, p.id)
         ORDER BY p.id
           FOR UPDATE OF p
    LOOP
        PERFORM script.fn_doc_scrivi_stato('vendite.preventivi'::regclass, v_id, v_scaduto_id);
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION vendite.fn_chiudi_preventivi_scaduti()
IS 'VERBO della scadenza dei preventivi (brief-db-scadenza-preventivi §8.1, E-1 (a) di Tid 2026-10-31): i preventivi nello stato di emissione (EMESSO, script.fn_stato_emissione_id) con validita_al passata (< script.fn_data_operativa(): validita_al e'' l''ultimo giorno valido; NULL non scade), nel perimetro dell''utente della sessione (script.fn_scope_ef_whitelist_via_preventivo: DEFINER, la RLS non c''e''), presi FOR UPDATE, passano allo stato di scadenza (script.fn_stato_scadenza_id, oggi SCADUTO) dalla scrittura comune (script.fn_doc_scrivi_stato, attraverso la porta; il guard di transizione giudica la matrice, dove EMESSO -> SCADUTO e'' di processo). Passaggio di processo per causa (la data): niente prima riga, nessuna azione. Nessun parametro: chiude solo cio'' che la chiusura per scadenza chiuderebbe. Dichiarato in dbops.automazione_chiusura_scadenze.verbo_chiusura: lo chiama dbops.fn_apply_chiusura_scadenze. Gemello di vendite.fn_cessa_contratti_scaduti e vendite.fn_chiudi_versioni_listino_scadute. Ritorna quanti preventivi ha portato allo stato di scadenza. EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
