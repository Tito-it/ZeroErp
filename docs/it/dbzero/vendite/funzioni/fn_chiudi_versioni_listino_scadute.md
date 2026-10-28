{% include-markdown "it/dbzero/vendite/manual/fn_chiudi_versioni_listino_scadute.md" %}
# ⚙️ Funzione `fn_chiudi_versioni_listino_scadute`

```sql
CREATE FUNCTION fn_chiudi_versioni_listino_scadute()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_chiudi_versioni_listino_scadute()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente    config.user_override_azioni.auth_user_id%TYPE;
    v_attiva_id config.stati_doc_listino_versioni.id%TYPE;
    v_chiusa_id config.stati_doc_listino_versioni.id%TYPE;
    v_id        vendite.listini_versioni.id%TYPE;
    -- CONTEGGIO delle versioni chiuse.
    v_n         integer := 0;
BEGIN
    -- ==========================================================
    -- Scopo: chiudere le versioni attive scadute del perimetro.
    --   Vedi l'intestazione del changeSet 20261028-13.
    -- Ritorna: quante versioni sono state chiuse.
    -- ==========================================================
    v_utente    := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    v_attiva_id := script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'ATTIVA');
    v_chiusa_id := script.fn_doc_stato_id('vendite.listini_versioni'::regclass, 'CHIUSA');

    IF v_attiva_id IS NULL OR v_chiusa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_chiudi_versioni_listino_scadute',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_listino_versioni',
                               'attiva_id', v_attiva_id, 'chiusa_id', v_chiusa_id),
            NULL::uuid, 'stati ATTIVA e CHIUSA (config.stati_doc_listino_versioni)');
    END IF;

    FOR v_id IN
        SELECT lv.id
          FROM vendite.listini_versioni lv
         WHERE lv.stato_doc_listino_versione_id = v_attiva_id
           AND lv.valido_al IS NOT NULL
           AND lv.valido_al < (SELECT script.fn_data_operativa())
           AND script.fn_scope_ef_whitelist_via_listino_versione(v_utente, lv.id)
         ORDER BY lv.id
           FOR UPDATE OF lv
    LOOP
        PERFORM script.fn_doc_scrivi_stato('vendite.listini_versioni'::regclass, v_id, v_chiusa_id);
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION vendite.fn_chiudi_versioni_listino_scadute()
IS 'VERBO della chiusura per scadenza delle versioni di listino (brief-modello-documento-vendita §16, L-2 di Tid 2026-10-28): le versioni ATTIVE con valido_al passata (< script.fn_data_operativa()), nel perimetro dell''utente della sessione (script.fn_scope_ef_whitelist_via_listino_versione: DEFINER, la RLS non c''e''), prese FOR UPDATE, passano a CHIUSA dalla scrittura comune (script.fn_doc_scrivi_stato, attraverso la porta; il guard di transizione giudica matrice e data passata). Passaggio di processo per causa (la data): niente prima riga, nessuna azione. Nessun parametro. Dichiarato in dbops.automazione_chiusura_scadenze.verbo_chiusura: lo chiama dbops.fn_apply_chiusura_scadenze. Gemello di vendite.fn_cessa_contratti_scaduti. Prende il posto dell''UPDATE dinamico del framework. Ritorna quante versioni ha chiuso. EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
