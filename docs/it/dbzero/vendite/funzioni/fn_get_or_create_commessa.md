{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_commessa.md" %}
# ⚙️ Funzione `fn_get_or_create_commessa`

```sql
CREATE FUNCTION fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying, p_policy_fatturazione character varying, p_fatturazione_immediata boolean, p_priorita_operativa character varying, p_competenza_dal date, p_competenza_al date, p_meta jsonb, p_force_new boolean, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying DEFAULT 'AUTO'::character varying, p_policy_fatturazione character varying DEFAULT 'DA_DOCUMENTO'::character varying, p_fatturazione_immediata boolean DEFAULT false, p_priorita_operativa character varying DEFAULT 'NORMALE'::character varying, p_competenza_dal date DEFAULT NULL::date, p_competenza_al date DEFAULT NULL::date, p_meta jsonb DEFAULT '{}'::jsonb, p_force_new boolean DEFAULT false, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_modalita_pagamento_id integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: recupera o crea la commessa coerente con il contesto
--        dimensionale. Da D-R la chiave comprende anche le condizioni
--        di pagamento: un documento con termine diverso NON riusa una
--        commessa esistente, ne apre una nuova — cosi' la divergenza
--        emerge al push e non a valle, in fattura.
-- Regole: la chiave vive in TRE posti (hash del lock, WHERE del riuso,
--         INSERT). ⚠️ I tre NON sono identici alla lettera, ed e'
--         voluto: l'emittente e' NOT NULL sulla colonna
--         (20260826-41), quindi il WHERE lo confronta con `=` puro,
--         mentre l'hash conserva il proprio COALESCE — cambiare la
--         stringa che si hasha cambierebbe l'IDENTITA' del lock senza
--         guadagno. Le DIMENSIONI restano le stesse in tutti e tre:
--         e' quello che va tenuto uguale, non il testo.
-- ⭐ Dal 2026-08-26 NON esiste piu' un parametro per l'emittente:
--         si deriva dal billing account e basta (decisione D-1).
DECLARE
    v_commessa_id vendite.commesse.id%TYPE;
    v_ba_utility  anagrafiche.billing_account.utility_id%TYPE;
    v_ba_found    BOOLEAN := FALSE;
    v_emittente   vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
    v_codice      vendite.commesse.codice%TYPE;
    -- ⭐ rev 2026-08-31 (C2-11): il codice non si fabbrica piu' qui, si
    --   COMPONE dal numero che consegna il registro.
    v_sigla       anagrafiche.emittenti_fiscali.codice%TYPE;
    v_registro    vendite.registri_fatturazione.id%TYPE;
    v_data        date;
    v_anno        smallint;
    v_numero      bigint;
    v_prefix      config.sistema_codici.prefisso%TYPE;
    v_sep         config.sistema_codici.separatore%TYPE;
    v_len         config.sistema_codici.lunghezza_numero%TYPE;
BEGIN
    -- Guard: parametri obbligatori
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid, 'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id),
            NULL::uuid, 'p_utility_id obbligatorio e > 0'
        );
    END IF;

    IF p_competenza_dal IS NOT NULL AND p_competenza_al IS NOT NULL AND p_competenza_dal > p_competenza_al THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_DATA_AL_MINORE_DAL',
            jsonb_build_object('competenza_dal', p_competenza_dal, 'competenza_al', p_competenza_al),
            NULL::uuid, p_competenza_al::text, p_competenza_dal::text
        );
    END IF;

    -- Verifica BA
    SELECT ba.utility_id, TRUE INTO v_ba_utility, v_ba_found
      FROM anagrafiche.billing_account ba WHERE ba.id = p_billing_account_id;

    IF NOT v_ba_found THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, concat('billing_account_id ', p_billing_account_id)
        );
    END IF;

    IF v_ba_utility IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_BILLING_ACCOUNT_UTILITY_NULL',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, p_billing_account_id::text
        );
    END IF;

    IF v_ba_utility <> p_utility_id THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_CLIENTE_UTILITY_MISMATCH_BA',
            jsonb_build_object('billing_account_id', p_billing_account_id, 'ba_utility_id', v_ba_utility, 'utility_id', p_utility_id),
            NULL::uuid, p_billing_account_id::text, p_utility_id::text, v_ba_utility::text
        );
    END IF;

    -- ⭐ L'emittente si DERIVA, e non c'e' piu' nessun modo di
    --   passarlo da fuori: e' la decisione D-1 portata a termine.
    --   La funzione SOLLEVA invece di tornare NULL, quindi da qui
    --   in poi v_emittente e' valorizzato per costruzione.
    --   ⚠️ Lo stesso valore lo riscriverebbe comunque
    --   trgfn_commesse_default_emittente sulla INSERT: qui serve
    --   PRIMA, perche' entra nella chiave di riuso e nel lock.
    v_emittente := anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id);

    IF NOT p_force_new THEN
        -- SPECCHIO 1 — advisory lock sul contesto dimensionale.
        -- ⛔ Il COALESCE su v_emittente resta anche se il NULL non
        --    e' piu' possibile: quello che si hasha e' l'IDENTITA'
        --    del lock, e cambiarla farebbe smettere di
        --    serializzarsi a due sessioni che girassero su due
        --    revisioni diverse di questa funzione.
        PERFORM pg_advisory_xact_lock(
            hashtext('fn_get_or_create_commessa'),
            hashtext(
                p_billing_account_id::text || E'\x1F' || p_utility_id::text || E'\x1F' ||
                p_tipo_commessa || E'\x1F' || p_policy_fatturazione || E'\x1F' ||
                p_fatturazione_immediata::text || E'\x1F' || p_priorita_operativa || E'\x1F' ||
                COALESCE(v_emittente::text, '') || E'\x1F' ||
                COALESCE(p_competenza_dal::text, '') || E'\x1F' || COALESCE(p_competenza_al::text, '') || E'\x1F' ||
                COALESCE(p_termine_pagamento_id::text, '') || E'\x1F' ||
                COALESCE(p_modalita_pagamento_id::text, '')
            )
        );

        -- SPECCHIO 2 — WHERE della commessa riusabile.
        -- ⭐ L'emittente si confronta con `=` PURO: la colonna e'
        --   NOT NULL (20260826-41) e v_emittente non e' mai NULL.
        -- ⚠️ IS NOT DISTINCT FROM resta sulle quattro dimensioni
        --   davvero nullable (competenza e condizioni di pagamento).
        SELECT c.id INTO v_commessa_id
          FROM vendite.commesse c
          JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id AND sc.chiude_commessa = FALSE
         WHERE c.billing_account_id = p_billing_account_id
           AND c.utility_id = p_utility_id
           AND c.tipo_commessa = p_tipo_commessa
           AND c.policy_fatturazione = p_policy_fatturazione
           AND c.fatturazione_immediata = p_fatturazione_immediata
           AND c.priorita_operativa = p_priorita_operativa
           AND c.emittente_soggetto_ruolo_id = v_emittente
           AND c.competenza_dal IS NOT DISTINCT FROM p_competenza_dal
           AND c.competenza_al IS NOT DISTINCT FROM p_competenza_al
           AND c.termine_pagamento_id  IS NOT DISTINCT FROM p_termine_pagamento_id
           AND c.modalita_pagamento_id IS NOT DISTINCT FROM p_modalita_pagamento_id
         ORDER BY c.id DESC LIMIT 1;

        IF v_commessa_id IS NOT NULL THEN RETURN v_commessa_id; END IF;
    END IF;

    -- ═══ IL CODICE, rev 2026-08-31 (C2-11) ═══════════════════
    -- ⛔ Prima era 'CMM-' || timestamp || '-' || md5(random()): un
    --   identificatore, non un codice. Diceva quando e' nata la riga
    --   — cosa che data_insert dice gia' — e affidava l'unicita' a
    --   sei caratteri casuali SOTTO un vincolo deterministico
    --   (uq_commesse_codice): un'unicita' probabilistica, che quando
    --   fallisce esce come 23505 nudo in mezzo a un fan-out.
    -- ⭐ Ora: CMM-<sigla emittente>-<anno>-<9 cifre>, e l'unicita' e'
    --   DETERMINISTICA — la sigla e' unica, l'anno e' un fatto, il
    --   numero viene da un contatore serializzato.

    -- La sigla entra nel codice, e per questo il contatore e' PER
    -- EMITTENTE: ogni dimensione del contatore dev'essere nella
    -- stringa, o al primo cambio di periodo la UNIQUE salta.
    SELECT ef.codice INTO v_sigla
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = v_emittente;

    -- ⛔ L'INVOLUCRO, non il lettore: qui si scrive, e un emittente
    --   senza registro COMMESSA deve fermare invece di far nascere
    --   una commessa senza codice.
    SELECT k.registro_id INTO v_registro
      FROM vendite.fn_get_registro_documento(
               p_famiglia_documento          => 'COMMESSA',
               p_emittente_soggetto_ruolo_id => v_emittente,
               p_utility_id                  => p_utility_id) k;

    -- ⭐ La commessa non ha una data documento: la sua data e' quella
    --   di CREAZIONE, e si legge da script.fn_data_operativa() —
    --   la data di oggi NEL FUSO DELL'AZIENDA, mai now() nudo.
    v_data := script.fn_data_operativa();
    v_anno := vendite.fn_get_anno_registro(v_data);

    -- ℹ️ serie vuota (la commessa non ne ha) e nessun bersaglio: la
    --   riga non esiste ancora, e il cancello non puo' mordere
    --   perche' la data e' sempre oggi.
    v_numero := vendite.fn_get_next_progressivo(
                    v_registro, v_data, NULL, '', NULL, 'COMMESSA');

    -- Formato dal catalogo, come per gli altri documenti: prefisso,
    -- separatore e lunghezza restano un DATO.
    SELECT prefisso, separatore, lunghezza_numero
      INTO v_prefix, v_sep, v_len
      FROM config.sistema_codici
     WHERE codice_interno = 'commessa';

    v_codice := COALESCE(v_prefix, 'CMM') || COALESCE(v_sep, '-')
             || v_sigla                   || COALESCE(v_sep, '-')
             || v_anno::text              || COALESCE(v_sep, '-')
             || lpad(v_numero::text, COALESCE(v_len, 9), '0');

    -- SPECCHIO 3 — INSERT: la commessa nasce con la chiave completa.
    INSERT INTO vendite.commesse (codice, tipo_commessa, policy_fatturazione, fatturazione_immediata,
        priorita_operativa, billing_account_id, utility_id, emittente_soggetto_ruolo_id,
        competenza_dal, competenza_al, meta,
        termine_pagamento_id, modalita_pagamento_id)
    VALUES (v_codice, p_tipo_commessa, p_policy_fatturazione, p_fatturazione_immediata,
        p_priorita_operativa, p_billing_account_id, p_utility_id, v_emittente,
        p_competenza_dal, p_competenza_al, COALESCE(p_meta, '{}'::jsonb),
        p_termine_pagamento_id, p_modalita_pagamento_id)
    RETURNING id INTO v_commessa_id;

    RETURN v_commessa_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying, p_policy_fatturazione character varying, p_fatturazione_immediata boolean, p_priorita_operativa character varying, p_competenza_dal date, p_competenza_al date, p_meta jsonb, p_force_new boolean, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
IS 'Recupera o crea la commessa coerente con il contesto dimensionale. La chiave di raggruppamento comprende anche (termine_pagamento_id, modalita_pagamento_id): un documento sorgente con condizioni diverse apre una commessa NUOVA. Advisory lock contro la doppia creazione, con le stesse dimensioni del WHERE. ⭐ rev 2026-08-31 (brief-db-registri-di-numerazione-emittente-e-trasloco, C2-11): IL CODICE VIENE DAL REGISTRO. Era ''CMM-'' || clock_timestamp() || ''-'' || substr(md5(random()),1,6) — 28 caratteri di cui sei di puro rumore e i primi dodici uguali per tutte le commesse dello stesso giorno: un IDENTIFICATORE e non un codice, che diceva quando era nata la riga, cioe'' cio'' che data_insert dice gia'' e con il tipo giusto. ⛔ E quella md5 era un''UNICITA'' PROBABILISTICA SOTTO UN VINCOLO DETERMINISTICO: uq_commesse_codice la collisione la impedisce gia'', il random la rendeva soltanto improbabile — e quando fosse capitata sarebbe uscita come 23505 nudo in mezzo a un fan-out, senza retry e senza codice di dominio. ⭐ Ora la forma e'' CMM-<sigla emittente>-<anno>-<9 cifre>: l''unicita'' e'' DETERMINISTICA e si legge nella stringa, perche'' la sigla e'' unica (uq:codice su anagrafiche.emittenti_fiscali), l''anno e'' un fatto e il numero viene da un contatore serializzato sotto advisory lock. ⭐ E'' l''invariante del cantiere applicato alla lettera: ogni dimensione del contatore deve comparire nella CHIAVE D''IDENTITA'' del numero — e per la commessa quella chiave e'' la STRINGA NUDA (uq_commesse_codice), quindi emittente e anno devono starci dentro per davvero, non basta che il contatore li conosca. ⭐ La sigla si puo'' usare qui mentre il 2026-08-30 sembrava impossibile, e la ragione e'' cambiata sotto: l''obiezione era che il generatore GENERICO (script.fn_generate_codice) non puo'' tradurre un id in sigla senza imparare a conoscere anagrafiche.emittenti_fiscali — vera, ma la commessa da quel generatore se n''e'' andata, e qui siamo dentro una funzione di dominio che legge cio'' che le serve. ⚠️ La sigla e'' IMMUTABILE (script.trgfn_lock_columns su emittenti_fiscali.codice): il codice non diventa mai falso. ⚠️ NESSUNA COLONNA NUOVA su vendite.commesse: sigla e anno stanno nella stringa, quindi uq_commesse_codice resta intatta e il codice continua a bastare da solo per trovare una commessa — e'' la decisione «A» del 2026-08-30. ℹ️ La data e'' quella di CREAZIONE, letta da script.fn_data_operativa() (la data di oggi nel fuso dell''AZIENDA, mai now() nudo): ne discende che il cancello di monotonia non puo'' morderla, ed e'' il motivo per cui la famiglia COMMESSA resta a presidia_data_documento = true senza che costi niente. ⛔ Si usa l''INVOLUCRO vendite.fn_get_registro_documento e non il lettore: qui si scrive, e un emittente senza registro COMMESSA deve fermare invece di far nascere una commessa senza codice. ⛔ Il pregresso NON si rinumera (decisione di Tid): le commesse vecchie tengono il loro codice e non collidono con i nuovi perche'' hanno una forma diversa — ed e'' l''unica cosa che li separa. ⚠️ La firma e'' INVARIATA (12 parametri): CREATE OR REPLACE basta, nessun DROP e nessun overload. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-11.';
```

---
{% include-markdown "signature-core.md" %}
