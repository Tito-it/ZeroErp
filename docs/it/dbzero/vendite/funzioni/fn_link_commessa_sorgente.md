{% include-markdown "it/dbzero/vendite/manual/fn_link_commessa_sorgente.md" %}
# ⚙️ Funzione `fn_link_commessa_sorgente`

```sql
CREATE FUNCTION fn_link_commessa_sorgente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_sorgente_riga bigint, p_meta jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
    v_altra_commessa_id vendite.commesse_sorgenti.commessa_id%TYPE;
    v_sorgente_id  vendite.commesse_sorgenti.sorgente_id%TYPE;
    v_sorgente_uid vendite.commesse_sorgenti.sorgente_uid%TYPE;
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

    -- La chiave da stoccare: il BB che scrive la provenienza
    -- (script.fn_sorgente_chiave) legge il key_selector del tipo, traduce
    -- l'uuid dei chiamanti per i tipi a chiave id (e l'id per i tipi a
    -- chiave uid), verifica che il documento esista e solleva E_SORG_CONF /
    -- E_SORG_FORMATO / E_SORG_NORM_NON_RISOLTA / E_SORG_NOT_FOUND. Restituisce
    -- la chiave del modello, una delle due colonne: idempotenza, lock e insert
    -- lavorano su quella. v_uid e' gia' senza spazi (btrim in testa).
    SELECT k.sorgente_id, k.sorgente_uid
      INTO v_sorgente_id, v_sorgente_uid
      FROM script.fn_sorgente_chiave(p_sorgente_tipo_id, v_uid) k;

    -- Verifica esistenza + LOCK commessa: serializza la decisione del
    -- ruolo (ROOT vs COLLEGATO) tra sessioni concorrenti sulla stessa
    -- commessa. Alla prima sorgente la ROOT non esiste ancora, quindi
    -- lockare la commessa (non la ROOT) e' il solo punto affidabile.
    PERFORM 1 FROM vendite.commesse c WHERE c.id = p_commessa_id FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id), NULL::uuid, concat('commessa_id ', p_commessa_id));
    END IF;

    -- Il link RESTA come storia dopo la chiusura o l'annullo della
    --   commessa (l'unicita' della tabella e' per commessa).
    --   «Un documento in una sola commessa APERTA» si decide qui.
    --   Il lock advisory sulla SORGENTE serializza due invii dello stesso
    --   documento verso commesse DIVERSE: il lock sulla commessa (sopra) non
    --   li vede, perche' bloccano due righe diverse. Forma a due argomenti,
    --   namespace = questa funzione. ⚠️ Vale in READ COMMITTED, come lavora
    --   l'applicazione: chi aspetta il lock rilegge con una fotografia nuova.
    --   La chiave del lock e' il tipo con la chiave del modello resa a testo
    --   (id::text o uuid::text): una sola delle due c'e'.
    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.fn_link_commessa_sorgente'),
        hashtext(p_sorgente_tipo_id::text || ':'
                 || COALESCE(v_sorgente_id::text, v_sorgente_uid::text)));

    -- Stessa commessa, stessa sorgente: idempotente. Il ruolo e la
    -- sorgente_riga gia' assegnati restano (link a livello documento).
    -- Il meta si riscrive solo se cambia: la porta la chiama la madre
    --   delle righe, una volta per riga di commessa, e un UPDATE a vuoto
    --   scriverebbe una riga di storico per ogni riga mandata.
    SELECT cs.* INTO v_existing
      FROM vendite.commesse_sorgenti cs
     WHERE cs.sorgente_tipo_id = p_sorgente_tipo_id
       AND (cs.sorgente_id = v_sorgente_id OR cs.sorgente_uid = v_sorgente_uid)
       AND cs.commessa_id      = p_commessa_id
     FOR UPDATE;

    IF FOUND THEN
        UPDATE vendite.commesse_sorgenti cs
           SET meta = cs.meta || COALESCE(p_meta, '{}'::jsonb)
         WHERE cs.id = v_existing.id
           AND cs.meta IS DISTINCT FROM cs.meta || COALESCE(p_meta, '{}'::jsonb);

        RETURN v_existing.id;
    END IF;

    -- Il documento sta gia' in un'ALTRA commessa APERTA: rifiuto. Una
    -- commessa chiusa o annullata non lo trattiene, il suo link e' storia.
    -- La domanda «quale commessa aperta» ha una sede sola, il building block.
    v_altra_commessa_id := vendite.fn_commessa_viva_di_sorgente(p_sorgente_tipo_id, v_sorgente_id, v_sorgente_uid);

    IF v_altra_commessa_id IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_link_commessa_sorgente', 'E_COMMESSA_SORGENTE_ALTRA_COMMESSA',
            jsonb_build_object(
                'commessa_richiesta', p_commessa_id,
                'commessa_esistente', v_altra_commessa_id,
                'sorgente_tipo_id', p_sorgente_tipo_id,
                'sorgente_id', v_sorgente_id,
                'sorgente_uid', v_sorgente_uid
            ), NULL::uuid, v_altra_commessa_id::text);
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

    -- Nessun blocco EXCEPTION sull'unique_violation: la corsa (la stessa
    --   sorgente su due commesse fra il SELECT e l'INSERT) la serializza il
    --   lock advisory; il doppione sulla stessa commessa, il lock sulla
    --   commessa.
    INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, ruolo_link, meta)
    VALUES (p_commessa_id, p_sorgente_tipo_id, v_sorgente_id, v_sorgente_uid, p_sorgente_riga, v_ruolo, COALESCE(p_meta, '{}'::jsonb))
    RETURNING id INTO v_link_id;

    RETURN v_link_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_link_commessa_sorgente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_sorgente_riga bigint, p_meta jsonb)
IS 'La porta del link documento -> commessa (vendite.commesse_sorgenti): collega una sorgente a una commessa in modo idempotente decidendo il ruolo (prima sorgente della commessa -> ROOT, successive -> COLLEGATO: commessa multi-sorgente, aggregazione del fatturabile). La chiave la decide il BB che scrive la provenienza, script.fn_sorgente_chiave: legge il key_selector del tipo, traduce la chiave del chiamante (l''uuid per un tipo a chiave id, l''id per un tipo a chiave uid), verifica che il documento esista, solleva E_SORG_CONF / E_SORG_FORMATO / E_SORG_NORM_NON_RISOLTA / E_SORG_NOT_FOUND e restituisce la chiave del modello, sorgente_id oppure sorgente_uid: idempotenza, lock e insert lavorano su quella. p_sorgente_uid e'' la chiave del documento come la passa il chiamante, id o uid resi a testo; nella tabella la riga e'' validata dal guard unico, script.trgfn_guard_sorgente. Un documento sta in UNA SOLA COMMESSA APERTA alla volta: il link resta come storia dopo la chiusura o l''annullo della commessa (unicita'' della tabella per commessa); se il documento sta gia'' in un''altra commessa aperta (vendite.fn_commessa_viva_di_sorgente) solleva E_COMMESSA_SORGENTE_ALTRA_COMMESSA. Due invii dello stesso documento verso commesse diverse li serializza un lock advisory sulla sorgente (forma a due argomenti, namespace = questa funzione; vale in READ COMMITTED, come l''applicazione); il lock sulla commessa serializza il ruolo. Il meta si riscrive solo se cambia. Chiamante: vendite.fn_upsert_commessa_attivita, per ogni riga con una sorgente di scope PUSH_COMMESSA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
