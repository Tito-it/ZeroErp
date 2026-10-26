{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_accrediti_guard.md" %}
# ⚙️ Funzione `trgfn_resi_accrediti_guard`

```sql
CREATE FUNCTION trgfn_resi_accrediti_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_accrediti_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il tetto del DOCUMENTO sul ponte accrediti.
--   Sigma qta per riga di FATTURA <= qta della riga.
--   E' il limite che parla la lingua del documento: «questa riga
--   di fattura ha fatturato 10 pezzi, non se ne possono
--   accreditare 11». Prima non esisteva: l'unico limite
--   all'accredito era il conto della merce.
-- ⚠️ Il tetto della MERCE non sta qui, e non e' una dimenticanza:
--   si misura in unita' PADRE, e su un articolo composito tre
--   righe di ponte valgono UNA unita' di merce. Sommarle riga per
--   riga direbbe «3» dove la merce dice «1» e rifiuterebbe il
--   secondo componente. Lo tiene vendite.fn_accredita_riga_reso,
--   come uguaglianza (D-NC-6), che e' anche piu' forte.
-- Mirror di trgfn_resi_riconsegne_guard e trgfn_resi_rinunce_guard.
DECLARE
    -- %TYPE anche nel DECLARE (linee-guida-sql §5b): la variabile
    -- segue la colonna che la riempie.
    v_qta_riga   vendite.fatture_righe.qta%TYPE;
    v_gia_riga   vendite.resi_righe_accrediti.qta%TYPE;
BEGIN
    -- 0) qta > 0 (difesa oltre al CHECK).
    IF NEW.qta IS NULL OR NEW.qta <= 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_accrediti_guard','E_QTA_NON_POSITIVA',
        jsonb_build_object('campo', 'qta', 'qta', NEW.qta), NEW.tx_id, NEW.qta::text);
    END IF;

    IF NEW.qta_partita IS NULL OR NEW.qta_partita <= 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_accrediti_guard','E_QTA_NON_POSITIVA',
        jsonb_build_object('campo', 'qta_partita', 'qta_partita', NEW.qta_partita),
        NEW.tx_id, NEW.qta_partita::text);
    END IF;

    -- 1) Lock: la riga di reso padre e il gruppo di accrediti
    --    della stessa riga di fattura. Serializza due resi
    --    DIVERSI che accreditano la stessa riga di fattura in
    --    momenti diversi — che e' il caso che il tetto del
    --    documento esiste per fermare. Nessun advisory lock: il
    --    FOR UPDATE basta, come nelle due sorelle.
    PERFORM 1 FROM vendite.resi_righe WHERE id = NEW.resi_riga_id FOR UPDATE;
    PERFORM 1 FROM vendite.resi_righe_accrediti a
      WHERE a.fattura_riga_rettificata_id = NEW.fattura_riga_rettificata_id
      FOR UPDATE;

    -- 2) Il tetto, letto sopra la RLS (vedi nota in testa).
    SELECT t.qta_riga_fattura
      INTO v_qta_riga
      FROM vendite.fn_resi_riga_tetti_accredito(
               NEW.resi_riga_id, NEW.fattura_riga_rettificata_id) t;

    -- 3) TETTO DEL DOCUMENTO. La stessa riga di fattura puo'
    --    essere accreditata da RESI DIVERSI in momenti diversi:
    --    la somma e' per riga di fattura, non per riga di reso.
    --    Esclude la riga corrente in UPDATE.
    SELECT COALESCE(SUM(a.qta), 0)
      INTO v_gia_riga
      FROM vendite.resi_righe_accrediti a
     WHERE a.fattura_riga_rettificata_id = NEW.fattura_riga_rettificata_id
       AND (TG_OP <> 'UPDATE' OR a.id <> NEW.id);

    IF v_gia_riga + NEW.qta > v_qta_riga THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_accrediti_guard','E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA',
        jsonb_build_object('resi_riga_id',     NEW.resi_riga_id,
                           'fattura_riga_id',  NEW.fattura_riga_rettificata_id,
                           'qta_riga_fattura', v_qta_riga,
                           'gia_accreditato',  v_gia_riga,
                           'qta_nuova',        NEW.qta),
        NEW.tx_id,
        NEW.fattura_riga_rettificata_id::text, v_qta_riga::text,
        v_gia_riga::text, NEW.qta::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_accrediti_guard()
IS 'Guard del ponte accrediti: il tetto del DOCUMENTO — Sigma qta per riga di FATTURA <= qta della riga (E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA). E'' il limite che parla la lingua del documento invece che della merce, e prima non esisteva: l''unico tetto all''accredito era il conto della merce. Si legge da vendite.fn_resi_riga_tetti_accredito, che e'' SECURITY DEFINER perche'' sotto RLS una riga fuori perimetro si legge come «non c''e''». ⚠️ Il tetto della MERCE NON sta qui, e non e'' una dimenticanza: si misura in unita'' PADRE, e su un articolo composito tre righe di ponte valgono UNA unita'' di merce — sommarle riga per riga direbbe «3» dove la merce dice «1» e rifiuterebbe il secondo componente di un accredito legittimo (e'' il primo caso reale della coda: la riga di reso 24, kit a tre componenti). Lo tiene vendite.fn_accredita_riga_reso come UGUAGLIANZA (D-NC-6, l''accredito e'' sempre pieno), che e'' anche piu'' forte di una disuguaglianza e costa lo stesso. Lock: FOR UPDATE sulla riga di reso padre e sul gruppo della riga di fattura, come nelle due sorelle; nessun advisory lock. rev 2026-08-18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
