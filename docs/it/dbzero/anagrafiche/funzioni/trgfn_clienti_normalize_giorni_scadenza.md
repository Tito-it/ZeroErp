{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_normalize_giorni_scadenza.md" %}
# ⚙️ Funzione `trgfn_clienti_normalize_giorni_scadenza`

```sql
CREATE FUNCTION trgfn_clienti_normalize_giorni_scadenza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_normalize_giorni_scadenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: normalize+guard simmetrico sul dominio scadenza
-- fattura del cliente. Pattern allineato a
-- trgfn_fornitori_guard_normalize:
--   - tipo NOT IN ('G','F') con nr_giorni valued -> NULL
--     forzato (normalize silenzioso, payload sporco)
--   - tipo IN ('G','F') con nr_giorni NULL o <= 0 -> raise
--     E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI (payload
--     ambiguo, l'utente probabilmente non ha specificato
--     il valore)
-- Le combinazioni valide sono ('G',>0), ('F',>0),
-- ('M', NULL), ('N', NULL).
BEGIN
    -- Branch 1: tipo non richiede giorni -> azzera.
    IF NEW.tipo_gg_scadenza_ft NOT IN ('G','F') THEN
        NEW.nr_giorni_scadenza := NULL;
        RETURN NEW;
    END IF;

    -- Branch 2: tipo richiede giorni -> guard.
    IF NEW.nr_giorni_scadenza IS NULL
       OR NEW.nr_giorni_scadenza <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI',
            jsonb_build_object(
                'cliente_id',         NEW.id,
                'tipo_gg_scadenza_ft', NEW.tipo_gg_scadenza_ft,
                'nr_giorni_scadenza',  NEW.nr_giorni_scadenza
            ),
            NEW.tx_id,
            NEW.tipo_gg_scadenza_ft,
            COALESCE(NEW.nr_giorni_scadenza::text, 'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_normalize_giorni_scadenza()
IS 'Normalize+guard scadenza fattura cliente. tipo NOT IN (G,F) -> nr_giorni=NULL forzato; tipo IN (G,F) con nr_giorni NULL/<=0 -> raise E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI. Pattern allineato a trgfn_fornitori_guard_normalize.';
```

---
{% include-markdown "signature-core.md" %}
