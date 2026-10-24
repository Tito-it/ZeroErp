{% include-markdown "it/dbzero/dbops/manual/fn_guardiano_digest.md" %}
# ⚙️ Funzione `fn_guardiano_digest`

```sql
CREATE FUNCTION fn_guardiano_digest()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_guardiano_digest()
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_processo  CONSTANT dbops.processi.codice%TYPE          := 'digest_presidi';
    v_job_type  CONSTANT dbops.coda_lavori_tipi.codice%TYPE  := 'NOTIFICA_DIGEST_MUTO';
    v_stato     dbops.vw_processi_programmazione.stato%TYPE;
    v_toll      dbops.processi.tolleranza_minuti%TYPE;
    v_ultimo    timestamptz;
    v_key       dbops.coda_lavori.idempotency_key%TYPE;
    v_job_id    dbops.coda_lavori.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Guardare il guardiano. Se il digest dei presidi ha
    --   smesso di girare, accodare UN lavoro al giorno che lo
    --   dica a una persona — dal drenatore, con il destinatario
    --   del backend.
    --
    -- ⭐ Il criterio di «MUTO» NON e' qui: si legge dal
    --   panorama, dove sta accanto al CASE che lo produce.
    -- =========================================================
    SELECT v.stato, v.tolleranza_minuti, v.ultimo_segno_di_vita
      INTO v_stato, v_toll, v_ultimo
      FROM dbops.vw_processi_programmazione v
     WHERE v.processo_codice = v_processo;

    -- ⛔ Il digest non e' a catalogo, o e' spento/ritirato: il
    --   guardiano non ha niente da guardare, e lo DICE. Un
    --   ritorno silenzioso qui sarebbe un guardiano che dorme.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'fn_guardiano_digest', 'E_CONFIG_MANCANTE',
            jsonb_build_object('processo_codice', v_processo),
            NULL::uuid,
            'il processo ' || v_processo || ' non e'' attivo in dbops.processi: '
            'il guardiano non ha niente da guardare');
    END IF;

    -- ⚠️ Solo MUTO: «era vivo ed e' taciuto». MAI_PARTITO lo
    --   dice gia' il panorama nel pannello, e un nagging orario
    --   su un'installazione nuova insegnerebbe a ignorarlo.
    IF v_stato <> 'MUTO' THEN
        RETURN 'DIGEST_' || v_stato;
    END IF;

    -- ⭐ Una notifica per GIORNO di silenzio. La chiave si
    --   controlla in qualunque stato: fn_accoda_lavoro dedupe
    --   solo fra PENDING/IN_CORSO, e un lavoro gia' FATTO non
    --   deve far partire il successivo un'ora dopo.
    v_key := 'guardiano_digest:' || script.fn_data_operativa()::text;
    IF EXISTS (SELECT 1
                 FROM dbops.coda_lavori c
                WHERE c.job_type = v_job_type
                  AND c.idempotency_key = v_key) THEN
        RETURN 'GIA_NOTIFICATO_OGGI';
    END IF;

    -- ⚠️ Se il tipo e' ancora attivo = false (backend senza
    --   handler), fn_accoda_lavoro SOLLEVA E_JOB_TYPE_NON_ATTIVO
    --   e la corsa e' rossa nel giornale: «ho visto e non ho
    --   potuto dirlo». E' voluto — non si aggira.
    v_job_id := dbops.fn_accoda_lavoro(
        p_job_type => v_job_type,
        p_payload  => jsonb_build_object(
            'processo_codice',    v_processo,
            'stato',              v_stato,
            'tolleranza_minuti',  v_toll,
            'ultimo_segno_di_vita', v_ultimo,
            'muto_da',            (now() - v_ultimo)::text),
        -- SISTEMA: un avviso di manutenzione non appartiene a
        -- un'azienda, e il processo e' di classe MANUTENZIONE.
        p_run_as   => 'SISTEMA',
        p_scope    => NULL,
        p_idempotency_key => v_key,
        p_origine  => 'CRON');

    RETURN 'ACCODATO:' || v_job_id::text;
END
$function$

COMMENT ON FUNCTION dbops.fn_guardiano_digest()
IS 'Il corpo del job pgAgent guardiano_digest: chi guarda il guardiano. Legge lo stato di digest_presidi da dbops.vw_processi_programmazione — il criterio di MUTO sta LA'', accanto al CASE, non qui — e se e'' MUTO accoda UN lavoro NOTIFICA_DIGEST_MUTO per giorno su dbops.coda_lavori (chiave guardiano_digest:<giorno>, controllata in qualunque stato perche'' fn_accoda_lavoro dedupe solo fra PENDING/IN_CORSO). ⛔ Non manda una mail: pgAgent non spedisce e non conosce il destinatario, che e'' un fatto di deploy e resta nel backend. Il lavoro lo esegue draina_coda_lavori — il processo piu'' vivo, con badge in topbar — che spedisce col destinatario suo. ⭐ E'' la guardia reciproca: il digest guarda tutti, pgAgent guarda il digest, e il guardiano e'' a catalogo come PGAGENT quindi il panorama guarda anche lui. ⚠️ Solo MUTO, non MAI_PARTITO: un digest mai installato lo dice il panorama nel pannello, e un nagging orario su un''installazione nuova insegnerebbe a ignorare il guardiano. ⚠️ Finche'' il tipo NOTIFICA_DIGEST_MUTO e'' attivo = false (backend senza handler), il digest vivo tiene il job verde, e il digest MUTO fa sollevare E_JOB_TYPE_NON_ATTIVO — corsa rossa in vw_job_run_da_guardare, cioe'' «ho visto e non ho potuto dirlo»: voluto, non si aggira. Torna l''esito come testo: DIGEST_<stato>, GIA_NOTIFICATO_OGGI, ACCODATO:<id>. Brief: brief-db-quattro-processi-senza-presidio §10.2, decisione di Tid 2026-09-11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
