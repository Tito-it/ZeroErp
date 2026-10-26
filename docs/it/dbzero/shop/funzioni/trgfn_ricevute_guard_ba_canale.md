{% include-markdown "it/dbzero/shop/manual/trgfn_ricevute_guard_ba_canale.md" %}
# ⚙️ Funzione `trgfn_ricevute_guard_ba_canale`

```sql
CREATE FUNCTION trgfn_ricevute_guard_ba_canale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION shop.trgfn_ricevute_guard_ba_canale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ba_canale config.canale_origine;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Vincolare shop.ricevute.billing_account_id a puntare
    --   SOLO a billing_account con canale_origine='SHOP'.
    --   L'invariante protegge la separazione di canale
    --   (decisione dominio 20-04-2026): ricevute shop vivono
    --   su BA dedicati, portale su BA portale, ADMIN su BA
    --   ADMIN.
    --
    -- Regole:
    --   1. INSERT: sempre verifica (NEW.billing_account_id e'
    --      NOT NULL per constraint tabella).
    --   2. UPDATE OF billing_account_id: scatta solo se la FK
    --      cambia; eventuali UPDATE su altri campi sono
    --      trasparenti (performance).
    --   3. SELECT lookup su billing_account: gia' protetto
    --      dalla FK fk_shop_ricevute_billing_account; qui
    --      interroghiamo la colonna canale_origine.
    --   4. Se BA non trovato (race con DELETE): la FK
    --      fk_shop_ricevute_billing_account gia' garantisce
    --      l'esistenza. Il v_ba_canale NULL non dovrebbe
    --      mai verificarsi in pratica, ma fail-closed.
    -- =========================================================

    SELECT ba.canale_origine
      INTO v_ba_canale
      FROM anagrafiche.billing_account ba
     WHERE ba.id = NEW.billing_account_id;

    IF v_ba_canale IS DISTINCT FROM 'SHOP'::config.canale_origine THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'shop.trgfn_ricevute_guard_ba_canale',
            'E_SHOP_RICEVUTA_BA_CANALE_INVALIDO',
            jsonb_build_object(
                'op', TG_OP,
                'ricevuta_id', NEW.id,
                'billing_account_id', NEW.billing_account_id,
                'canale_ba', COALESCE(v_ba_canale::text, 'NULL')
            ),
            NULL::uuid,
            -- ⚠️ ARITA' (2026-08-18): la frase composta qui dentro era la
            --   COPIA ESATTA del messaggio a catalogo, passata come valore
            --   unico a un template che ha due segnaposto -> 22023.
            --   Si vede bene, in questo punto, perche' comporre nel plpgsql sia
            --   sbagliato in se': la frase era scritta due volte, e la copia nel
            --   codice non sarebbe stata traducibile.
            NEW.id::text,
            COALESCE(v_ba_canale::text, 'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION shop.trgfn_ricevute_guard_ba_canale()
IS 'Trigger function: blocca INSERT/UPDATE di shop.ricevute se billing_account_id punta a un BA con canale_origine != SHOP. Applicata BEFORE INSERT + UPDATE OF billing_account_id. Codice errore E_SHOP_RICEVUTA_BA_CANALE_INVALIDO (id 386).';
```

</div>

---
{% include-markdown "signature-core.md" %}
