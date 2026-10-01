{% include-markdown "it/dbzero/script/manual/fn_check_ultimo_super_admin_attivo.md" %}
# ⚙️ Funzione `fn_check_ultimo_super_admin_attivo`

```sql
CREATE FUNCTION fn_check_ultimo_super_admin_attivo(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ultimo_super_admin_attivo(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Scopo:
    --   Predicato per-utente: true sse rimuovere il privilegio
    --   SUPER_ADMIN da p_auth_user_id porterebbe il sistema a
    --   0 super-admin attivi (lockout).
    --
    -- Algoritmo (single-pass, due EXISTS short-circuit):
    --   1) p_auth_user_id IS NOT NULL.
    --   2) Target e' SA attivo (EXISTS si ferma alla prima riga).
    --   3) NESSUN altro auth_user e' SA attivo (NOT EXISTS si
    --      ferma alla prima riga "altra").
    --
    -- Filtri SA coerenti con script.fn_is_super_admin (single
    -- source of truth concettuale):
    --   identita attiva, ruolo OPERATORE, in finestra,
    --   binding attivo, profilo attivo, tipo SUPER_ADMIN.
    --   ⭐ rev 2026-09-25: e credenziale NON bloccata
    --   dall'amministratore (config.credenziali.bloccata_at),
    --   come fn_check_almeno_un_super_admin_attivo — un SUPER_ADMIN
    --   bloccato non e' raggiungibile. Brief:
    --   brief-db-blocco-login-per-credenziale §3.3.
    --
    -- NB: la duplicazione del blocco filtri e' voluta. Una CTE
    -- referenziata 2 volte verrebbe materializzata da PG e
    -- valutata interamente; con EXISTS+NOT EXISTS l'optimizer
    -- usa indici partial (uq_identita_digitali_*_attivo) e
    -- short-circuita.
    -- =========================================================
    SELECT
            p_auth_user_id IS NOT NULL
        AND EXISTS (
            SELECT 1
              FROM anagrafiche.identita_digitali       id
              JOIN config.profili_accesso_bindings     pab
                ON pab.identita_digitale_id = id.id
              JOIN config.profili_accesso              pa
                ON pa.id = pab.profilo_accesso_id
             WHERE id.auth_user_id      = p_auth_user_id
               AND id.attivo            = true
               AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
               AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
               AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
               AND pab.attivo = true
               AND pa.attivo  = true
               AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
               AND NOT EXISTS (
                   SELECT 1
                     FROM config.credenziali c
                    WHERE c.auth_user_id = id.auth_user_id
                      AND c.bloccata_at IS NOT NULL
               )
        )
        AND NOT EXISTS (
            SELECT 1
              FROM anagrafiche.identita_digitali       id
              JOIN config.profili_accesso_bindings     pab
                ON pab.identita_digitale_id = id.id
              JOIN config.profili_accesso              pa
                ON pa.id = pab.profilo_accesso_id
             WHERE id.auth_user_id     <> p_auth_user_id
               AND id.attivo            = true
               AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
               AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
               AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
               AND pab.attivo = true
               AND pa.attivo  = true
               AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
               AND NOT EXISTS (
                   SELECT 1
                     FROM config.credenziali c
                    WHERE c.auth_user_id = id.auth_user_id
                      AND c.bloccata_at IS NOT NULL
               )
        );
$function$

COMMENT ON FUNCTION script.fn_check_ultimo_super_admin_attivo(p_auth_user_id integer)
IS 'Predicato per-utente: true sse questo auth_user e'' l''unico SUPER_ADMIN attivo e raggiungibile del sistema (rimuovergli il privilegio causerebbe lockout). Raggiungibile = identita OPERATORE attiva e in finestra, binding e profilo SUPER_ADMIN attivi, credenziale NON bloccata dall''amministratore (config.credenziali.bloccata_at; rev 2026-09-25, stesso gate di fn_check_almeno_un_super_admin_attivo). Usato per le capability can_disable / can_demote_super_admin del drawer Operatore. LANGUAGE sql STABLE, pure check, nessun raise. Param INTEGER esplicito (django.auth_user.id; niente %TYPE su colonne django.*).';
```

---
{% include-markdown "signature-core.md" %}
