{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_guard_spegnimento_storia.md" %}
# ⚙️ Funzione `trgfn_listini_guard_spegnimento_storia`

```sql
CREATE FUNCTION trgfn_listini_guard_spegnimento_storia()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_guard_spegnimento_storia()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   BEFORE UPDATE OF attivo su vendite.listini: un listino con
    --   storia (vendite.fn_listino_ha_storia) non si spegne; si
    --   chiude con la fine validita' della versione in vigore.
    -- =========================================================
    IF OLD.attivo IS TRUE
       AND NEW.attivo IS FALSE
       AND vendite.fn_listino_ha_storia(OLD.id) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_LISTINO_CON_STORIA_NON_SPEGNIBILE',
            jsonb_build_object(
                'campo',      'attivo',
                'listino_id', OLD.id,
                'codice',     OLD.codice),
            NEW.tx_id,
            OLD.codice::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_guard_spegnimento_storia()
IS 'Guard BEFORE UPDATE OF attivo su vendite.listini (montato a05, prima della catena generica a10_*_block_deact): un listino con STORIA (vendite.fn_listino_ha_storia: almeno una versione ATTIVA o CHIUSA) non si spegne con l''interruttore -> E_LISTINO_CON_STORIA_NON_SPEGNIBILE (CONFLITTO_STATO; valori: codice del listino; campo attivo). Si chiude con la fine validita'' della versione in vigore (decisione di Tid del 2026-10-21; storia: D-1 del 2026-10-22). Prima usciva E_ATTIVO_BLOCK_CHILDREN_ACTIVE col rimedio «disattivare le righe», non eseguibile. Un listino senza storia passa e trova la catena generica. Richiesta BE §9.8 di brief-be-utenti-di-sviluppo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
