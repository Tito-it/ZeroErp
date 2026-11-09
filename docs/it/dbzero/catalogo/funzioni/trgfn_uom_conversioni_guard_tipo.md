{% include-markdown "it/dbzero/catalogo/manual/trgfn_uom_conversioni_guard_tipo.md" %}
# ⚙️ Funzione `trgfn_uom_conversioni_guard_tipo`

```sql
CREATE FUNCTION trgfn_uom_conversioni_guard_tipo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_from_tipo   catalogo.unita_misura.tipo_uom_id%TYPE;
    v_to_tipo     catalogo.unita_misura.tipo_uom_id%TYPE;
    v_from_codice catalogo.unita_misura.codice%TYPE;
    v_to_codice   catalogo.unita_misura.codice%TYPE;
    v_from_tdesc  catalogo.uom_tipi.descrizione%TYPE;
    v_to_tdesc    catalogo.uom_tipi.descrizione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una conversione generale vale solo fra unita' della stessa
    --   tipologia (massa con massa, tempo con tempo). Le conversioni
    --   fra tipologie diverse (il cartone di pezzi) sono dell'articolo:
    --   catalogo.articoli_uom_operativa.
    -- FOR SHARE: la tipologia letta non cambia finche' la conversione
    --   non e' scritta. Senza, una transazione che cambia la tipologia
    --   dell'unita' (e conta zero conversioni) e una che scrive la
    --   conversione (e legge la tipologia vecchia) passerebbero tutte e
    --   due. FOR SHARE aspetta il NO KEY UPDATE dell'altra, e viceversa.
    -- =========================================================
    SELECT u.tipo_uom_id, u.codice INTO v_from_tipo, v_from_codice
      FROM catalogo.unita_misura u
     WHERE u.id = NEW.uom_from_id
       FOR SHARE;

    SELECT u.tipo_uom_id, u.codice INTO v_to_tipo, v_to_codice
      FROM catalogo.unita_misura u
     WHERE u.id = NEW.uom_to_id
       FOR SHARE;

    -- Un'unita' che non c'e': parla la FK.
    IF v_from_codice IS NULL OR v_to_codice IS NULL THEN
        RETURN NEW;
    END IF;

    IF v_from_tipo IS DISTINCT FROM v_to_tipo THEN
        SELECT t.descrizione INTO v_from_tdesc FROM catalogo.uom_tipi t WHERE t.id = v_from_tipo;
        SELECT t.descrizione INTO v_to_tdesc   FROM catalogo.uom_tipi t WHERE t.id = v_to_tipo;
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_uom_conversioni_guard_tipo',
            'E_UOM_CONVERSIONE_TIPO_DIVERSO',
            jsonb_build_object(
                'campo',       'uom_to_id',
                'uom_from_id', NEW.uom_from_id,
                'uom_to_id',   NEW.uom_to_id,
                'tipo_from',   v_from_tipo,
                'tipo_to',     v_to_tipo),
            NULL::uuid,
            v_from_codice, v_to_codice,
            COALESCE(v_from_tdesc, '—'), COALESCE(v_to_tdesc, '—'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()
IS 'Guard BEFORE INSERT e UPDATE OF uom_from_id, uom_to_id su catalogo.unita_misura_conversioni: una conversione generale vale solo fra unita'' della stessa tipologia (catalogo.unita_misura.tipo_uom_id), altrimenti E_UOM_CONVERSIONE_TIPO_DIVERSO. Le conversioni fra tipologie diverse (il cartone di pezzi) stanno nella mappatura dell''articolo, catalogo.articoli_uom_operativa. Legge le due unita'' FOR SHARE, cosi'' un cambio di tipologia concorrente (catalogo.trgfn_unita_misura_guard_tipo) aspetta la conversione, o la conversione aspetta lui. Un''unita'' che non esiste la rifiuta la FK.';
```

</div>

---
{% include-markdown "signature-core.md" %}
