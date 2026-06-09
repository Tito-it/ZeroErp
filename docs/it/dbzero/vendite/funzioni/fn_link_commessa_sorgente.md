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
    -- a UNA sola commessa (uq_commesse_sorgenti_src_uid). Lookup globale.
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
IS 'Collega una sorgente a una commessa in modo idempotente decidendo il ruolo: prima sorgente -> ROOT, successive -> COLLEGATO (commessa multi-sorgente, aggregazione del fatturabile). Una sorgente appartiene a una sola commessa (uq_commesse_sorgenti_src_uid): se gia su altra commessa solleva E_COMMESSA_SORGENTE_ALTRA_COMMESSA. Lock su vendite.commesse serializza la decisione del ruolo.';
```

---
{% include-markdown "signature-core.md" %}
