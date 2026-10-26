{% include-markdown "it/dbzero/script/manual/fn_check_lotto_riportabile_a_draft.md" %}
# ⚙️ Funzione `fn_check_lotto_riportabile_a_draft`

```sql
CREATE FUNCTION fn_check_lotto_riportabile_a_draft(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_lotto_riportabile_a_draft(p_lotto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono il RITORNO IN BOZZA di
--   un lotto. Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura. Consumatori: vendite.fn_riporta_lotto_a_draft
--   (che solleva il codice del primo motivo) e
--   script.fn_available_actions_lotto (che espone enabled + reasons).
-- Ritorna: [] se riportabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi    jsonb := '[]'::jsonb;
  v_stato_cod   vendite.vw_lotti_fase.stato_codice_interno%TYPE;
  -- ⭐ rev 2026-09-09: il DERIVATO gia' fail-closed della sede unica, non piu'
  --   il flag grezzo con la COALESCE ricopiata qui sotto. La difesa e' scritta
  --   in un posto solo, e ha un NOME.
  v_pre_fiscale vendite.vw_lotti_fase.pre_fiscale%TYPE;
  v_trovato   boolean;
  v_numerate  integer;
BEGIN
  -- Guard parametro (AGENTS.md).
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_riportabile_a_draft','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','lotto_id','valore',p_lotto_id),
      NULL::uuid, 'lotto_id obbligatorio (>0)');
  END IF;

  -- ⭐ rev 2026-09-09 — SI LEGGE DALLA SEDE UNICA, vendite.vw_lotti_fase, che
  --   fa la stessa LEFT JOIN che stava qui: un lotto senza stato risolvibile
  --   ha comunque la sua riga e arriva al confronto.
  SELECT true, f.stato_codice_interno, f.pre_fiscale
    INTO v_trovato, v_stato_cod, v_pre_fiscale
    FROM vendite.vw_lotti_fase f
   WHERE f.lotto_id = p_lotto_id;

  IF NOT COALESCE(v_trovato, false) THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_riportabile_a_draft','E_LOTTO_NON_TROVATO',
      jsonb_build_object('lotto_id',p_lotto_id),
      NULL::uuid, p_lotto_id::text);
  END IF;

  -- MOTIVO 1 — il lotto e' oltre il pre-fiscale.
  -- Oltre EMESSA c'e' la numerazione: il punto di non ritorno
  -- del documento fiscale, non una scelta di questa funzione.
  -- ⭐ LA SOGLIA E' UN DATO, non una lista scritta qui (D33).
  --    Fino al 2026-08-30 questa funzione portava la propria copia di
  --    `NOT IN ('DRAFT','EMESSA')`. Erano OTTO copie della stessa frase,
  --    e `config.stati_doc_fiscale.congela_fiscale` era nata (I10) proprio
  --    per toglierle: era stata collegata a un solo lettore.
  -- ⚠️ Il comportamento NON cambia: verificato che sui sei stati esistenti
  --    colonna e lista dicono la stessa cosa. Cambia la SEDE, cioe' quante
  --    cose vanno toccate il giorno che il confine si sposta - da otto a una.
  -- ⚠️ E il trattamento dello STATO MANCANTE resta identico a prima: e' una
  --    decisione di questa funzione, non della soglia.
  -- ⚠️ Il fail-closed non e' sparito: si e' SPOSTATO dentro `pre_fiscale`,
  --    che su uno stato non risolvibile vale FALSE. Il ritorno a bozza resta
  --    bloccato esattamente come prima — e la stessa decisione non e' piu'
  --    ricopiata in tre funzioni.
  IF NOT v_pre_fiscale THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_LOTTO_NON_RIPORTABILE_A_DRAFT',
      'reason',     'STATO_NON_PRE_FISCALE',
      'reason_key', 'vendite.lotti.azione_reason.stato_non_pre_fiscale',
      'dettaglio',  COALESCE(v_stato_cod, '-'));
  END IF;

  -- MOTIVO 2 — fatture oltre il pre-fiscale (sede unica).
  v_motivi := v_motivi
            || script.fn_check_lotto_fatture_pre_fiscali(p_lotto_id);

  -- MOTIVO 3 — fatture gia' numerate.
  -- ⚠️ Ridondante per costruzione rispetto al motivo 2 (a EMESSA
  -- la fattura non e' numerata, C-19) e va tenuto lo stesso: il
  -- danno sarebbe irreversibile, quindi si guarda il FATTO e non
  -- lo stato che dovrebbe implicarlo.
  SELECT count(*)
    INTO v_numerate
    FROM vendite.fatture f
    JOIN vendite.fatturazione_lotti_fatture lf
      ON lf.fattura_id = f.id
   WHERE lf.lotto_id = p_lotto_id
     AND f.numero IS NOT NULL;

  IF v_numerate > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_LOTTO_FATTURE_NUMERATE',
      'reason',     'FATTURE_NUMERATE',
      'reason_key', 'vendite.lotti.azione_reason.fatture_numerate',
      'dettaglio',  v_numerate);
  END IF;

  -- ⭐ MOTIVO 4 (2026-08-22) — righe gia' RETTIFICATE.
  -- Delegato: la domanda vive in un posto solo, condiviso dalle
  -- tre porte di reset.
  -- ⚠️ NON e' coperto dal motivo 3, ed e' il punto: la
  -- protezione dei documenti numerati non arriva qui, perche'
  -- l'accredito si registra PRIMA della numerazione — e' ancorato
  -- alla coda dei resi, non al numero. Senza questo motivo il
  -- reset passa il gate e poi esplode con una violazione di
  -- chiave esterna grezza dentro fn_cleanup_fatture_by_ids.
  v_motivi := v_motivi
            || script.fn_check_fatture_con_rettifiche(
                   ARRAY(SELECT lf.fattura_id
                           FROM vendite.fatturazione_lotti_fatture lf
                          WHERE lf.lotto_id = p_lotto_id));

  -- ⭐ MOTIVO 5 (2026-10-04) — fatture che hanno gia' CONSUMATO plafond.
  -- Delegato, come il 4: sede unica condivisa dalle tre porte di reset.
  -- ⚠️ NON e' coperto dal motivo 3: il plafond si consuma PRIMA della
  -- numerazione (consuma_plafond_lotto precede numera_fatture), quindi una
  -- fattura puo' avere consumato senza avere ancora il numero. Senza
  -- questo motivo il reset passa il gate e poi esplode con una violazione
  -- di chiave esterna grezza dentro fn_cleanup_fatture_by_ids.
  -- Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §14 (strada A).
  v_motivi := v_motivi
            || script.fn_check_fatture_con_plafond_consumato(
                   ARRAY(SELECT lf.fattura_id
                           FROM vendite.fatturazione_lotti_fatture lf
                          WHERE lf.lotto_id = p_lotto_id));

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_lotto_riportabile_a_draft(p_lotto_id bigint)
IS 'Funzione PURA (fn_check_*): motivi ostativi al ritorno in bozza di un lotto. Ritorna [] se riportabile, altrimenti array ordinato di {codice, reason, reason_key, dettaglio}. Motivo 1: lotto oltre il pre-fiscale (codice 800). Motivo 2: fatture oltre il pre-fiscale (codice 799), delegato a script.fn_check_lotto_fatture_pre_fiscali. Motivo 3: fatture gia'' NUMERATE (codice 801) — ⚠️ deliberatamente ridondante rispetto al 2 e da NON semplificare via: guarda il numero e non lo stato che dovrebbe implicarlo. ⭐ Motivo 4 (2026-08-22): righe di fattura gia'' RETTIFICATE, delegato a script.fn_check_fatture_con_rettifiche — ⚠️ NON e'' coperto dal motivo 3, ed e'' il punto: l''accredito si registra PRIMA della numerazione (e'' ancorato alla coda dei resi), quindi la protezione dei documenti numerati non arriva fin li''. Senza, il reset passava il gate e poi esplodeva con un 23503 dentro fn_cleanup_fatture_by_ids. Sorgente UNICA condivisa da vendite.fn_riporta_lotto_a_draft (solleva) e script.fn_available_actions_lotto (espone enabled/reasons). rev 2026-08-22. rev 2026-09-09: la fase del lotto si legge da vendite.vw_lotti_fase (sede unica) e il confine pre-fiscale arriva gia'' fail-closed nel derivato pre_fiscale, invece di essere ricomposto qui con una COALESCE; parametri con %TYPE — nessuna decisione cambia. ⭐ Motivo 5 (2026-10-04): fatture che hanno gia'' CONSUMATO il plafond di un titolo IVA, delegato a script.fn_check_fatture_con_plafond_consumato — il consumo avviene PRIMA della numerazione, quindi il motivo sul numero non lo copre; un movimento e'' un fatto contabile e la fattura non si disfa piu'' (brief-db-bom-flag-quantita-e-kit-in-fattura §14, strada A).';
```

</div>

---
{% include-markdown "signature-core.md" %}
