{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_listino_se_composito.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_listino_se_composito`

```sql
CREATE FUNCTION trgfn_articoli_guard_listino_se_composito()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_listino_se_composito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE UPDATE OF is_composito — blocca la promozione di un
--   articolo a composito se ha gia' righe dirette in listini_righe.
--   I prezzi diretti in listino sarebbero semanticamente errati per
--   un composito (prezzo = SUM componenti, non dato di listino).
BEGIN
    -- Scatta solo quando is_composito passa da FALSE/NULL a TRUE
    IF NOT COALESCE(OLD.is_composito, FALSE)
       AND COALESCE(NEW.is_composito, FALSE)
    THEN
        IF EXISTS (
            SELECT 1 FROM vendite.listini_righe lr
             WHERE lr.articolo_id = NEW.id
               AND lr.attivo = TRUE
             LIMIT 1
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', TG_NAME, 'E_LISTINO_RIGA_COMPOSITO_VIETATO',
                jsonb_build_object(
                    'articolo_id', NEW.id,
                    'hint', 'Disattivare le righe listino esistenti prima di rendere composito l''articolo.'
                ),
                NULL::uuid,
                NEW.codice
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_listino_se_composito()
IS 'Trigger BEFORE UPDATE OF is_composito su articoli: blocca promozione a composito se esistono righe attive in listini_righe. Raise E_LISTINO_RIGA_COMPOSITO_VIETATO (446). rev 2026-05-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
