{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_componente.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_guard_componente`

```sql
CREATE FUNCTION trgfn_articoli_componenti_guard_componente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
    --   Rifiutare una composizione che la distinta non ammette:
    --   solleva il primo motivo di script.fn_check_articolo_riga
    --   (documento ARTICOLO, padre = prodotto_id). Il lato documento
    --   della check rifiuta un padre non composito
    --   (E_ARTICOLO_NON_COMPOSITO); i motivi giudicano il componente.
    --   BEFORE INSERT OR UPDATE OF componente_id, prodotto_id,
    --   attivo, valido_al.
    -- Una composizione nuova e': un legame attivo che nasce, che si
    --   attiva, che cambia componente o padre, o la cui fine si
    --   allontana (valido_al tolto o spostato in avanti). Chiudere
    --   un legame, o anticiparne la fine, non compone niente e non
    --   si giudica: un legame si chiude sempre.
    -- =========================================================
    IF NOT NEW.attivo THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND OLD.attivo
       AND NEW.componente_id IS NOT DISTINCT FROM OLD.componente_id
       AND NEW.prodotto_id   IS NOT DISTINCT FROM OLD.prodotto_id
       AND NOT (OLD.valido_al IS NOT NULL
                AND (NEW.valido_al IS NULL OR NEW.valido_al > OLD.valido_al)) THEN
        RETURN NEW;
    END IF;

    -- p_scelta_nuova = true: qui arriva solo una composizione nuova,
    -- quindi un componente ritirato e' un motivo.
    v_motivi := script.fn_check_articolo_riga(
        'ARTICOLO', NULL, NEW.componente_id, NULL, NULL, NEW.prodotto_id, true);

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
IS 'Guard BEFORE INSERT OR UPDATE OF componente_id, prodotto_id, attivo, valido_al su catalogo.articoli_componenti: giudica ogni composizione nuova con script.fn_check_articolo_riga (documento ARTICOLO, padre = prodotto_id, p_scelta_nuova = true) e solleva il primo motivo. Il lato documento della check rifiuta un padre inesistente o non composito (E_ARTICOLO_NON_COMPOSITO, campo prodotto_id); i motivi giudicano il componente: ritirato (E_ARTICOLO_OBSOLETO), uguale al padre (E_BOM_COMPONENTE_PADRE), composito, perche'' la distinta ha un livello solo (E_BOM_COMPONENTE_COMPOSITO), con un''IVA diversa dal padre (E_BOM_IVA_DISCORDANTE). Composizione nuova = un legame attivo che nasce, che si attiva, che cambia componente o padre, o la cui fine si allontana (valido_al tolto o spostato in avanti). Un legame spento, o che si chiude, non si giudica. Le righe-componente dei documenti espanse da una distinta esistente sono derivate e non passano di qui; il prodotto ritirato non conta, perche'' la sua distinta si continua a mantenere.';
```

</div>

---
{% include-markdown "signature-core.md" %}
