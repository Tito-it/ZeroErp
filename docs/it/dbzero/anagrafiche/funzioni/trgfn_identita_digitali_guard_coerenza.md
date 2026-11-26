{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_guard_coerenza.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_guard_coerenza`

```sql
CREATE FUNCTION trgfn_identita_digitali_guard_coerenza()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_guard_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE sulle colonne sorgente per coerenza automatica col DDL.
    v_soggetto_id anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
BEGIN
    -- ------------------------------------------------------------
    -- Trigger function: guard coerenza ruolo_applicativo <-> soggetto_ruolo
    -- su anagrafiche.identita_digitali (fase a10, BEFORE INSERT/UPDATE).
    --
    -- Logica:
    --   - DISABILITATO: rifiuto (rev 2026-10-02, R-DB-1). Non e' piu' un
    --     tipo di veste: una veste si spegne con attivo = false e il suo
    --     tipo resta. Il CHECK chk_identita_digitali_ruolo_non_ritirato
    --     lo dice alla tabella; questo ramo parla PRIMA del CHECK (guard
    --     BEFORE ROW) e con un codice che dice il rimedio.
    --   - API_CLIENT: early-exit, nessuna query.
    --   - OPERATORE: SELECT soggetto_id, poi DUE mondi disgiunti
    --     secondo il flag `tecnica` (rev 2026-09-04):
    --       persona  -> RIS_UMANA + PF pura
    --       processo -> PROC_AUTO
    --   - Altri ruoli: delega a fn_guard_soggetto_ruolo passando NULL
    --     come p_soggetto_id (parametro opzionale supportato dalla
    --     funzione) — evita una query ridondante.
    -- ------------------------------------------------------------

    -- 0) ⛔ DISABILITATO e' ritirato come tipo di veste (rev 2026-10-02,
    --    brief-db-be-fe-area-accessi R-DB-1). Fino a quel giorno lo scriveva
    --    lo spegnimento dell'operatore al posto di OPERATORE, e la veste
    --    spenta perdeva il suo tipo: questo guard usciva in anticipo e non
    --    controllava piu' niente. Ora l'operatore spento resta OPERATORE
    --    con attivo = false, e il ramo OPERATORE qui sotto lo controlla
    --    come quello acceso. Il valore resta nell'enum solo perche' lo
    --    porta la storia (storico.identita_digitali).
    IF NEW.ruolo_applicativo = 'DISABILITATO' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_RUOLO_APPLICATIVO_RITIRATO',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'identita_id', NEW.id,
                'auth_user_id', NEW.auth_user_id,
                'ruolo_applicativo', NEW.ruolo_applicativo
            ),
            NULL::uuid,
            NEW.ruolo_applicativo::text
        );
    END IF;

    -- 0-bis) ⛔ `tecnica` dice «e' l'identita' di un PROCESSO», e un
    --    processo entra solo dalla porta dell'operatore (ogni policy
    --    rls_*_ef_whitelist pretende OPERATORE). Su ogni altra veste il
    --    flag farebbe della credenziale una credenziale di macchina senza
    --    nessun requisito: si rifiuta per tutte, API_CLIENT compreso.
    IF NEW.tecnica AND NEW.ruolo_applicativo <> 'OPERATORE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_VESTE_TECNICA_SOLO_OPERATORE',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'identita_id', NEW.id,
                'auth_user_id', NEW.auth_user_id,
                'ruolo_applicativo', NEW.ruolo_applicativo
            ),
            NULL::uuid,
            NEW.ruolo_applicativo::text
        );
    END IF;

    -- 0-ter) ⛔ Un'identita' tecnica non ha il profilo SUPER_ADMIN: un
    --    processo passerebbe sopra ogni permesso. Il binding nuovo lo
    --    ferma config.trgfn_profili_accesso_bindings_guard_coerenza; qui
    --    la veste che DIVENTA tecnica portandoselo dietro.
    IF NEW.tecnica
       AND TG_OP = 'UPDATE'
       AND NOT OLD.tecnica
       AND EXISTS (SELECT 1
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso          pa
                       ON pa.id = pab.profilo_accesso_id
                    WHERE pab.identita_digitale_id = NEW.id
                      AND pab.attivo
                      AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_SUPER_ADMIN_SU_VESTE_TECNICA',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'identita_id', NEW.id,
                'auth_user_id', NEW.auth_user_id
            ),
            NULL::uuid,
            NEW.id::text
        );
    END IF;

    -- 1) Early-exit per ruoli senza vincoli di coerenza.
    IF NEW.ruolo_applicativo = 'API_CLIENT' THEN
        RETURN NEW;
    END IF;

    -- 2) Dispatch per gli altri ruoli applicativi.
    CASE NEW.ruolo_applicativo
        WHEN 'OPERATORE' THEN
            -- Serve il soggetto_id in entrambi i rami. Unica query.
            SELECT sr.soggetto_id
              INTO v_soggetto_id
              FROM anagrafiche.soggetti_ruoli sr
             WHERE sr.id = NEW.soggetto_ruolo_id;

            IF NOT FOUND THEN
                -- Caso limite (record cancellato da altra transazione):
                -- la FK lo impedirebbe, ma fail-fast esplicito.
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_SOGGETTI_RUOLI',
                    jsonb_build_object(
                        'table', TG_TABLE_NAME,
                        'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                        'nota', 'soggetto_ruolo_id non trovato in anagrafiche.soggetti_ruoli'
                    ),
                    NULL::uuid,
                    -- ⚠️ ARITA' (2026-08-18): E_SOGGETTI_RUOLI ha tre
                    --   segnaposto e qui ne arrivava uno solo -> format()
                    --   alzava 22023 al posto del P0001. Gli altri due non
                    --   si possono valorizzare: si arriva qui PERCHE' la
                    --   riga non e' stata trovata.
                    NEW.soggetto_ruolo_id::text,
                    'NULL',
                    'NULL'
                );
            END IF;

            IF NEW.tecnica THEN
                -- ⭐ PROCESSO AUTOMATICO (rev 2026-09-04).
                --   Un processo non e' una persona e non deve
                --   fingersi tale: si pretende il ruolo dedicato
                --   PROC_AUTO. ⛔ Niente fn_guard_soggetto_pf_pura:
                --   non c'e' nessuna persona fisica da verificare.
                --   ⚠️ Questo ramo NON e' piu' permissivo dell'altro:
                --   scambia un requisito chiuso con un altro. Con
                --   tecnica=true NON si puo' appendere un'identita'
                --   operatore a un soggetto qualsiasi.
                PERFORM script.fn_guard_soggetto_ruolo(
                    v_soggetto_id,
                    NEW.soggetto_ruolo_id,
                    'PROC_AUTO'
                );
            ELSE
                -- PERSONA: invariato dal 2026-04.
                PERFORM script.fn_guard_soggetto_ruolo(
                    v_soggetto_id,
                    NEW.soggetto_ruolo_id,
                    'RIS_UMANA'
                );
                PERFORM script.fn_guard_soggetto_pf_pura(v_soggetto_id);
            END IF;

        WHEN 'CLIENTE_PORTALE', 'SHOP_CUSTOMER' THEN
            -- Entrambi i ruoli condividono lo stesso tipo_ruolo
            -- anagrafico 'CL': la differenza tra portale B2B e
            -- shop self-service e' solo a livello di namespace API
            -- e profilo capability, non di anagrafica.
            PERFORM script.fn_guard_soggetto_ruolo(
                NULL,
                NEW.soggetto_ruolo_id,
                'CL'
            );

        WHEN 'FORNITORE_PORTALE' THEN
            -- Fornitore portale: ruolo FORNITORE (codice interno 'FO').
            PERFORM script.fn_guard_soggetto_ruolo(
                NULL,
                NEW.soggetto_ruolo_id,
                'FO'
            );

        ELSE
            -- Nuovo valore enum senza regola qui: fail-fast esplicito
            -- (evita bypass silenzioso quando si estende l'enum —
            -- il guard non deve "aprire" per omissione).
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME,
                'E_RUOLO_APPLICATIVO_NON_GESTITO',
                jsonb_build_object(
                    'table', TG_TABLE_NAME,
                    'ruolo_applicativo', NEW.ruolo_applicativo,
                    'nota', 'Ruolo applicativo sconosciuto al guard di coerenza'
                ),
                NULL::uuid,
                NEW.ruolo_applicativo::text
            );
    END CASE;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_guard_coerenza()
IS 'Guard di coerenza ruolo_applicativo <-> soggetto_ruolo su anagrafiche.identita_digitali (BEFORE INSERT/UPDATE, fase a10). Rifiuta il tipo ritirato DISABILITATO (E_RUOLO_APPLICATIVO_RITIRATO: una veste si spegne con attivo = false e tiene il tipo); il flag tecnica fuori dalla veste OPERATORE (E_VESTE_TECNICA_SOLO_OPERATORE); una veste che diventa tecnica con un binding SUPER_ADMIN attivo (E_SUPER_ADMIN_SU_VESTE_TECNICA). Poi, per tipo: API_CLIENT senza altri vincoli; OPERATORE in due mondi disgiunti secondo tecnica, una persona vuole RIS_UMANA e una persona fisica pura, un processo vuole il ruolo PROC_AUTO (il flag scambia un requisito chiuso con un altro, non apre il ramo); CLIENTE_PORTALE e SHOP_CUSTOMER vogliono un ruolo cliente, FORNITORE_PORTALE un ruolo fornitore (script.fn_guard_soggetto_ruolo). Serve perche'' ogni policy rls_*_ef_whitelist pretende ruolo_applicativo = OPERATORE: e'' l''unica porta di un processo automatico.';
```

</div>

---
{% include-markdown "signature-core.md" %}
