{% include-markdown "it/dbzero/script/manual/fn_check_preventivo_annullabile.md" %}
# ⚙️ Funzione `fn_check_preventivo_annullabile`

```sql
CREATE FUNCTION fn_check_preventivo_annullabile(p_preventivo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_preventivo_annullabile(p_preventivo_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ANNULLAMENTO di un
--   preventivo. Funzione PURA (fn_check_*): nessun raise di
--   dominio, nessuna scrittura. Consumatori: il guard di
--   transizione, la porta vendite.fn_cambia_stato_preventivo e
--   script.fn_available_actions_preventivo.
--   Brief: brief-db-vie-uscita-operatore §3.1 e §7.3.
-- Ritorna: [] se annullabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}. L'ordine e' quello
--   di gravita': chi consuma solleva il PRIMO.
-- rev 2026-08-04 (§7.3): assorbito il criterio che viveva dentro
--   la porta (righe gia' EMESSA in commessa) -> MOTIVO 2. Da qui
--   la porta non ha piu' una regola propria: chiama questa.
-- rev 2026-11-06 (brief-db-sorgente-documento-e-riga, giro T.3):
--   il MOTIVO 1 cerca l'ordine figlio dalla sua provenienza
--   (ordini.sorgente_*, tipo PREVENTIVO), come il gemello sui DDT.
--   La provenienza dell'ordine stava prima in una colonna
--   parallela (documento_origine_tipo/id), e sorgente_* era
--   l'origine «import», che nessuno scriveva.
-- rev 2026-08-10: esclusi gli ordini figli ANNULLATI via is_abortito:
--   altrimenti un figlio morto bloccherebbe il padre per
--   sempre. Decisione di Tid 2026-08-10: qualunque altro stato
--   blocca, bozza compresa (la via d'uscita e' abbandonare
--   prima la bozza dell'ordine).
DECLARE
  v_motivi  jsonb := '[]'::jsonb;
  v_uid     vendite.preventivi.uid%TYPE;
  v_ordini  integer := 0;
  v_emesse  integer := 0;
BEGIN
  IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_preventivo_annullabile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','preventivo_id','valore',p_preventivo_id),
      NULL::uuid, 'preventivo_id obbligatorio (>0)');
  END IF;

  SELECT p.uid INTO v_uid
    FROM vendite.preventivi p
   WHERE p.id = p_preventivo_id;

  IF v_uid IS NULL THEN
    RETURN v_motivi;   -- preventivo inesistente: decide il chiamante
  END IF;

  -- MOTIVO 1 — un ordine e' gia' nato da questo preventivo: l'ordine
  -- che dichiara il preventivo come provenienza, con la regola
  -- d'incontro del modello (doc.id = sorgente_id OR doc.uid =
  -- sorgente_uid) sugli indici ix_ordini_v_sorgente_uid / _id.
  -- Gli ordini figli ANNULLATI non contano: un documento
  -- morto non deve bloccare il padre per sempre.
  SELECT count(*)
    INTO v_ordini
    FROM vendite.ordini o
    JOIN config.sorgenti s ON s.id = o.sorgente_tipo_id
                          AND s.codice_interno = 'PREVENTIVO'
    JOIN config.stati_doc_ordini so ON so.id = o.stato_doc_ordine_id
   WHERE (o.sorgente_id = p_preventivo_id OR o.sorgente_uid = v_uid)
     AND so.is_abortito IS NOT TRUE;

  IF v_ordini > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_PREV_ORDINE_GIA_GENERATO',
      'reason',     'ORDINE_GIA_GENERATO',
      'reason_key', 'vendite.preventivi.azione_reason.ordine_gia_generato',
      'dettaglio',  v_ordini);
  END IF;

  -- MOTIVO 2 — righe gia' EMESSE in commessa: a valle esiste un
  -- documento fiscale. E' il criterio che stava dentro la porta
  -- (§7.3) e legge l'EFFETTO (le attivita' di commessa, scritte
  -- dalle funzioni di dominio), non la registrazione della
  -- sorgente letta dal MOTIVO 3, che la scrive il backend con una
  -- chiamata separata. Sono due fatti diversi: oggi coincidono,
  -- per costruzione non devono.
  -- starts_with() (PG 18, index-friendly) come nella porta.
  -- ⭐ rev 2026-08-26 (L7b) — il CONTEGGIO si delega, il CODICE resta.
  -- La condizione e' la stessa di tutti gli altri documenti («ci sono righe
  -- gia' EMESSA»), quindi si calcola in UN posto solo:
  -- script.fn_check_sorgente_chiudibile. Ma Tid ha deciso (Q-9) che il
  -- preventivo tiene il PROPRIO codice, che il frontend gia' mappa: qui il
  -- motivo si RIETICHETTA, non si ricalcola.
  -- ⭐ Una implementazione, due superfici. E' anche il motivo per cui sui
  -- preventivi NON si monta il guard generico: uscirebbero due codici diversi
  -- per lo stesso rifiuto, a seconda di quale trigger parla per primo.
  -- ⚠️ Cambia anche la CHIAVE, ed e' un guadagno: prima si contava con
  -- starts_with() sul segment_key ('PREV:<uid>:R:'), cioe' su una convenzione
  -- di stringa; adesso sulla coppia (sorgente_tipo_id, sorgente_uid), che e'
  -- il legame dichiarato. Le due oggi coincidono, per costruzione non devono.
  SELECT count(*)
    INTO v_emesse
    FROM jsonb_array_elements(
           script.fn_check_sorgente_chiudibile(
               (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
               p_preventivo_id, v_uid)) AS m
   WHERE m ->> 'codice' = 'E_SORGENTE_CON_RIGHE_EMESSE';

  IF v_emesse > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_PREV_ANNULLA_COMMESSA_EMESSA',
      'reason',     'COMMESSA_GIA_EMESSA',
      'reason_key', 'vendite.preventivi.azione_reason.commessa_gia_emessa',
      'dettaglio',  v_emesse);
  END IF;

  -- MOTIVO 3 — il preventivo e' gia' entrato in una commessa,
  -- anche se nulla e' ancora uscito. Tabella polimorfa: la chiave
  -- e' testo, e per PREVENTIVO config.sorgenti.key_selector dice
  -- 'uid'.
  -- ⛔ rev 2026-08-26 (L7b, Q-9) — E_PREV_GIA_IN_COMMESSA SI RITIRA.
  -- Vietava di annullare un preventivo che aveva gia' spinto in commessa
  -- «anche se nulla e' ancora uscito», e il motivo era che NON C'ERA MODO di
  -- disfare il push. Adesso c'e': alla chiusura il documento RITIRA da se' le
  -- righe che nessuno ha ancora emesso
  -- (trg_preventivi_z90_ritira_commessa_attivita_upd).
  -- ⭐ E il preventivo si allinea agli altri documenti: l'ordine aveva lo
  -- stesso divieto (E_ORD_ANNULLA_IN_COMMESSA) e si ritira insieme a questo.
  -- Resta il solo MOTIVO 2, che e' una condizione vera e ha una via d'uscita.
  -- ⚠️ Il codice resta a catalogo con `obsoleto_dal`: non si cancella, smette
  -- di essere sollevato.

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_preventivo_annullabile(p_preventivo_id bigint)
IS 'Check puro: i motivi che impediscono l''annullamento di un preventivo. [] = lecito. Sede unica della regola, condivisa da vendite.trgfn_preventivi_guard_annullamento, dalla porta vendite.fn_cambia_stato_preventivo e da script.fn_available_actions_preventivo. Motivi in ordine di gravita'' (chi consuma solleva il primo): 1) un ordine nato dal preventivo e non annullato, cioe'' un ordine che lo dichiara come provenienza (sorgente_tipo_id PREVENTIVO, chiave del preventivo) con config.stati_doc_ordini.is_abortito non vero (E_PREV_ORDINE_GIA_GENERATO); qualunque altro stato del figlio blocca, bozza compresa: la via d''uscita e'' abbandonare prima la bozza dell''ordine; 2) righe gia'' EMESSA in commessa, da script.fn_check_sorgente_chiudibile: a valle esiste una fattura (E_PREV_ANNULLA_COMMESSA_EMESSA). Le righe di commessa NON_EMESSA non bloccano: si ritirano con la conferma all''annullo (vendite.fn_annulla_preventivo). Un preventivo inesistente non ha motivi: decide il chiamante. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
