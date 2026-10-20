{% include-markdown "it/dbzero/script/manual/fn_check_ordine_annullabile.md" %}
# ⚙️ Funzione `fn_check_ordine_annullabile`

```sql
CREATE FUNCTION fn_check_ordine_annullabile(p_ordine_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ordine_annullabile(p_ordine_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ANNULLAMENTO di un
--   ordine. Funzione PURA (fn_check_*). Consumatori: il guard di
--   transizione e script.fn_available_actions_ordine.
--   Brief: brief-db-vie-uscita-operatore §3.2.
-- rev 2026-08-15: il MOTIVO 1 non conta piu' i DDT figli ANNULLATI.
--   Lacuna speculare a quella corretta sul preventivo il 2026-08-10
--   (20260810-03), dove l'esclusione del figlio annullato e' stata
--   dichiarata voluta: «un figlio morto non deve bloccare il padre per
--   sempre e senza uscita». Sull'ordine quella ragione vale identica.
--   ⚠️ Era stata classificata «asimmetria latente, oggi non morde»
--   perche' nessun DDT bloccante risultava annullato — ma era una conta
--   su dati di TEST. In esercizio annullare un DDT e' ordinario
--   (destinatario sbagliato, merce sbagliata, duplicato): l'ordine il
--   cui unico figlio e' stato annullato resterebbe bloccato per sempre.
--   Il predicato usa `is_abortito`, l'asse uniforme cross-catalogo, non
--   `codice_interno = 'ANNULLATO'`. ⚠️ Esclude SOLO l'annullato: il DDT
--   in stato RESO ha is_abortito = false e continua a bloccare, ed e'
--   giusto — la merce e' tornata ma il documento e' vissuto.
--   brief-db-vie-uscita-operatore §12.6.
DECLARE
  v_motivi   jsonb := '[]'::jsonb;
  v_uid      vendite.ordini.uid%TYPE;
  v_numero   vendite.ordini.numero%TYPE;
  v_ddt      integer := 0;
BEGIN
  IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_ordine_annullabile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','ordine_id','valore',p_ordine_id),
      NULL::uuid, 'ordine_id obbligatorio (>0)');
  END IF;

  -- ⭐ `o.numero` sulla SELECT che c'era gia': serve a COMPORRE la frase
  --   («Ordine %s: esistono gia' documenti di trasporto ...»), non a decidere.
  SELECT o.uid, o.numero INTO v_uid, v_numero
    FROM vendite.ordini o
   WHERE o.id = p_ordine_id;

  IF v_uid IS NULL THEN
    RETURN v_motivi;   -- ordine inesistente: decide il chiamante
  END IF;

  -- MOTIVO 1 — merce gia' uscita: esiste un DDT figlio VIVO.
  -- Catena diretta: ddt.sorgente_uid e' uuid e punta all'uid.
  -- ⚠️ I DDT ANNULLATI non contano: un documento morto non deve
  -- bloccare il padre per sempre e senza uscita (stessa regola del
  -- preventivo, 20260810-03). `is_abortito` e non il codice: e' l'asse
  -- uniforme cross-catalogo, «true = stato di annullamento».
  SELECT count(*)
    INTO v_ddt
    FROM vendite.ddt d
    JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
   WHERE d.sorgente_uid = v_uid
     AND d.sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s
                                WHERE s.codice_interno = 'ORDINE_VENDITA')
     AND sdd.is_abortito IS NOT TRUE;

  IF v_ddt > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_ORD_ANNULLA_CON_DDT',
      'reason',     'DDT_COLLEGATI',
      'reason_key', 'vendite.ordini.azione_reason.ddt_collegati',
      'dettaglio',  v_ddt,
      'valori',     jsonb_build_array(COALESCE(v_numero, p_ordine_id::text)));
  END IF;

  -- MOTIVO 2 — l'ordine e' gia' entrato in una commessa.
  -- Tabella polimorfa: per ORDINE_VENDITA key_selector dice 'id'.
  -- ⛔ rev 2026-08-26 (L7b, Q-9) — E_ORD_ANNULLA_IN_COMMESSA SI RITIRA.
  -- Vietava di annullare un ordine che aveva spinto in commessa, e il motivo
  -- era che NON C'ERA MODO di disfare il push. Adesso c'e': alla chiusura il
  -- documento RITIRA da se' le righe che nessuno ha ancora emesso
  -- (trg_ordini_z90_ritira_commessa_attivita_upd).
  -- ⭐ Al suo posto resta un freno SOLO, e su una condizione VERA: le righe
  -- gia' EMESSA sono in volo verso una fattura e non si ritirano. Il conteggio
  -- non si riscrive qui — si delega alla primitiva condivisa, la stessa che il
  -- guard generico usa: una implementazione, due superfici (questa accende il
  -- pulsante, quella ferma la scrittura).
  -- ⚠️ Il codice resta a catalogo con `obsoleto_dal`: non si cancella, smette
  -- di essere sollevato.
  -- ⛔ E la CHIAVE cambia insieme al criterio: la primitiva legge
  -- vendite.commesse_attivita, dove `sorgente_uid` porta `uid::text` — non
  -- l'`id::text` che vendite.commesse_sorgenti usa per l'ordine. Passare la
  -- chiave vecchia non darebbe errore: darebbe zero motivi.
  -- ⚠️ I motivi di questa check arrivano QUI DENTRO gia' fatti, `valori`
  --   compresi: non si ricompongono e non si riordinano. E' il motivo per cui
  --   fn_check_sorgente_chiudibile e' entrata nello stesso cantiere — senza,
  --   meta' dei motivi di questa funzione sarebbe rimasta senza valori.
  v_motivi := v_motivi || script.fn_check_sorgente_chiudibile(
      (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
      v_uid::text);

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ordine_annullabile(p_ordine_id bigint)
IS 'Pure check: motivi che impediscono l''annullamento di un ordine. [] = lecito. Motivi: 1) un DDT figlio vivo (vendite.ddt.sorgente_uid = ordini.uid, chiave uuid): E_ORD_ANNULLA_CON_DDT; 2) righe di commessa gia'' EMESSA spinte dall''ordine (script.fn_check_sorgente_chiudibile, chiave <ordine>.uid::text): E_SORGENTE_CON_RIGHE_EMESSE. Le righe di commessa NON_EMESSA non bloccano: si ritirano con la conferma all''annullo (vendite.fn_annulla_ordine). Sede unica condivisa dal guard di transizione e da script.fn_available_actions_ordine. Brief: brief-db-vie-uscita-operatore. rev 2026-08-15: il MOTIVO 1 conta solo i DDT figli VIVI — i DDT con config.stati_doc_ddt.is_abortito true sono esclusi. Lacuna speculare a quella corretta sul preventivo con 20260810-03, dove l''esclusione del figlio annullato e'' dichiarata voluta: un figlio morto non deve bloccare il padre per sempre e senza uscita, che e'' il difetto stesso che il cantiere vie-d''uscita ha chiuso. ⚠️ Era stata classificata «asimmetria latente, oggi non morde» perche'' nessun DDT bloccante risultava annullato: era una conta su dati di TEST, e in esercizio annullare un DDT e'' ordinario. Esclude SOLO l''annullato — il DDT in stato RESO ha is_abortito false e continua a bloccare, ed e'' giusto: la merce e'' tornata ma il documento e'' vissuto. brief-db-vie-uscita-operatore §12.6. rev 2026-10-12 (brief-db-annullo-a-valle-riapre-a-monte, R-12): commento riallineato al corpo. Citava come secondo motivo «una riga in vendite.commesse_sorgenti (chiave id::text)», che il corpo non legge piu'': dal 2026-08-26 il secondo motivo viene da script.fn_check_sorgente_chiudibile sulle righe EMESSA. Corpo invariato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
