{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_iva.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_guard_iva`

```sql
CREATE FUNCTION trgfn_articoli_componenti_guard_iva()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_guard_iva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INSERT su articoli_componenti — verifica che iva_id del
--   componente coincida con iva_id del padre composito. NULL = NULL = coerente.
--   Messaggio parlante: mostra aliquota % invece dell''id numerico interno.
DECLARE
    v_iva_padre      catalogo.articoli.iva_id%TYPE;
    v_iva_figlio     catalogo.articoli.iva_id%TYPE;
    v_codice_padre   catalogo.articoli.codice%TYPE;
    v_codice_figlio  catalogo.articoli.codice%TYPE;
    v_iva_padre_pct  text;
    v_iva_figlio_pct text;
BEGIN
    -- Legge iva_id, codice e aliquota % di padre e figlio in unica query
    SELECT a_padre.iva_id,  a_padre.codice,
           COALESCE(iva_p.aliquota_iva::text, '—'),
           a_figlio.iva_id, a_figlio.codice,
           COALESCE(iva_f.aliquota_iva::text, '—')
      INTO v_iva_padre,  v_codice_padre,  v_iva_padre_pct,
           v_iva_figlio, v_codice_figlio, v_iva_figlio_pct
      FROM catalogo.articoli a_padre
      JOIN catalogo.articoli a_figlio
        ON a_figlio.id = NEW.componente_id
      LEFT JOIN config.iva iva_p ON iva_p.id = a_padre.iva_id
      LEFT JOIN config.iva iva_f ON iva_f.id = a_figlio.iva_id
     WHERE a_padre.id = NEW.prodotto_id;

    -- IVA padre e figlio devono coincidere (IS DISTINCT FROM gestisce NULL)
    IF v_iva_padre IS DISTINCT FROM v_iva_figlio THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME, 'E_BOM_IVA_DISCORDANTE',
            jsonb_build_object(
                'prodotto_id',    NEW.prodotto_id,
                'componente_id',  NEW.componente_id,
                'iva_padre_id',   v_iva_padre,
                'iva_figlio_id',  v_iva_figlio,
                'iva_padre_pct',  v_iva_padre_pct,
                'iva_figlio_pct', v_iva_figlio_pct
            ),
            NULL::uuid,
            v_codice_padre,
            v_iva_padre_pct,
            v_codice_figlio,
            v_iva_figlio_pct
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_guard_iva()
IS 'Trigger BEFORE INSERT su articoli_componenti: verifica iva_id figlio = iva_id padre composito. NULL = NULL = coerente. Messaggio mostra aliquota % (non id numerico). Raise E_BOM_IVA_DISCORDANTE (445). rev 2026-05-13.';
```

---
{% include-markdown "signature-core.md" %}
