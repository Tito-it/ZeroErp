{% include-markdown "it/dbzero/vendite/manual/fn_annulla_commessa_attivita.md" %}
# ⚙️ Funzione `fn_annulla_commessa_attivita`

```sql
CREATE FUNCTION fn_annulla_commessa_attivita(p_commessa_attivita_id bigint, p_motivo text)
```

**Definizione completa:**

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
  v_sorgente_uid     vendite.commesse_attivita.sorgente_uid%TYPE;
  v_prezzo_snapshot  vendite.commesse_attivita.prezzo_snapshot%TYPE;
  v_tipo_movimento   vendite.commesse_attivita.tipo_movimento%TYPE;
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
         ca.sorgente_tipo_id, ca.sorgente_uid, ca.prezzo_snapshot,
         ca.tipo_movimento
    INTO v_commessa_id, v_segment_key, v_stato_emissione,
         v_sorgente_tipo_id, v_sorgente_uid, v_prezzo_snapshot,
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
  --    ANNULLATA e' per costruzione manuale (nessun altro
  --    percorso scrive quel valore), quindi non toglie mai il
  --    posto a una diagnosi migliore. Codice DEDICATO: dire
  --    "gia' emessa" a chi ha riannullato una riga e' falso e lo
  --    manda a cercare una fattura che non esiste.
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
  -- 4. Guard "e' manuale" = SOURCELESS. Prima di "gia' emessa"
  --    perche' e' l'identita' della riga, non una condizione:
  --    per una riga da push il rimedio e' SEMPRE a monte, sul
  --    documento, sia essa emessa o no.
  --    NOTA: fn_upsert_commessa_attivita ha p_sorgente_tipo_id
  --    DEFAULT NULL, quindi "sourceless" e' garantito dalla
  --    disciplina di chi chiama e non dalla struttura -> questo
  --    guard e' necessario e non va dato per implicito.
  -- ---------------------------------------------------------
  IF v_sorgente_tipo_id IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_annulla_commessa_attivita','E_RIGA_COMMESSA_NON_MANUALE',
      jsonb_build_object('commessa_attivita_id', p_commessa_attivita_id,
                         'commessa_id', v_commessa_id,
                         'segment_key', v_segment_key,
                         'sorgente_tipo_id', v_sorgente_tipo_id,
                         'sorgente_uid', v_sorgente_uid),
      NULL::uuid, p_commessa_attivita_id::text, v_segment_key,
      COALESCE(v_sorgente_uid,'?'));
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
IS 'Madre DB annullamento riga MANUALE di commessa (brief-annullamento-righe-manuali-commessa §4). Porta stato_emissione a ANNULLATA e scrive vendite.commesse_attivita_log (evento RIGA_MANUALE_ANNULLATA con motivo, stato_precedente, prezzo_snapshot, tipo_movimento): due scritture, una unita'' atomica (linee-guida-sql §5b). NON cancella: la riga resta con importo e storia, smette solo di essere eleggibile -- ANNULLATA e'' gia'' filtrato da fn_emit_attivita_fatturabili_da_commessa, fn_list_commesse_emittibili, fn_list_emittibili_lane, fn_approva_commessa_attivita (=> nessun ripristino), vw_dash_competenza_attivita e vw_dash_fatturazione_commesse. Nessuna colonna nuova. PERIMETRO: righe SOURCELESS (sorgente_tipo_id IS NULL) e NON_EMESSA; il discriminante e'' la sorgente, non tipo_movimento=ONERE (natura, non origine) ne'' il prefisso MAN: della segment_key (convenzione, non contratto). ORDINE GUARD: gia''-annullata (564) -> non-manuale (565) -> gia''-emessa (566); "non manuale" precede "gia'' emessa" perche'' e'' l''identita'' della riga e per una riga da push il rimedio e'' sempre a monte sul documento. Motivo obbligatorio (567): l''annullamento e'' irreversibile e il log e'' l''unica traccia del perche''. SELECT ... FOR UPDATE sulla riga: senza, due annullamenti concorrenti scriverebbero due eventi per un solo annullamento. SECURITY INVOKER: RLS e scope emittente restano applicati. Presidio permessi (carica_voce_manuale) sul BE. Ritorna commessa_attivita_id. rev 2026-07-28.';
```

---
{% include-markdown "signature-core.md" %}
