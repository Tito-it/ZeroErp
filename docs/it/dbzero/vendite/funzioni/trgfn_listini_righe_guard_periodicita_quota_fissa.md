# ⚙️ Funzione `trgfn_listini_righe_guard_periodicita_quota_fissa`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_periodicita_quota_fissa()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_periodicita_quota_fissa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: fuori dalla bozza la riga di una quota fissa a canone non resta
--   senza periodicita'. Regola completa nell'intestazione del changeSet
--   20261031-51.
DECLARE
    v_stato    config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_versione vendite.listini_versioni.codice_versione%TYPE;
    v_codice   catalogo.articoli.codice%TYPE;
BEGIN
    IF NEW.periodicita IS NOT NULL THEN
        RETURN NEW;
    END IF;

    SELECT s.codice_interno, lv.codice_versione INTO v_stato, v_versione
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = NEW.listino_versione_id;

    IF v_stato = 'BOZZA' OR NOT vendite.fn_articolo_quota_fissa_a_canone(NEW.articolo_id) THEN
        RETURN NEW;
    END IF;

    SELECT a.codice INTO v_codice FROM catalogo.articoli a WHERE a.id = NEW.articolo_id;

    PERFORM script.fn_log_and_raise_error(
        'vendite', TG_NAME, 'E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA',
        jsonb_build_object(
            'campo',               'periodicita',
            'listino_riga_id',     NEW.id,
            'listino_versione_id', NEW.listino_versione_id,
            'stato_versione',      v_stato),
        NEW.tx_id,
        COALESCE(v_codice, NEW.articolo_id::text),
        COALESCE(v_versione, NEW.listino_versione_id::text));
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_periodicita_quota_fissa()
IS 'Guard di vendite.listini_righe (BEFORE UPDATE OF periodicita, quando la periodicita'' va a NULL): fuori dalla bozza la riga di una quota fissa a canone (vendite.fn_articolo_quota_fissa_a_canone) non resta senza periodicita'' (E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA, campo periodicita). Cambiarla con un''altra resta una rettifica, come il prezzo (vendite.trgfn_listini_righe_guard_stato). Chiude il buco del controllo all''attivazione (D-3): senza, la quota la perdeva dopo, e ogni contratto del listino restava in CANONE_NON_GENERABILE. Nasce il 2026-10-31 (20261031-51), brief-db-contratto-righe-periodiche-in-commessa §7.10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
