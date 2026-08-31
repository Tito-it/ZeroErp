# ⚙️ Funzione `fn_assegna_numero_documento`

```sql
CREATE FUNCTION fn_assegna_numero_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_data date, p_documento_id bigint, p_utility_id integer, p_corpo text, p_serie character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_assegna_numero_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_data date, p_documento_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_corpo text DEFAULT NULL::text, p_serie character varying DEFAULT NULL::character varying)
 RETURNS TABLE(registro_id bigint, anno smallint, progressivo bigint, numero text, serie character varying)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_registro vendite.registri_fatturazione.id%TYPE;
    v_serie    vendite.registri_fatturazione.serie_default%TYPE;
    v_prefisso vendite.registri_fatturazione.prefisso%TYPE;
    v_suffisso vendite.registri_fatturazione.suffisso%TYPE;
    v_len      vendite.registri_fatturazione.lunghezza_numero%TYPE;
    v_anno     vendite.ddt.anno%TYPE;
    v_num      bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I SEI PASSI che ogni documento numerato su un registro
    --   deve fare, in una sede sola: risolvere il registro,
    --   ricavare l'anno, chiedere il progressivo, leggere il
    --   formato, comporre.
    --
    -- ⛔ Prima stavano in QUATTRO funzioni identiche, e una
    --   correzione alla composizione andava fatta quattro volte:
    --   chi ne dimenticava una produceva un documento formattato
    --   diverso dagli altri, che nessun vincolo respinge.
    --
    -- ⚠️ Cosa NON fa, ed e' deliberato: non decide QUANDO. Il
    --   momento e' l'unica cosa che distingue davvero i quattro
    --   documenti — DDT a EMESSO, resi a CONFERMATO, ordini e
    --   commessa alla creazione — e resta nel trigger di ciascuno.
    -- =========================================================

    -- 1) Il registro. ⛔ L'INVOLUCRO e non il lettore: qui si
    --    scrive, e un emittente senza registro deve fermare.
    SELECT k.registro_id, k.serie
      INTO v_registro, v_serie
      FROM vendite.fn_get_registro_documento(
               p_famiglia_documento          => p_famiglia_documento,
               p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id,
               p_utility_id                  => p_utility_id) k;

    -- 2) L'anno, dalla DATA DEL DOCUMENTO.
    v_anno := vendite.fn_get_anno_registro(p_data);

    -- ⚠️ La serie si risolve UNA volta: quella del documento, poi
    --   quella del registro, poi vuota. Lo stesso valore va al
    --   contatore e torna al chiamante per la colonna.
    v_serie := COALESCE(p_serie, v_serie, '');

    -- 3) Il progressivo, sotto il lock del motore.
    v_num := vendite.fn_get_next_progressivo(
                 v_registro, p_data, NULL,
                 v_serie, p_documento_id,
                 p_famiglia_documento);

    -- 4) Il formato, da DUE sedi divise per RUOLO: la lunghezza e'
    --    del tipo documento e sta nel catalogo dei formati, il
    --    prefisso e il suffisso sono il nome del sezionale e
    --    stanno sul registro.
    SELECT sc.lunghezza_numero INTO v_len
      FROM config.sistema_codici sc
     WHERE sc.codice_interno = lower(p_famiglia_documento);

    SELECT r.prefisso, r.suffisso
      INTO v_prefisso, v_suffisso
      FROM vendite.registri_fatturazione r
     WHERE r.id = v_registro;

    -- 5) La composizione, dalla funzione pura.
    RETURN QUERY
    SELECT v_registro, v_anno, v_num,
           vendite.fn_componi_numero_documento(
               v_prefisso, p_corpo, v_num, v_len, v_suffisso),
           v_serie;
END;
$function$

COMMENT ON FUNCTION vendite.fn_assegna_numero_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_data date, p_documento_id bigint, p_utility_id integer, p_corpo text, p_serie character varying)
IS 'I SEI PASSI che ogni documento numerato su un registro deve fare, in una sede sola: risolve il registro, ricava l''anno dalla data del documento, chiede il progressivo al motore, legge il formato e compone. Torna (registro_id, anno, progressivo, numero, serie). ⭐ La SERIE risolta esce perche'' chi ha quella colonna deve scriverla: e'' la stessa che entra nella chiave del contatore, e risolverla due volte con due COALESCE diversi e'' il modo in cui il contatore e la UNIQUE cominciano a guardare sezionali diversi. ⛔ Prima stavano in QUATTRO funzioni identiche — vendite.trgfn_ddt_gen_numero_emesso, trgfn_ordini_gen_numero, trgfn_resi_gen_numero e fn_get_or_create_commessa — verificato il 2026-08-31: gli stessi sei passi, ognuno per conto proprio. ⚠️ Una correzione alla composizione andava fatta in quattro posti, e chi ne dimenticava uno produceva un difetto MUTO: un documento formattato diverso dagli altri, che nessun vincolo respinge. ⭐ TORNA ANCHE `progressivo` e non solo `numero`, ed e'' cio'' che permette alla commessa di usare la stessa funzione: il suo codice porta sigla e anno DENTRO la stringa, quindi passa quei due pezzi come `corpo` — vuoto per gli altri tre. ⚠️ COSA NON FA, ed e'' deliberato: non decide QUANDO. Il momento e'' l''unica cosa che distingue davvero i quattro documenti (DDT a EMESSO, resi a CONFERMATO, ordini e commessa alla creazione) e resta nel trigger di ciascuno — centralizzare anche quello significherebbe mettere in una funzione la sola cosa che non e'' comune. ⭐ Il formato viene da DUE sedi divise per RUOLO: la LUNGHEZZA e'' del tipo documento e resta in config.sistema_codici, PREFISSO e SUFFISSO sono il nome del sezionale e stanno sul registro. ⛔ Usa l''INVOLUCRO fn_get_registro_documento e non il lettore: qui si scrive, e un emittente senza registro deve fermare. ⚠️ SECURITY DEFINER: legge il registro, e chi la chiama e'' un trigger che gira sotto RLS. Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, P-3.';
```

---
{% include-markdown "signature-core.md" %}
