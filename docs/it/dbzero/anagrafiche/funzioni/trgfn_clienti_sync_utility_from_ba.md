{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_sync_utility_from_ba.md" %}
# ⚙️ Funzione `trgfn_clienti_sync_utility_from_ba`

```sql
CREATE FUNCTION trgfn_clienti_sync_utility_from_ba()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la fornitura del cliente e il suo PDP.
--   1. ruolo e utility sono COPIE del billing account: le scrive o le
--      rifiuta il BB script.fn_cliente_dal_billing_account (rev
--      2026-10-10, brief-db-esecutivi-ba-coppia, regola del 2);
--   2. se la utility lo richiede, il PDP e' obbligatorio;
--   3. il PDP e' della stessa utility.
DECLARE
    v_pdp_utility_id anagrafiche.pdp.utility_id%TYPE;
    v_richiede_pdp   config.utilities.richiede_pdp%TYPE := false;
BEGIN
    -- Nessun billing_account: niente da sincronizzare (la colonna
    -- e' NOT NULL: il vincolo parla dopo i BEFORE ROW).
    IF NEW.billing_account_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- 1. Ruolo e utility dal BA. Su UPDATE solo se il chiamante tocca
    --    una delle tre colonne: e allora ha gia' parlato il lock.
    IF TG_OP = 'INSERT'
       OR NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id
       OR NEW.soggetto_ruolo_id  IS DISTINCT FROM OLD.soggetto_ruolo_id
       OR NEW.utility_id         IS DISTINCT FROM OLD.utility_id THEN
        SELECT f.soggetto_ruolo_id, f.utility_id
          INTO NEW.soggetto_ruolo_id, NEW.utility_id
          FROM script.fn_cliente_dal_billing_account(
                   NEW.billing_account_id,
                   NEW.soggetto_ruolo_id,
                   NEW.utility_id,
                   'Cliente #' || NEW.id::text,
                   'soggetto_ruolo_id',
                   NEW.tx_id) f;
    END IF;

    -- 2. Policy richiede_pdp dalla utility
    SELECT coalesce(u.richiede_pdp, false)
      INTO v_richiede_pdp
      FROM config.utilities u
     WHERE u.id = NEW.utility_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_utility_from_ba',
            'E_CODICE',
            jsonb_build_object('utility_id', NEW.utility_id),
            NEW.tx_id,
            NEW.utility_id::text, 'config.utilities'
        );
    END IF;

    IF v_richiede_pdp AND NEW.pdp_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_utility_from_ba',
            'E_PDP_OBBLIGATORIO',
            jsonb_build_object(
                'billing_account_id', NEW.billing_account_id,
                'utility_id', NEW.utility_id
            ),
            NEW.tx_id,
            NEW.utility_id::text,
            coalesce(NEW.billing_account_id::text, 'NULL')
        );
    END IF;

    -- 3. Coerenza utility tra billing_account e PDP
    IF NEW.pdp_id IS NOT NULL THEN
        SELECT p.utility_id
          INTO v_pdp_utility_id
          FROM anagrafiche.pdp p
         WHERE p.id = NEW.pdp_id;

        IF v_pdp_utility_id IS NULL OR v_pdp_utility_id::integer <> NEW.utility_id THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'anagrafiche.trgfn_clienti_sync_utility_from_ba',
                'E_PDP_UTILITY_MISMATCH',
                jsonb_build_object(
                    'billing_account_id', NEW.billing_account_id,
                    'pdp_id', NEW.pdp_id,
                    'utility_da_billing', NEW.utility_id,
                    'utility_da_pdp', v_pdp_utility_id
                ),
                NEW.tx_id,
                coalesce(NEW.billing_account_id::text, 'NULL'),
                coalesce(NEW.pdp_id::text, 'NULL'),
                NEW.utility_id::text,
                coalesce(v_pdp_utility_id::text, 'NULL')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()
IS 'Fornitura e PDP del cliente: (1) ruolo e utility sono copie del billing account, scritte se mancano e rifiutate se dissentono dal BB script.fn_cliente_dal_billing_account (E_DOC_CLIENTE_DIVERSO_DA_BA), su INSERT e quando cambia una delle tre colonne (su UPDATE parla prima il lock E_CLIENTE_FORNITURA_IMMUTABILE); (2) policy richiede_pdp della utility (E_PDP_OBBLIGATORIO); (3) PDP della stessa utility (E_PDP_UTILITY_MISMATCH). rev 2026-10-10 (brief-db-esecutivi-ba-coppia §10.2 domanda 2, regola del 2): la copia passa al BB, anche per il ruolo; esce il ramo E_BILLING_ACCOUNT_UTILITY_NULL (billing_account.utility_id e'' NOT NULL); E_CLIENTE_UTILITY_MISMATCH_BA non e'' piu'' sollevato qui (resta a catalogo per fn_get_or_create_commessa).';
```

</div>

---
{% include-markdown "signature-core.md" %}
