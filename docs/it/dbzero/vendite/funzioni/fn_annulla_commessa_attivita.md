{% include-markdown "it/dbzero/vendite/manual/fn_annulla_commessa_attivita.md" %}
# ⚙️ Funzione `fn_annulla_commessa_attivita`

```sql
CREATE FUNCTION fn_annulla_commessa_attivita(p_commessa_attivita_id bigint, p_motivo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_commessa_attivita(p_commessa_attivita_id bigint, p_motivo text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_motivo           text;
  v_commessa_id      vendite.commesse_attivita.commessa_id%TYPE;
  v_segment_key      vendite.commesse_attivita.segment_key%TYPE;
  v_stato_emissione  vendite.commesse_attivita.stato_emissione%TYPE;
  v_sorgente_tipo_id vendite.commesse_attivita.sorgente_tipo_id%TYPE;
  v_sorgente_id      vendite.commesse_attivita.sorgente_id%TYPE;
  v_sorgente_uid     vendite.commesse_attivita.sorgente_uid%TYPE;
  v_prezzo_snapshot  vendite.commesse_attivita.prezzo_snapshot%TYPE;
  v_tipo_movimento   vendite.commesse_attivita.tipo_movimento%TYPE;
  -- ⭐ D-6: il NUMERO leggibile del documento sorgente. text e non %TYPE:
  --   non riflette una colonna, e' cio' che il resolver COMPONE — e su
  --   sorgenti diverse arriva da colonne diverse (`numero` o `codice`,
  --   secondo config.sorgenti.label_selector).
  v_sorgente_doc_numero text;
BEGIN
  -- Scopo: madre DB dell'annullamento di una riga MANUALE di
  -- commessa. Perimetro: una sola riga, due scritture in una
  -- unita' atomica (UPDATE stato + INSERT evento di log).
  -- Risultato: l'id della riga annullata. Non cancella nulla:
  -- la riga resta, con importo e storia, e smette solo di essere
  -- eleggibile alla fatturazione (tutte le porte filtrano gia'
  -- ANNULLATA). Il presidio permessi vive sul BE.

  -- ---------------------------------------------------------
  -- 1. Guard parametri (AGENTS.md: NULL o <=0 -> errore parlante,
  --    mai normalizzazione silenziosa).
  -- ---------------------------------------------------------
  IF p_commessa_attivita_id IS NULL OR p_commessa_attivita_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','commessa_attivita_id',
                         'valore',p_commessa_attivita_id),
      NULL::uuid, 'commessa_attivita_id obbligatorio (>0)');
  END IF;

  -- Motivo: normalizzato con btrim, poi obbligatorio non vuoto.
  -- L'annullamento e' irreversibile e l'unica traccia del PERCHE'
  -- e' l'evento di log: senza motivo resta il fatto senza la
  -- ragione, e a mesi di distanza un importo sparito senza
  -- spiegazione e' indistinguibile da un errore.
  v_motivo := btrim(COALESCE(p_motivo, ''));
  IF v_motivo = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id),
      NULL::uuid, p_commessa_attivita_id::text);
  END IF;

  -- ---------------------------------------------------------
  -- 2. Caricare la riga SOTTO LOCK.
  --    FOR UPDATE serializza i concorrenti sulla stessa riga:
  --    due annullamenti simultanei scriverebbero altrimenti due
  --    eventi di log per un solo annullamento, e una emissione
  --    concorrente darebbe esito non deterministico. Sotto READ
  --    COMMITTED chi aspetta ri-legge la versione aggiornata e
  --    cade sul guard corretto (gia' annullata / gia' emessa).
  -- ---------------------------------------------------------
  SELECT ca.commessa_id, ca.segment_key, ca.stato_emissione,
         ca.sorgente_tipo_id, ca.sorgente_id, ca.sorgente_uid, ca.prezzo_snapshot,
         ca.tipo_movimento
    INTO v_commessa_id, v_segment_key, v_stato_emissione,
         v_sorgente_tipo_id, v_sorgente_id, v_sorgente_uid, v_prezzo_snapshot,
         v_tipo_movimento
    FROM vendite.commesse_attivita ca
   WHERE ca.id = p_commessa_attivita_id
   FOR UPDATE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_VALORE_MANCANTE',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id),
      NULL::uuid, concat('commessa_attivita_id ', p_commessa_attivita_id));
  END IF;

  -- ---------------------------------------------------------
  -- 3. Guard "gia' annullata". PRIMO della catena: una riga
  --    ANNULLATA e' per costruzione gia' passata da qui, quindi
  --    non toglie mai il posto a una diagnosi migliore. Codice
  --    DEDICATO: dire "gia' emessa" a chi ha riannullato una riga
  --    e' falso e lo manda a cercare una fattura che non esiste.
  -- ---------------------------------------------------------
  IF v_stato_emissione = 'ANNULLATA' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_RIGA_COMMESSA_GIA_ANNULLATA',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id,
                         'commessa_id', v_commessa_id,
                         'segment_key', v_segment_key),
      NULL::uuid, p_commessa_attivita_id::text, v_segment_key);
  END IF;

  -- ---------------------------------------------------------
  -- 4. Guard ORIGINE: la riga nasce da un documento?
  --    Prima di "gia' emessa" perche' e' l'identita' della riga,
  --    non una condizione: per una riga da push il rimedio e'
  --    SEMPRE a monte, sul documento, sia essa emessa o no.
  --    NOTA: fn_upsert_commessa_attivita ha p_sorgente_tipo_id
  --    DEFAULT NULL, quindi "sourceless" e' garantito dalla
  --    disciplina di chi chiama e non dalla struttura -> questo
  --    guard e' necessario e non va dato per implicito.
  -- ---------------------------------------------------------
  IF v_sorgente_tipo_id IS NOT NULL THEN
    -- ⭐ D-6 (2026-08-26): IL DOCUMENTO SI NOMINA, NON SI FA CERCARE.
    --   Il terzo %s del messaggio riceveva `sorgente_uid`, cioe' un UUID:
    --   diceva «nasce dal documento sorgente
    --   0198f3a2-...» a una persona, che con quel valore non puo' fare
    --   niente. Il resolver unico lo traduce nel numero che l'operatore
    --   legge davvero (ORD0000227, DDT0010839).
    -- ⚠️ Il resolver NON solleva e restituisce SEMPRE una riga, anche tutta
    --   a NULL: e' SECURITY INVOKER, quindi su un documento fuori perimetro
    --   il numero non c'e'. Il COALESCE ripiega sull'uid — un messaggio meno
    --   utile, mai un messaggio mancante.
    -- ⛔ Un errore non deve poter morire dentro la sua diagnostica: se un
    --   giorno il resolver cambiasse idea e sollevasse, il rifiuto del guard
    --   diventerebbe un 500 e la regola sparirebbe. Il contratto su cui
    --   ci si appoggia sta nel suo COMMENT: non solleva, e una riga la
    --   restituisce sempre — anche tutta a NULL.
    SELECT ref.documento_numero
      INTO v_sorgente_doc_numero
      FROM script.fn_sorgente_documento(
             v_sorgente_tipo_id, v_sorgente_id, v_sorgente_uid) ref;

    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_RIGA_COMMESSA_NON_MANUALE',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id,
                         'commessa_id', v_commessa_id,
                         'segment_key', v_segment_key,
                         'sorgente_tipo_id', v_sorgente_tipo_id,
                         'sorgente_id', v_sorgente_id,
                         'sorgente_uid', v_sorgente_uid,
                         -- ℹ️ Il numero entra anche nel diario: chi indaga su
                         --   dbops.error_log a mesi di distanza non ha piu' il
                         --   messaggio composto, ha il context.
                         'sorgente_documento_numero', v_sorgente_doc_numero),
      NULL::uuid, p_commessa_attivita_id::text, v_segment_key,
      COALESCE(v_sorgente_doc_numero, v_sorgente_id::text, v_sorgente_uid::text, '?'));
  END IF;

  -- ---------------------------------------------------------
  -- 4-bis. ⭐ Guard NATURA (2026-08-20, segnalazione BE).
  --    ORIGINE e NATURA sono DUE FATTI DIVERSI, e fino al
  --    2026-08-18 coincidevano solo per assenza: sourceless
  --    voleva dire ONERE perche' nessuno scriveva RETTIFICA.
  --    Da quando fn_accredita_riga_reso ne scrive — e le scrive
  --    sourceless per progetto — il solo guard di origine lascia
  --    passare una riga di NOTA DI CREDITO.
  --    ⚠️ E il danno non e' un errore: l'annullo riesce, il ponte
  --    in vendite.resi_righe_accrediti SOPRAVVIVE, la quota resta
  --    accreditata e la riga del reso NON torna in coda. Credito
  --    al cliente, nessun documento, nessun segnale.
  --    ⭐ WHITELIST e non blacklist: si ammette ONERE. Un quarto
  --    movimento manuale dovra' essere ammesso esplicitamente,
  --    non ereditare in silenzio un verbo distruttivo.
  --    Sta PRIMA di "gia' emessa" perche' e' identita', non
  --    condizione: per una rettifica il rimedio e' «annulla
  --    l'accredito» sia da NON_EMESSA sia da EMESSA.
  -- ---------------------------------------------------------
  IF v_tipo_movimento IS DISTINCT FROM 'ONERE' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id,
                         'commessa_id', v_commessa_id,
                         'segment_key', v_segment_key,
                         'tipo_movimento', v_tipo_movimento),
      NULL::uuid, p_commessa_attivita_id::text, v_segment_key,
      COALESCE(v_tipo_movimento::text,'?'));
  END IF;

  -- ---------------------------------------------------------
  -- 5. Guard "non emessa". Scritto come <> 'NON_EMESSA' e non
  --    = 'EMESSA': se domani il CHECK ammettesse un quarto stato,
  --    il default resta il rifiuto (fail-closed).
  --    Una riga emessa ha gia' generato la sua attivita_fatturabili:
  --    annullare qui non la toglierebbe dalla catena, lascerebbe
  --    un'AF orfana in viaggio verso la fattura.
  -- ---------------------------------------------------------
  IF v_stato_emissione <> 'NON_EMESSA' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_RIGA_COMMESSA_GIA_EMESSA',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id,
                         'commessa_id', v_commessa_id,
                         'segment_key', v_segment_key,
                         'stato_emissione', v_stato_emissione),
      NULL::uuid, p_commessa_attivita_id::text, v_segment_key,
      v_stato_emissione::text);
  END IF;

  -- ---------------------------------------------------------
  -- 6. L'annullamento. stato_approvazione resta com'e': sono due
  --    assi distinti con CHECK separati, e una riga annullata
  --    conserva la memoria di essere stata approvata.
  --    data_update/user_update/tx_id/storico: li mettono i
  --    trigger della tabella (la madre fa solo dominio).
  -- ---------------------------------------------------------
  UPDATE vendite.commesse_attivita ca
     SET stato_emissione = 'ANNULLATA'
   WHERE ca.id = p_commessa_attivita_id;

  -- ---------------------------------------------------------
  -- 7. Audit. Secondo evento di commesse_attivita_log dopo
  --    ONERE_AGGIUNTO. La colonna evento non ha CHECK ne'
  --    tabella-vocabolario: nessun seed da estendere.
  --    prezzo_snapshot e tipo_movimento restano nel dettaglio
  --    perche' l'informazione utile a chi indaga e' QUANTO
  --    valore e' uscito dal giro, non solo che e' uscito.
  -- ---------------------------------------------------------
  INSERT INTO vendite.commesse_attivita_log (commessa_attivita_id, evento, dettaglio)
  VALUES (
    p_commessa_attivita_id,
    'RIGA_MANUALE_ANNULLATA',
    jsonb_build_object(
      'motivo',            v_motivo,
      'stato_precedente',  v_stato_emissione,
      'prezzo_snapshot',   v_prezzo_snapshot,
      'tipo_movimento',    v_tipo_movimento,
      'segment_key',       v_segment_key,
      'commessa_id',       v_commessa_id
    )
  );

  RETURN p_commessa_attivita_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_annulla_commessa_attivita(p_commessa_attivita_id bigint, p_motivo text)
IS 'Madre DB annullamento riga MANUALE di commessa (brief-annullamento-righe-manuali-commessa §4). Porta stato_emissione a ANNULLATA e scrive vendite.commesse_attivita_log (evento RIGA_MANUALE_ANNULLATA con motivo, stato_precedente, prezzo_snapshot, tipo_movimento): due scritture, una unita'' atomica (linee-guida-sql §5b). NON cancella: la riga resta con importo e storia, smette solo di essere eleggibile -- ANNULLATA e'' gia'' filtrato da fn_emit_attivita_fatturabili_da_commessa, fn_list_commesse_emittibili, fn_list_emittibili_lane, fn_approva_commessa_attivita (=> nessun ripristino), vw_dash_competenza_attivita e vw_dash_fatturazione_commesse. ⭐ PERIMETRO, rev 2026-08-20 (segnalazione BE): righe SOURCELESS **E** tipo_movimento = ''ONERE'', e NON_EMESSA. Fino a quel giorno il discriminante era la sola ORIGINE, con la nota esplicita «non tipo_movimento = ONERE (natura, non origine)»: era corretta quando fu scritta, perche'' sourceless equivaleva a ONERE — nessuno scriveva righe RETTIFICA. Dal 2026-08-18 vendite.fn_accredita_riga_reso ne scrive, e le scrive SOURCELESS per progetto: l''equazione si e'' rotta e una riga di NOTA DI CREDITO passava il guard. 🔴 Il danno non era un errore: l''annullo riusciva, il ponte in vendite.resi_righe_accrediti sopravviveva, fn_resi_riga_accreditato_partita continuava a dichiarare la quota accreditata e la riga del reso non tornava in coda — credito al cliente, nessun documento, nessun segnale. Stessa famiglia del buco su fn_annulla_reso (E_RESO_ANNULLO_CON_ACCREDITO), da un''altra porta. ⭐ ORIGINE e NATURA sono due fatti distinti e si controllano ENTRAMBI: il CHECK chk_commesse_attivita_sorgente_pair garantisce la coerenza della coppia sorgente_*, non che origine e natura restino allineate. WHITELIST fail-closed (si ammette ONERE, non si vieta RETTIFICA): un quarto movimento manuale andra'' ammesso esplicitamente. ORDINE GUARD: gia''-annullata (564) -> origine (565) -> NATURA (935) -> gia''-emessa (566); la natura precede lo stato perche'' e'' identita'' e non condizione — per una rettifica il rimedio e'' «annulla l''accredito» sia da NON_EMESSA sia da EMESSA, e dire «gia'' emessa» manderebbe a cercare una nota di credito che non c''e''. Il codice 935 e'' UNO e non due: un secondo codice generico guarderebbe un ramo oggi irraggiungibile (il CHECK ammette tre valori, due sono gestiti), e un ramo morto sembra coperto senza esserlo. Motivo obbligatorio (567). SELECT ... FOR UPDATE sulla riga. SECURITY INVOKER. Presidio permessi (carica_voce_manuale) sul BE. Ritorna commessa_attivita_id. ⭐ Rev 2026-08-26 (D-6, brief-db-residui-competenza-dimensione-e-chiave): il guard 4 NOMINA il documento invece di lasciarlo cercare. Il terzo segnaposto di E_RIGA_COMMESSA_NON_MANUALE riceveva sorgente_uid, cioe'' un UUID, e la `soluzione` a catalogo chiudeva con una query SQL da eseguire a mano: si diceva a una persona di andare a cercare un documento dandogli una chiave tecnica. Adesso arriva da vendite.fn_get_sorgente_documento_ref — lo STESSO resolver che alimenta la colonna «Origine» della lista attivita'' — quindi a video si legge ORD0000227, non un UUID, e le due superfici non possono divergere perche'' la risoluzione e'' una sola. ⚠️ Il resolver e'' SECURITY INVOKER e non solleva mai: su un documento fuori perimetro il numero e'' NULL e il COALESCE ripiega sull''uid — un messaggio meno utile, mai un messaggio mancante, e mai un 500 al posto di un rifiuto di dominio. ⭐ E la `soluzione` cambia perche'' e'' cambiato il MONDO, non la frase: da L7b (20260826-34..36) chiudere il documento sorgente RITIRA da se'' le righe non ancora emesse, quindi «il rimedio e'' a monte» adesso e'' una istruzione eseguibile invece di una direzione. rev 2026-08-26.';
```

</div>

---
{% include-markdown "signature-core.md" %}
