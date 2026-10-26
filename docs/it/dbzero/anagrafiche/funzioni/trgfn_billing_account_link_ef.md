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
    v_user_id integer;
    v_emittente_id           anagrafiche.emittenti_fiscali.id%TYPE;
    v_emittente_sr_id        anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_existing               bigint;
BEGIN
    -- 1) Lettura GUC utente corrente (settato dal middleware Django)
    BEGIN
        v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;

    -- Seed/bootstrap senza utente => no auto-link
    IF v_user_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- 2) Resolve emittente per l'operatore (PK reale)
    v_emittente_id := script.fn_resolve_emittente_for_user(v_user_id);

    -- 3) Admin globale o istanza "0 emittenti": niente da linkare.
    --    Il guard BEFORE INSERT (a10) ha gia' bloccato il caso
    --    "admin globale + emittenti presenti", quindi qui un NULL
    --    significa solo "non c'e' nulla da linkare".
    IF v_emittente_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- 4) La tabella di mapping usa emittente_soggetto_ruolo_id,
    --    non la PK reale: lookup.
    SELECT ef.soggetto_ruolo_id
      INTO v_emittente_sr_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = v_emittente_id;

    -- Difensivo: race con disattivazione emittente fra resolver e qui
    IF v_emittente_sr_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- 5) Idempotenza: se esiste gia' un mapping (es. doppia
    --    esecuzione del trigger o INSERT applicativa parallela)
    --    non duplichiamo. uq_emittenti_fiscali_ba garantisce
    --    unicita' su billing_account_id non NULL, ma il check
    --    esplicito da' un errore piu' chiaro.
    SELECT efba.id
      INTO v_existing
      FROM anagrafiche.emittenti_fiscali_billing_account efba
     WHERE efba.billing_account_id = NEW.id
     LIMIT 1;

    IF v_existing IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- 6) INSERT mapping specifico (is_default = false)
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
IS 'Auto-link AFTER INSERT su billing_account: crea il mapping in emittenti_fiscali_billing_account collegando il BA all''emittente dell''operatore corrente (via GUC app.current_user_id e script.fn_resolve_emittente_for_user). is_default=false (mapping specifico). Skip in caso di seed/bootstrap o "0 emittenti". ⚠️ rev 2026-08-26 — QUESTA E'' LA SCELTA, e conviene saperlo qui: un billing account non passa MAI da uno stato «senza emittente», nasce gia'' agganciato, e se l''operatore stava lavorando sull''emittente sbagliato nasce AGGANCIATO MALE. Dal 20260826-49 quel legame si corregge solo finche'' sul cliente non e'' passato del lavoro — nessuna fattura, nessuna commessa (anagrafiche.trgfn_efba_guard_storia_emittente): dopo, i documenti gia'' emessi congelano chi li ha emessi e spostare il cliente li lascerebbe orfani. ⇒ La finestra di correzione si apre qui e si chiude al primo push. Brief: brief-db-billing-account-cambio-emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
