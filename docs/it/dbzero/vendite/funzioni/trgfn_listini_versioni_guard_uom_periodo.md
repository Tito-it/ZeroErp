{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_versioni_guard_uom_periodo.md" %}
# ⚙️ Funzione `trgfn_listini_versioni_guard_uom_periodo`

```sql
CREATE FUNCTION trgfn_listini_versioni_guard_uom_periodo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_versioni_guard_uom_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_riga record;
BEGIN
    -- =========================================================
    -- Scopo: il periodo nuovo di una versione copre solo giorni in
    --   cui le unita' dei suoi prezzi attivi si convertono.
    -- Eventi: AFTER UPDATE OF valido_dal, valido_al; WHEN il
    --   periodo nuovo non sta dentro il vecchio.
    -- =========================================================
    SELECT x.* INTO v_riga
      FROM vendite.fn_listino_versione_riga_uom_non_convertibile(NEW.id) x;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite', 'vendite.trgfn_listini_versioni_guard_uom_periodo', 'E_LISTINO_UOM_NON_CONVERTIBILE',
        jsonb_build_object(
            'campo',               CASE WHEN NEW.valido_dal IS DISTINCT FROM OLD.valido_dal
                                        THEN 'valido_dal' ELSE 'valido_al' END,
            'listino_versione_id', NEW.id,
            'riga_id',             v_riga.riga_id,
            'articolo_id',         v_riga.articolo_id,
            'primo_giorno',        v_riga.primo_giorno,
            'bersaglio',           jsonb_build_array(
                                       jsonb_build_object('tipo', 'LISTINO_VERSIONE', 'id', NEW.id::text))),
        NEW.tx_id,
        NEW.codice_versione::text,
        v_riga.uom_codice::text,
        v_riga.articolo_codice::text,
        to_char(v_riga.primo_giorno, 'DD/MM/YYYY'));
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_versioni_guard_uom_periodo()
IS 'Guard del periodo di una versione di listino rispetto alle unita'' dei suoi prezzi (vendite.listini_versioni): allungare o spostare il periodo non lascia un prezzo attivo in un''unita'' che, in un giorno del periodo nuovo, non si converte per l''articolo. AFTER UPDATE OF valido_dal, valido_al, quando il periodo nuovo non sta dentro quello di prima (accorciare non scopre niente). Legge vendite.fn_listino_versione_riga_uom_non_convertibile. Scoperto -> E_LISTINO_UOM_NON_CONVERTIBILE (campo: la data cambiata, valido_al o valido_dal; valori: versione, unita'', articolo, primo giorno scoperto; bersaglio LISTINO_VERSIONE). In ATTIVA la fine la cambiano solo i verbi (vendite.trgfn_listini_versioni_guard_per_stato), e il giudizio vale anche per loro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
