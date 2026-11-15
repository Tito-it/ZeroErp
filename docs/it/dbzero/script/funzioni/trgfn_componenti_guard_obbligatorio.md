{% include-markdown "it/dbzero/script/manual/trgfn_componenti_guard_obbligatorio.md" %}
# ⚙️ Funzione `trgfn_componenti_guard_obbligatorio`

```sql
CREATE FUNCTION trgfn_componenti_guard_obbligatorio()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_guard_obbligatorio()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE UPDATE OF attivo su *_righe_componenti — blocca
--   disattivazione (TRUE->FALSE) di componenti obbligatori.
--   I componenti obbligatori fanno sempre parte del documento;
--   per escluderli occorre modificare la BoM in catalogo.
DECLARE
    v_obbligatorio catalogo.articoli_componenti.obbligatorio%TYPE;
    v_codice_comp  catalogo.articoli.codice%TYPE;
BEGIN
    -- Scatta solo su transizione attivo TRUE -> FALSE
    IF OLD.attivo = TRUE AND NEW.attivo = FALSE THEN
        SELECT ac.obbligatorio, a.codice
          INTO v_obbligatorio, v_codice_comp
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
         WHERE ac.id = OLD.articolo_componente_id;

        IF v_obbligatorio THEN
            PERFORM script.fn_log_and_raise_error(
                'script', TG_NAME, 'E_DOC_COMPONENTE_OBBLIGATORIO',
                jsonb_build_object(
                    'articolo_componente_id', OLD.articolo_componente_id,
                    'componente_id',          OLD.componente_id
                ),
                NULL::uuid,
                COALESCE(v_codice_comp, OLD.componente_id::text)
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_guard_obbligatorio()
IS 'Trigger BEFORE UPDATE OF attivo su *_righe_componenti: blocca disattivazione (TRUE->FALSE) di componenti obbligatori. Raise E_DOC_COMPONENTE_OBBLIGATORIO (443). rev 2026-05-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
