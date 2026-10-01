{% include-markdown "it/dbzero/script/manual/fn_get_stato_testata_documento.md" %}
# ⚙️ Funzione `fn_get_stato_testata_documento`

```sql
CREATE FUNCTION fn_get_stato_testata_documento(p_documento text, p_testata_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_stato_testata_documento(p_documento text, p_testata_id bigint)
 RETURNS TABLE(stato text, etichetta text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
-- ⚠️ Tipi nudi DICHIARATI (rev 2026-09-28): p_documento e' un selettore senza
--   colonna-vocabolario; p_testata_id e lo stato in uscita sono POLIMORFI —
--   l'id di cinque testate diverse, il codice_interno di cinque vocabolari
--   diversi (e lo stato di una mail) — quindi non c'e' UNA colonna da ancorare.
BEGIN
  -- =========================================================
  -- Scopo:
  --   Rispondere a «la testata esiste ancora, e in che stato e'?»
  --   SENZA passare dalla RLS delle testate.
  --
  -- Contratto:
  --   - zero righe  -> la testata NON esiste (cancellata, o mai
  --     esistita). Il chiamante deve trattarlo come CASCADE.
  --   - una riga    -> stato = codice_interno, etichetta = frase
  --     per l'operatore.
  --
  -- ⚠️ Lo stato e' NOT NULL su tutte le testate e la FK verso
  --    config.stati_doc_* garantisce la riga di stato: se la
  --    testata c'e', `stato` non e' mai NULL. Il chiamante puo'
  --    quindi usare l'assenza di riga come segnale, e non deve
  --    distinguere un NULL da un vuoto.
  --    (EMAIL_BOZZA: `stato` e' NOT NULL sulla tabella stessa,
  --    ed e' gia' il codice — il contratto regge uguale.)
  --
  -- Chi lo chiama (2026-09-25):
  --   - vendite.trgfn_doc_righe_lock_fuori_bozza (il guard
  --     generico: righe di documento solo in bozza);
  --   - vendite.trgfn_dlt_block_ordrig_ddtrig (l'etichetta per i
  --     messaggi sui legami a valle);
  --   - config.trgfn_email_allegato_guard_solo_bozza (gli
  --     allegati di una mail si toccano solo in bozza);
  --   - vendite.trgfn_ddt_righe_prelievi_guard (i prelievi di una
  --     bolla, 2026-09-28);
  --   - vendite.trgfn_resi_righe_rientri_guard (i rientri di un
  --     reso, 2026-09-28).
  -- =========================================================
  IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
    RETURN;   -- nessuna riga: il chiamante lo legge come «assente»
  END IF;

  IF p_documento = 'DDT' THEN
    RETURN QUERY
    SELECT s.codice_interno::text,
           concat('DDT ', COALESCE(d.numero, '#' || d.id::text))
      FROM vendite.ddt d
      JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
     WHERE d.id = p_testata_id;

  ELSIF p_documento = 'ORDINE' THEN
    RETURN QUERY
    SELECT s.codice_interno::text,
           concat('Ordine ', COALESCE(o.numero, '#' || o.id::text))
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
     WHERE o.id = p_testata_id;

  ELSIF p_documento = 'CONTRATTO' THEN
    -- rev 2026-09-22: terzo adottante del guard generico delle righe.
    RETURN QUERY
    SELECT s.codice_interno::text,
           concat('Contratto ', COALESCE(c.numero, '#' || c.id::text))
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
     WHERE c.id = p_testata_id;

  ELSIF p_documento = 'EMAIL_BOZZA' THEN
    -- rev 2026-09-25: la bozza di una mail. Lo stato e' gia' il
    -- codice; l'etichetta e' l'oggetto, che una persona riconosce.
    RETURN QUERY
    SELECT o.stato::text,
           concat('La mail «', left(o.oggetto, 80), '»')
      FROM config.email_outbox o
     WHERE o.id = p_testata_id;

  ELSIF p_documento = 'RESO' THEN
    -- rev 2026-09-28: il reso di vendita, per il guard dei suoi
    -- rientri (vendite.trgfn_resi_righe_rientri_guard): stesso
    -- rifiuto delle righe di documento, stessa etichetta.
    RETURN QUERY
    SELECT s.codice_interno::text,
           concat('Reso ', COALESCE(r.numero, '#' || r.id::text))
      FROM vendite.resi r
      JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
     WHERE r.id = p_testata_id;

  ELSE
    -- Errore di CHIAMANTE, non di dato: nessuna persona sceglie
    -- questo valore. Classe TECNICO, messaggio che nomina il
    -- valore ricevuto (fratello di E_RUOLO_APPLICATIVO_NON_GESTITO).
    PERFORM script.fn_log_and_raise_error(
      'script',
      'fn_get_stato_testata_documento',
      'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('documento', p_documento,
                         'testata_id', p_testata_id),
      NULL::uuid,
      COALESCE(p_documento, '<null>'));
  END IF;

  RETURN;
END;
$function$

COMMENT ON FUNCTION script.fn_get_stato_testata_documento(p_documento text, p_testata_id bigint)
IS 'Lettore SECURITY DEFINER dello stato e dell''etichetta di una testata di documento. Nasce il 2026-08-26 per vendite.trgfn_dlt_block_ordrig_ddtrig, che deve distinguere «la testata non c''e'' piu''» (CASCADE partito dalla testata) da «la testata non la vedo» (RLS). ⛔ SECURITY DEFINER perche'' quella distinzione e'' il perno della decisione: le testate hanno RLS — e dal 22-09 anche le righe (ddt_righe, ordini_righe, contratti_righe: letto dal catalogo) — e un guard che leggesse sotto RLS diventerebbe fail-open proprio per chi sta fuori perimetro. ⭐ CONTRATTO: zero righe = testata assente; una riga = stato (codice_interno) piu'' etichetta per l''operatore. Lo stato e'' NOT NULL su tutte le testate e la FK garantisce la riga di stato, quindi l''assenza di riga e'' un segnale non ambiguo. ⚠️ L''etichetta ripiega sull''id quando `numero` e'' NULL, che sui documenti in bozza e'' il caso normale, non un residuo. PERIMETRO: legge due colonne, non scrive, non espone dati riservati. Tipi ammessi: DDT | ORDINE | CONTRATTO (rev 2026-09-22, per vendite.trgfn_doc_righe_lock_fuori_bozza); qualunque altro valore e'' un errore di chiamante (E_DOC_TIPO_NON_GESTITO, TECNICO). Chiamanti: vendite.trgfn_doc_righe_lock_fuori_bozza, vendite.trgfn_dlt_block_ordrig_ddtrig. rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso): + RESO (vendite.resi, stato da config.stati_doc_reso, etichetta «Reso <numero>»), per vendite.trgfn_resi_righe_rientri_guard. Chiamanti anche vendite.trgfn_ddt_righe_prelievi_guard (Lotto 3) e vendite.trgfn_resi_righe_rientri_guard.';
```

---
{% include-markdown "signature-core.md" %}
