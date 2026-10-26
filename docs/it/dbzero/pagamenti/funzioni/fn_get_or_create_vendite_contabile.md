{% include-markdown "it/dbzero/pagamenti/manual/fn_get_or_create_vendite_contabile.md" %}
# ⚙️ Funzione `fn_get_or_create_vendite_contabile`

```sql
CREATE FUNCTION fn_get_or_create_vendite_contabile(p_centro_riscossione_id bigint, p_data_contabile date, p_data_registrazione date, p_ente_incasso_id bigint, p_lotto_id bigint, p_codice_stato_interno text, p_meta jsonb, p_origine character varying, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_or_create_vendite_contabile(p_centro_riscossione_id bigint, p_data_contabile date, p_data_registrazione date DEFAULT script.fn_data_operativa(), p_ente_incasso_id bigint DEFAULT NULL::bigint, p_lotto_id bigint DEFAULT NULL::bigint, p_codice_stato_interno text DEFAULT 'BOZZA'::text, p_meta jsonb DEFAULT '{}'::jsonb, p_origine character varying DEFAULT 'GENERATA'::character varying, p_emittente_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_contabile_id pagamenti.vendite_contabili.id%TYPE;
  v_stato_id pagamenti.vendite_contabili_stati.id%TYPE;
  v_data_registrazione pagamenti.vendite_contabili.data_registrazione%TYPE;
  v_operatore pagamenti.vendite_contabili.user_insert%TYPE;
  v_emittente_sr pagamenti.vendite_contabili.emittente_soggetto_ruolo_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Recuperare o creare una testata contabile vendite.
  --
  -- Regole principali:
  --   - ⭐ una distinta MANUALE e' il LOTTO DI LAVORO DI UN OPERATORE:
  --     il riuso comprende CHI STA LAVORANDO, non solo la giornata.
  --     Cosi' la contesa fra due operatori non esiste, e il lock che
  --     sarebbe servito a governarla non si costruisce (D12-a).
  --
  -- Rev 2026-09-15 (brief distinta-numerata-sul-registro, L6):
  --   la distinta SA DI CHI E' (D3). Parametro in coda
  --   p_emittente_fiscale_id (PK), derivazione dal lotto, poi la
  --   sede unica pagamenti.fn_get_emittente_distinta; l'emittente
  --   entra nella CHIAVE DI RIUSO di entrambi i rami e
  --   nell'INSERT. ⛔ `codice` non si passa: lo assegna il trigger
  --   sul registro (D5) — sparito il DEFAULT di colonna del 28-08.
  --
  -- Rev 2026-08-22 (lotto 7, D15-e): sparisce p_compensazione_id, e
  --   con lui il ramo di riuso «una testata per atto», la mutua
  --   esclusione con p_lotto_id e la colonna nell'INSERT.
  --   ⭐ Girato il verso del legame e' l'ATTO a generare la contabile e
  --   a tenerne l'id: chiederla qui voleva dire far nascere la testata
  --   SAPENDO gia' di chi sarebbe stata, cioe' il verso opposto a come
  --   funziona il processo. L'unicita' «una contabile per atto» vive
  --   adesso su uq_sistemazioni_contabile.
  --   ⚠️ Nessun chiamante passava quel parametro: misurato il
  --   2026-08-22 su tutte le funzioni DB e su backend/ + frontend/.
  --
  -- Rev 2026-08-21 (passo P-7): i nove E_GENERICO passano ai codici
  -- registrati. Nessun predicato e' cambiato.
  -- =========================================================

  -- ⭐ I DUE guard che un OPERATORE puo' far scattare davvero: il
  --    centro e la data li sceglie lui in un form. Codice di dominio,
  --    non un codice trasversale, perche' il messaggio lo legge una
  --    persona e non deve nominare un parametro PL/pgSQL.
  IF p_centro_riscossione_id IS NULL OR p_centro_riscossione_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_CONTABILE_DATI_OBBLIGATORI',
      jsonb_build_object(
        'detail', 'p_centro_riscossione_id obbligatorio > 0',
        'campo', 'centro_riscossione_id',
        'p_centro_riscossione_id', p_centro_riscossione_id
      ),
      NULL::uuid,
      'il centro di riscossione'
    );
  END IF;

  IF p_data_contabile IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_CONTABILE_DATI_OBBLIGATORI',
      jsonb_build_object(
        'detail', 'p_data_contabile obbligatoria',
        'campo', 'data_contabile'
      ),
      NULL::uuid,
      'la data contabile'
    );
  END IF;

  -- ⚠️ Da qui in giu' i guard non difendono un DATO dell'operatore:
  --    difendono un'INVARIANTE DELLA CHIAMATA. Su questi il NULL e'
  --    AMMESSO, e un id <= 0 o uno stato vuoto non escono da nessuna
  --    interfaccia — li produce solo un chiamante rotto. Per questo il
  --    codice e' E_PAGAMENTI_CHIAMATA_NON_VALIDA, classe TECNICO (500):
  --    l'operatore non ha niente da correggere, e il messaggio nomina il
  --    parametro perche' il suo lettore e' chi ha scritto la chiamata.
  --    ⛔ NON E_PARAMETRO_INVALIDO: quello e' uno split rimandato
  --    (D11 di brief-db-be-classe-codici-errore) che sopravvive per le
  --    funzioni vecchie, non una sede per il codice nuovo.

  IF p_ente_incasso_id IS NOT NULL AND p_ente_incasso_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'p_ente_incasso_id deve essere > 0 se valorizzato',
        'p_ente_incasso_id', p_ente_incasso_id
      ),
      NULL::uuid,
      'pagamenti.fn_get_or_create_vendite_contabile', 'p_ente_incasso_id (se valorizzato, maggiore di zero)'
    );
  END IF;

  IF p_lotto_id IS NOT NULL AND p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'p_lotto_id deve essere > 0 se valorizzato',
        'p_lotto_id', p_lotto_id
      ),
      NULL::uuid,
      'pagamenti.fn_get_or_create_vendite_contabile', 'p_lotto_id (se valorizzato, maggiore di zero)'
    );
  END IF;

  -- Rev 2026-09-15: stessa specie dei due sopra — NULL ammesso, un
  -- id <= 0 lo produce solo un chiamante rotto.
  IF p_emittente_fiscale_id IS NOT NULL AND p_emittente_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'p_emittente_fiscale_id deve essere > 0 se valorizzato',
        'p_emittente_fiscale_id', p_emittente_fiscale_id
      ),
      NULL::uuid,
      'pagamenti.fn_get_or_create_vendite_contabile', 'p_emittente_fiscale_id (se valorizzato, maggiore di zero)'
    );
  END IF;

  IF p_codice_stato_interno IS NULL OR btrim(p_codice_stato_interno) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'p_codice_stato_interno obbligatorio'
      ),
      NULL::uuid,
      'pagamenti.fn_get_or_create_vendite_contabile', 'p_codice_stato_interno (obbligatorio, non vuoto)'
    );
  END IF;

  -- Il vocabolario e' presidiato anche dal CHECK, ma un 23514 non dice
  -- quale colonna: un valore fuori vocabolario lo produce solo un
  -- chiamante rotto, quindi TECNICO.
  IF p_origine IS NULL OR p_origine NOT IN ('MANUALE', 'AUTOMATICA', 'GENERATA') THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'p_origine fuori vocabolario',
        'p_origine', p_origine
      ),
      NULL::uuid,
      'pagamenti.fn_get_or_create_vendite_contabile',
      'p_origine (MANUALE, AUTOMATICA o GENERATA)'
    );
  END IF;

  -- Chi sta lavorando: la STESSA espressione con cui
  -- script.trgfn_audit_data_user_generic valorizza user_insert, cosi' la
  -- chiave di riuso e la colonna scritta non possono divergere.
  v_operatore := COALESCE(
      NULLIF(current_setting('app.jwt_user', true), ''),
      CURRENT_USER
  );

  SELECT s.id
    INTO v_stato_id
    FROM pagamenti.vendite_contabili_stati s
   WHERE s.codice_interno = p_codice_stato_interno
     AND s.attivo IS TRUE
   LIMIT 1;

  -- ⚠️ Non e' un parametro sbagliato: e' il catalogo degli stati a
  -- non avere quella riga, o ad averla spenta. Classe TECNICO.
  IF v_stato_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_CONTABILE_STATO_NON_CONFIGURATO',
      jsonb_build_object(
        'detail', 'stato contabile non trovato/attivo',
        'codice_interno', p_codice_stato_interno
      ),
      NULL::uuid,
      p_codice_stato_interno
    );
  END IF;

  v_data_registrazione := COALESCE(p_data_registrazione, script.fn_data_operativa());

  -- =========================================================
  -- Rev 2026-09-15 — DI CHI E' LA DISTINTA, PRIMA DI CERCARLA.
  --   La chiave di riuso comprende l'emittente (D3): si risolve
  --   qui, prima delle due SELECT, o la manuale non ritroverebbe
  --   mai «quella di prima».
  -- =========================================================

  -- 1) Il parametro: PK -> SR, esplicito, come trgfn_ordini_gen_numero.
  --    Un id che non e' un emittente lo produce solo un chiamante rotto.
  IF p_emittente_fiscale_id IS NOT NULL THEN
    SELECT ef.soggetto_ruolo_id
      INTO v_emittente_sr
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = p_emittente_fiscale_id;

    IF v_emittente_sr IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
        jsonb_build_object(
          'detail', 'p_emittente_fiscale_id non e'' un emittente fiscale',
          'p_emittente_fiscale_id', p_emittente_fiscale_id
        ),
        NULL::uuid,
        'pagamenti.fn_get_or_create_vendite_contabile', 'p_emittente_fiscale_id (non e'' un emittente fiscale)'
      );
    END IF;
  END IF;

  -- 2) Dal LOTTO: chi passa un lotto sa gia' di chi e' la distinta
  --    (fatturazione_lotti.emittente_soggetto_ruolo_id e' NOT NULL), e
  --    lo dice per primo — il giro di massa di un admin globale in
  --    modalita' «tutti gli emittenti» ha lotti di N aziende e una
  --    sessione che non risolve nessuno.
  -- ⚠️ STRICT: questa funzione e' INVOKER e fatturazione_lotti ha la
  --    RLS. Un lotto che non c'e' o che non si vede NON cade sulla
  --    sessione: la distinta del lotto di un altro nascerebbe di chi
  --    agisce, agganciata a un lotto altrui (la FK del link non guarda
  --    la RLS). Dalla pipeline non ci si arriva — il sync legge il
  --    lotto della fattura che sta lavorando, nel proprio perimetro —
  --    ci arriva solo una chiamata a mano. TECNICO.
  IF v_emittente_sr IS NULL AND p_lotto_id IS NOT NULL THEN
    SELECT l.emittente_soggetto_ruolo_id
      INTO v_emittente_sr
      FROM vendite.fatturazione_lotti l
     WHERE l.id = p_lotto_id;

    IF v_emittente_sr IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.fn_get_or_create_vendite_contabile', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
        jsonb_build_object(
          'detail', 'p_lotto_id: lotto inesistente o fuori perimetro',
          'p_lotto_id', p_lotto_id
        ),
        NULL::uuid,
        'pagamenti.fn_get_or_create_vendite_contabile', 'p_lotto_id (lotto inesistente o fuori perimetro)'
      );
    END IF;
  END IF;

  -- 3) La sede unica: dato e coerente col canale / dal canale /
  --    dalla sessione / rifiuto parlante (D4). Il trigger a10_emittente
  --    la ri-applica all'INSERT (livelli 0-1, idempotente).
  v_emittente_sr := pagamenti.fn_get_emittente_distinta(v_emittente_sr, p_ente_incasso_id);

  IF p_lotto_id IS NULL THEN
    -- ⭐ D12-a: su una distinta MANUALE la chiave di riuso comprende
    --    l'OPERATORE. Il raggruppamento «giornata + canale» non ha un
    --    referente nel mondo — nessun documento reale corrisponde a «tutti
    --    gli incassi banca di lunedi' digitati a mano» — mentre il lotto di
    --    lavoro di una persona ce l'ha. E con questo la contesa fra due
    --    operatori non esiste: niente colonne di blocco, niente scadenze del
    --    lock, niente sblocco d'emergenza.
    -- ⚠️ Sulle altre due origini la chiave resta quella di prima: una
    --    distinta GENERATA non e' il lotto di lavoro di nessuno, e una
    --    AUTOMATICA e' il file.
    -- ⭐ Rev 2026-09-15: l'EMITTENTE entra nella chiave su tutte le
    --    origini (D3). Sulla manuale non cambia niente in pratica
    --    (operatore => emittente); la GENERATA senza lotto smette di
    --    raccogliere i fondi di tutti — e' la decisione aperta del
    --    20260822-20, chiusa nel verso «una per emittente».
    SELECT vc.id
      INTO v_contabile_id
      FROM pagamenti.vendite_contabili vc
     WHERE vc.centro_riscossione_id = p_centro_riscossione_id
       AND vc.ente_incasso_id IS NOT DISTINCT FROM p_ente_incasso_id
       AND vc.emittente_soggetto_ruolo_id = v_emittente_sr
       AND vc.data_contabile = p_data_contabile
       AND vc.data_registrazione = v_data_registrazione
       AND vc.stato_id = v_stato_id
       AND vc.origine = p_origine
       AND (p_origine <> 'MANUALE' OR vc.user_insert = v_operatore)
     ORDER BY vc.id DESC
     LIMIT 1;
  ELSE
    SELECT vc.id
      INTO v_contabile_id
      FROM pagamenti.vendite_contabili vc
      JOIN pagamenti.vendite_contabili_lotti vcl
        ON vcl.contabile_id = vc.id
     WHERE vcl.lotto_id = p_lotto_id
       AND vc.centro_riscossione_id = p_centro_riscossione_id
       AND vc.ente_incasso_id IS NOT DISTINCT FROM p_ente_incasso_id
       AND vc.emittente_soggetto_ruolo_id = v_emittente_sr
       AND vc.data_contabile = p_data_contabile
       AND vc.data_registrazione = v_data_registrazione
       AND vc.stato_id = v_stato_id
       AND vc.origine = p_origine
       AND (p_origine <> 'MANUALE' OR vc.user_insert = v_operatore)
     ORDER BY vc.id DESC
     LIMIT 1;
  END IF;

  IF v_contabile_id IS NULL THEN
    -- ⭐ Rev 2026-09-15: il codice lo assegna il TRIGGER sul registro
    --    DISTINTA dell'emittente (a10_gen_codice, D5): non si passa.
    --    Fino a oggi lo metteva il DEFAULT della colonna (rev 28-08),
    --    caduto con 20260915-21. L'emittente entra nella riga: il
    --    trigger a10_emittente lo ri-valuta (livelli 0-1, idempotente).
    INSERT INTO pagamenti.vendite_contabili (
      centro_riscossione_id,
      ente_incasso_id,
      emittente_soggetto_ruolo_id,
      data_contabile,
      data_registrazione,
      stato_id,
      origine,
      meta
    ) VALUES (
      p_centro_riscossione_id,
      p_ente_incasso_id,
      v_emittente_sr,
      p_data_contabile,
      v_data_registrazione,
      v_stato_id,
      p_origine,
      COALESCE(p_meta, '{}'::jsonb)
    )
    RETURNING id INTO v_contabile_id;
  END IF;

  IF p_lotto_id IS NOT NULL THEN
    INSERT INTO pagamenti.vendite_contabili_lotti (
      lotto_id,
      contabile_id,
      meta
    ) VALUES (
      p_lotto_id,
      v_contabile_id,
      jsonb_build_object('source','fn_get_or_create_vendite_contabile')
    )
    ON CONFLICT (lotto_id, contabile_id) DO NOTHING;
  END IF;

  RETURN v_contabile_id;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_or_create_vendite_contabile(p_centro_riscossione_id bigint, p_data_contabile date, p_data_registrazione date, p_ente_incasso_id bigint, p_lotto_id bigint, p_codice_stato_interno text, p_meta jsonb, p_origine character varying, p_emittente_fiscale_id bigint)
IS 'Recupera o crea la testata contabile per un centro, un canale e una giornata. ⭐ Su una distinta MANUALE la chiave di riuso comprende CHI STA LAVORANDO (D12-a): il raggruppamento «giornata + canale» non ha un referente nel mondo, il lotto di lavoro di una persona si'' — e con quello la contesa fra due operatori non esiste, quindi il lock che sarebbe servito a governarla non si costruisce. ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, L6): LA DISTINTA SA DI CHI E'' (D3). Parametro in coda p_emittente_fiscale_id (la PK, cio'' che backend e frontend conoscono; PK -> SR esplicito nel corpo); se manca si deriva dal LOTTO — chi passa un lotto sa gia'' di chi e'' la distinta, e il giro di massa di un admin globale in modalita'' «tutti gli emittenti» ha lotti di N aziende e una sessione che non risolve nessuno — con un ramo STRICT (lotto inesistente o fuori perimetro = TECNICO, non la sessione: la distinta del lotto di un altro nascerebbe di chi agisce, agganciata a un lotto altrui); poi la sede unica pagamenti.fn_get_emittente_distinta (canale / operatore in sessione / rifiuto parlante). L''emittente ENTRA NELLA CHIAVE DI RIUSO di entrambi i rami e nell''INSERT: la GENERATA senza lotto smette di raccogliere i fondi di tutti — e'' la decisione aperta del changeSet 20260822-20, chiusa nel verso «una per emittente» a costo zero, perche'' nessun percorso vivo la esercitava nell''altro. ⛔ `codice` non si passa: lo assegna il trigger a10_gen_codice sul registro DISTINTA dell''emittente (D5); il DEFAULT di colonna della rev 28-08 e'' caduto. 🔴 La firma e'' cambiata, quindi la funzione a otto parametri e'' stata eliminata e ricreata: una sostituzione con parametri diversi affianca un overload, e coi default le chiamate diventano ambigue. I due chiamanti vivi (backend pagamenti_repository, vendite.fn_sync_contabili_fondo_fattura) passano gli argomenti per nome e non cambiano. ⚠️ Rev 2026-08-22 (lotto 7, D15-e): sparisce p_compensazione_id — girato il verso del legame e'' l''ATTO a tenere l''id della sua contabile; l''unicita'' «una contabile per atto» vive su uq_sistemazioni_contabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
