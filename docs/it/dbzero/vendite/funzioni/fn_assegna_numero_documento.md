{% include-markdown "it/dbzero/vendite/manual/fn_assegna_numero_documento.md" %}
# ⚙️ Funzione `fn_assegna_numero_documento`

```sql
CREATE FUNCTION fn_assegna_numero_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_data date, p_documento_id bigint, p_utility_id integer, p_corpo text, p_serie character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_assegna_numero_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_data date, p_documento_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_corpo text DEFAULT NULL::text, p_serie character varying DEFAULT NULL::character varying)
 RETURNS TABLE(registro_id bigint, anno smallint, progressivo bigint, numero text, serie character varying)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_registro vendite.registri_fatturazione.id%TYPE;
    v_serie    vendite.registri_fatturazione.serie_default%TYPE;
    v_prefisso vendite.registri_fatturazione.prefisso%TYPE;
    v_suffisso vendite.registri_fatturazione.suffisso%TYPE;
    v_len      vendite.registri_fatturazione.lunghezza_numero%TYPE;
    v_anno     vendite.ddt.anno%TYPE;
    v_num      bigint;
    -- ⭐ La scelta del sezionale: l'anno entra nella stringa del numero.
    v_anno_in  vendite.registri_fatturazione.anno_nel_numero%TYPE;
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

    -- 4) Il formato, TUTTO dalla stessa riga: prefisso, suffisso
    --    e lunghezza sono l'EFFETTIVO del sezionale e stanno sul
    --    registro. I DEFAULT stanno in vendite.famiglie_documento
    --    ed e' da li' che nascono i registri nuovi.
    --
    -- ⛔ Fino al 2026-08-31 la lunghezza si leggeva da
    --    config.sistema_codici, e quando il 20260831-53 ne ha
    --    tolto le quattro righe la SELECT ha smesso di trovarne:
    --    v_len NULL, COALESCE a 7 per tutti — giusto per caso su
    --    DDT, ordini e resi, e SBAGLIATO sulla commessa, che ne
    --    vuole 9. Un codice piu' corto, senza un errore.
    SELECT r.prefisso, r.suffisso, r.lunghezza_numero, r.anno_nel_numero
      INTO v_prefisso, v_suffisso, v_len, v_anno_in
      FROM vendite.registri_fatturazione r
     WHERE r.id = v_registro;

    -- 5) La composizione, dalla funzione pura.
    --
    -- ⭐ L'ANNO ENTRA NEL CORPO, e non e' cosmesi: un registro che azzera
    --   il progressivo ogni anno consegna la STESSA stringa in anni
    --   diversi. Il database non se ne accorge — la sua unicita' porta
    --   l'anno in colonna — quindi non fallisce niente e l'ambiguita'
    --   arriva intera a chi legge la lista o cita il numero al telefono.
    --   E' l'invariante degli assi dichiarati applicata alla stringa:
    --   cio' che discrimina il contatore deve discriminare anche il
    --   numero che una persona legge.
    --
    -- ⭐⭐ IN CODA AL CORPO DEL CHIAMANTE, E LA POSIZIONE E' UN FATTO
    --   MISURATO, non una preferenza. Il codice commessa di oggi e'
    --   `CMM-<sigla>-<anno>-<9 cifre>`: con l'anno DOPO il corpo
    --   (`sigla-`) la stringa esce identica byte per byte — verificato
    --   sui codici esistenti il 2026-09-08 — mentre con l'anno prima
    --   diventerebbe `CMM-<anno>-<sigla>-…`, cioe' una forma nuova
    --   accanto a quella vecchia sullo stesso registro. E' esattamente
    --   il difetto che il guard della forma esiste per impedire.
    --   ⇒ Il corpo risponde a CHI, l'anno a QUANDO, e il progressivo
    --   chiude: e' anche l'ordine che si legge meglio.
    --
    -- ⚠️ Il separatore e' `-`, lo stesso che la commessa gia' usa fra i
    --   pezzi del suo codice. Un solo separatore in tutto il dominio.
    RETURN QUERY
    SELECT v_registro, v_anno, v_num,
           vendite.fn_componi_numero_documento(
               v_prefisso,
               COALESCE(p_corpo, '')
                   || CASE WHEN v_anno_in THEN v_anno::text || '-' ELSE '' END,
               v_num, v_len, v_suffisso),
           v_serie;
END;
$function$

COMMENT ON FUNCTION vendite.fn_assegna_numero_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_data date, p_documento_id bigint, p_utility_id integer, p_corpo text, p_serie character varying)
IS 'I SEI PASSI che ogni documento numerato su un registro deve fare, in una sede sola: risolve il registro, ricava l''anno dalla data del documento, chiede il progressivo al motore, legge il formato e compone. Torna (registro_id, anno, progressivo, numero, serie). ⭐ La SERIE risolta esce perche'' chi ha quella colonna deve scriverla: e'' la stessa che entra nella chiave del contatore, e risolverla due volte con due COALESCE diversi e'' il modo in cui il contatore e la UNIQUE cominciano a guardare sezionali diversi. ⛔ Prima stavano in QUATTRO funzioni identiche — vendite.trgfn_ddt_gen_numero_emesso, trgfn_ordini_gen_numero, trgfn_resi_gen_numero e fn_get_or_create_commessa — verificato il 2026-08-31: gli stessi sei passi, ognuno per conto proprio. ⚠️ Una correzione alla composizione andava fatta in quattro posti, e chi ne dimenticava uno produceva un difetto MUTO: un documento formattato diverso dagli altri, che nessun vincolo respinge. ⭐ TORNA ANCHE `progressivo` e non solo `numero`, ed e'' cio'' che permette alla commessa di usare la stessa funzione: il suo codice porta sigla e anno DENTRO la stringa, quindi passa quei due pezzi come `corpo` — vuoto per gli altri tre. ⚠️ COSA NON FA, ed e'' deliberato: non decide QUANDO. Il momento e'' l''unica cosa che distingue davvero i quattro documenti (DDT a EMESSO, resi a CONFERMATO, ordini e commessa alla creazione) e resta nel trigger di ciascuno — centralizzare anche quello significherebbe mettere in una funzione la sola cosa che non e'' comune. ⭐ IL FORMATO VIENE TUTTO DAL REGISTRO, in una lettura sola: prefisso, suffisso e lunghezza sono l''EFFETTIVO del sezionale; i DEFAULT con cui un registro nasce stanno in vendite.famiglie_documento. ⛔ Dal 20260831-41 al 20260831-54 la LUNGHEZZA si leggeva invece da config.sistema_codici: quando il 20260831-53 ne ha tolto le quattro righe la SELECT ha smesso di trovarne, v_len e'' rimasta NULL e il COALESCE della composizione ha dato 7 a tutti — giusto per caso su DDT, ordini e resi, e SBAGLIATO sulla commessa, che ne vuole 9 (CMM-ACME-2026-0000007 invece di CMM-ACME-2026-000000007). Nessun errore, nessun vincolo violato: solo un codice piu'' corto, e la forma e'' proprio cio'' che separa i codici nuovi dal pregresso. ⚠️ LA LEZIONE: le preCondition del 20260831-53 verificavano che la sede NUOVA fosse popolata e nessuna chiedeva CHI LEGGE ancora quella vecchia — prima di cancellare una fonte si censiscono i suoi lettori (pg_proc.prosrc e i file pgTAP), non l''inventario del sostituto. ⛔ Usa l''INVOLUCRO fn_get_registro_documento e non il lettore: qui si scrive, e un emittente senza registro deve fermare. ⚠️ SECURITY DEFINER: legge il registro, e chi la chiama e'' un trigger che gira sotto RLS. Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, P-15.';
```

</div>

---
{% include-markdown "signature-core.md" %}
