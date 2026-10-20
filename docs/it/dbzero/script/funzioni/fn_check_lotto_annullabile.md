{% include-markdown "it/dbzero/script/manual/fn_check_lotto_annullabile.md" %}
# ⚙️ Funzione `fn_check_lotto_annullabile`

```sql
CREATE FUNCTION fn_check_lotto_annullabile(p_lotto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_lotto_annullabile(p_lotto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ANNULLAMENTO di un
--   lotto. Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura. Consumatori: vendite.fn_annulla_lotto_da_draft
--   (che solleva il codice del primo motivo) e
--   script.fn_available_actions_lotto (che espone enabled + reasons).
-- Ritorna: [] se annullabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi    jsonb := '[]'::jsonb;
  v_stato_cod vendite.vw_lotti_fase.stato_codice_interno%TYPE;
  v_trovato   boolean;
  v_numerate  integer;
BEGIN
  -- Guard parametro (AGENTS.md).
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_annullabile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','lotto_id','valore',p_lotto_id),
      NULL::uuid, 'lotto_id obbligatorio (>0)');
  END IF;

  -- Stato corrente per CODICE: il codice_interno e' la chiave
  -- stabile, l'id no (lezione B-4).
  -- ⭐ rev 2026-09-09 — SI LEGGE DALLA SEDE UNICA, vendite.vw_lotti_fase.
  --   La vista fa la stessa LEFT JOIN che stava qui: un lotto senza stato
  --   risolvibile ha comunque la sua riga e arriva al confronto, quindi NON
  --   cambia nessuna decisione — cambia da dove si legge il fatto. Erano
  --   CINQUE letture uguali, e la quinta aveva scritto «vivo» come «non
  --   annullato».
  SELECT true, f.stato_codice_interno
    INTO v_trovato, v_stato_cod
    FROM vendite.vw_lotti_fase f
   WHERE f.lotto_id = p_lotto_id;

  IF NOT COALESCE(v_trovato, false) THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_annullabile','E_LOTTO_NON_TROVATO',
      jsonb_build_object('lotto_id',p_lotto_id),
      NULL::uuid, p_lotto_id::text);
  END IF;

  -- MOTIVO 1 — il lotto non e' in bozza.
  -- L'annullamento e' terminale (ANNULLATA chiude il lotto e non
  -- si riapre): si concede solo prima che il lotto abbia
  -- prodotto qualcosa. Da EMESSA la strada e' «riporta in bozza».
  IF COALESCE(v_stato_cod, '') <> 'DRAFT' THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_LOTTO_NON_ANNULLABILE',
      'reason',     'STATO_NON_DRAFT',
      'reason_key', 'vendite.lotti.azione_reason.stato_non_draft',
      'dettaglio',  COALESCE(v_stato_cod, '-'));
  END IF;

  -- MOTIVO 2 — fatture oltre il pre-fiscale. Delegato: la
  -- definizione di «pre-fiscale» sta in un posto solo.
  v_motivi := v_motivi
            || script.fn_check_lotto_fatture_pre_fiscali(p_lotto_id);

  -- MOTIVO 3 — fatture gia' NUMERATE (aggiunto 2026-08-18).
  -- ⚠️ DELIBERATAMENTE RIDONDANTE rispetto al 2, e da NON
  --   semplificare via: il motivo 2 si affida allo stato, che
  --   pre-fiscale IMPLICA non numerata (C-19); qui si guarda il
  --   FATTO, perche' cancellare una fattura numerata apre un buco
  --   nella numerazione fiscale e il danno non si ripara.
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
  -- ⚠️ Qui il caso e' MENO probabile che sulle sorelle — questa
  -- porta vuole il lotto in DRAFT — ma piu' GRAVE: ANNULLATA e'
  -- terminale, quindi un annullamento passato per errore
  -- toglierebbe anche la via d'uscita.
  -- Il motivo 3 non copre questo: l'accredito si registra PRIMA
  -- della numerazione (e' ancorato alla coda dei resi).
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

COMMENT ON FUNCTION script.fn_check_lotto_annullabile(p_lotto_id bigint)
IS 'Funzione PURA (fn_check_*): motivi ostativi all''annullamento di un lotto. Ritorna [] se annullabile, altrimenti array ordinato di {codice, reason, reason_key, dettaglio}. Motivo 1: lotto non in DRAFT (798) — ANNULLATA e'' terminale e non si riapre; da EMESSA la via d''uscita non distruttiva e'' fn_riporta_lotto_a_draft. Motivo 2: fatture oltre il pre-fiscale (799), delegato a script.fn_check_lotto_fatture_pre_fiscali. Motivo 3 (2026-08-18): fatture gia'' NUMERATE (801), deliberatamente ridondante rispetto al 2 e da NON semplificare via. ⭐ Motivo 4 (2026-08-22): righe di fattura gia'' RETTIFICATE, delegato a script.fn_check_fatture_con_rettifiche — ⚠️ meno probabile qui (questa porta vuole il DRAFT) ma piu'' grave, perche'' ANNULLATA e'' terminale e un annullamento passato per errore toglierebbe anche la via d''uscita. Il motivo 3 non lo copre: l''accredito si registra PRIMA della numerazione. Il tipo di lotto NON e'' un motivo: dal 2026-08-02 vale per MASSIVO e GIORNALIERO. rev 2026-08-22. rev 2026-09-09: lo stato del lotto si legge da vendite.vw_lotti_fase (sede unica della fase di un lotto) invece che con un join proprio, e i parametri usano %TYPE — nessuna decisione cambia, e i pgTAP di questa funzione restano verdi senza essere toccati. ⭐ Motivo 5 (2026-10-04): fatture che hanno gia'' CONSUMATO il plafond di un titolo IVA, delegato a script.fn_check_fatture_con_plafond_consumato — il consumo avviene PRIMA della numerazione, quindi il motivo sul numero non lo copre; un movimento e'' un fatto contabile e la fattura non si disfa piu'' (brief-db-bom-flag-quantita-e-kit-in-fattura §14, strada A).';
```

</div>

---
{% include-markdown "signature-core.md" %}
