{% include-markdown "it/dbzero/script/manual/fn_get_sorgente_emittente_sr_id.md" %}
# ⚙️ Funzione `fn_get_sorgente_emittente_sr_id`

```sql
CREATE FUNCTION fn_get_sorgente_emittente_sr_id(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_sorgente_emittente_sr_id(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_target    regclass;
    v_selector  config.sorgenti.key_selector%TYPE;
    v_codice    config.sorgenti.codice_interno%TYPE;
    v_uid       text := btrim(p_sorgente_uid);
    v_colonna   text;        -- predicato sulla chiave: 'id' oppure 'uid'
    v_chiave    text;
    v_sr_id     anagrafiche.soggetti_ruoli.id%TYPE;
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dato (tipo sorgente, chiave canonica) dire CHI EMETTE
    --   quel documento, in convenzione soggetto_ruolo.
    --
    -- ⛔ NON si passa dal billing account, ed e' la correzione
    --   che ha fatto nascere questa funzione: su ordini,
    --   preventivi, ddt e resi il BA e' NULLABLE — uno stato
    --   LEGALE — mentre emittente_fiscale_id e' NOT NULL su
    --   tutte e sei le tabelle documento. Chiedere il cliente
    --   per sapere l'emittente e' la strada lunga, e su quattro
    --   tabelle e' una strada chiusa.
    --
    -- ⚠️ SECURITY DEFINER: le tabelle documento hanno la RLS.
    --   Da SECURITY INVOKER la sorgente di un altro emittente
    --   sarebbe invisibile e il chiamante concluderebbe «non
    --   esiste» invece di «e' di un altro».
    --
    -- ⛔ Fail-closed ovunque: mai un NULL silenzioso.
    -- =========================================================
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_CONF',
            jsonb_build_object('detail', 'Tipo sorgente non valorizzato',
                               'sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid, COALESCE(p_sorgente_tipo_id::text, '<nessuno>'));
    END IF;

    SELECT s.target_table, s.key_selector, s.codice_interno
      INTO v_target, v_selector, v_codice
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id
       AND s.attivo = true;

    IF v_target IS NULL OR v_selector IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_CONF',
            jsonb_build_object('detail', 'Sorgente non attiva o senza target_table/key_selector',
                               'sorgente_tipo_id', p_sorgente_tipo_id,
                               'target_table', COALESCE(v_target::text, '<NULL>'),
                               'key_selector', COALESCE(v_selector, '<NULL>')),
            NULL::uuid, p_sorgente_tipo_id::text);
    END IF;

    IF v_uid IS NULL OR v_uid = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_KEY_MISSING',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'key_selector', v_selector),
            NULL::uuid, p_sorgente_tipo_id::text, v_selector);
    END IF;

    -- Formato della chiave secondo il catalogo. ⚠️ La chiave
    -- attesa e' quella CANONICA (quella che
    -- fn_link_commessa_sorgente NORMALIZZA in scrittura), non
    -- quella che il push passa in giro.
    -- ⭐ rev 2026-10-05 (20261005-26): «canonica» lo controllano ora i
    --   building block script.fn_sorgente_chiave_id / _uuid, la stessa regola
    --   del guard e dei lettori; prima le regex larghe accettavano '007' e le
    --   maiuscole, cioe' il commento qui sopra non era vero. Sul valore
    --   RICEVUTO, non sulla copia senza spazi. Chiamati per nome qualificato:
    --   questa funzione e' DEFINER con search_path stretto.
    IF v_selector = 'id' THEN
        IF script.fn_sorgente_chiave_id(p_sorgente_uid) IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_FORMATO',
                jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                   'sorgente_uid', p_sorgente_uid,
                                   'key_selector', v_selector),
                NULL::uuid, concat('atteso id::text, ricevuto «', p_sorgente_uid, '»'));
        END IF;
        v_colonna := 'id';
    ELSIF v_selector = 'uid' THEN
        IF script.fn_sorgente_chiave_uuid(p_sorgente_uid) IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_FORMATO',
                jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                                   'sorgente_uid', p_sorgente_uid,
                                   'key_selector', v_selector),
                NULL::uuid, concat('atteso uuid, ricevuto «', p_sorgente_uid, '»'));
        END IF;
        v_colonna := 'uid';
    ELSE
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_KEYSEL',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'key_selector', v_selector),
            NULL::uuid, v_selector);
    END IF;

    -- ⚠️ UN SOLO parametro, con il cast NELLA query: passarne
    --   due (uno bigint e uno uuid, l'altro NULL) romperebbe
    --   l'EXECUTE — «too many parameters specified». La chiave
    --   viaggia come testo e la si converte qui.
    v_chiave := format('t.%I = $1::%s', v_colonna,
                       CASE WHEN v_colonna = 'id' THEN 'bigint' ELSE 'uuid' END);

    -- ── STRADA 1: la colonna SR, che e' gia' la risposta ──────
    --   commesse, fatture, fatturazione_lotti: nessuna
    --   traduzione, e' una copia.
    IF EXISTS (SELECT 1 FROM pg_attribute
                WHERE attrelid = v_target
                  AND attname  = 'emittente_soggetto_ruolo_id'
                  AND attnum   > 0 AND NOT attisdropped) THEN
        EXECUTE format('SELECT t.emittente_soggetto_ruolo_id FROM %s t WHERE %s',
                       v_target::text, v_chiave)
          INTO v_sr_id
         USING v_uid;

    -- ── STRADA 2: l'emittente del documento, tradotto in SR ──
    --   E' il caso dei SEI documenti, e la colonna e' NOT NULL
    --   su tutti e sei: e' il motivo per cui questa funzione
    --   esiste al posto di quella che chiedeva il cliente.
    ELSIF EXISTS (SELECT 1 FROM pg_attribute
                   WHERE attrelid = v_target
                     AND attname  = 'emittente_fiscale_id'
                     AND attnum   > 0 AND NOT attisdropped) THEN
        EXECUTE format('SELECT t.emittente_fiscale_id FROM %s t WHERE %s',
                       v_target::text, v_chiave)
          INTO v_ef_id
         USING v_uid;

        SELECT ef.soggetto_ruolo_id INTO v_sr_id
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id = v_ef_id;

    -- ── STRADA 3: il cliente, per chi l'emittente non ce l'ha ─
    --   attivita_consumi e attivita_fatturabili: nessuna colonna
    --   emittente, ma il billing account si'.
    ELSIF EXISTS (SELECT 1 FROM pg_attribute
                   WHERE attrelid = v_target
                     AND attname  = 'billing_account_id'
                     AND attnum   > 0 AND NOT attisdropped) THEN
        EXECUTE format('SELECT t.billing_account_id FROM %s t WHERE %s',
                       v_target::text, v_chiave)
          INTO v_ba_id
         USING v_uid;

        IF v_ba_id IS NOT NULL THEN
            v_sr_id := anagrafiche.fn_get_emittente_fiscale_id(v_ba_id);
        END IF;

    ELSE
        -- Nessuna delle tre: la sorgente non e' interrogabile.
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_CONF',
            jsonb_build_object('detail', 'target_table senza colonna emittente ne'' billing account',
                               'sorgente_tipo_id', p_sorgente_tipo_id,
                               'target_table', v_target::text),
            NULL::uuid, p_sorgente_tipo_id::text);
    END IF;

    -- ⛔ Documento inesistente, oppure esistente ma senza un
    --    emittente risolvibile: per il chiamante sono la stessa
    --    cosa — non si puo' dire chi lo emette — e un NULL qui
    --    disarmerebbe il guard a valle.
    IF v_sr_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_get_sorgente_emittente_sr_id', 'E_SORG_EMITTENTE_NON_RISOLTO',
            jsonb_build_object('detail', 'documento inesistente o senza emittente risolvibile',
                               'sorgente_tipo_id', p_sorgente_tipo_id,
                               'sorgente_uid', v_uid,
                               'target_table', v_target::text),
            NULL::uuid, COALESCE(v_codice, p_sorgente_tipo_id::text), v_uid);
    END IF;

    RETURN v_sr_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_sorgente_emittente_sr_id(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'Risolve «CHI EMETTE questo documento» per la sorgente polimorfa: dato (sorgente_tipo_id, chiave CANONICA secondo config.sorgenti.key_selector) restituisce il soggetto_ruolo dell''emittente. ⛔ SOSTITUISCE script.fn_get_sorgente_billing_account_id (20260826-43), che passava dal BILLING ACCOUNT ed era la strada sbagliata: letto sulla doc auto-gen il 2026-08-26, billing_account_id e'' NULLABLE su QUATTRO tabelle sorgente su sei (ordini, preventivi, ddt, resi) — uno stato LEGALE del modello — mentre emittente_fiscale_id e'' NOT NULL su tutte e sei. Il risolutore vecchio si fermava fail-closed su documenti perfettamente validi, e un guard che rifiuta uno stato che il modello ammette non e'' severo: e'' rotto. Trovato da un pgTAP (vendite/test-ordini-guard-transizione-v1, che crea ordini con billing_account_id NULL di proposito), non da un ragionamento. ⭐ La correzione rende il guard piu'' FORTE e non piu'' debole: la tentazione era «BA nullo -> salta il controllo», che e'' cio'' che fanno i sei guard fratelli (trgfn_ordini_guard_emittente_ba e famiglia, «Skip: nessun BA su cui ancorare la coerenza») — li'' e'' giusto perche'' quei guard confrontano PROPRIO il BA con l''emittente, qui si confrontano DUE EMITTENTI e non c''e'' niente da saltare. TRE STRADE, in ordine di direttezza: (1) emittente_soggetto_ruolo_id se la target ce l''ha — commesse, fatture, lotti: nessuna traduzione, e'' una copia; (2) emittente_fiscale_id tradotto in SR con il join 1:1 su anagrafiche.emittenti_fiscali — i sei documenti; (3) billing_account_id delegato ad anagrafiche.fn_get_emittente_fiscale_id — attivita_consumi e attivita_fatturabili, che l''emittente non ce l''hanno. Nessuna delle tre -> E_SORG_CONF. ⛔ FAIL-CLOSED ovunque, mai un NULL silenzioso: documento inesistente o senza emittente risolvibile -> E_SORG_EMITTENTE_NON_RISOLTO; chiave malformata -> E_SORG_FORMATO; key_selector fuori catalogo -> E_SORG_KEYSEL. ⚠️ SECURITY DEFINER: le tabelle documento hanno la RLS, e da SECURITY INVOKER la sorgente di un altro emittente sarebbe invisibile — il chiamante concluderebbe «non esiste» invece di «e'' di un altro». ⚠️ La chiave attesa e'' quella CANONICA, cioe'' quella che vendite.fn_link_commessa_sorgente normalizza in scrittura, non quella che il push passa (guida /guide/sorgente-polimorfa §4a). Piano: brief-db-emittente-commessa-invariante, L6. ⭐ rev 2026-10-05 (20261005-26): il formato CANONICO della chiave lo controllano i building block script.fn_sorgente_chiave_id / _uuid (chiamati per nome qualificato: DEFINER con search_path stretto), la stessa regola del guard della sorgente polimorfa e del rubinetto. Prima le regex larghe accettavano ''007'' e gli uuid maiuscoli, contro quanto la funzione dichiarava.';
```

</div>

---
{% include-markdown "signature-core.md" %}
