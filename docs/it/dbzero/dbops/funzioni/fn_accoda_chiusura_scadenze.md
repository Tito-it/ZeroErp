{% include-markdown "it/dbzero/dbops/manual/fn_accoda_chiusura_scadenze.md" %}
# ⚙️ Funzione `fn_accoda_chiusura_scadenze`

```sql
CREATE FUNCTION fn_accoda_chiusura_scadenze()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_accoda_chiusura_scadenze()
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_processo  dbops.processi.codice%TYPE := 'chiusura_scadenze_daily';
    v_job_type  dbops.coda_lavori_tipi.codice%TYPE := 'CHIUSURA_SCADENZE';
    v_riga      record;
    v_job_id    dbops.coda_lavori.id%TYPE;
    v_accodati  integer := 0;
    v_falliti   integer := 0;
    v_saltati   integer := 0;
    v_dettaglio jsonb   := '[]'::jsonb;
    -- ⭐ Il GIORNO AZIENDALE, letto una volta: la chiave del lavoro e il
    --   controllo «gia' fatto oggi» devono parlare dello stesso giorno.
    v_oggi      date    := script.fn_data_operativa();
    v_chiave    dbops.coda_lavori.idempotency_key%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Svegliare la chiusura scadenze, non eseguirla. Un lavoro
    --   per azienda, ciascuno con l'identita' tecnica di quella
    --   azienda: da li' in poi e' la RLS a garantire il perimetro,
    --   e non piu' la buona volonta' di una query.
    --
    -- ⭐ Isolamento per azienda: se A fallisce, B e C vengono
    --   accodate lo stesso. Prima era un giro unico — un errore
    --   su una tabella fermava tutto, per tutti, in silenzio.
    -- =========================================================
    FOR v_riga IN
        SELECT r.auth_user_id, r.username, r.identita_id,
               r.emittente_fiscale_id, r.emittente_codice
          FROM dbops.vw_processi_roster r
         WHERE r.processo_codice = v_processo
         -- L'ordine lo da' gia' la vista: qui non si ri-ordina,
         -- o sarebbero due posti che decidono la stessa cosa.
    LOOP
        v_chiave := v_job_type || ':' || v_riga.emittente_codice || ':' || v_oggi::text;

        -- ⭐ UNA VOLTA PER GIORNO AZIENDALE (brief-be-db-fe-un-solo-fuso-aziendale,
        --   T-4): la sveglia e' oraria, e il giorno lo decide il fuso
        --   dell'azienda, non l'orario dell'host. La chiave idempotente di
        --   fn_accoda_lavoro protegge solo i lavori VIVI (PENDING/IN_CORSO): un
        --   lavoro gia' FATTO oggi per questa azienda chiude il giorno e non si
        --   riaccoda. Uno in ERRORE o ANNULLATO no: la sveglia dopo ci riprova.
        IF EXISTS (SELECT 1 FROM dbops.coda_lavori cl
                    WHERE cl.job_type = v_job_type
                      AND cl.idempotency_key = v_chiave
                      AND cl.stato = 'FATTO') THEN
            v_saltati := v_saltati + 1;
            CONTINUE;
        END IF;

        BEGIN
            v_job_id := dbops.fn_accoda_lavoro(
                p_job_type => v_job_type,
                p_payload  => jsonb_build_object(
                    'emittente_fiscale_id', v_riga.emittente_fiscale_id,
                    'emittente_codice',     v_riga.emittente_codice),
                -- ⛔ OPERATORE, non SISTEMA: il guard di classe in
                --   fn_accoda_lavoro lo pretende per un processo di
                --   dominio, ed e' la ragione per cui questo
                --   cantiere esiste.
                p_run_as   => 'OPERATORE',
                p_scope    => jsonb_build_object(
                    'auth_user_id', v_riga.auth_user_id,
                    'username',     v_riga.username,
                    'identita_id',  v_riga.identita_id,
                    -- ⚠️ CONGELATO all'accodamento: il worker
                    --   esegue minuti dopo, e senza questo valore
                    --   girerebbe in modalita' globale — cioe' un
                    --   lavoro chiesto «dentro A» toccherebbe
                    --   anche B, silenziosamente.
                    'emittente_attivo_id', v_riga.emittente_fiscale_id,
                    'emittente_ids', jsonb_build_array(
                                         v_riga.emittente_fiscale_id)),
                -- ⚠️ Per (azienda, GIORNO), senza l'ora: due
                --   sveglie nello stesso giorno sono la stessa
                --   intenzione, non due.
                p_idempotency_key => v_chiave,
                p_origine  => 'CRON');

            v_accodati := v_accodati + 1;
            v_dettaglio := v_dettaglio || jsonb_build_object(
                'emittente', v_riga.emittente_codice,
                'job_id',    v_job_id);
        EXCEPTION WHEN OTHERS THEN
            -- ⭐ Si continua: l'isolamento per azienda e' il
            --   guadagno principale della migrazione sulla coda.
            v_falliti := v_falliti + 1;
            v_dettaglio := v_dettaglio || jsonb_build_object(
                'emittente', v_riga.emittente_codice,
                'errore',    left(SQLERRM, 200));
        END;
    END LOOP;

    -- ⚠️ Si RITORNA un riepilogo invece di sollevare: chi chiama e'
    --   un job notturno, e un riepilogo finisce nel giornale
    --   mentre un'eccezione si perde.
    RETURN jsonb_build_object(
        '_processo',    v_processo,
        '_accodati',    v_accodati,
        '_falliti',     v_falliti,
        '_saltati',     v_saltati,
        '_dettaglio',   v_dettaglio,
        '_executed_at', now());
END
$function$

COMMENT ON FUNCTION dbops.fn_accoda_chiusura_scadenze()
IS 'Accoda un lavoro di chiusura scadenze per OGNI azienda del roster, con l''identita'' tecnica di quella azienda nello scope. ⭐ E'' cio'' che il job pgAgent chiama al posto di dbops.fn_apply_chiusura_scadenze: da qui in poi pgAgent SVEGLIA e non lavora, ed e'' la regola presa il 2026-09-05 — nessun processo di classe DOMINIO esegue dentro pgAgent, dove non ha identita'' e dove un fallimento non arriva a nessuno (R-12: sei mesi di fallimenti silenziosi). ⭐ Isolamento per azienda: un EXCEPTION per riga, cosi'' se A fallisce B e C vengono accodate lo stesso — prima un errore su una tabella fermava tutto, per tutti. ⚠️ Idempotente per (azienda, GIORNO) senza l''ora: due sveglie nello stesso giorno sono la stessa intenzione. ⚠️ run_as OPERATORE e non SISTEMA: lo pretende il guard di classe di fn_accoda_lavoro, ed e'' il punto del cantiere. ⚠️ emittente_attivo_id e'' CONGELATO all''accodamento: senza, il worker girerebbe in modalita'' globale e un lavoro chiesto dentro A toccherebbe anche B. ⚠️ Ritorna un riepilogo invece di sollevare: chi chiama e'' un job notturno, e un riepilogo finisce nel giornale mentre un''eccezione si perde.';
```

</div>

---
{% include-markdown "signature-core.md" %}
