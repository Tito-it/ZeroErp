{% include-markdown "it/dbzero/vendite/manual/fn_cessa_contratti_scaduti.md" %}
# ⚙️ Funzione `fn_cessa_contratti_scaduti`

```sql
CREATE FUNCTION fn_cessa_contratti_scaduti()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cessa_contratti_scaduti()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente     config.user_override_azioni.auth_user_id%TYPE;
    v_attivo_id  config.stati_doc_contratti.id%TYPE;
    v_cessato_id config.stati_doc_contratti.id%TYPE;
    v_id         vendite.contratti.id%TYPE;
    -- CONTEGGIO dei contratti cessati.
    v_n          integer := 0;
BEGIN
    -- ==========================================================
    -- Scopo: cessare i contratti attivi scaduti del perimetro.
    --   Vedi l'intestazione del changeSet.
    --   rev 2026-10-31 (20261031-12, brief-modello-documento-vendita §17): anche lo
    --   stato di cessazione dal vocabolario, non 'CESSATO'.
    -- Ritorna: quanti contratti sono stati cessati.
    -- ==========================================================
    v_utente     := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    v_attivo_id  := script.fn_stato_emissione_id('vendite.contratti'::regclass);
    v_cessato_id := script.fn_stato_cessazione_id('vendite.contratti'::regclass);

    IF v_attivo_id IS NULL OR v_cessato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cessa_contratti_scaduti',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_contratti',
                               'attivo_id', v_attivo_id, 'cessato_id', v_cessato_id),
            NULL::uuid, 'stato di emissione e di cessazione (config.stati_doc_contratti)');
    END IF;

    FOR v_id IN
        SELECT c.id
          FROM vendite.contratti c
         WHERE c.stato_doc_contratto_id = v_attivo_id
           AND c.valido_al IS NOT NULL
           AND c.valido_al < (SELECT script.fn_data_operativa())
           AND script.fn_scope_ef_whitelist_via_contratto(v_utente, c.id)
         ORDER BY c.id
           FOR UPDATE OF c
    LOOP
        PERFORM script.fn_doc_scrivi_stato('vendite.contratti'::regclass, v_id, v_cessato_id);
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cessa_contratti_scaduti()
IS 'VERBO della cessazione automatica dei contratti (brief-modello-documento-vendita §11, Y-2 di Tid 2026-10-26): i contratti nello stato di emissione (ATTIVO, script.fn_stato_emissione_id) con valido_al passata (< script.fn_data_operativa()), nel perimetro dell''utente della sessione (script.fn_scope_ef_whitelist_via_contratto: DEFINER, la RLS non c''e''), presi FOR UPDATE, passano allo stato di cessazione (script.fn_stato_cessazione_id, dal 2026-10-31, §17; oggi CESSATO) dalla scrittura comune (script.fn_doc_scrivi_stato, attraverso la porta; il guard di transizione giudica matrice e data arrivata). Passaggio di processo per causa (la data): niente prima riga. Nessun parametro: cessa solo cio'' che la chiusura per scadenza cesserebbe. La chiama dbops.fn_apply_chiusura_scadenze per il bersaglio vendite.contratti (sotto la porta). Prende il posto dell''UPDATE dinamico del framework e della GUC app.cessazione_automatica. Ritorna quanti contratti ha cessato. EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
