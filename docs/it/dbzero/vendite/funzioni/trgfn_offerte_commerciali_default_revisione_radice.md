# ⚙️ Funzione `trgfn_offerte_commerciali_default_revisione_radice`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_default_revisione_radice()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_default_revisione_radice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: derivare revisione_radice_id, l'identita' della catena delle
--   revisioni: l'id della rev.1 su se' stessa, la radice del padre su
--   ogni revisione successiva. Il valore passato dal chiamante non conta.
-- Regole:
--   - NEW.id e' gia' valorizzato (default di sequence, applicato prima
--     dei trigger BEFORE ROW);
--   - il padre si legge sotto RLS: se non si vede (o non esiste) la
--     revisione non nasce, con un errore dichiarato.
-- Brief: brief-db-liste-datatable-grezze §3.2 (2026-09-27).
DECLARE
    v_radice_id vendite.offerte_commerciali.revisione_radice_id%TYPE;
BEGIN
    IF NEW.revisione_padre_id IS NULL THEN
        NEW.revisione_radice_id := NEW.id;
        RETURN NEW;
    END IF;

    SELECT oc.revisione_radice_id
      INTO v_radice_id
      FROM vendite.offerte_commerciali oc
     WHERE oc.id = NEW.revisione_padre_id;

    IF v_radice_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_OFFERTA_REVISIONE_PADRE_NON_TROVATO',
            jsonb_build_object('revisione_padre_id', NEW.revisione_padre_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]
        );
    END IF;

    NEW.revisione_radice_id := v_radice_id;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_default_revisione_radice()
IS 'BEFORE INSERT su offerte_commerciali: deriva revisione_radice_id (l''id della rev.1 su se'' stessa; la radice del padre sulle revisioni successive). Il valore passato dal chiamante non conta. Padre non visibile o inesistente: E_OFFERTA_REVISIONE_PADRE_NON_TROVATO. Brief: brief-db-liste-datatable-grezze §3.2 (2026-09-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
