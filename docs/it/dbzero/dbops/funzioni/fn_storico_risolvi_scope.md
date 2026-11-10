{% include-markdown "it/dbzero/dbops/manual/fn_storico_risolvi_scope.md" %}
# ⚙️ Funzione `fn_storico_risolvi_scope`

```sql
CREATE FUNCTION fn_storico_risolvi_scope(p_schema text, p_tabella text, p_riga jsonb, p_profondita integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_storico_risolvi_scope(p_schema text, p_tabella text, p_riga jsonb, p_profondita integer DEFAULT 0)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    -- Oltre questa profondità non c'è una catena legittima: la più
    -- lunga dichiarata è a due salti. È un tetto contro il ciclo,
    -- non un limite di disegno.
    c_max_profondita CONSTANT integer := 8;
    v_mappa     dbops.storico_scope_policy%ROWTYPE;
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_sr_id     anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_chiave    text;
    v_padre_oid oid;
    v_tipo_id   text;
    v_padre     jsonb;
    -- Ripiego sull'archivio del padre: la sua shadow e la colonna che
    -- vi punta alla riga (STORICO_FK, con override).
    v_sto_oid   oid;
    v_fk_hist   text;
    v_ha_orig   boolean;
BEGIN
    -- 0) Il tetto: una catena che a questo punto è ancora PADRE gira
    --    in cerchio. È l'unico caso in cui si solleva.
    IF p_profondita > c_max_profondita THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'fn_storico_risolvi_scope',
            'E_STORICO_SCOPE_CATENA_CICLICA',
            jsonb_build_object('schema', p_schema, 'tabella', p_tabella,
                               'profondita', p_profondita),
            NULL::uuid,
            p_schema || '.' || p_tabella, p_profondita::text);
    END IF;

    -- 1) La riga di mappa della madre. Senza riga: NULL, e il
    --    presidio pgTAP vede la madre non dichiarata.
    SELECT * INTO v_mappa
      FROM dbops.storico_scope_policy m
     WHERE m.schema_tabella = p_schema
       AND m.nome_tabella   = p_tabella;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- 2) La strada dichiarata.
    CASE v_mappa.modo
        WHEN 'NESSUNO' THEN
            RETURN NULL;

        WHEN 'EF' THEN
            -- La colonna È l'emittente fiscale: si copia.
            v_ef_id := NULLIF(p_riga ->> v_mappa.colonna, '')::bigint;
            RETURN v_ef_id;

        WHEN 'SR' THEN
            -- Soggetto-ruolo dell'emittente: 1:1 con l'emittente
            -- fiscale, si normalizza alla rappresentazione della
            -- canonica. Nessuna riga -> NULL (fail-closed).
            v_sr_id := NULLIF(p_riga ->> v_mappa.colonna, '')::bigint;
            IF v_sr_id IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT ef.id INTO v_ef_id
              FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.soggetto_ruolo_id = v_sr_id;
            RETURN v_ef_id;

        WHEN 'BA' THEN
            -- Un billing account ha ESATTAMENTE UN emittente
            -- (specifico, o il gestore globale): lo dice la
            -- funzione che già serve le policy via_efba.
            v_sr_id := script.fn_get_ba_emittente_sr_id(
                           NULLIF(p_riga ->> v_mappa.colonna, '')::bigint);
            IF v_sr_id IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT ef.id INTO v_ef_id
              FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.soggetto_ruolo_id = v_sr_id;
            RETURN v_ef_id;

        WHEN 'COPPIA' THEN
            -- La coppia (istanza, utility): le due colonne dichiarate,
            -- «<istanza>,<utility>», sono la chiave di
            -- anagrafiche.billing_account (istanza_utility_id,
            -- utility_id). Il BA della coppia, poi il suo emittente come
            -- nel modo BA. Una colonna vuota, o una coppia senza BA:
            -- NULL, fail-closed (rev 2026-10-09, brief-db-istanza-nasce-col-ba).
            -- ⭐ Rev 2026-10-21 (20261021-28): il BA lo dice
            --   script.fn_get_ba_id_da_coppia, la stessa domanda della
            --   policy di anagrafiche.istanze_dati_precontrattuali (regola
            --   del 2: era scritta qui e in via_coppia, ritirata dal -27).
            v_ba_id := script.fn_get_ba_id_da_coppia(
                           NULLIF(p_riga ->> split_part(v_mappa.colonna, ',', 1), '')::bigint,
                           NULLIF(p_riga ->> split_part(v_mappa.colonna, ',', 2), '')::integer);
            IF v_ba_id IS NULL THEN
                RETURN NULL;
            END IF;
            v_sr_id := script.fn_get_ba_emittente_sr_id(v_ba_id);
            IF v_sr_id IS NULL THEN
                RETURN NULL;
            END IF;
            SELECT ef.id INTO v_ef_id
              FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.soggetto_ruolo_id = v_sr_id;
            RETURN v_ef_id;

        WHEN 'PADRE' THEN
            -- La FK verso il padre. Vuota (FK nullable) -> NULL.
            v_chiave := NULLIF(p_riga ->> v_mappa.colonna, '');
            IF v_chiave IS NULL THEN
                RETURN NULL;
            END IF;
            -- Il padre si risolve per NOME QUALIFICATO con to_regclass,
            -- non cercando nspname nel catalogo: così vale anche per
            -- `pg_temp` (alias della temp schema, che nel catalogo si
            -- chiama pg_temp_N) — è ciò che permette al pgTAP di
            -- costruire una catena su tabelle temporanee.
            v_padre_oid := pg_catalog.to_regclass(
                               pg_catalog.format('%I.%I', v_mappa.padre_schema,
                                                          v_mappa.padre_tabella));
            IF v_padre_oid IS NULL THEN
                -- Padre dichiarato che non esiste: lo vede il pgTAP; qui NULL.
                RETURN NULL;
            END IF;
            -- Il tipo VERO della PK `id` del padre, per castare il
            -- testo del JSON e usare l'indice.
            SELECT pg_catalog.format_type(a.atttypid, a.atttypmod)
              INTO v_tipo_id
              FROM pg_catalog.pg_attribute a
             WHERE a.attrelid = v_padre_oid
               AND a.attname  = 'id'
               AND NOT a.attisdropped;
            IF v_tipo_id IS NULL THEN
                -- Padre senza `id`: la mappa dice una cosa che il
                -- catalogo non conferma. Lo vede il pgTAP; qui NULL.
                RETURN NULL;
            END IF;
            -- La riga del padre, letta come proprietario: è il
            -- motivo del SECURITY DEFINER.
            EXECUTE pg_catalog.format(
                'SELECT pg_catalog.to_jsonb(t) FROM %I.%I t WHERE t.id = %L::%s',
                v_mappa.padre_schema, v_mappa.padre_tabella, v_chiave, v_tipo_id)
               INTO v_padre;
            IF v_padre IS NULL THEN
                -- Padre non piu' vivo — ammesso dal modello (nessuna FK sulle
                -- shadow) e NORMALE in un DELETE a cascata: il padre e' gia'
                -- stato cancellato quando il trigger del figlio scrive la sua
                -- versione finale. Ma il padre ha un ARCHIVIO: la sua ultima
                -- versione nello storico porta ancora l'emittente. Leggere
                -- l'archivio del padre e' leggere il passato, non il presente.
                v_sto_oid := pg_catalog.to_regclass(pg_catalog.format('storico.%I', v_mappa.padre_tabella));
                IF v_sto_oid IS NOT NULL THEN
                    v_fk_hist := dbops.fn_get_override_col(v_mappa.padre_schema, v_mappa.padre_tabella,
                                                            'STORICO_FK', v_mappa.padre_tabella || '_id');
                    SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                                    WHERE a.attrelid = v_sto_oid AND a.attname = 'origine_schema'
                                      AND NOT a.attisdropped)
                      INTO v_ha_orig;
                    IF EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                                WHERE a.attrelid = v_sto_oid AND a.attname = v_fk_hist
                                  AND NOT a.attisdropped) THEN
                        -- L'ultima versione scritta; nelle shadow condivise solo quella
                        -- dello schema giusto (o non attribuita, prima del backfill).
                        EXECUTE pg_catalog.format(
                            'SELECT s.snapshot FROM storico.%I s WHERE s.%I = %L::%s %s
                              ORDER BY s.valid_from DESC, s.id DESC LIMIT 1',
                            v_mappa.padre_tabella, v_fk_hist, v_chiave, v_tipo_id,
                            CASE WHEN v_ha_orig
                                 THEN pg_catalog.format('AND (s.origine_schema = %L OR s.origine_schema IS NULL)',
                                                        v_mappa.padre_schema)
                                 ELSE '' END)
                           INTO v_padre;
                    END IF;
                END IF;
            END IF;
            IF v_padre IS NULL THEN
                -- Nemmeno l'archivio lo conosce: NULL, fail-closed sulla shadow.
                RETURN NULL;
            END IF;
            -- Si continua sulla riga di mappa del padre.
            RETURN dbops.fn_storico_risolvi_scope(
                       v_mappa.padre_schema, v_mappa.padre_tabella,
                       v_padre, p_profondita + 1);
    END CASE;
END;
$function$

COMMENT ON FUNCTION dbops.fn_storico_risolvi_scope(p_schema text, p_tabella text, p_riga jsonb, p_profondita integer)
IS 'Risolve l''emittenti_fiscali.id a cui appartiene la riga (to_jsonb) di una madre storicizzata, seguendo la strada dichiarata in dbops.storico_scope_policy: EF (copia), SR (converte 1:1), BA (l''unico emittente del billing account), COPPIA (la colonna dichiara due nomi, «<istanza>,<utility>», la chiave di anagrafiche.billing_account: il BA della coppia lo trova script.fn_get_ba_id_da_coppia, e se ne prende l''emittente come nel modo BA), PADRE (carica la riga del padre per id o, se il padre non e'' piu'' vivo, la sua ultima versione nello storico, normale in un DELETE a cascata dove il padre sparisce prima che il figlio scriva, e si richiama ricorsivamente), NESSUNO (NULL). La chiama il trigger di storico per congelare lo scope nella shadow. SECURITY DEFINER del proprietario, non di un superuser: catturare lo scope e'' un atto di sistema e deve vedere il padre anche quando chi scrive non lo vedrebbe sotto RLS; attraversa la RLS perche'' chi migra possiede le tabelle (ENABLE senza FORCE), e il pgTAP lo asserisce. Non solleva mai (madre non mappata, colonna vuota, coppia senza BA, padre sparito danno NULL, fail-closed sulla shadow), tranne su una catena che non termina (E_STORICO_SCOPE_CATENA_CICLICA).';
```

</div>

---
{% include-markdown "signature-core.md" %}
