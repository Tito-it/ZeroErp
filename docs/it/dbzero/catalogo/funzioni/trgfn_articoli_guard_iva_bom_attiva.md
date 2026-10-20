{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_iva_bom_attiva`

```sql
CREATE FUNCTION trgfn_articoli_guard_iva_bom_attiva()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_iva_bom_attiva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE UPDATE OF iva_id su articoli — blocca modifiche che
--   renderebbero incoerente la BoM. Caso A: padre composito con figli
--   aventi IVA diversa da NEW.iva_id. Caso B: figlio in BoM attive
--   con padre avente IVA diversa da NEW.iva_id.
--   Messaggio parlante: mostra aliquota % invece dell''id numerico interno.
DECLARE
    v_codice_altro   catalogo.articoli.codice%TYPE;
    v_iva_altro      catalogo.articoli.iva_id%TYPE;
    v_iva_altro_pct  text;
    v_iva_nuovo_pct  text;
BEGIN
    -- Lookup aliquota IVA nuova (NEW.iva_id) — usata in entrambi i casi
    SELECT COALESCE(aliquota_iva::text, '—') INTO v_iva_nuovo_pct
      FROM config.iva WHERE id = NEW.iva_id;

    -- Caso A: articolo e' padre composito — cerca figlio attivo con IVA diversa
    IF COALESCE(NEW.is_composito, FALSE) THEN
        SELECT a.codice, a.iva_id, COALESCE(iva.aliquota_iva::text, '—')
          INTO v_codice_altro, v_iva_altro, v_iva_altro_pct
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
          LEFT JOIN config.iva iva ON iva.id = a.iva_id
         WHERE ac.prodotto_id = NEW.id
           AND ac.attivo      = TRUE
           AND a.iva_id IS DISTINCT FROM NEW.iva_id
         LIMIT 1;

        IF FOUND THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', TG_NAME, 'E_BOM_IVA_DISCORDANTE',
                jsonb_build_object(
                    'prodotto_id',     NEW.id,
                    'iva_padre_nuova', NEW.iva_id,
                    'iva_padre_pct',   v_iva_nuovo_pct,
                    'codice_figlio',   v_codice_altro,
                    'iva_figlio',      v_iva_altro,
                    'iva_figlio_pct',  v_iva_altro_pct
                ),
                NULL::uuid,
                NEW.codice,
                v_iva_nuovo_pct,
                v_codice_altro,
                v_iva_altro_pct
            );
        END IF;
    END IF;

    -- Caso B: articolo e' figlio — cerca padre attivo con IVA diversa
    SELECT a.codice, a.iva_id, COALESCE(iva.aliquota_iva::text, '—')
      INTO v_codice_altro, v_iva_altro, v_iva_altro_pct
      FROM catalogo.articoli_componenti ac
      JOIN catalogo.articoli a ON a.id = ac.prodotto_id
      LEFT JOIN config.iva iva ON iva.id = a.iva_id
     WHERE ac.componente_id = NEW.id
       AND ac.attivo        = TRUE
       AND a.iva_id IS DISTINCT FROM NEW.iva_id
     LIMIT 1;

    IF FOUND THEN
        -- Caso B: padre = v_codice_altro, figlio = NEW.codice
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME, 'E_BOM_IVA_DISCORDANTE',
            jsonb_build_object(
                'componente_id',   NEW.id,
                'iva_figlio_nuova', NEW.iva_id,
                'iva_figlio_pct',   v_iva_nuovo_pct,
                'codice_padre',     v_codice_altro,
                'iva_padre',        v_iva_altro,
                'iva_padre_pct',    v_iva_altro_pct
            ),
            NULL::uuid,
            v_codice_altro,
            v_iva_altro_pct,
            NEW.codice,
            v_iva_nuovo_pct
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_iva_bom_attiva()
IS 'Trigger BEFORE UPDATE OF iva_id su articoli: caso A padre composito -> figli attivi devono avere stessa IVA; caso B figlio -> padre attivo deve avere stessa IVA. Messaggio mostra aliquota % (non id numerico). Raise E_BOM_IVA_DISCORDANTE (445). rev 2026-05-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
