{% include-markdown "it/dbzero/vendite/manual/fn_escludi_documento_da_giro.md" %}
# ⚙️ Funzione `fn_escludi_documento_da_giro`

```sql
CREATE FUNCTION fn_escludi_documento_da_giro(p_lotto_id bigint, p_gruppo_key text, p_motivo text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_escludi_documento_da_giro(p_lotto_id bigint, p_gruppo_key text, p_motivo text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: togliere UN documento dal giro di fatturazione, cosi' che
--        il lotto possa ripartire con quelli che restano.
-- Ritorna: un consuntivo di cio' che e' stato fatto, perche' il
--        chiamante deve poterlo raccontare all'operatore.
DECLARE
    v_motivi      jsonb;
    v_trascinati  jsonb;
    v_fatture     bigint[];
    v_fattura_id  vendite.fatture.id%TYPE;
    v_cancellate  integer := 0;
    v_riemesse    integer := 0;
    v_riaperti    integer := 0;
    v_esito_riga  RECORD;
BEGIN
    -- ── Guard di parametro ────────────────────────────────
    -- ⚠️ Il motivo vuoto NON e' una condizione di dominio: il
    --    frontend lo rende obbligatorio, quindi se arriva vuoto e'
    --    un chiamante rotto. Il CHECK di tabella lo rifiuterebbe
    --    comunque, ma con un messaggio che non parla all'operatore.
    IF COALESCE(btrim(p_motivo), '') = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_escludi_documento_da_giro', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_motivo'),
            NULL::uuid, 'p_motivo obbligatorio: un documento che esce senza motivo non e'' spiegabile');
    END IF;

    -- ── Le precondizioni: sede unica, non riscritte qui ───
    v_motivi := script.fn_check_documento_escludibile_da_giro(p_lotto_id, p_gruppo_key);
    -- ⭐ La coda del primo motivo sta in un posto solo: l'helper legge il
    --   codice da `v_motivi -> 0`, ne prende i `valori` per la frase, fonde il
    --   `dettaglio` nel contesto e ci mette sempre l'elenco COMPLETO dei motivi
    --   (il backend puo' mostrarli tutti anche se la frase ne nomina uno).
    -- ⚠️ L'IF e' sparito e NON e' fail-open: l'helper tace su un array vuoto,
    --   che e' esattamente la risposta «passa». Su un non-array resta rumoroso.
    -- 🔴 Rimessa qui dal 20260909-68: il -22, riscrivendo questa funzione per
    --   la riga di giornale, aveva ripristinato la coda a mano — e con essa il
    --   difetto che il -11 aveva chiuso (p_gruppo_key al posto dello stato del
    --   lotto nella frase di E_LOTTO_NON_PRE_FISCALE).
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'fn_escludi_documento_da_giro',
        v_motivi,
        NULL,          -- nessun campo da accendere: non e' un errore di form
        NULL::uuid,
        jsonb_build_object('lotto_id',   p_lotto_id,
                           'gruppo_key', p_gruppo_key,
                           'bersaglio',  jsonb_build_array(
                               jsonb_build_object('tipo', 'LOTTO',
                                                  'id', p_lotto_id::text))));

    -- ── Chi viene via insieme, PRIMA di cancellare ────────
    -- ⚠️ Dopo la cancellazione il legame non c'e' piu': letto qui
    --    dopo, direbbe «non trascina nessuno» su un lotto che ha
    --    appena riaperto tre documenti.
    v_trascinati := script.fn_gruppi_trascinati_da_uscita(p_lotto_id, p_gruppo_key);

    SELECT COALESCE(array_agg(DISTINCT r.fattura_id), ARRAY[]::bigint[])
      INTO v_fatture
      FROM script.vw_lotto_documento_righe r
     WHERE r.lotto_id = p_lotto_id
       AND r.gruppo_key = p_gruppo_key;

    -- ── Le bozze: si compone la primitiva, non se ne scrive una seconda
    -- ⭐ fn_elimina_fattura_da_lotto ha la sua check e la sua
    --    semantica gia' decise (RD-7: togliere = cancellare, le
    --    attivita' tornano NON_EMESSA). Qui non si duplica niente.
    -- ⚠️ Puo' essere piu' di una: le righe di un documento possono
    --    finire in bozze diverse.
    FOREACH v_fattura_id IN ARRAY v_fatture LOOP
        SELECT c.deleted_fatture, c.riemesse_attivita
          INTO STRICT v_esito_riga
          FROM vendite.fn_elimina_fattura_da_lotto(p_lotto_id, v_fattura_id) AS c;
        v_cancellate := v_cancellate + COALESCE(v_esito_riga.deleted_fatture, 0);
        v_riemesse   := v_riemesse   + COALESCE(v_esito_riga.riemesse_attivita, 0);
    END LOOP;

    -- ── Il documento esce ────────────────────────────────
    -- ⚠️ `uscita_quando` e `uscita_da` NON si scrivono qui: le
    --    deriva il trigger dalla GUC. Scriverle sarebbe una seconda
    --    sede della stessa regola.
    UPDATE vendite.fatturazione_lotti_esiti
       SET stato_esecuzione = 'ESCLUSO',
           uscita_motivo    = btrim(p_motivo)
     WHERE lotto_id = p_lotto_id
       AND gruppo_key = p_gruppo_key;

    -- ── ⭐ L'USCITA SI RACCONTA NEL GIORNALE ──────────────
    -- ⛔ Fino al 2026-09-09 l'uscita non lasciava NESSUNA riga di giornale: il
    --   timbro stava solo sulla riga dell'esito (uscita_motivo, uscita_quando,
    --   uscita_da). Chi guardava la storia del lotto non vedeva che un
    --   documento era uscito, ne' perche' — e l'esclusione e' una cosa che si
    --   fa apposta, con una motivazione che il CHECK di tabella rende
    --   obbligatoria. Un fatto voluto e motivato che il giornale non registra
    --   e' esattamente cio' che un giornale non deve fare.
    -- ⭐ Status `I`: e' un fatto, non un allarme. E la scelta non e' estetica —
    --   dal 2026-09-09 fn_log_pipeline_fase RIFIUTA `W` e `C` su un documento
    --   uscito, e accetta le `I` proprio perche' questa riga possa esistere.
    -- ⚠️ La `gruppo_key` c'e': senza, la riga sarebbe «del giro» e nessuno
    --   potrebbe piu' toglierla ne' capire di chi parla.
    -- ⚠️ Il motivo va NEL MESSAGGIO e non solo in meta: chi legge il giornale
    --   legge il messaggio, e un motivo che sta solo nel carico e' un motivo
    --   che nessuno vede.
    PERFORM vendite.fn_log_pipeline_fase(
        p_lotto_id,
        (SELECT l.stato_doc_fiscale_id FROM vendite.fatturazione_lotti l
          WHERE l.id = p_lotto_id),
        'USCITA_DAL_GIRO',
        'I'::char,
        format('Documento %s tolto dal giro: %s', p_gruppo_key, btrim(p_motivo)),
        jsonb_build_object('uscita_motivo', btrim(p_motivo)),
        NULL,
        p_gruppo_key);

    -- ── I trascinati tornano in coda ─────────────────────
    -- ⛔ `PENDING`, non `ESCLUSO`: non sono usciti da niente, e non
    --    `COMPLETED`, che direbbe «e' andato bene» su un documento
    --    che non ha piu' nessuna fattura.
    IF jsonb_array_length(v_trascinati) > 0 THEN
        UPDATE vendite.fatturazione_lotti_esiti e
           SET stato_esecuzione = 'PENDING',
               errore_codice    = NULL,
               errore_messaggio = NULL,
               errore_quando    = NULL
         WHERE e.lotto_id = p_lotto_id
           AND e.gruppo_key IN (
               SELECT jsonb_array_elements_text(v_trascinati))
           -- ⚠️ Un trascinato che fosse gia' uscito per conto suo
           --    NON si riapre: dal suo stato terminale non si torna
           --    indietro, e il guard rifiuterebbe la scrittura.
           AND e.stato_esecuzione <> 'ESCLUSO';
        GET DIAGNOSTICS v_riaperti = ROW_COUNT;
    END IF;

    RETURN jsonb_build_object(
        'lotto_id',            p_lotto_id,
        'gruppo_escluso',      p_gruppo_key,
        'fatture_cancellate',  v_cancellate,
        'attivita_riemesse',   v_riemesse,
        'gruppi_riaperti',     v_trascinati,
        'n_gruppi_riaperti',   v_riaperti);
END;
$function$

COMMENT ON FUNCTION vendite.fn_escludi_documento_da_giro(p_lotto_id bigint, p_gruppo_key text, p_motivo text)
IS 'Toglie UN documento rotto dal giro di fatturazione, cosi'' che il lotto possa ripartire con quelli che restano. Funzione MADRE: una sola SELECT, atomica per costruzione, SECURITY INVOKER (RLS e perimetro emittente restano applicati). ⭐ Non riscrive il predicato: CHIAMA script.fn_check_documento_escludibile_da_giro — la stessa da cui il frontend prende il motivo del pulsante spento — e solleva il codice del PRIMO motivo, perche'' l''ordine dell''array e'' il contratto. ⭐ Compone vendite.fn_elimina_fattura_da_lotto invece di riscriverne la semantica (RD-7: togliere = cancellare, le attivita'' tornano NON_EMESSA). ⭐ D-2b: se la bozza copre PIU'' documenti si cancella lo stesso e li TRASCINA — tornano da emettere, con l''esito riportato a PENDING e non a ESCLUSO (non sono usciti da niente) ne'' lasciato a COMPLETED (non hanno piu'' una fattura). Rifiutare su bozza condivisa lascerebbe bloccati anche i documenti di un''ALTRA bozza. ⚠️ I trascinati si leggono PRIMA di cancellare: dopo, il legame non esiste piu''. ⚠️ uscita_quando/uscita_da le deriva il trigger dalla GUC, non questa funzione. ⛔ Il perimetro (fatturazione_lotti_gruppi) non si tocca (D-1): il lotto ricorda di aver preso in carico anche il documento uscito. Brief: brief-db-uscita-documento-dal-giro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
