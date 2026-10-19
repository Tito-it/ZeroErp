# ⚙️ Funzione `trgfn_template_standard_guard_sola_lettura`

```sql
CREATE FUNCTION trgfn_template_standard_guard_sola_lettura()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il modello standard (template_documenti.standard) e le sue
--   versioni si scrivono solo dal proprietario della tabella, cioe'
--   dal seed e dai changeSet. Dall'applicazione: sola lettura.
-- Montaggio: BEFORE INSERT OR UPDATE OR DELETE, FOR EACH ROW, su
--   documenti.template_documenti e documenti.template_documenti_versioni.
DECLARE
    v_template_id  documenti.template_documenti.id%TYPE;
    v_standard     documenti.template_documenti.standard%TYPE := false;
    v_codice       documenti.template_documenti.codice%TYPE;
BEGIN
    IF TG_TABLE_NAME = 'template_documenti' THEN
        -- La riga stessa: quella di prima (UPDATE, DELETE) e quella
        -- di dopo (INSERT, UPDATE). IF annidati: OLD e NEW si
        -- leggono solo dove l'operazione li ha.
        IF TG_OP IN ('UPDATE', 'DELETE') THEN
            IF OLD.standard THEN
                v_standard := true;
                v_template_id := OLD.id;
                v_codice := OLD.codice;
            END IF;
        END IF;
        IF TG_OP IN ('INSERT', 'UPDATE') THEN
            IF NEW.standard THEN
                v_standard := true;
                v_template_id := NEW.id;
                v_codice := NEW.codice;
            END IF;
        END IF;
    ELSE
        -- Una versione: lo dice il modello a cui appartiene, prima
        -- e dopo (una versione non si sposta da uno standard).
        IF TG_OP IN ('UPDATE', 'DELETE') THEN
            SELECT t.id, t.codice
              INTO v_template_id, v_codice
              FROM documenti.template_documenti t
             WHERE t.id = OLD.template_documento_id
               AND t.standard;
            v_standard := FOUND;
        END IF;
        IF NOT v_standard AND TG_OP IN ('INSERT', 'UPDATE') THEN
            SELECT t.id, t.codice
              INTO v_template_id, v_codice
              FROM documenti.template_documenti t
             WHERE t.id = NEW.template_documento_id
               AND t.standard;
            v_standard := FOUND;
        END IF;
    END IF;

    IF v_standard AND NOT script.fn_is_proprietario_tabella(TG_RELID) THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'trgfn_template_standard_guard_sola_lettura',
            'E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA',
            jsonb_build_object(
                'template_documento_id', v_template_id,
                'operazione',            TG_OP,
                'tabella',               TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'current_user',          current_user,
                'detail',                'Il modello standard si scrive dal seed e dai changeSet; dall''applicazione si personalizza per un emittente'
            ),
            NULL::uuid,
            v_codice::text
        );
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()
IS 'Guard BEFORE INSERT/UPDATE/DELETE su documenti.template_documenti e documenti.template_documenti_versioni (2026-10-20, brief-db-modelli-documento-standard D-2): il modello standard (colonna standard) e le sue versioni si scrivono solo dal proprietario della tabella (script.fn_is_proprietario_tabella: il seed e i changeSet). Dall''applicazione si leggono, e chi vuole un modello diverso lo personalizza per il suo emittente. Su UPDATE conta la riga di prima e quella di dopo; sulle versioni conta il modello padre di prima e di dopo. Rifiuto E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA (NON_PERMESSO; valori: codice del modello). Fase a05: parla prima degli altri guard e del default dell''emittente.';
```

---
{% include-markdown "signature-core.md" %}
