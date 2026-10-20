{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_componente.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_guard_componente`

```sql
CREATE FUNCTION trgfn_articoli_componenti_guard_componente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_guard_componente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_motivi jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare un componente che la distinta non ammette: solleva
    --   il primo motivo di script.fn_check_articolo_riga
    --   (documento ARTICOLO, padre = prodotto_id). BEFORE INSERT OR
    --   UPDATE OF componente_id, prodotto_id, attivo.
    -- =========================================================
    IF NOT COALESCE(NEW.attivo, FALSE) THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND COALESCE(OLD.attivo, FALSE)
       AND NEW.componente_id IS NOT DISTINCT FROM OLD.componente_id
       AND NEW.prodotto_id   IS NOT DISTINCT FROM OLD.prodotto_id THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_articolo_riga(
        'ARTICOLO', NULL, NEW.componente_id, NULL, NULL, NEW.prodotto_id);

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'catalogo', TG_NAME::text,
        v_motivi,
        COALESCE(v_motivi -> 0 -> 'dettaglio' ->> 'campo', 'componente_id'),
        NEW.tx_id,
        jsonb_build_object('legame_id', NEW.id, 'prodotto_id', NEW.prodotto_id));
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_guard_componente()
IS 'Guard BEFORE INSERT OR UPDATE OF componente_id, prodotto_id, attivo su catalogo.articoli_componenti (Lotto 3c di brief-db-articoli-ammessi-per-documento, 2026-10-13): solleva il primo motivo di script.fn_check_articolo_riga per il componente (documento ARTICOLO, padre = prodotto_id): componente uguale al padre (E_BOM_COMPONENTE_PADRE), composito (E_BOM_COMPONENTE_COMPOSITO, D-4), IVA diversa dal padre (E_BOM_IVA_DISCORDANTE). Giudica un legame attivo quando nasce, quando si attiva e quando cambia componente o padre; un legame spento no. Guard suo perche'' qui articolo e padre sono componente_id e prodotto_id (uuid), non articolo_id e un id di documento; la regola resta una, nella check. Sostituisce catalogo.trgfn_articoli_componenti_guard_un_livello e catalogo.trgfn_articoli_componenti_guard_iva (ritirati da 20261013-61).';
```

</div>

---
{% include-markdown "signature-core.md" %}
