{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_guard_chiusura.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_guard_chiusura`

```sql
CREATE FUNCTION trgfn_vendite_contabili_guard_chiusura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_guard_chiusura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_a    pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_pronte     integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una distinta contabile non si CHIUDE finche' ha righe
    --   pronte da registrare. E' la porta d'uscita del difetto
    --   C-5, e quella che capita davvero: si registra, restano due
    --   righe non pronte, qualcuno chiude comunque - e quelle
    --   righe spariscono da entrambi i conti.
    --
    -- ⚠️ Vale su CHIUSA, NON su ANNULLATA: «e' fatta» e «non e'
    --    mai successa» sono opposti. Una distinta annullata non
    --    deve contare in nessun conto, righe pronte comprese.
    --
    -- ⚠️ Il blocco lo danno le righe is_postabile, non le NON
    --    finali: DA_ABBINARE e SOSPESA non bloccano, o la distinta
    --    non si chiuderebbe mai.
    -- =========================================================

    IF NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
        RETURN NEW;
    END IF;

    SELECT s.codice_interno
      INTO v_stato_a
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.id = NEW.stato_id;

    IF v_stato_a IS DISTINCT FROM 'CHIUSA' THEN
        RETURN NEW;
    END IF;

    SELECT count(*)
      INTO v_pronte
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati s ON s.id = cr.stato_id
     WHERE cr.contabile_id = NEW.id
       AND cr.attivo IS TRUE
       AND s.is_postabile IS TRUE;

    IF v_pronte = 0 THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'database',
        'pagamenti.trgfn_vendite_contabili_guard_chiusura',
        'E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE',
        jsonb_build_object(
            'contabile_id',  NEW.id,
            'codice',        NEW.codice,
            'righe_pronte',  v_pronte
        ),
        NEW.tx_id,
        NEW.codice,
        v_pronte::text
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_guard_chiusura()
IS 'C-5, porta d''USCITA: una distinta contabile non si chiude finche'' ha righe is_postabile ancora attive. E'' il percorso che capita davvero - si registra, restano righe non pronte, qualcuno chiude comunque - e quelle righe spariscono da entrambi i conti. ⚠️ Vale su CHIUSA e NON su ANNULLATA: «e'' fatta» e «non e'' mai successa» sono opposti. ⚠️ Il blocco lo danno le righe PRONTE (is_postabile), non le non-finali: con NOT is_final una distinta con una riga DA_ABBINARE non si chiuderebbe mai. ⭐ Con questo guard la chiusura smette di essere una scelta della funzione madre e diventa una conseguenza (chiude in gran parte Q-6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
