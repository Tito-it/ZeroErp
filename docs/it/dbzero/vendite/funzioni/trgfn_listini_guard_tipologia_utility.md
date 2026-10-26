{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_guard_tipologia_utility.md" %}
# ⚙️ Funzione `trgfn_listini_guard_tipologia_utility`

```sql
CREATE FUNCTION trgfn_listini_guard_tipologia_utility()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_guard_tipologia_utility()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: verifica che la coppia (utility_id, tipologia_id) sia ammessa
--   dalla matrice config.listini_tipologie_utilities con attivo = true.
-- Regole:
--   - Se la coppia non esiste o non e` attiva → errore E_LISTINO_TIPOLOGIA_UTILITY
--   - Scatta solo su INSERT e UPDATE OF utility_id, tipologia_id
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM config.listini_tipologie_utilities ltu
         WHERE ltu.utility_id = NEW.utility_id
           AND ltu.tipologia_id = NEW.tipologia_id
           AND ltu.attivo = true
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.trgfn_listini_guard_tipologia_utility',
            'E_LISTINO_TIPOLOGIA_UTILITY',
            jsonb_build_object(
                'campo', 'tipologia_id',
                'listino_id', NEW.id,
                'utility_id', NEW.utility_id,
                'tipologia_id', NEW.tipologia_id
            ),
            NEW.tx_id,
            NEW.utility_id::text, NEW.tipologia_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_guard_tipologia_utility()
IS 'Guard: verifica ammissibilita` coppia (utility_id, tipologia_id) nella matrice config.listini_tipologie_utilities.';
```

</div>

---
{% include-markdown "signature-core.md" %}
