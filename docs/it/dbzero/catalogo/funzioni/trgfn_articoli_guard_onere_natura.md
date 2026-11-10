{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_onere_natura.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_onere_natura`

```sql
CREATE FUNCTION trgfn_articoli_guard_onere_natura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_onere_natura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_natura        config.nature_vendita.descrizione%TYPE;
    -- Il nome di una colonna di catalogo.articoli: nessuna colonna
    -- ne e' il riflesso (come in trgfn_articoli_guard_struttura_se_usato).
    v_campo         text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un articolo-onere (causale_onere_id valorizzato) e' un
    --   addebito, non un bene:
    --   1. la sua natura non e' merce (script.fn_natura_e_merce);
    --   2. non e' gestito a magazzino, non e' composito, non e' a
    --      lotti ne' a matricola.
    --   BEFORE INSERT OR UPDATE OF natura_vendita_id,
    --   causale_onere_id, gestito_a_magazzino, is_composito,
    --   requires_lotto, requires_serial su catalogo.articoli. Un
    --   UPDATE che non cambia nessuna delle sei colonne non si
    --   rigiudica.
    -- =========================================================
    IF NEW.causale_onere_id IS NULL THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE'
       AND NEW.natura_vendita_id   IS NOT DISTINCT FROM OLD.natura_vendita_id
       AND NEW.causale_onere_id    IS NOT DISTINCT FROM OLD.causale_onere_id
       AND NEW.gestito_a_magazzino IS NOT DISTINCT FROM OLD.gestito_a_magazzino
       AND NEW.is_composito        IS NOT DISTINCT FROM OLD.is_composito
       AND NEW.requires_lotto      IS NOT DISTINCT FROM OLD.requires_lotto
       AND NEW.requires_serial     IS NOT DISTINCT FROM OLD.requires_serial THEN
        RETURN NEW;
    END IF;

    -- 1. La natura. Natura assente: il BB da' NULL, parla la FK.
    IF script.fn_natura_e_merce(NEW.natura_vendita_id) IS TRUE THEN
        SELECT COALESCE(nv.descrizione, nv.codice)
          INTO v_natura
          FROM config.nature_vendita nv
         WHERE nv.id = NEW.natura_vendita_id;

        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME::text, 'E_ARTICOLO_ONERE_NATURA_MERCE',
            jsonb_build_object(
                'campo',             'natura_vendita_id',
                'articolo_id',       NEW.id,
                'causale_onere_id',  NEW.causale_onere_id,
                'natura_vendita_id', NEW.natura_vendita_id),
            NEW.tx_id,
            NEW.codice,
            v_natura);
    END IF;

    -- 2. La struttura: la prima caratteristica da bene, in
    --    quest'ordine (magazzino, distinta, lotto, matricola).
    v_campo := CASE
        WHEN NEW.gestito_a_magazzino IS TRUE THEN 'gestito_a_magazzino'
        WHEN NEW.is_composito        IS TRUE THEN 'is_composito'
        WHEN NEW.requires_lotto      IS TRUE THEN 'requires_lotto'
        WHEN NEW.requires_serial     IS TRUE THEN 'requires_serial'
    END;

    IF v_campo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME::text, 'E_ARTICOLO_ONERE_STRUTTURA',
            jsonb_build_object(
                'campo',            v_campo,
                'articolo_id',      NEW.id,
                'causale_onere_id', NEW.causale_onere_id),
            NEW.tx_id,
            NEW.codice,
            catalogo.fn_articolo_flag_etichetta(v_campo));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_onere_natura()
IS 'Guard BEFORE INSERT OR UPDATE OF natura_vendita_id, causale_onere_id, gestito_a_magazzino, is_composito, requires_lotto, requires_serial su catalogo.articoli: un articolo-onere (causale_onere_id valorizzato) e'' un addebito, non un bene. 1. La sua natura non e'' merce (script.fn_natura_e_merce, la destinazione ORDINE_VENDITA dal vocabolario config.nature_vendita) -> E_ARTICOLO_ONERE_NATURA_MERCE, campo natura_vendita_id: un onere creato senza dire la natura prenderebbe il DEFAULT, la merce. 2. Non e'' gestito a magazzino, non e'' composito, non e'' a lotti ne'' a matricola -> E_ARTICOLO_ONERE_STRUTTURA, campo = la prima colonna in quest''ordine, valori codice dell''articolo e nome leggibile della caratteristica (catalogo.fn_articolo_flag_etichetta); nessuna porta amministratore. Cosi'' magazzino, prelievi, scarico e distinta restano a posto per costruzione anche con gli oneri sulle righe di ordine e bolla. La 1 parla prima della 2. Un UPDATE che non cambia nessuna delle sei colonne non rigiudica.';
```

</div>

---
{% include-markdown "signature-core.md" %}
