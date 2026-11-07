{% include-markdown "it/dbzero/vendite/manual/fn_list_contratti_da_pushare.md" %}
# ⚙️ Funzione `fn_list_contratti_da_pushare`

```sql
CREATE FUNCTION fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_contratto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_contratto_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(contratto_id bigint, contratto_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_chiave text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint, termine_pagamento_id bigint, modalita_pagamento_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: le righe di commessa che i contratti devono mandare a questo giro:
--   gli addebiti maturati di vendite.fn_contratti_addebiti_maturati (la sede
--   della regola: una tantum, canoni, storni) senza gli scartati, con le
--   colonne della commessa che non dipendono dalla riga.
-- rev 2026-10-30 (20261030-01): i tre rami; prima solo UNA_TANTUM.
-- rev 2026-10-31 (20261031-01): lo storno segue la fine anche quando si
--   sposta dopo il primo storno.
-- rev 2026-10-31 (20261031-03): il corpo passa a
--   vendite.fn_contratti_addebiti_maturati (20261031-02), che lo condivide
--   con la dashboard; qui resta il filtro.
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'CONTRATTO' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_contratti_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'CONTRATTO'),
      NULL::uuid, 'CONTRATTO', 'config.sorgenti'
    );
  END IF;

  RETURN QUERY
  SELECT
    a.contratto_id, a.contratto_uid, a.riga_id,
    a.billing_account_id, a.utility_id, a.emittente_soggetto_ruolo_id,
    a.competenza_dal, a.competenza_al,
    -- Corsia di instradamento: valore reale del contratto.
    a.fatturazione_immediata,
    v_sorgente_tipo_id,
    a.contratto_uid::text,
    a.segment_key,
    a.articolo_id, a.istanza_utility_id, a.data_attivita, a.uom_id,
    a.quantita, a.qta_operativa, a.uom_operativa_id, a.factor_to_base,
    a.competenza_mese,
    a.prezzo_snapshot, a.prezzo_bloccato,
    'FIXED'::varchar,
    'NORMALE'::varchar,
    NULL::integer,
    a.meta,
    v_tipo_doc_fiscale_id,
    NULL::bigint,
    NULL::integer
  FROM vendite.fn_contratti_addebiti_maturati(
         p_competenza_mese, p_billing_account_id, p_contratto_id) a
  -- Gli scartati non partono: li segnala la dashboard.
  WHERE a.scarto IS NULL
  ORDER BY a.contratto_id, a.ramo, a.segment_key
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_contratto_id bigint)
IS 'Le righe di commessa che i contratti ATTIVO e CESSATO devono mandare a questo giro, in tre rami. (1) UNA_TANTUM: le righe ADESIONE e AGGIUNTA dei contratti ATTIVO, una volta, con competenza il giorno di attivazione (valido_dal); l''OVERRIDE non si addebita (e'' il prezzo del cliente), l''ESCLUSIONE non si fattura. (2) CANONE: i pezzi di periodo maturati e non ancora addebitati, da vendite.fn_canone_periodi (sede unica della regola), per le righe a canone ADESIONE e AGGIUNTA, per l''OVERRIDE solo su una quota fissa (prende il posto della riga di listino), e per le quote fisse del listino (config.listini_tipologie.e_quota_fissa, erogazione di default CANONE) senza una riga del contratto sullo stesso articolo: quantita'' 1 a periodo, periodicita'' della riga di listino. Il «da» e'' il giorno dopo l''ultimo pezzo addebitato della fonte; la generazione e'' coalesce(riga, testata); quantita'' fissa = riga x frazione, durata = giorni del pezzo o mesi (frazione x mesi). Prezzo: della riga, o del listino del contratto all''inizio del pezzo (vendite.fn_resolve_prezzo_listino_v2_esito, con la variazione globale; senza prezzo la riga non parte). Chiave del push CONTRATTO:<uid>:R:<riga>:M:<AAAA-MM> (mese d''inizio del pezzo) o, per la quota fissa del listino, CONTRATTO:<uid>:A:<articolo>:M:<AAAA-MM>. (3) STORNO: un pezzo addebitato che va oltre valido_al si storna per la parte non goduta (addebitato meno dovuto con la fine nota, stessa regola dei mesi e dei giorni), una riga per riga addebitata, al prezzo addebitato. La fine si puo'' spostare finche'' il contratto e'' ATTIVO: lo storno e'' la differenza fra il dovuto con la fine di oggi e quanto e'' gia'' stornato per il pezzo (negativa se la fine arretra, positiva se avanza o sparisce), chiave <base del pezzo>#STO[:<n>][#CMP:...]: la prima #STO, le successive #STO:2, #STO:3, ... Canone e storno hanno competenza_mese = il mese del giro (fine del mese di p_competenza_mese, o l''oggi aziendale), competenza_dal/al = il pezzo. Esclusione gia'' inviato: script.fn_get_stato_push_segment = LIBERA. Righe senza periodicita'' o senza prezzo non partono: le segnala la dashboard (vendite.vw_dash_fatturazione_contratti, CANONE_NON_GENERABILE). Il corpo e'' in vendite.fn_contratti_addebiti_maturati, sede comune con la dashboard; qui il filtro (scarto NULL), le colonne costanti della commessa, l''ordine e il limite. La chiave del documento esce in sorgente_chiave, l''uid del contratto in testo, come la riceve la madre vendite.fn_upsert_commessa_attivita (p_sorgente_chiave) e come la legge la chiave sorgente_chiave del batch vendite.fn_batch_upsert_commessa_attivita. Il backend legge le colonne per nome.';
```

</div>

---
{% include-markdown "signature-core.md" %}
