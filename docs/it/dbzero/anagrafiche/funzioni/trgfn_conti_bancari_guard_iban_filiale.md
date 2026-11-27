# ⚙️ Funzione `trgfn_conti_bancari_guard_iban_filiale`

```sql
CREATE FUNCTION trgfn_conti_bancari_guard_iban_filiale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_conti_bancari_guard_iban_filiale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi     CONSTANT dbops.error_log.function_name%TYPE := 'anagrafiche.trgfn_conti_bancari_guard_iban_filiale';
    v_banca   anagrafiche.bank_branches.bank_code%TYPE;
    v_filiale anagrafiche.bank_branches.branch_code%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: l'IBAN del conto porta banca e filiale della sua
    --   filiale, dove lo stato dell'IBAN dichiara dove stanno
    --   (anagrafiche.fn_iban_coerente_con_filiale).
    --   Montata BEFORE INSERT OR UPDATE, fase a12: IBAN e filiale
    --   nella forma della normalizzazione a01. In modifica giudica
    --   solo se cambia l'IBAN o la filiale.
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND NEW.iban IS NOT DISTINCT FROM OLD.iban
       AND NEW.bank_branch_id IS NOT DISTINCT FROM OLD.bank_branch_id THEN
        RETURN NEW;
    END IF;

    SELECT b.bank_code, b.branch_code
      INTO v_banca, v_filiale
      FROM anagrafiche.bank_branches b
     WHERE b.id = NEW.bank_branch_id;

    -- Una filiale che non c'e' la rifiuta la FK: qui si tace.
    IF FOUND
       AND NOT anagrafiche.fn_iban_coerente_con_filiale(NEW.iban, v_banca, v_filiale) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_CONTO_IBAN_FILIALE_INCOERENTE',
            jsonb_build_object('campo', 'bank_branch_id',
                               'tabella', 'anagrafiche.conti_bancari',
                               'conto_bancario_id', NEW.id,
                               'bank_branch_id', NEW.bank_branch_id),
            NEW.tx_id,
            v_banca::text, v_filiale::text);
    END IF;
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_conti_bancari_guard_iban_filiale()
IS 'BEFORE INSERT OR UPDATE su anagrafiche.conti_bancari, fase a12: l''IBAN porta il codice della banca e quello della filiale del conto, dove lo stato dell''IBAN dichiara dove stanno (anagrafiche.fn_iban_coerente_con_filiale). In modifica giudica solo un cambio di IBAN o di filiale. Rifiuto: E_CONTO_IBAN_FILIALE_INCOERENTE, campo bank_branch_id. Il verso della filiale lo tiene anagrafiche.trgfn_bank_branches_guard_iban_conti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
