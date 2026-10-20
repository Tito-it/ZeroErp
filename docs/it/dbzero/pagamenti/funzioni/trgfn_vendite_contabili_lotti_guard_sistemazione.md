{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_lotti_guard_sistemazione.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_lotti_guard_sistemazione`

```sql
CREATE FUNCTION trgfn_vendite_contabili_lotti_guard_sistemazione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sistemazione_id pagamenti.sistemazioni.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire di agganciare a un lotto di fatturazione una
    --   distinta contabile nata da una SISTEMAZIONE.
    --
    -- ⭐ Un lotto raccoglie le fatture prodotte in un giro di
    --   emissione; una distinta di sistemazione registra un
    --   rimborso o una compensazione decisi su documenti gia'
    --   emessi. Non appartiene a nessun giro.
    --
    -- 🔴 La domanda si fa FUORI dalla row security: pagamenti.sistemazioni
    --   ha la RLS, e questo guard e' SECURITY INVOKER. La contabile
    --   di una compensazione e' una distinta INTERNA, quindi
    --   VISIBILE A TUTTI: senza la SECURITY DEFINER, un operatore
    --   di un'altra azienda la aggancerebbe al proprio lotto e il
    --   guard non vedrebbe l'atto che c'e' dietro.
    --
    -- Rev 2026-08-22 (lotto 7, D15-e): era
    -- trgfn_vendite_contabili_lotti_guard_compensazione e leggeva
    -- vendite_contabili.compensazione_id, che non esiste piu'.
    -- =========================================================

    v_sistemazione_id :=
        script.fn_get_sistemazione_di_contabile(NEW.contabile_id);

    IF v_sistemazione_id IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione',
            'E_CONTABILE_SISTEMAZIONE_CON_LOTTO',
            jsonb_build_object(
                'detail', 'distinta nata da una sistemazione: non si collega a un lotto',
                'contabile_id', NEW.contabile_id,
                'lotto_id', NEW.lotto_id,
                'sistemazione_id', v_sistemazione_id
            ),
            NULL::uuid,
            NEW.contabile_id::text
        );
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione()
IS 'Una distinta contabile nata da una SISTEMAZIONE non si aggancia a un lotto di fatturazione: il lotto raccoglie le fatture prodotte in un giro di emissione, la distinta registra un rimborso o una compensazione decisi su documenti gia'' emessi. ⭐ Sostituisce trgfn_vendite_contabili_lotti_guard_compensazione (2026-08-22, D15-e): il predicato si allarga a tutte e tre le destinazioni — anche una distinta di rimborso non c''entra con un lotto, e la regola vecchia non la copriva solo perche'' il rimborso non esisteva ancora come atto. ⭐ E da DUE porte diventa UNA: girato il verso del legame la contabile non sa piu'' di essere nata da un atto, quindi il guard gemello su vendite_contabili perde il dato e il momento in cui scattare. Resta quella giusta: il pericolo e'' agganciare al lotto, e si presidia dove si aggancia. 🔴 La lettura passa da script.fn_get_sistemazione_di_contabile, SECURITY DEFINER: sistemazioni ha la RLS e la contabile di una compensazione e'' una distinta INTERNA, visibile a tutti — da SECURITY INVOKER il guard tacerebbe proprio nel caso che deve coprire.';
```

</div>

---
{% include-markdown "signature-core.md" %}
