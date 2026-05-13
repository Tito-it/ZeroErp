{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_guard_no_composito.md" %}
# ⚙️ Funzione `trgfn_listini_righe_guard_no_composito`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_no_composito()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_no_composito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INSERT su listini_righe — blocca inserimento diretto
--   di prezzo per articoli compositi. Il prezzo padre di un composito
--   e' la somma dei prezzi componenti (listini_righe_componenti).
DECLARE
    v_is_composito catalogo.articoli.is_composito%TYPE;
    v_codice       catalogo.articoli.codice%TYPE;
BEGIN
    SELECT a.is_composito, a.codice
      INTO v_is_composito, v_codice
      FROM catalogo.articoli a
     WHERE a.id = NEW.articolo_id;

    IF COALESCE(v_is_composito, FALSE) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_LISTINO_RIGA_COMPOSITO_VIETATO',
            jsonb_build_object(
                'articolo_id',          NEW.articolo_id,
                'listino_versione_id',  NEW.listino_versione_id
            ),
            NULL::uuid,
            v_codice
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_no_composito()
IS 'Trigger BEFORE INSERT su listini_righe: blocca inserimento per articoli is_composito=TRUE. Prezzo composito = SUM componenti via listini_righe_componenti. Raise E_LISTINO_RIGA_COMPOSITO_VIETATO (446). rev 2026-05-13.';
```

---
{% include-markdown "signature-core.md" %}
