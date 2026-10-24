{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_versioni_guard_date_chiusa.md" %}
# ⚙️ Funzione `trgfn_listini_versioni_guard_date_chiusa`

```sql
CREATE FUNCTION trgfn_listini_versioni_guard_date_chiusa()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_versioni_guard_date_chiusa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare il cambio di valido_dal / valido_al su una
--   versione di listino CHIUSA. Una versione chiusa e' la storia dei
--   prezzi di un periodo: spostarne le date riscrive quale versione
--   valeva in quelle date, e allungarne la fine la fa tornare valida
--   accanto all'ATTIVA.
-- Uso:   BEFORE UPDATE OF valido_dal, valido_al FOR EACH ROW
--        WHEN (OLD.stato = 'CHIUSA').
-- brief-db-liste-righe-documento §8.15 b), 2026-09-28.
BEGIN
    IF NEW.valido_dal IS DISTINCT FROM OLD.valido_dal
       OR NEW.valido_al IS DISTINCT FROM OLD.valido_al THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_LISTINO_VERSIONE_CHIUSA_DATE_IMMUTABILI',
            jsonb_build_object(
                'versione_id',   OLD.id,
                'listino_id',    OLD.listino_id,
                'valido_dal_da', OLD.valido_dal,
                'valido_dal_a',  NEW.valido_dal,
                'valido_al_da',  OLD.valido_al,
                'valido_al_a',   NEW.valido_al),
            NEW.tx_id,
            OLD.codice_versione::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_versioni_guard_date_chiusa()
IS 'Guard: le date di validita'' (valido_dal, valido_al) di una versione di listino CHIUSA non si modificano piu'' (E_LISTINO_VERSIONE_CHIUSA_DATE_IMMUTABILI). Una versione chiusa e'' la storia dei prezzi di un periodo: spostarne le date riscriverebbe quale versione valeva in quelle date, e allungarne la fine la farebbe tornare valida accanto all''ATTIVA. Rifiuta solo un cambio vero (IS DISTINCT FROM); la chiusura stessa (ATTIVA -> CHIUSA) non e'' toccata. Con ex_listini_versioni_no_overlap esteso a CHIUSA garantisce che per ogni data la versione in vigore sia al piu'' una (vendite.fn_listino_versione_in_vigore). Decisione di Tid del 2026-09-28, brief-db-liste-righe-documento §8.15.';
```

</div>

---
{% include-markdown "signature-core.md" %}
