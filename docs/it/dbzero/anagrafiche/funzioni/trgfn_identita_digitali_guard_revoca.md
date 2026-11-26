# ⚙️ Funzione `trgfn_identita_digitali_guard_revoca`

```sql
CREATE FUNCTION trgfn_identita_digitali_guard_revoca()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_guard_revoca()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_proprietario boolean;  -- risposta di una check, nessuna colonna di cui sia il riflesso
    v_revocata_id  anagrafiche.identita_digitali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: la revoca dell'amministratore tiene. Il segno
    --   (revocata_at, revocata_da_user_id) lo scrivono solo i
    --   verbi; una coppia (credenziale, ruolo anagrafico,
    --   veste) che porta il segno non ha vesti accese.
    -- =========================================================
    v_proprietario := script.fn_is_proprietario_tabella(TG_RELID);

    IF TG_OP = 'DELETE' THEN
        -- 1) cancellare una veste revocata cancellerebbe il segno
        IF num_nulls(OLD.revocata_at) = 0 AND NOT v_proprietario THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_VESTE_REVOCA_SOLO_DAL_VERBO',
                jsonb_build_object('table', TG_TABLE_NAME, 'operazione', TG_OP,
                                   'identita_id', OLD.id),
                NULL::uuid, TG_OP::text);
        END IF;
        RETURN OLD;
    END IF;

    -- 1) il segno si scrive solo dai verbi
    IF NOT v_proprietario
       AND ((TG_OP = 'INSERT'
             AND num_nulls(NEW.revocata_at, NEW.revocata_da_user_id) < 2)
         OR (TG_OP = 'UPDATE'
             AND (NEW.revocata_at, NEW.revocata_da_user_id)
                 IS DISTINCT FROM (OLD.revocata_at, OLD.revocata_da_user_id)))
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_VESTE_REVOCA_SOLO_DAL_VERBO',
            jsonb_build_object('table', TG_TABLE_NAME, 'operazione', TG_OP,
                               'identita_id', NEW.id),
            NULL::uuid, TG_OP::text);
    END IF;

    -- 2) una veste revocata non cambia coppia
    IF TG_OP = 'UPDATE'
       AND num_nulls(OLD.revocata_at) = 0
       AND NOT v_proprietario
       AND (NEW.auth_user_id, NEW.soggetto_ruolo_id, NEW.ruolo_applicativo)
           IS DISTINCT FROM (OLD.auth_user_id, OLD.soggetto_ruolo_id, OLD.ruolo_applicativo)
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_VESTE_REVOCA_SOLO_DAL_VERBO',
            jsonb_build_object('table', TG_TABLE_NAME, 'operazione', TG_OP,
                               'identita_id', NEW.id,
                               'detail', 'cambio di coppia di una veste revocata'),
            NULL::uuid, TG_OP::text);
    END IF;

    -- 3) nessuna veste accesa su una coppia revocata. Si giudica
    --    quando la veste diventa accesa o cambia coppia da accesa.
    IF NEW.attivo
       AND (TG_OP = 'INSERT'
            OR NOT OLD.attivo
            OR (NEW.auth_user_id, NEW.soggetto_ruolo_id, NEW.ruolo_applicativo)
               IS DISTINCT FROM (OLD.auth_user_id, OLD.soggetto_ruolo_id, OLD.ruolo_applicativo))
    THEN
        IF num_nulls(NEW.revocata_at) = 0 THEN
            v_revocata_id := NEW.id;
        ELSE
            SELECT idg.id
              INTO v_revocata_id
              FROM anagrafiche.identita_digitali idg
             WHERE idg.auth_user_id      = NEW.auth_user_id
               AND idg.soggetto_ruolo_id = NEW.soggetto_ruolo_id
               AND idg.ruolo_applicativo = NEW.ruolo_applicativo
               AND idg.id IS DISTINCT FROM NEW.id
               AND idg.revocata_at IS NOT NULL
             ORDER BY idg.id
             LIMIT 1;
        END IF;

        IF v_revocata_id IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_VESTE_REVOCATA',
                jsonb_build_object('table', TG_TABLE_NAME, 'operazione', TG_OP,
                                   'identita_id', NEW.id,
                                   'identita_revocata_id', v_revocata_id,
                                   'ruolo_applicativo', NEW.ruolo_applicativo),
                NULL::uuid, NEW.ruolo_applicativo::text);
        END IF;
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_guard_revoca()
IS 'Guard BEFORE INSERT/UPDATE/DELETE di anagrafiche.identita_digitali: la revoca dell''amministratore tiene. (1) Il segno (revocata_at, revocata_da_user_id) si scrive e si toglie solo dal proprietario della tabella, cioe'' dai verbi anagrafiche.fn_revoca_veste, anagrafiche.fn_togli_revoca_veste e dal migrate; vale anche per il DELETE di una veste revocata. (2) Una veste revocata non cambia credenziale, ruolo anagrafico o veste se non dal proprietario. (3) Sulla coppia (credenziale, ruolo anagrafico, veste) di una veste revocata non c''e'' una veste accesa: rifiuta l''accensione della riga revocata, l''INSERT di una riga accesa e la riaccensione di un''altra riga della coppia, anche al proprietario. Codici: E_VESTE_REVOCA_SOLO_DAL_VERBO (1, 2), E_VESTE_REVOCATA (3). Riconosce il proprietario con script.fn_is_proprietario_tabella, senza GUC. Rilegge la tabella solo per le altre righe della coppia; la tabella non ha RLS. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
