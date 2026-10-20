{% include-markdown "it/dbzero/script/manual/fn_blocca_credenziale.md" %}
# ⚙️ Funzione `fn_blocca_credenziale`

```sql
CREATE FUNCTION fn_blocca_credenziale(p_auth_user_id integer, p_motivo text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_blocca_credenziale(p_auth_user_id integer, p_motivo text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: bloccare una credenziale su tutte le porte, per decisione di un
--   SUPER_ADMIN. Non scade; lo toglie solo script.fn_sblocca_credenziale.
DECLARE
    v_utente integer;
    -- Nudo: l'array dei motivi di fn_check_credenziale_bloccabile.
    v_motivi jsonb;
BEGIN
    -- Prima riga: chi agisce dev'essere SUPER_ADMIN (D-B1). Anche dal
    -- server: il blocco ha sempre un autore (chk_credenziali_blocco).
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_super_admin(v_utente);

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_blocca_credenziale', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_blocca_credenziale',
                           'credenziale assente o non valida']);
    END IF;

    IF p_motivo IS NULL OR btrim(p_motivo) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_blocca_credenziale', 'E_CREDENZIALE_MOTIVO_OBBLIGATORIO',
            jsonb_build_object('campo', 'motivo', 'auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_blocca_credenziale', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- La regola sta nella check: qui la si chiama, non la si riscrive
    -- (linee-guida-sql §12.5.2).
    v_motivi := script.fn_check_credenziale_bloccabile(p_auth_user_id);

    -- D-1: dal server una credenziale di sistema si blocca, ed e'
    -- l'uscita d'emergenza (una chiave rubata). Si toglie SOLO quel
    -- motivo, conservando l'ordine degli altri.
    IF dbops.fn_sessione_del_migratore() THEN
        SELECT COALESCE(jsonb_agg(m.motivo ORDER BY m.pos), '[]'::jsonb)
          INTO v_motivi
          FROM jsonb_array_elements(v_motivi) WITH ORDINALITY AS m(motivo, pos)
         WHERE m.motivo ->> 'reason' <> 'CREDENZIALE_DI_SISTEMA';
    END IF;

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'database', 'script.fn_blocca_credenziale', v_motivi,
        p_context_extra => jsonb_build_object('auth_user_id', p_auth_user_id,
                                              'chi_agisce',   v_utente));

    INSERT INTO config.credenziali AS c
           (auth_user_id, bloccata_at, bloccata_da, motivo_blocco)
    VALUES (p_auth_user_id, now(), v_utente, btrim(p_motivo))
    ON CONFLICT (auth_user_id) DO UPDATE
       SET bloccata_at   = EXCLUDED.bloccata_at,
           bloccata_da   = EXCLUDED.bloccata_da,
           motivo_blocco = EXCLUDED.motivo_blocco;
END;
$function$

COMMENT ON FUNCTION script.fn_blocca_credenziale(p_auth_user_id integer, p_motivo text)
IS 'Blocco VERO di una credenziale, atto autorizzato (D-1 riletta: le password sbagliate frenano chi le prova, chiudere e'' una decisione con un autore). Prima riga script.fn_guard_super_admin(app.current_user_id) (D-B1), anche dalla sessione del migratore: il blocco ha sempre un autore (chk_credenziali_blocco). Motivo obbligatorio (E_CREDENZIALE_MOTIVO_OBBLIGATORIO); credenziale inesistente -> E_CREDENZIALE_NON_TROVATA. Poi solleva il primo motivo di script.fn_check_credenziale_bloccabile, la stessa regola che spegne il pulsante (§12.5.2): CREDENZIALE_DI_SISTEMA (E_CREDENZIALE_DI_SISTEMA; non vale dalla sessione del migratore, dbops.fn_sessione_del_migratore: l''uscita d''emergenza per una credenziale di sistema compromessa, D-1 del 2026-10-03) e ULTIMO_SUPER_ADMIN (E_PROFILO_ULTIMO_SUPER_ADMIN, da ogni strada). Scrive bloccata_at/bloccata_da/motivo_blocco in upsert: vale su tutte le porte, non scade, il reset password non lo toglie (D-B3); un secondo blocco riscrive l''ultimo stato. La rete per le corse resta il guard su config.credenziali (fn_check_almeno_un_super_admin_attivo, stato dopo). SECURITY DEFINER del PROPRIETARIO, non di un superuser, search_path bloccato. La blacklist delle sessioni e'' del backend. Brief: brief-db-blocco-login-per-credenziale §3.3, brief-db-credenziale-verbi-amministratore (R-DB-A5, R-DB-A6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
