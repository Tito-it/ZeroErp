{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_soggetto_coerenza_istanza.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_soggetto_coerenza_istanza`

```sql
CREATE FUNCTION trgfn_billing_account_guard_soggetto_coerenza_istanza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il ruolo del billing account e' quello giusto per la
--   sua istanza:
--   1. il soggetto raggiunto via NEW.soggetto_ruolo_id coincide
--      con il soggetto dell'istanza (NEW.istanza_utility_id);
--   2. il ruolo e' di tipo CLIENTE (rev 2026-10-09, D-7 di
--      brief-db-esecutivi-ba-coppia): dal BB
--      script.fn_guard_soggetto_ruolo, come le specializzazioni.
-- Allinea il vincolo DB al modello documentato in
-- istanze_utilities §7.3 ("il cliente vive dentro l'istanza").
-- ⚠️ Gira in fascia _a20_, DOPO il lock di colonna: su UPDATE
--   di soggetto_ruolo_id o istanza_utility_id deve parlare
--   l'immutabilita' (E_BA_ISTANZA_IMMUTABILE), non la coerenza.
-- rev 2026-10-19 (D-17b di brief-db-processi-accensione-per-
--   ambiente §6.17.1): il punto 1 dal BB
--   anagrafiche.fn_istanza_di_altro_soggetto, comune ai guard
--   di indirizzi, contatti, conti del ruolo e pratiche.
DECLARE
    v_soggetto_ruolo  anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
BEGIN
    SELECT sr.soggetto_id
      INTO v_soggetto_ruolo
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = NEW.soggetto_ruolo_id;

    -- 1. Il soggetto.
    -- Il BB risponde col soggetto dell'istanza solo quando e'
    -- diverso. Se il ruolo o l'istanza non si risolvono non dice
    -- niente: l'errore strutturale lo danno le FK.
    v_soggetto_istanza := anagrafiche.fn_istanza_di_altro_soggetto(
        NEW.istanza_utility_id, v_soggetto_ruolo);

    IF v_soggetto_istanza IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_BA_SOGGETTO_INCOERENTE_ISTANZA',
            jsonb_build_object(
                'campo', 'istanza_utility_id',
                'billing_account_id',  NEW.id,
                'codice',              NEW.codice,
                'istanza_utility_id',  NEW.istanza_utility_id,
                'soggetto_ruolo_id',   NEW.soggetto_ruolo_id,
                'ba_soggetto_id',      v_soggetto_ruolo,
                'istanza_soggetto_id', v_soggetto_istanza
            ),
            NEW.tx_id,
            NEW.codice,
            v_soggetto_ruolo::text,
            v_soggetto_istanza::text
        );
    END IF;

    -- 2. Il tipo: un billing account e' di un ruolo CLIENTE.
    --   Il soggetto l'ha gia' guardato il punto 1, quindi al BB
    --   si passa NULL: qui serve solo il tipo.
    PERFORM script.fn_guard_soggetto_ruolo(
        p_soggetto_id       := NULL,
        p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
        p_cd_int_ruolo      := 'CL');

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()
IS 'Guard del ruolo del billing account: (1) soggetti_ruoli.soggetto_id = istanze_utilities.soggetto_id, E_BA_SOGGETTO_INCOERENTE_ISTANZA — rev 2026-10-19 (D-17b, brief-db-processi-accensione-per-ambiente §6.17.1): il confronto dal BB anagrafiche.fn_istanza_di_altro_soggetto, comune ai guard di indirizzi, contatti, conti del ruolo e pratiche (regola del 2); codice, contesto e frase invariati; (2) rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-7): il ruolo e'' di tipo CLIENTE, dal BB script.fn_guard_soggetto_ruolo(NULL, sr, ''CL''), E_SOGGETTI_RUOLI — prima un BA poteva nascere sul ruolo FORNITORE del soggetto giusto, perche'' si confrontava il soggetto e non il tipo. Trigger in fascia _a20_ (dal 20261009-69): dopo il lock di colonna, che su UPDATE del ruolo o dell''istanza deve parlare per primo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
