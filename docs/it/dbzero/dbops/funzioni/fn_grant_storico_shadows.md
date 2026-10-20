# ⚙️ Funzione `fn_grant_storico_shadows`

```sql
CREATE FUNCTION fn_grant_storico_shadows(p_dry_run boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_grant_storico_shadows(p_dry_run boolean DEFAULT false)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: allineare i privilegi delle shadow `storico.*` a quelli
--   della loro madre, derivandoli invece di elencarli.
--   Idempotente e forward-only: non revoca mai niente.
DECLARE
    r          record;
    v_fatte    int := 0;
    v_saltate  int := 0;
BEGIN
    FOR r IN
        -- ⚠️ La CTE e' MATERIALIZED apposta: e' una barriera. Nel
        --   primo stadio solo catalogo; `has_table_privilege` sulla
        --   shadow sta fuori, perche' valutarlo insieme al resto
        --   non ha un ordine garantito.
        WITH coppia AS MATERIALIZED (
            SELECT hc.oid      AS sto_oid,
                   hc.relname  AS tabella,
                   mn.nspname  AS madre_schema,
                   mc.relacl   AS madre_acl,
                   hc.relowner AS sto_owner
              FROM pg_class hc
              JOIN pg_namespace hn ON hn.oid = hc.relnamespace
                                  AND hn.nspname = 'storico'
              JOIN pg_class mc ON mc.relname = hc.relname
                              AND mc.relkind IN ('r', 'p')
              JOIN pg_namespace mn ON mn.oid = mc.relnamespace
                                  AND mn.nspname <> 'storico'
              -- ⭐ Il marcatore di «questa tabella e' storicizzata»
              --   e' il TRIGGER, non un elenco: se un domani una
              --   tabella esce dalla storicizzazione, esce da qui
              --   da sola.
              JOIN pg_trigger tg ON tg.tgrelid = mc.oid
                                AND NOT tg.tgisinternal
              JOIN pg_proc pr ON pr.oid = tg.tgfoid
                             AND pr.proname = 'trgfn_storico_generic'
             WHERE hc.relkind IN ('r', 'p')
        )
        SELECT DISTINCT c.tabella, c.madre_schema, c.sto_oid,
               rol.rolname AS ruolo
          FROM coppia c
          CROSS JOIN LATERAL aclexplode(c.madre_acl) a
          JOIN pg_roles rol ON rol.oid = a.grantee
         WHERE a.privilege_type IN ('INSERT', 'UPDATE')
           -- Il proprietario ha gia' tutto; i superuser non hanno
           -- bisogno di grant.
           AND rol.oid <> c.sto_owner
           AND NOT rol.rolsuper
           -- Niente da fare dove i privilegi ci sono gia': cosi'
           -- la passata normale non scrive e non registra nulla.
           AND NOT (
                    has_table_privilege(rol.oid, c.sto_oid, 'INSERT')
                AND has_table_privilege(rol.oid, c.sto_oid, 'UPDATE')
                AND has_table_privilege(rol.oid, c.sto_oid, 'SELECT')
               )
         ORDER BY c.tabella, rol.rolname
    LOOP
        IF p_dry_run THEN
            v_fatte := v_fatte + 1;
            CONTINUE;
        END IF;

        -- ⛔ SELECT, INSERT, UPDATE — e MAI DELETE: uno snapshot
        --   SCD non si cancella (test 19 della postura).
        EXECUTE format(
            'GRANT SELECT, INSERT, UPDATE ON storico.%I TO %I',
            r.tabella, r.ruolo);

        -- 🔴 SI VERIFICA L'ESITO, NON SI SUPPONE.
        --   Quando il concedente non e' proprietario dell'oggetto,
        --   PostgreSQL non solleva: emette un WARNING
        --   («nessun privilegio e' stato concesso») e prosegue.
        --   ⚠️ Un `EXCEPTION WHEN insufficient_privilege` qui NON
        --   scatterebbe mai, e questa funzione registrerebbe OK
        --   senza aver concesso niente — un'etichetta rassicurante,
        --   cioe' la cosa peggiore, perche' nessuno la ricontrolla.
        --   Misurato il 2026-09-02: `titodb` che concede su una
        --   shadow di `postgres` ottiene il warning, non un errore.
        IF has_table_privilege(r.ruolo, r.sto_oid, 'INSERT')
           AND has_table_privilege(r.ruolo, r.sto_oid, 'UPDATE')
           AND has_table_privilege(r.ruolo, r.sto_oid, 'SELECT') THEN
            v_fatte := v_fatte + 1;
        ELSE
            -- Non e' un errore da fermare il migrate: la shadow
            -- appartiene a un altro ruolo (le crea chi esegue
            -- l'automazione, a volte il job pgAgent come
            -- `postgres`). Si registra e si prosegue; a concedere
            -- sara' il provisioning, che gira da superuser.
            v_saltate := v_saltate + 1;
            PERFORM dbops.fn_audit_log_once(
                p_function_name => 'fn_grant_storico_shadows',
                -- ⚠️ 'WARN' e non 'SKIP': dbops.audit_log ha un
                --   CHECK (chk_audit_status) che ammette solo
                --   START/OK/ERROR/DRYRUN/WARN. Uno stato
                --   inventato non passa, e a scoprirlo e' il
                --   percorso d'ECCEZIONE — cioe' quello che si
                --   percorre solo quando qualcosa e' gia' andato
                --   storto. Verificato eseguendo il ramo.
                p_status        => 'WARN',
                p_rule_type     => 'STORICO_GRANT',
                p_params        => jsonb_build_object(
                                     'table', 'storico.' || r.tabella,
                                     'role',  r.ruolo,
                                     'reason', 'GRANT senza effetto: non proprietario'),
                p_message       => 'GRANT non concedibile da questo ruolo'
            );
        END IF;
    END LOOP;

    IF v_fatte > 0 OR v_saltate > 0 THEN
        PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_grant_storico_shadows',
            p_status        => CASE WHEN p_dry_run THEN 'DRYRUN' ELSE 'OK' END,
            p_rule_type     => 'STORICO_GRANT',
            p_dry_run       => p_dry_run,
            p_params        => jsonb_build_object('granted', v_fatte,
                                                  'skipped', v_saltate),
            p_message       => 'Allineamento privilegi shadow storico'
        );
    END IF;
END;
$function$

COMMENT ON FUNCTION dbops.fn_grant_storico_shadows(p_dry_run boolean)
IS 'Allinea i privilegi delle shadow storico.* a quelli della loro madre, DERIVANDOLI invece di elencarli: per ogni tabella storico.<t> la cui madre porta un trigger script.trgfn_storico_generic, concede SELECT/INSERT/UPDATE ai ruoli che sulla madre hanno INSERT o UPDATE. ⭐ Nessun nome scritto da nessuna parte: il marcatore e'' il TRIGGER, quindi una tabella che esce dalla storicizzazione esce da qui da sola, e una shadow nuova e'' coperta senza che nessuno se ne ricordi. ⛔ MAI DELETE, ed e'' una regola di dominio: uno snapshot SCD non si cancella — la stessa che asserisce il test 19 di db/pgtap/rls/test-role-batch-fatturazione-postura.sql. Per questo la regola NON e'' «copia i privilegi della madre»: sulla madre il ruolo batch ha anche DELETE. ⚠️ Legge pg_class.relacl e non information_schema.role_table_grants, che mostra solo i grant del ruolo CONNESSO e da un altro ruolo risponde zero righe sempre (e'' il difetto che aveva reso muto il test 8 della postura). ⚠️ Verifica l''ESITO di ogni GRANT invece di supporlo: quando il concedente non e'' proprietario dell''oggetto PostgreSQL emette un WARNING e prosegue, non solleva — un EXCEPTION WHEN insufficient_privilege non scatterebbe mai e la funzione registrerebbe OK senza aver concesso niente. ⚠️ Il trigger di storicizzazione e'' SECURITY INVOKER: scrive nella shadow come il ruolo che aggiorna la madre, quindi senza questi privilegi e'' l''UPDATE sulla madre a fallire, non solo lo storico a perdersi. 🔴 LIMITE: un GRANT lo da'' il proprietario, e le shadow ereditano il proprietario da chi ha eseguito l''automazione — misurate il 2026-09-02, cinque di postgres e quattro di titodb. Dove non e'' proprietaria la funzione REGISTRA e prosegue (audit SKIP) invece di fermare il migrate: a concedere sara'' il provisioning, che gira da superuser. Idempotente e forward-only: non revoca mai, e non scrive dove i privilegi ci sono gia''. Chiamata da migrations_v2/90_end/20260902-10-run-grant-storico-shadows.';
```

</div>

---
{% include-markdown "signature-core.md" %}
