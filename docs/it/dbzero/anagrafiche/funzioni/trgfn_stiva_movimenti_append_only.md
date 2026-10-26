{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_stiva_movimenti_append_only.md" %}
# ⚙️ Funzione `trgfn_stiva_movimenti_append_only`

```sql
CREATE FUNCTION trgfn_stiva_movimenti_append_only()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_stiva_movimenti_append_only()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rendere il registro dei movimenti di plafond IVA
--   «solo aggiunte». Una riga scritta non si modifica e non si
--   cancella: si corregge scrivendo un CONTRO-MOVIMENTO di segno
--   opposto, che lascia a video l'errore, la correzione, e la
--   data di entrambi.
--   Decisione di Tid del 2026-08-30 (B-1).
--   Piano: brief-db-titoli-iva-movimenti-annullo.
--
-- ⛔ VIETA ENTRAMBI, e la meta' che sembra meno grave e' la
--   peggiore: un UPDATE riscrive la storia IN SILENZIO, perche'
--   l'accumulatore ricalcola e il totale resta «giusto» — nessuno
--   vede che un importo e' cambiato. Un DELETE almeno lascia un
--   buco.
--
-- ⚠️ Da qui in poi sono IRRAGGIUNGIBILI, e restano dove sono
--   come difesa in profondita': la branca `TG_OP <> 'INSERT'`
--   dell'accumulatore (compreso il suo commento sul «movimento
--   spostato da un titolo a un altro», che da oggi descrive un
--   caso che non puo' piu' succedere), il trigger di storico e la
--   branca UPDATE dell'audit.
--
-- ⚠️ Nessuna esenzione per l'owner: e' un trigger e scatta per
--   tutti. Una bonifica futura passa da una porta dichiarata, non
--   dal ruolo.
--
-- ⛔ E LA PULIZIA DELLA FATTURA, UN GIORNO, DOVRA' PASSARE.
--   Oggi non tocca questa tabella (eccezione SCOPERTA_NOTA in
--   test-cleanup-fattura-copertura-figlie-v1.sql), ma con I5
--   servira' decidere. Due strade:
--     1) un'apertura dichiarata via GUC, che questo guard dovra'
--        leggere — e che chi la apre deve RICHIUDERE;
--     2) la pulizia STORNA invece di cancellare, cioe' scrive un
--        contro-movimento come fa l'annullo — e allora qui non
--        serve nessuna eccezione.
--   La seconda e' preferibile, ed e' anche cio' che la nota di
--   quell'eccezione gia' indica.
DECLARE
    v_tx_id anagrafiche.soggetti_titoli_iva_movimenti.tx_id%TYPE;
BEGIN
    v_tx_id := OLD.tx_id;

    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', TG_NAME, 'E_TITOLO_IVA_MOVIMENTO_IMMUTABILE',
        jsonb_build_object(
            'movimento_id',   OLD.id,
            'titolo_iva_id',  OLD.titolo_iva_id,
            'tipo_movimento', OLD.tipo_movimento,
            'operazione',     TG_OP),
        v_tx_id,
        -- ⚠️ Nel VARIADIC il tipo di movimento e la sua data, che
        --   sono le due cose che una persona riconosce sul
        --   registro. Mai l'id tecnico, che non si cerca a mano.
        OLD.tipo_movimento,
        to_char(OLD.data_movimento, 'DD/MM/YYYY'));

    -- Irraggiungibile: fn_log_and_raise_error solleva sempre.
    -- Sta qui perche' PL/pgSQL pretende un RETURN su una funzione
    -- trigger, non perche' possa servire.
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_stiva_movimenti_append_only()
IS 'Rende il registro dei movimenti di plafond IVA «solo aggiunte»: rifiuta UPDATE e DELETE con E_TITOLO_IVA_MOVIMENTO_IMMUTABILE. Una riga si corregge con un CONTRO-MOVIMENTO di segno opposto, che lascia a video l''errore, la correzione e la data di entrambi. Decisione di Tid del 2026-08-30: prima era una promessa che il backend manteneva, e l''argomento del brief ci poggiava sopra. ⛔ Vieta ENTRAMBI, e la meta'' che sembra meno grave e'' la peggiore: un UPDATE riscrive la storia in silenzio, perche'' l''accumulatore ricalcola e il totale resta «giusto». ⚠️ Da qui sono irraggiungibili — e restano come difesa in profondita'' — la branca non-INSERT dell''accumulatore, il trigger di storico e l''audit su UPDATE. ⚠️ Nessuna esenzione per l''owner. ⛔ La pulizia della fattura, con I5, dovra'' passare: o un''apertura dichiarata via GUC, o (preferibile) storna invece di cancellare. Piano: brief-db-titoli-iva-movimenti-annullo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
