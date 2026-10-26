{% include-markdown "it/dbzero/dbops/manual/fn_storico_arma_scope.md" %}
# ⚙️ Funzione `fn_storico_arma_scope`

```sql
CREATE FUNCTION fn_storico_arma_scope(p_schema_base text, p_table_base text, p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_storico_arma_scope(p_schema_base text, p_table_base text, p_dry_run boolean DEFAULT false)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: portare la shadow di UNA madre alla forma decisa (colonne di
--   scope e origine, RLS e policy se la madre è protetta). Idempotente,
--   forward-only, solo se il migratore possiede la shadow.
DECLARE
    v_sto_oid   oid  := pg_catalog.to_regclass(format('storico.%I', p_table_base));
    v_full_sto  text := format('storico.%I', p_table_base);
    v_madre     text := p_schema_base || '.' || p_table_base;
    v_owner     text;
    v_rls       boolean;
    v_modo      dbops.storico_scope_policy.modo%TYPE;
    v_arma      boolean := false;
    v_azioni    text[]  := '{}';
    -- Nomi entro i 63 caratteri: il nome di tabella più lungo dello
    -- schema storico è 38, il suffisso più lungo 13 -> 59.
    v_pol_sel   text := left(format('rls_sto_%s_ef_whitelist', p_table_base), 63);
    v_pol_ins   text := left(format('rls_sto_%s_trg_ins',      p_table_base), 63);
    v_pol_upd   text := left(format('rls_sto_%s_trg_upd',      p_table_base), 63);
    v_ix        text := left(format('ix_%s_scope_ef',           p_table_base), 63);
    v_sql       text;
    v_vuota     boolean;
BEGIN
    -- 0) Senza shadow non c'è niente da armare: la madre non è ancora
    --    storicizzata (o non lo sarà). Non è un errore.
    IF v_sto_oid IS NULL THEN
        RETURN jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                                  'esito', 'NO_SHADOW');
    END IF;

    -- 1) Solo il proprietario può fare DDL sulla shadow. Dove non lo
    --    siamo si registra e si prosegue: a farlo sarà il provisioning.
    SELECT pg_get_userbyid(c.relowner), c.relrowsecurity
      INTO v_owner, v_rls
      FROM pg_catalog.pg_class c WHERE c.oid = v_sto_oid;
    IF v_owner <> current_user THEN
        IF NOT p_dry_run THEN
            PERFORM dbops.fn_audit_log_once(
                p_function_name => 'fn_storico_arma_scope',
                p_status        => 'WARN',
                p_rule_type     => 'STORICO_SCOPE',
                p_params        => jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                                                      'owner', v_owner, 'current_user', current_user),
                p_message       => 'Shadow di un altro proprietario: colonne e policy le allinea il provisioning da superuser');
        END IF;
        RETURN jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                                  'esito', 'SKIP_OWNER', 'owner', v_owner);
    END IF;

    -- 2) Le due colonne e l'indice, solo se mancano.
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = v_sto_oid AND a.attname = 'origine_schema'
                      AND NOT a.attisdropped) THEN
        v_azioni := array_append(v_azioni, 'ADD_COLUMN origine_schema');
        IF NOT p_dry_run THEN
            EXECUTE format('ALTER TABLE %s ADD COLUMN origine_schema text', v_full_sto);
            -- Il trigger la scrive SEMPRE: su una shadow vuota (appena nata)
            -- il NOT NULL è vero da subito. Su una shadow con righe legacy
            -- resta nullable finché il backfill non le attribuisce (passo 5).
            EXECUTE format('SELECT NOT EXISTS (SELECT 1 FROM %s)', v_full_sto) INTO v_vuota;
            IF v_vuota THEN
                v_azioni := array_append(v_azioni, 'SET_NOT_NULL origine_schema');
                EXECUTE format('ALTER TABLE %s ALTER COLUMN origine_schema SET NOT NULL', v_full_sto);
            END IF;
            EXECUTE format($c$COMMENT ON COLUMN %s.origine_schema IS
                'Lo schema della madre da cui viene questa versione (TG_TABLE_SCHEMA nel trigger). Serve perché il nome della shadow è il nome NUDO della madre e sei shadow sono condivise fra due schemi: senza, due documenti con lo stesso id si chiuderebbero a vicenda. Le versioni scritte prima del 2026-09-11 lo ricevono dal backfill; dove il backfill non sa attribuirle resta NULL. Brief: brief-db-rls-storico-scope-congelato §4b (D2).'$c$,
                v_full_sto);
        END IF;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = v_sto_oid AND a.attname = 'scope_emittente_fiscale_id'
                      AND NOT a.attisdropped) THEN
        v_azioni := array_append(v_azioni, 'ADD_COLUMN scope_emittente_fiscale_id');
        IF NOT p_dry_run THEN
            EXECUTE format('ALTER TABLE %s ADD COLUMN scope_emittente_fiscale_id bigint', v_full_sto);
            EXECUTE format($c$COMMENT ON COLUMN %s.scope_emittente_fiscale_id IS
                'L''emittente fiscale (anagrafiche.emittenti_fiscali.id) a cui apparteneva la riga QUANDO è stata fotografata: il trigger lo risolve con dbops.fn_storico_risolvi_scope seguendo la mappa dbops.storico_scope_policy e lo congela. Non si ricalcola mai: un archivio che cambia col presente non è un archivio. NULL = madre non protetta, o versione precedente al backfill non attribuibile: con la RLS della shadow accesa quella versione non si vede (fail-closed). La policy rls_sto_<tab>_ef_whitelist legge questa colonna. Brief: brief-db-rls-storico-scope-congelato §4b (D1).'$c$,
                v_full_sto);
        END IF;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class i
                    JOIN pg_catalog.pg_index x ON x.indexrelid = i.oid
                   WHERE x.indrelid = v_sto_oid AND i.relname = v_ix) THEN
        v_azioni := array_append(v_azioni, 'CREATE_INDEX ' || v_ix);
        IF NOT p_dry_run THEN
            EXECUTE format('CREATE INDEX %I ON %s (scope_emittente_fiscale_id)', v_ix, v_full_sto);
        END IF;
    END IF;

    -- 2b) Uno snapshot non si cancella: all'applicazione SELECT, INSERT e
    --     UPDATE (il trigger scrive e chiude), MAI DELETE. I DEFAULT
    --     PRIVILEGES del loop dei grant e del provisioning lo darebbero a
    --     ogni shadow nuova: qui, dove la shadow converge, si toglie.
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'zeroerp_app')
       AND pg_catalog.has_table_privilege('zeroerp_app', v_sto_oid, 'DELETE') THEN
        v_azioni := array_append(v_azioni, 'REVOKE_DELETE zeroerp_app');
        IF NOT p_dry_run THEN
            EXECUTE format('REVOKE DELETE ON TABLE %s FROM zeroerp_app', v_full_sto);
        END IF;
    END IF;

    -- 3) La mappa decide se la shadow si ARMA. Nessuna riga o NESSUNO:
    --    solo le colonne. Non si disarma mai.
    SELECT m.modo INTO v_modo
      FROM dbops.storico_scope_policy m
     WHERE m.schema_tabella = p_schema_base AND m.nome_tabella = p_table_base;
    v_arma := (v_modo IS NOT NULL AND v_modo <> 'NESSUNO');

    IF v_arma THEN
        IF NOT v_rls THEN
            v_azioni := array_append(v_azioni, 'ENABLE_RLS');
            IF NOT p_dry_run THEN
                EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', v_full_sto);
            END IF;
        END IF;

        -- Lettura: veste OPERATORE, stesso adapter delle madri con colonna EF.
        IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policy p
                        WHERE p.polrelid = v_sto_oid AND p.polname = v_pol_sel) THEN
            v_azioni := array_append(v_azioni, 'CREATE_POLICY ' || v_pol_sel);
            IF NOT p_dry_run THEN
                v_sql := format($p$CREATE POLICY %I ON %s FOR SELECT
                    USING ((current_setting('app.ruolo_applicativo', true) = 'OPERATORE')
                           -- ⭐ rev 2026-10-18 (D-3b-2c, 20261018-27): il perimetro dell'operatore
                           --    in UNA sottoquery non correlata, valutata una volta per istruzione;
                           --    per riga resta fn_scope_ef_perimetro(perimetro, scope).
                           AND script.fn_scope_ef_perimetro(
                                   (SELECT script.fn_get_emittenti_scope_pk_ids(
                                       NULLIF(current_setting('app.current_user_id', true), '')::integer)),
                                   scope_emittente_fiscale_id))$p$,
                    v_pol_sel, v_full_sto);
                EXECUTE v_sql;
            END IF;
        END IF;

        -- Scrittura del trigger: non si filtra. La madre ha già la sua RLS,
        -- e un filtro qui romperebbe o zittirebbe la storicizzazione.
        IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policy p
                        WHERE p.polrelid = v_sto_oid AND p.polname = v_pol_ins) THEN
            v_azioni := array_append(v_azioni, 'CREATE_POLICY ' || v_pol_ins);
            IF NOT p_dry_run THEN
                EXECUTE format('CREATE POLICY %I ON %s FOR INSERT WITH CHECK (true)',
                               v_pol_ins, v_full_sto);
            END IF;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policy p
                        WHERE p.polrelid = v_sto_oid AND p.polname = v_pol_upd) THEN
            v_azioni := array_append(v_azioni, 'CREATE_POLICY ' || v_pol_upd);
            IF NOT p_dry_run THEN
                EXECUTE format('CREATE POLICY %I ON %s FOR UPDATE USING (true) WITH CHECK (true)',
                               v_pol_upd, v_full_sto);
            END IF;
        END IF;
    END IF;

    -- 4) Audit solo se ha fatto (o farebbe) qualcosa: la passata normale su
    --    una shadow allineata non scrive e non registra nulla.
    IF cardinality(v_azioni) > 0 THEN
        PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_storico_arma_scope',
            p_status        => CASE WHEN p_dry_run THEN 'DRYRUN' ELSE 'OK' END,
            p_rule_type     => 'STORICO_SCOPE',
            p_dry_run       => p_dry_run,
            p_params        => jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                                                  'modo', v_modo, 'armata', v_arma,
                                                  'azioni', to_jsonb(v_azioni)),
            p_message       => CASE WHEN p_dry_run THEN 'Shadow: azioni che verrebbero fatte'
                                    ELSE 'Shadow allineata alla forma dello scope' END);
    END IF;

    RETURN jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                              'esito', CASE WHEN cardinality(v_azioni) > 0 THEN 'ALLINEATA' ELSE 'GIA_ALLINEATA' END,
                              'modo', v_modo, 'armata', v_arma,
                              'azioni', to_jsonb(v_azioni), 'dry_run', p_dry_run);
END;
$function$

COMMENT ON FUNCTION dbops.fn_storico_arma_scope(p_schema_base text, p_table_base text, p_dry_run boolean)
IS '⭐ rev 2026-10-18 (20261018-20, D-3b-2): la policy di lettura chiama script.fn_scope_ef_perimetro col perimetro in due sottoquery non correlate (una volta per istruzione), non piu'' script.fn_scope_ef_whitelist per riga. Porta la shadow storico.<tabella> di una madre alla forma dello scope congelato: colonne origine_schema e scope_emittente_fiscale_id (con indice) e, se dbops.storico_scope_policy dice che la madre è protetta (modo diverso da NESSUNO), RLS accesa con tre policy — rls_sto_<tab>_ef_whitelist FOR SELECT sull''emittente congelato (veste OPERATORE, adapter script.fn_scope_ef_whitelist), rls_sto_<tab>_trg_ins e rls_sto_<tab>_trg_upd con «true» perché la shadow la scrive il trigger e filtrare la scrittura romperebbe o zittirebbe la storicizzazione. Idempotente e forward-only: aggiunge solo ciò che manca e non disarma mai. ⚠️ Solo se il migratore possiede la shadow: altrimenti WARN nell''audit e si prosegue (le allinea il provisioning da superuser). Torna un jsonb con esito e azioni. La chiamano il generatore fn_ensure_storico_table sulla shadow appena creata e fn_storico_arma_scope_tutte. Brief: brief-db-rls-storico-scope-congelato §4b.';
```

</div>

---
{% include-markdown "signature-core.md" %}
