{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_soggetto_coerenza_istanza.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_soggetto_coerenza_istanza`

```sql
CREATE FUNCTION trgfn_billing_account_guard_soggetto_coerenza_istanza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: garantire la coerenza modello "1 soggetto per istanza".
-- Verifica che il soggetto raggiunto via NEW.soggetto_ruolo_id
-- coincida con il soggetto dell'istanza ancorata in
-- NEW.istanza_utility_id. Raise se differiscono.
-- Allinea il vincolo DB al modello documentato in
-- istanze_utilities §7.3 ("il cliente vive dentro l'istanza").
DECLARE
    v_soggetto_ruolo  anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
BEGIN
    SELECT sr.soggetto_id
      INTO v_soggetto_ruolo
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = NEW.soggetto_ruolo_id;

    SELECT iu.soggetto_id
      INTO v_soggetto_istanza
      FROM anagrafiche.istanze_utilities iu
     WHERE iu.id = NEW.istanza_utility_id;

    -- Difensivo: se uno dei due lookup non risolve, le FK
    -- esistenti gestiranno l'errore strutturale. Qui il
    -- guard si limita al confronto quando entrambi sono
    -- popolati (caso normale grazie ai NOT NULL).
    IF v_soggetto_ruolo IS NOT NULL
       AND v_soggetto_istanza IS NOT NULL
       AND v_soggetto_ruolo IS DISTINCT FROM v_soggetto_istanza
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_BA_SOGGETTO_INCOERENTE_ISTANZA',
            jsonb_build_object(
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

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()
IS 'Guard coerenza soggetto BA <-> istanza_utilities. Verifica che soggetti_ruoli.soggetto_id == istanze_utilities.soggetto_id. Raise E_BA_SOGGETTO_INCOERENTE_ISTANZA. Allinea il vincolo DB al modello documentato (1 cliente per istanza).';
```

---
{% include-markdown "signature-core.md" %}
