{% include-markdown "it/dbzero/script/manual/trgfn_componenti_check_prezzo_obbligatorio.md" %}
# ⚙️ Funzione `trgfn_componenti_check_prezzo_obbligatorio`

```sql
CREATE FUNCTION trgfn_componenti_check_prezzo_obbligatorio()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INSERT OR UPDATE su *_righe_componenti — blocca
--   prezzo_unitario=0 solo per componenti obbligatori. Componenti
--   opzionali ammettono prezzo=0 (incluso a costo zero). Negativi
--   ammessi per entrambi (sconti, abbuoni).
DECLARE
    v_obbligatorio  catalogo.articoli_componenti.obbligatorio%TYPE;
    v_codice_comp   catalogo.articoli.codice%TYPE;
BEGIN
    -- Legge obbligatorio e codice componente in unica query
    SELECT ac.obbligatorio, a.codice
      INTO v_obbligatorio, v_codice_comp
      FROM catalogo.articoli_componenti ac
      JOIN catalogo.articoli a ON a.id = ac.componente_id
     WHERE ac.id = NEW.articolo_componente_id;

    -- Obbligatorio + prezzo zero: bloccato
    IF COALESCE(v_obbligatorio, TRUE) AND NEW.prezzo_unitario = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO',
            jsonb_build_object(
                'campo',                  'prezzo_unitario',
                'articolo_componente_id', NEW.articolo_componente_id,
                'componente_id',          NEW.componente_id,
                'prezzo_unitario',        NEW.prezzo_unitario
            ),
            NULL::uuid,
            COALESCE(v_codice_comp, NEW.componente_id::text)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()
IS 'Trigger BEFORE INS/UPD su *_righe_componenti: blocca prezzo_unitario=0 se articoli_componenti.obbligatorio=TRUE. Opzionali e padre ammettono 0. Raise E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO (444). rev 2026-05-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
