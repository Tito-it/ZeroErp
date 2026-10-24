{% include-markdown "it/dbzero/vendite/manual/fn_cleanup_fatture_by_ids.md" %}
# ⚙️ Funzione `fn_cleanup_fatture_by_ids`

```sql
CREATE FUNCTION fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
 RETURNS TABLE(deleted_fatture integer, deleted_righe integer, updated_attivita integer, riemesse_attivita integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_righe_ids         bigint[];
  v_af_ids            bigint[];
  v_deleted_fatture   integer := 0;
  v_deleted_righe     integer := 0;
  v_updated_attivita  integer := 0;
  v_riemesse_attivita integer := 0;
  v_motivi_rettifiche jsonb;
  v_motivi_plafond    jsonb;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Cleanup centralizzato di fatture/righe e ripristino
  --   COMPLETO di cio' che le fatture avevano consumato:
  --   attivita_fatturabili (sblocco) e commesse_attivita
  --   (ritorno in coda di emissione).
  --
  -- Regole:
  --   - ⛔ SI RIPRISTINA PRIMA DI CANCELLARE. L'ordine e' la
  --     correzione D-1' del 2026-08-26, non una preferenza di
  --     stile: il motivo sta nel blocco marcato qui sotto;
  --   - usa GUC di manutenzione per bypass guard fatturato
  --   - su ripristino: stato_esecuzione torna a NULL
  --   - D-N pezzo 3 (C-23): PRIMA di cancellare, restituisce
  --     all'ambito di compensazione l'arrotondamento che le
  --     fatture cancellate gli avevano lasciato
  --   - RD-4: il ritorno a NON_EMESSA delle commesse_attivita
  --     vive QUI e non nei chiamanti, perche' i chiamanti sono
  --     tre e la correttezza di ognuno dipende dal fatto che
  --     facciano la stessa cosa. Dal 2026-08-26 la coppia di
  --     scritture e' nella primitiva condivisa
  --     vendite.fn_libera_attivita_fatturabili, che serve anche
  --     il verbo di recupero «Riporta da emettere»
  -- =========================================================
  -- ⭐ rev 2026-09-12 — L'USCITA ANTICIPATA VALE SOLO SE NON C'E' NIENTE DA
  --    FARE: ne' fatture, ne' un giro da liberare. Prima usciva su «zero
  --    fatture» e basta: un lotto fermo PRIMA di generate_fatture_righe (un
  --    pull fallito, il 13338 del 12-09) non ha fatture, e il reset non
  --    liberava NESSUNA attivita' — nemmeno quelle lockate dalla select, non
  --    solo quelle emesse-non-lockate del ramo nuovo qui sotto. E' la causa
  --    sotto quella che il brief §10.4 vedeva. Con fatture assenti e un giro
  --    da liberare i passi sulle fatture girano su un insieme vuoto: innocui.
  p_fatture_ids := COALESCE(p_fatture_ids, ARRAY[]::bigint[]);
  IF array_length(p_fatture_ids, 1) IS NULL AND p_lock_batch_id IS NULL THEN
    RETURN QUERY SELECT 0, 0, 0, 0;
    RETURN;
  END IF;

  -- ══ GUARD FAIL-LOUD (2026-08-22) ═════════════════════════════
  -- ⛔ Una riga di fattura gia' RETTIFICATA non si cancella: su di
  --    essa e' gia' stato registrato un accredito, e
  --    `fattura_riga_rettificata_id` e' il SECONDO TETTO di quel
  --    accredito (20260818-27 punto 2) piu' il DatiFattureCollegate
  --    della TD04. Azzerare il legame per far passare la pulizia
  --    toglierebbe quel tetto proprio mentre le quantita' vengono
  --    ri-derivate: non si distrugge la prova per far riuscire
  --    l'operazione.
  --
  -- ⭐ PERCHE' QUI E NON SOLO NELLE fn_check_*. Le porte sono TRE, e
  --    le loro fn_check_* servono all'INTERFACCIA — spiegano prima
  --    del click. Questo e' l'unico punto che tutte e tre
  --    attraversano: e' il presidio della QUARTA porta, quella che
  --    nessuno ha ancora scritto. Il commento di questa funzione la
  --    chiedeva gia', a proposito di fatture_rettifiche.
  --
  -- ⚠️ Senza, il difetto non e' un errore di dominio ma una
  --    violazione di chiave esterna GREZZA (23503) dentro una
  --    funzione che i suoi chiamanti danno per infallibile —
  --    misurato il 2026-08-22 su test-riporta-lotto-a-draft-v1.
  --
  -- ⚠️ Il guard legge sotto ROW SECURITY (questa funzione e'
  --    SECURITY INVOKER). Un chiamante fuori perimetro potrebbe non
  --    vedere le righe che rettificano e passare di qui: in quel
  --    caso pero' NON si perde niente in silenzio, perche' e' la FK
  --    a fermare la cancellazione — si torna al 23503 di prima, che
  --    e' il comportamento attuale, non un peggioramento.
  v_motivi_rettifiche := script.fn_check_fatture_con_rettifiche(p_fatture_ids);

  IF jsonb_array_length(v_motivi_rettifiche) > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_cleanup_fatture_by_ids',
      'E_FATTURE_RIGHE_RETTIFICATE',
      jsonb_build_object(
        'detail',      'Righe di fattura gia rettificate: pulizia rifiutata',
        'fatture_ids', to_jsonb(p_fatture_ids),
        'motivi',      v_motivi_rettifiche),
      NULL::uuid,
      (v_motivi_rettifiche -> 0 ->> 'dettaglio'));
  END IF;

  -- ══ GUARD FAIL-LOUD (2026-10-04) — il plafond consumato ══════════
  -- ⛔ Una fattura che ha gia' consumato il plafond di un titolo IVA non
  --    si cancella: il registro dei movimenti e' append-only e le sue FK
  --    verso fattura e riga sono NO ACTION di proposito (un movimento e'
  --    un fatto contabile). Il consumo avviene PRIMA della numerazione,
  --    quindi il controllo sul numero delle porte non lo copre.
  -- ⭐ Qui per la stessa ragione del guard qui sopra: e' il punto che
  --    tutte le porte attraversano, la difesa della quarta che nessuno ha
  --    ancora scritto. Senza, il difetto e' un 23503 grezzo.
  -- Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §14 (strada A).
  v_motivi_plafond := script.fn_check_fatture_con_plafond_consumato(p_fatture_ids);

  IF jsonb_array_length(v_motivi_plafond) > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_cleanup_fatture_by_ids',
      'E_FATTURE_PLAFOND_CONSUMATO',
      jsonb_build_object(
        'detail',      'Fatture che hanno consumato plafond: pulizia rifiutata',
        'fatture_ids', to_jsonb(p_fatture_ids),
        'motivi',      v_motivi_plafond),
      NULL::uuid,
      (v_motivi_plafond -> 0 ->> 'dettaglio'));
  END IF;

  PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);

  -- ── D-N pezzo 3 / C-23: storno prima di ogni cancellazione ────
  -- In testa alla funzione perche' legge le fatture INTATTE: cosi'
  -- resta corretto qualunque passo venga aggiunto qui sotto.
  -- UPDATE e non upsert: se la riga d'ambito non c'e', quella
  -- fattura non ha mai contribuito e non c'e' niente da togliere —
  -- crearla con saldo negativo inventerebbe un debito.
  -- IS NOT DISTINCT FROM sulle due colonne nullable: con `=` le
  -- fatture senza modalita' (la maggioranza) non troverebbero il
  -- proprio ambito e non stornerebbero nulla, in silenzio.
  WITH storno AS (
    SELECT f.billing_account_id,
           f.utility_id,
           f.tipo_doc_fiscale_id,
           f.emittente_soggetto_ruolo_id,
           f.valuta_id,
           f.termine_pagamento_id,
           f.modalita_pagamento_id,
           SUM(COALESCE(f.arrotondamento_attuale, 0)) AS quota
      FROM vendite.fatture f
     WHERE f.id = ANY(p_fatture_ids)
       AND COALESCE(f.arrotondamento_attuale, 0) <> 0
     GROUP BY f.billing_account_id, f.utility_id, f.tipo_doc_fiscale_id,
              f.emittente_soggetto_ruolo_id, f.valuta_id,
              f.termine_pagamento_id, f.modalita_pagamento_id
  )
  UPDATE vendite.fatture_arrotondamenti_scope s
     SET saldo_arrotondamento = s.saldo_arrotondamento - st.quota
    FROM storno st
   WHERE s.billing_account_id          = st.billing_account_id
     AND s.utility_id                  = st.utility_id
     AND s.tipo_doc_fiscale_id         = st.tipo_doc_fiscale_id
     AND s.emittente_soggetto_ruolo_id = st.emittente_soggetto_ruolo_id
     AND s.valuta_id                   = st.valuta_id
     AND s.termine_pagamento_id  IS NOT DISTINCT FROM st.termine_pagamento_id
     AND s.modalita_pagamento_id IS NOT DISTINCT FROM st.modalita_pagamento_id;

  PERFORM vendite.fn_reset_fondi_fattura(f_id)
    FROM unnest(p_fatture_ids) AS f_id;

  SELECT array_agg(r.id)
    INTO v_righe_ids
    FROM vendite.fatture_righe r
   WHERE r.fattura_id = ANY(p_fatture_ids);

  IF v_righe_ids IS NULL THEN
    v_righe_ids := ARRAY[]::bigint[];
  END IF;

  -- ══ RIPRISTINO PRIMA DELLA CANCELLAZIONE (D-1', 2026-08-26) ══
  -- ⛔ L'ORDINE E' LA CORREZIONE, non una preferenza di stile.
  --    `fk_attivita_fatturabili_fattura_riga` e' ON DELETE SET
  --    NULL e NOT DEFERRABLE: l'azione referenziale scatta a
  --    FINE ISTRUZIONE del DELETE sulle righe, qui sotto. Fino al
  --    2026-08-26 questo ripristino stava DOPO quel DELETE,
  --    quindi girava quando `af.fattura_riga_id` era gia' NULL e
  --    il predicato non corrispondeva piu' a nessuna riga.
  -- ⛔ Il danno era DOPPIO: dallo stesso predicato nasceva anche
  --    l'insieme delle commesse_attivita da riportare in coda.
  --    Restavano sia `fatturato = true` (e
  --    fn_select_attivita_fatturabili non la seleziona mai piu')
  --    sia `stato_emissione = 'EMESSA'` (e
  --    fn_emit_attivita_fatturabili_da_commessa non la ri-emette
  --    mai piu'). Due porte chiuse invece di una, e in silenzio:
  --    la funzione tornava updated_attivita = 0, e nessuno legge
  --    quel contatore come un'anomalia.
  -- ⭐ Riordinando, il legame si usa MENTRE E' ANCORA VIVO e la
  --    ON DELETE SET NULL diventa INERTE: quando il DELETE
  --    arriva non c'e' piu' nessun puntatore verso le righe che
  --    sta cancellando.
  -- ⚠️ CHI AGGIUNGE UN PASSO non lo metta fra questo blocco e i
  --    DELETE: il ripristino deve restare a monte di qualunque
  --    cosa tocchi vendite.fatture_righe. E' l'unica cosa che
  --    tiene in piedi il predicato.
  -- ⚠️ La GUC di manutenzione e' impostata sopra, e da qui in
  --    avanti serve per QUESTA scrittura: gira mentre
  --    `fattura_riga_id` e' ancora valorizzato, cioe' proprio
  --    dove trgfn_attivita_fatturabili_guard_fatturato blocca.
  --    Prima copriva l'UPDATE IMPLICITA della chiave esterna.
  --
  -- ⚠️ Il primo ramo prende TUTTE le attivita' del batch: e'
  --    voluto nel reset globale (libera anche quelle agganciate
  --    al lotto che non sono mai diventate riga) ed e' il motivo
  --    per cui il reset PER-FATTURA deve passare p_lock_batch_id
  --    NULL (C-22).
  -- ⭐ E il predicato si valuta UNA VOLTA SOLA. Prima era
  --    ripetuto identico in due punti «di proposito, perche' se
  --    divergessero si sbloccherebbe un insieme e se ne
  --    rimetterebbe in coda un altro»: quel rischio ora sparisce
  --    per costruzione, l'insieme e' uno ed e' un array di id.
  -- ⭐ rev 2026-09-12 — IL TERZO RAMO: le attivita' EMESSE dal giro e NON
  --    ANCORA LOCKATE. Fra il pull (che scrive `emit_batch_id`) e la select
  --    (che scrive `lock_batch_id`) c'e' una finestra: un giro che cade li',
  --    o un select saltato, lascia attivita' col marchio del lotto e nessun
  --    lucchetto. Il ramo del lucchetto non le vedeva, e la riga di commessa
  --    restava EMESSA con un'attivita' libera: i due livelli divergenti che
  --    fn_libera_attivita_fatturabili descrive, e che nessun giro riprendeva
  --    (il pull la vede EMESSA, la select di un lotto nuovo non trova il suo
  --    marchio). Verificato il 12-09 sul lotto 13338.
  --    «Agganciate al lotto» — la frase del commento qui sopra — vuol dire
  --    anche questo: l'aggancio nasce col marchio, prima del lucchetto.
  -- ⚠️ `lock_batch_id IS NULL`: un lucchetto ALTRUI non si tocca (se e' il
  --    mio, e' gia' nel primo ramo). `fattura_riga_id IS NULL`: una riga gia'
  --    in fattura passa dal secondo ramo, se la fattura e' nel perimetro, e
  --    altrimenti non si libera da qui (`fatturato` e' generata da questo).
  -- ⚠️ Vale solo col marchio del giro (p_lock_batch_id NOT NULL): il reset
  --    PER-FATTURA passa NULL (C-22) e non tocca questo ramo.
  SELECT array_agg(af.id)
    INTO v_af_ids
    FROM vendite.attivita_fatturabili af
   WHERE (p_lock_batch_id IS NOT NULL AND af.lock_batch_id = p_lock_batch_id)
      OR af.fattura_riga_id = ANY(v_righe_ids)
      OR (p_lock_batch_id IS NOT NULL
          AND af.emit_batch_id = p_lock_batch_id
          AND af.lock_batch_id IS NULL
          AND af.fattura_riga_id IS NULL);

  IF v_af_ids IS NULL THEN
    v_af_ids := ARRAY[]::bigint[];
  END IF;

  -- 🔴 RD-4 — il livello che mancava, e che ora vive nella
  -- primitiva condivisa (20260826-24): «attivita' liberata» e
  -- «commessa_attivita di nuovo NON_EMESSA» sono UN fatto solo su
  -- due livelli, e il verbo di recupero «Riporta da emettere»
  -- consuma la stessa primitiva — cosi' la duplicazione non
  -- esiste mai.
  SELECT l.updated_attivita, l.riemesse_attivita
    INTO v_updated_attivita, v_riemesse_attivita
    FROM vendite.fn_libera_attivita_fatturabili(v_af_ids) AS l;

  DELETE FROM vendite.note
   WHERE target_tipo = 'FATTURA'
     AND target_riga_id = ANY(v_righe_ids);

  DELETE FROM vendite.note
   WHERE target_tipo = 'FATTURA'
     AND target_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatture_riepiloghi_iva
   WHERE fattura_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatture_righe
   WHERE fattura_id = ANY(p_fatture_ids);
  GET DIAGNOSTICS v_deleted_righe = ROW_COUNT;

  DELETE FROM vendite.fatture_log
   WHERE fattura_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatturazione_lotti_fatture
   WHERE fattura_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatture
   WHERE id = ANY(p_fatture_ids);
  GET DIAGNOSTICS v_deleted_fatture = ROW_COUNT;

  RETURN QUERY
  SELECT v_deleted_fatture, v_deleted_righe, v_updated_attivita, v_riemesse_attivita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
IS 'Pulizia centralizzata delle fatture e ripristino COMPLETO di cio'' che avevano consumato. Storna dall''ambito di compensazione l''arrotondamento delle fatture cancellate (D-N pezzo 3 / C-23) PRIMA di toccarle; azzera i fondi; RIPRISTINA le attivita_fatturabili (sblocco) e le commesse_attivita collegate (ritorno a stato_emissione = NON_EMESSA, dal 2026-08-03 RD-4); e SOLO DOPO cancella note, riepiloghi IVA, righe, log, collegamento al lotto e testate. ⚠️ Il ritorno a NON_EMESSA vive QUI e non nei chiamanti: sono TRE (fn_annulla_lotto_da_draft, fn_elimina_fattura_da_lotto, fn_riporta_lotto_a_draft) e la correttezza di ognuno dipende dal fatto che facciano la stessa cosa — senza, le attivita'' restano emesse senza fattura e nessun giro futuro le riprende. ⛔ L''ORDINE DEI PASSI E'' PORTANTE, dal 2026-08-26 (D-1''): il ripristino avviene PRIMA di qualunque cancellazione. fk_attivita_fatturabili_fattura_riga e'' ON DELETE SET NULL e NOT DEFERRABLE, quindi l''azione referenziale scatta a fine istruzione del DELETE sulle righe: con il ripristino a valle il predicato girava quando fattura_riga_id era gia'' NULL e non corrispondeva piu'' a nessuna riga, e il danno era DOPPIO perche'' dallo stesso predicato nasceva l''insieme delle commesse_attivita. L''attivita'' restava fatturata senza fattura e la sua riga di commessa su EMESSA, in silenzio: updated_attivita tornava 0, e nessuno legge quel contatore come un''anomalia. ⭐ Riordinando, il legame si usa mentre e'' ancora vivo e la SET NULL diventa INERTE — quando il DELETE arriva non c''e'' piu'' nessun puntatore verso le righe che sta cancellando. ⚠️ Chi aggiunge un passo NON lo metta fra il ripristino e i DELETE. ⭐ E il predicato si valuta UNA volta sola: prima era ripetuto identico in due punti «di proposito», e bastava che i due divergessero per sbloccare un insieme e rimetterne in coda un altro. ⭐ La coppia di scritture del ripristino vive in vendite.fn_libera_attivita_fatturabili, consumata anche dal verbo di recupero «Riporta da emettere»: la duplicazione non esiste mai. ⚠️ Il ramo su p_lock_batch_id prende TUTTE le attivita'' del batch: corretto nel reset globale, ed e'' il motivo per cui il reset per-fattura deve passare NULL (C-22). ⭐ NON cancella da vendite.fatture_rettifiche, e NON e'' una dimenticanza (domanda del backend, 2026-08-18, brief note-credito P-2). La proiezione del legame documentale delle note di credito la scrive il task popola_fatture_rettifiche, che gira DOPO numera_fatture: esiste quindi solo su documenti NUMERATI. E un documento numerato non e'' raggiungibile da nessuna delle tre porte di reset, perche'' tutte e tre lo rifiutano con un controllo ESPLICITO sul numero — fn_check_fattura_eliminabile_da_lotto motivo 4 (E_FATTURA_GIA_NUMERATA), fn_check_lotto_riportabile_a_draft motivo 3 e fn_check_lotto_annullabile motivo 3 (E_LOTTO_FATTURE_NUMERATE, aggiunto il 2026-08-18 proprio per chiudere l''ultima che si affidava al solo stato). ⚠️ La garanzia sta in quelle CONDIZIONI, non nei nomi delle funzioni: l''argomento «sono tutte *_da_draft» era vero e ha smesso di esserlo il 2026-08-04, quando fn_elimina_fattura_da_lotto_draft e'' stata rinominata e il suo perimetro allargato al pre-fiscale (RD-7). ⚠️ Se un giorno una porta di reset ammettesse un documento numerato, questa funzione dovrebbe cancellare anche la coppia in fatture_rettifiche: fk_fatture_ret_fattura NON e'' ON DELETE CASCADE, quindi il reset sbatterebbe su una violazione di chiave esterna grezza dentro una funzione che i suoi chiamanti danno per infallibile. Piano: brief-db-lavoro-che-non-torna-indietro, L1. ⭐ rev 2026-10-04 (brief-db-bom-flag-quantita-e-kit-in-fattura §14, strada A): secondo guard fail-loud accanto a quello delle rettifiche — una fattura che ha gia'' consumato plafond (script.fn_check_fatture_con_plafond_consumato) non si cancella, E_FATTURE_PLAFOND_CONSUMATO invece del 23503 grezzo sulle FK NO ACTION del registro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
