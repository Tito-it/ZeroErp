{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_link_ef.md" %}
# ⚙️ Funzione `trgfn_billing_account_link_ef`

```sql
CREATE FUNCTION trgfn_billing_account_link_ef()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_link_ef()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_user_id         config.user_override_aree.auth_user_id%TYPE;
    v_emittente_id    anagrafiche.emittenti_fiscali.id%TYPE;
    v_emittente_sr_id anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
    v_existing        anagrafiche.emittenti_fiscali_billing_account.id%TYPE;
BEGIN
    -- 1) L'azienda di chi agisce. ⛔ Nessun blocco EXCEPTION: un
    --    app.current_user_id illeggibile lo rifiuta il building block,
    --    e il rifiuto sale.
    v_user_id := script.fn_utente_di_sessione('anagrafiche.trgfn_billing_account_link_ef');

    IF v_user_id IS NOT NULL THEN
        v_emittente_id := script.fn_resolve_emittente_for_user(v_user_id);
        IF v_emittente_id IS NOT NULL THEN
            SELECT ef.soggetto_ruolo_id
              INTO v_emittente_sr_id
              FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.id = v_emittente_id;
        END IF;
    END IF;

    -- 2) Senza sessione, o senza un'azienda di chi agisce: la
    --    predefinita. Un BA non resta mai scollegato.
    IF v_emittente_sr_id IS NULL THEN
        SELECT d.emittente_soggetto_ruolo_id
          INTO v_emittente_sr_id
          FROM anagrafiche.emittenti_fiscali_billing_account d
         WHERE d.is_default;
    END IF;

    -- 3) Nessuna azienda nell'installazione: il BA non nasce.
    IF v_emittente_sr_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_billing_account_link_ef',
            'E_EMITTENTE_DEFAULT_MISSING',
            jsonb_build_object('billing_account_id', NEW.id,
                               'codice',             NEW.codice),
            NEW.tx_id,
            'un billing account nasce collegato a un''azienda, e non ne esiste nessuna');
    END IF;

    -- 4) Idempotenza: il collegamento c'e' gia' (doppia esecuzione).
    SELECT efba.id
      INTO v_existing
      FROM anagrafiche.emittenti_fiscali_billing_account efba
     WHERE efba.billing_account_id = NEW.id;
    IF v_existing IS NOT NULL THEN
        RETURN NEW;
    END IF;

    INSERT INTO anagrafiche.emittenti_fiscali_billing_account (
        billing_account_id,
        emittente_soggetto_ruolo_id,
        is_default
    ) VALUES (
        NEW.id,
        v_emittente_sr_id,
        false
    );
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_link_ef()
IS 'Trigger AFTER INSERT di anagrafiche.billing_account: il billing account nasce collegato a un''azienda (anagrafiche.emittenti_fiscali_billing_account). L''azienda e'' quella di chi agisce (script.fn_resolve_emittente_for_user), oppure, senza sessione o senza un''azienda di chi agisce, l''azienda predefinita. Senza nessuna azienda la nascita e'' rifiutata (E_EMITTENTE_DEFAULT_MISSING). Un app.current_user_id che non e'' l''id di un utente lo rifiuta script.fn_utente_di_sessione. Se il collegamento c''e'' gia'' non ne scrive un altro. Ogni billing account ha sempre il suo collegamento: spostare la predefinita non cambia l''azienda di nessun cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
