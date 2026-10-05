{% include-markdown "it/dbzero/vendite/manual/fn_link_commessa_sorgente.md" %}
# ⚙️ Funzione `fn_link_commessa_sorgente`

```sql
CREATE FUNCTION fn_link_commessa_sorgente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_sorgente_riga bigint, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_link_commessa_sorgente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_sorgente_riga bigint DEFAULT NULL::bigint, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_link_id  vendite.commesse_sorgenti.id%TYPE;
    v_uid      text := btrim(p_sorgente_uid);
    v_existing vendite.commesse_sorgenti%ROWTYPE;
    v_ruolo    vendite.commesse_sorgenti.ruolo_link%TYPE;
    -- Normalizzazione chiave canonica (brief-db-guard-sorgente-polimorfa §2a)
    c_uuid_re  CONSTANT text := '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';
    v_target   regclass;
    v_selector text;
    v_norm     text;
BEGIN
    -- Guard: parametri obbligatori
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id), NULL::uuid, 'p_commessa_id obbligatorio e > 0');
    END IF;

    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_sorgente_tipo_id', 'valore', p_sorgente_tipo_id), NULL::uuid, 'p_sorgente_tipo_id obbligatorio e > 0');
    END IF;

    IF p_sorgente_uid IS NULL OR v_uid = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_sorgente_uid', 'valore', p_sorgente_uid), NULL::uuid, 'p_sorgente_uid obbligatoria');
    END IF;

    IF p_sorgente_riga IS NOT NULL AND p_sorgente_riga < 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_sorgente_riga', 'valore', p_sorgente_riga), NULL::uuid, 'p_sorgente_riga se fornita deve essere >= 0');
    END IF;

    -- Normalizzazione chiave canonica: la chiave stoccata segue
    -- config.sorgenti.key_selector ('id' -> id::text, 'uid' -> uuid).
    -- I chiamanti storici passano l'uid del documento anche per i
    -- tipi a chiave id: qui si traduce, prima di idempotenza e
    -- insert, cosi' uq_commesse_sorgenti_src_uid lavora sempre
    -- sulla forma canonica. Niente chiavi inventate: se l'uuid non
    -- risolve la fn fallisce in modo parlante.
    SELECT s.target_table, s.key_selector
      INTO v_target, v_selector
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id
       AND s.attivo = true;

    IF v_target IS NULL OR v_selector IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_SORG_CONF',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'target_table', COALESCE(v_target::text, '<NULL>'),
                               'key_selector', COALESCE(v_selector, '<NULL>')),
            NULL::uuid, concat('sorgente_tipo_id ', p_sorgente_tipo_id));
    END IF;

    IF v_selector = 'id' THEN
        IF v_uid ~ c_uuid_re THEN
            -- uuid ricevuto per tipo a chiave id: traduzione via colonna uid del target
            IF NOT EXISTS (SELECT 1 FROM pg_attribute
                            WHERE attrelid = v_target
                              AND attname  = 'uid'
                              AND attnum   > 0
                              AND NOT attisdropped) THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_SORG_NORM_NON_RISOLTA',
                    jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                       'sorgente_uid', v_uid,
                                       'target_table', v_target::text,
                                       'detail', 'target_table senza colonna uid'),
                    NULL::uuid, concat('target ', v_target::text, ' senza colonna uid; uid ', v_uid));
            END IF;

            EXECUTE format('SELECT id::text FROM %s WHERE uid = $1', v_target::text)
              INTO v_norm
              USING v_uid::uuid;

            IF v_norm IS NULL THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_SORG_NORM_NON_RISOLTA',
                    jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                       'sorgente_uid', v_uid,
                                       'target_table', v_target::text,
                                       'detail', 'uuid non presente nella target_table'),
                    NULL::uuid, concat('uid ', v_uid, ' non trovato in ', v_target::text));
            END IF;

            v_uid := v_norm;
        -- ⭐ rev 2026-10-05 (20261005-25): forma CANONICA (id::text), con lo
        --   stesso building block del guard e dei lettori. Prima '^[0-9]+$'
        --   lasciava passare '007': chiave che esiste, ma che nessun lettore
        --   risolve. v_uid e' gia' senza spazi (btrim in testa, normalizzazione
        --   dichiarata di questo rubinetto).
        ELSIF script.fn_sorgente_chiave_id(v_uid) IS NULL THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_SORG_FORMATO',
                jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                   'sorgente_uid', v_uid,
                                   'key_selector', v_selector),
                NULL::uuid, concat('atteso id numerico in testo, ricevuto ', v_uid));
        END IF;
    ELSIF v_selector = 'uid' THEN
        -- ⭐ rev 2026-10-05 (20261005-25): forma CANONICA (uuid::text,
        --   minuscolo). La regex accettava le maiuscole, e la chiave salvata
        --   cosi' non la ritrova nessun lettore.
        IF script.fn_sorgente_chiave_uuid(v_uid) IS NULL THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_SORG_FORMATO',
                jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                   'sorgente_uid', v_uid,
                                   'key_selector', v_selector),
                NULL::uuid, concat('atteso uuid, ricevuto ', v_uid));
        END IF;
    ELSE
        -- key_selector fuori catalogo: config.sorgenti dovrebbe impedirlo con CHECK
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_SORG_KEYSEL',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'key_selector', v_selector),
            NULL::uuid, concat('key_selector ', v_selector));
    END IF;

    -- Verifica esistenza + LOCK commessa: serializza la decisione del
    -- ruolo (ROOT vs COLLEGATO) tra sessioni concorrenti sulla stessa
    -- commessa. Alla prima sorgente la ROOT non esiste ancora, quindi
    -- lockare la commessa (non la ROOT) e' il solo punto affidabile.
    PERFORM 1 FROM vendite.commesse c WHERE c.id = p_commessa_id FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id), NULL::uuid, concat('commessa_id ', p_commessa_id));
    END IF;

    -- Unicita'/idempotenza sorgente: una sorgente (tipo+uid) appartiene
    -- a UNA sola commessa (uq_commesse_sorgenti_src_uid). Lookup globale
    -- sulla chiave GIA' normalizzata.
    SELECT cs.* INTO v_existing
      FROM vendite.commesse_sorgenti cs
     WHERE cs.sorgente_tipo_id = p_sorgente_tipo_id
       AND cs.sorgente_uid = v_uid
     FOR UPDATE;

    IF FOUND THEN
        IF v_existing.commessa_id <> p_commessa_id THEN
            -- Sorgente gia' agganciata ad ALTRA commessa: incoerente
            -- (un documento contribuisce a una sola commessa).
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_COMMESSA_SORGENTE_ALTRA_COMMESSA',
                jsonb_build_object(
                    'commessa_richiesta', p_commessa_id,
                    'commessa_esistente', v_existing.commessa_id,
                    'sorgente_tipo_id', p_sorgente_tipo_id,
                    'sorgente_uid', v_uid,
                    'ruolo_link', v_existing.ruolo_link
                ), NULL::uuid, v_existing.commessa_id::text);
        END IF;

        -- Stessa commessa, stessa sorgente: idempotente. Merge meta;
        -- ruolo e sorgente_riga gia' assegnati restano (link a livello
        -- documento, indipendente da p_sorgente_riga).
        UPDATE vendite.commesse_sorgenti cs
           SET meta = COALESCE(cs.meta, '{}'::jsonb) || COALESCE(p_meta, '{}'::jsonb)
         WHERE cs.id = v_existing.id
        RETURNING cs.id INTO v_link_id;

        RETURN v_link_id;
    END IF;

    -- Sorgente nuova per questa commessa: assegna il ruolo.
    --   commessa senza ROOT -> ROOT (primaria);
    --   commessa con ROOT   -> COLLEGATO (contributore).
    -- Serializzato dal lock sulla commessa (sopra).
    IF EXISTS (SELECT 1 FROM vendite.commesse_sorgenti cs
                WHERE cs.commessa_id = p_commessa_id AND cs.ruolo_link = 'ROOT') THEN
        v_ruolo := 'COLLEGATO';
    ELSE
        v_ruolo := 'ROOT';
    END IF;

    BEGIN
        INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, sorgente_riga, ruolo_link, meta)
        VALUES (p_commessa_id, p_sorgente_tipo_id, v_uid, p_sorgente_riga, v_ruolo, COALESCE(p_meta, '{}'::jsonb))
        RETURNING id INTO v_link_id;
    EXCEPTION
        WHEN unique_violation THEN
            -- Race su uq_commesse_sorgenti_src_uid: tra il SELECT e
            -- l'INSERT un'altra sessione ha agganciato la stessa sorgente.
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_COMMESSA_SORGENTE_ALTRA_COMMESSA',
                jsonb_build_object('commessa_richiesta', p_commessa_id, 'sorgente_tipo_id', p_sorgente_tipo_id, 'sorgente_uid', v_uid),
                NULL::uuid, p_commessa_id::text);
    END;

    RETURN v_link_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_link_commessa_sorgente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_sorgente_riga bigint, p_meta jsonb)
IS 'Collega una sorgente a una commessa in modo idempotente decidendo il ruolo: prima sorgente -> ROOT, successive -> COLLEGATO (commessa multi-sorgente, aggregazione del fatturabile). NORMALIZZA la chiave secondo config.sorgenti.key_selector prima di idempotenza e insert (id -> id::text, traducendo l''uuid dei chiamanti storici via target_table.uid; uid -> uuid testuale); formato non conforme o uuid non risolvibile -> E_SORG_FORMATO / E_SORG_NORM_NON_RISOLTA. Una sorgente appartiene a una sola commessa (uq_commesse_sorgenti_src_uid): se gia su altra commessa solleva E_COMMESSA_SORGENTE_ALTRA_COMMESSA. Lock su vendite.commesse serializza la decisione del ruolo. rev 2026-07-18 (brief-db-guard-sorgente-polimorfa §2a). ⭐ rev 2026-10-05 (20261005-25): i due controlli di formato finali chiedono la FORMA CANONICA con i building block script.fn_sorgente_chiave_id / _uuid, gli stessi del guard trgfn_guard_sorgente_polimorfa_testuale: prima ''^[0-9]+$'' accettava ''007'' e la regex uuid le maiuscole. Restano le normalizzazioni dichiarate del rubinetto: btrim della chiave e traduzione uuid -> id::text per i tipi a chiave id (il risultato e'' gia'' canonico).';
```

---
{% include-markdown "signature-core.md" %}
