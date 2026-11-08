{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_stiva_movimenti_guard_annullo.md" %}
# ⚙️ Funzione `trgfn_stiva_movimenti_guard_annullo`

```sql
CREATE FUNCTION trgfn_stiva_movimenti_guard_annullo()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_stiva_movimenti_guard_annullo()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'anagrafiche', 'config', 'script', 'pg_temp'
AS $function$
-- Scopo: presidiare le righe che ANNULLANO un movimento del
--   registro plafond IVA, in due famiglie di controlli.
--   Uso: BEFORE INSERT FOR EACH ROW
--        WHEN (NEW.annulla_movimento_id IS NOT NULL)
--   Piano: brief-db-titoli-iva-movimenti-annullo, B-c.
--
-- 1) AMMISSIBILITA' — non e' scritta qui: si CHIAMA
--    script.fn_check_annullo_movimento_titolo_iva e si solleva il
--    codice del PRIMO motivo. ⭐ E' il punto: il pulsante spento
--    (vw_stiva_movimenti_dettaglio) e questo rifiuto leggono LA
--    STESSA regola, quindi non possono divergere. Il presidio da
--    scrivere non e' «gli esiti coincidono», e' «il guard non
--    contiene piu' il predicato».
--
-- 2) COERENZA della riga scritta — stesso titolo, importo
--    opposto. Questa sta qui, ed e' difesa contro una scrittura
--    DIRETTA: passando dalla madre quei due valori sono DERIVATI
--    dalla riga annullata e non possono sbagliare. Il messaggio
--    dice infatti che qualcuno ha scritto a mano — e' TECNICO.
--
-- ⛔ SECURITY DEFINER: legge la riga ANNULLATA, e la tabella ha
--    la RLS attiva. Da INVOKER una riga fuori perimetro si
--    leggerebbe come «non esiste» e il guard passerebbe su una
--    premessa non verificata, mentre la FK — che la RLS la
--    scavalca sempre — il riferimento l'avrebbe accettato.
--    ⚠️ La MADRE resta INVOKER: la scrittura passa comunque dalla
--    policy, qui si scavalca solo per una LETTURA di coerenza.
DECLARE
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro). Non c'e' niente da ancorare.
    v_motivi   jsonb;
    v_ann      RECORD;
BEGIN
    -- ---- 1) AMMISSIBILITA' ------------------------------------
    v_motivi := script.fn_check_annullo_movimento_titolo_iva(
                    NEW.annulla_movimento_id);

    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⭐⭐ `NEW.tx_id` e' GIUSTO, anche se il guard e' `_a10_`, e questa riga
    --   e' l'eccezione che spiega la regola: i BEFORE girano in ordine
    --   LESSICOGRAFICO sul NOME INTERO del trigger, e questo abbrevia il nome
    --   della tabella —
    --     trg_soggetti_titoli_iva_movimenti_gen_tx_id_ins_upd   ('so' ...)
    --     trg_stiva_movimenti_a10_guard_annullo_ins             ('st' ...)
    --   quindi gen_tx_id scatta PRIMA e la transazione c'e'. ⛔ Non e' il
    --   prefisso di fase a decidere: e' la stringa intera.
    -- ⭐ `motivi` non si passa piu': lo mette l'helper, sempre.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', TG_NAME,
        v_motivi,
        NULL,
        NEW.tx_id,
        jsonb_build_object(
            'movimento_annullato_id', NEW.annulla_movimento_id,
            'titolo_iva_id',          NEW.titolo_iva_id));

    -- ---- 2) COERENZA -----------------------------------------
    -- La riga esiste ed e' annullabile: la si rilegge per i due
    -- confronti. Nessuna query in piu' rispetto a prima — la
    -- check non restituisce questi valori di proposito, perche'
    -- non sono motivi di blocco ma difetti di scrittura.
    SELECT m.titolo_iva_id, m.imponibile
      INTO v_ann
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.id = NEW.annulla_movimento_id;

    IF NEW.titolo_iva_id IS DISTINCT FROM v_ann.titolo_iva_id THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', TG_NAME,
            'E_TITOLO_IVA_ANNULLO_INCOERENTE',
            jsonb_build_object(
                'movimento_annullato_id', NEW.annulla_movimento_id,
                'titolo_atteso',          v_ann.titolo_iva_id,
                'titolo_ricevuto',        NEW.titolo_iva_id),
            NEW.tx_id,
            NEW.annulla_movimento_id::text,
            'l''annullo appartiene a un titolo IVA diverso da quello del movimento annullato');
    END IF;

    IF NEW.imponibile IS DISTINCT FROM (- v_ann.imponibile) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', TG_NAME,
            'E_TITOLO_IVA_ANNULLO_INCOERENTE',
            jsonb_build_object(
                'movimento_annullato_id', NEW.annulla_movimento_id,
                'imponibile_atteso',      - v_ann.imponibile,
                'imponibile_ricevuto',    NEW.imponibile),
            NEW.tx_id,
            NEW.annulla_movimento_id::text,
            'l''importo dell''annullo non e'' l''opposto esatto del movimento annullato');
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_stiva_movimenti_guard_annullo()
IS 'Guard sulle righe che ANNULLANO un movimento del registro plafond IVA (BEFORE INSERT, WHEN annulla_movimento_id IS NOT NULL). Due famiglie di controlli: (1) AMMISSIBILITA'', che non e'' scritta qui ma si CHIAMA da script.fn_check_annullo_movimento_titolo_iva sollevando il codice del PRIMO motivo — cosi'' il pulsante spento del read-side e questo rifiuto leggono la stessa regola e non possono divergere; (2) COERENZA della riga scritta — stesso titolo IVA e importo esattamente opposto — che e'' difesa contro una scrittura DIRETTA, perche'' passando dalla madre quei valori sono derivati. ⛔ Il controllo sull''importo e'' cio'' che rende vero il presidio del brief: senza, un annullo di 100 su una forzatura di 250 passerebbe e imponibile_utilizzato non tornerebbe al valore precedente. ⛔ Quello sul titolo e'' il peggiore dei due: decurterebbe il plafond sbagliato SENZA sollevare niente, perche'' l''accumulatore somma per titolo e del collegamento non sa nulla. ⛔ SECURITY DEFINER perche'' legge la riga annullata su una tabella con RLS: da INVOKER «fuori perimetro» si leggerebbe come «non esiste» mentre la FK la RLS la scavalca sempre. La madre resta INVOKER. ⚠️ Solo BEFORE INSERT: dal 20260830-22 il registro non ammette UPDATE. Piano: brief-db-titoli-iva-movimenti-annullo, B-c.';
```

</div>

---
{% include-markdown "signature-core.md" %}
