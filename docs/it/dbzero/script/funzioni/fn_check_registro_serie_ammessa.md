# ⚙️ Funzione `fn_check_registro_serie_ammessa`

```sql
CREATE FUNCTION fn_check_registro_serie_ammessa(p_famiglia_documento character varying, p_serie character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_registro_serie_ammessa(p_famiglia_documento character varying, p_serie character varying)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi  jsonb := '[]'::jsonb;
    v_colonna vendite.famiglie_documento.colonna_serie%TYPE;
    v_trovata boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire se un sezionale di questa famiglia puo' portare una
    --   SERIE. Funzione PURA (fn_check_*): nessuna scrittura,
    --   nessun raise di dominio.
    --   Consumatori: il guard di vendite.registri_fatturazione,
    --   che la CHIAMA per rifiutare (§12.5.2), e la maschera del
    --   registro, che deve disabilitare il campo col PERCHE'.
    --
    -- Ritorna: [] se la serie e' ammessa (o non e' valorizzata);
    --   altrimenti array ORDINATO di {codice, reason, reason_key,
    --   dettaglio, valori}.
    --
    -- ⭐ SI INTERROGA PER FAMIGLIA, NON PER REGISTRO, e non e'
    --   una comodita': il guard deve rispondere anche in INSERT,
    --   quando il registro NON ESISTE ANCORA. Una check che
    --   partisse dall'id non saprebbe rispondere proprio nel
    --   momento in cui si sta creando la riga sbagliata.
    --
    -- ⛔ PERCHE' IL DIVIETO: la serie entra nella chiave del
    --   contatore, quindi cambiarla apre un secchio nuovo che
    --   riparte da 1. Se il documento la serie non la registra e
    --   non ce l'ha nel proprio vincolo di unicita' (resi,
    --   commesse), quel numero collide con uno gia' emesso: il
    --   vincolo rifiuta, il rollback riporta indietro anche il
    --   contatore, e il documento non si numera piu'.
    -- =========================================================

    -- ⭐ Serie assente = niente da vietare. Si guarda il VALORE, e
    --   la stringa vuota e' un'assenza: e' cio' che il form manda
    --   quando il campo non e' compilato.
    IF COALESCE(btrim(p_serie), '') = '' THEN
        RETURN v_motivi;
    END IF;

    IF p_famiglia_documento IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT f.colonna_serie, true
      INTO v_colonna, v_trovata
      FROM vendite.famiglie_documento f
     WHERE f.codice_interno = p_famiglia_documento;

    -- ⛔ BOOTSTRAP, NON FAIL-OPEN. In esercizio questo ramo non si
    --   raggiunge: fk_registri_fatturazione_famiglia garantisce che
    --   la famiglia esista, e a rifiutare sarebbe lei con un
    --   messaggio suo. Si raggiunge in UNA finestra sola — il
    --   migrate di un database ricostruito da zero, dove il mirror
    --   dei registri gira prima di quello delle famiglie perche'
    --   includeAll ordina per nome file.
    -- ⚠️ Senza questo ramo, il guard farebbe fallire il migrate su
    --   un database nuovo. Lo stato finale lo verifica il pgTAP.
    IF NOT COALESCE(v_trovata, false) THEN
        RETURN v_motivi;
    END IF;

    IF v_colonna IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_REGISTRO_SERIE_NON_AMMESSA',
            'reason',     'SERIE_NON_GESTITA',
            'reason_key', 'amministrazione.registri_fatturazione.serie_blocco.non_gestita',
            'dettaglio',  jsonb_build_object(
                              'famiglia_documento', p_famiglia_documento,
                              'serie',              p_serie),
            -- ⭐ I due valori riempiono i due %s del messaggio a
            --   catalogo, NELL'ORDINE: prima la famiglia che non
            --   gestisce le serie, poi la serie che si stava
            --   scrivendo. ⛔ Nessun nome di colonna o di
            --   parametro: qui va cio' che una PERSONA legge.
            -- ⚠️ L'ordine si verifica LEGGENDO LA FRASE RESA, non
            --   contando i segnaposto: la prima stesura passava
            --   (serie, famiglia) su un messaggio che comincia per
            --   «Registro %s», e a video usciva «Registro X1» —
            --   l'etichetta di un campo davanti al valore di un
            --   altro. Arita' giusta, frase falsa.
            'valori',     jsonb_build_array(p_famiglia_documento, p_serie));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_registro_serie_ammessa(p_famiglia_documento character varying, p_serie character varying)
IS 'Pure check (§12.5.1): un sezionale di questa famiglia puo'' portare una SERIE? Ritorna [] se si'' (o se la serie non e'' valorizzata), altrimenti il motivo SERIE_NON_GESTITA. NOMINA il codice e non solleva. Consumatori: vendite.trgfn_registri_fatturazione_guard_serie_ammessa, che la CHIAMA per rifiutare (§12.5.2), e la maschera del registro, che deve disabilitare il campo col PERCHE'' invece di lasciarlo grigio. ⭐ SI INTERROGA PER FAMIGLIA E SERIE, NON PER registro_id, e non e'' una comodita'': il guard deve poter rispondere anche in INSERT, quando il registro non esiste ancora — una check che partisse dall''id sarebbe muta proprio nel momento in cui si crea la riga sbagliata. ⛔ PERCHE'' IL DIVIETO ESISTE: la serie entra nella chiave del contatore (uq_regprog_key), quindi cambiare serie_default apre un secchio nuovo che riparte da 1. Su fatture, ddt e ordini e'' innocuo — la serie e'' in colonna E nel vincolo di unicita'' del numero, quindi i blocchi restano distinguibili, ed e'' il modo legittimo di aprire una serie. Su resi e commesse no: non la registrano da nessuna parte, quindi il numero 1 collide con uno gia'' emesso, il vincolo rifiuta e col rollback torna indietro anche il contatore — il documento non si numera piu''. ⭐ LA FONTE E'' vendite.famiglie_documento.colonna_serie, cioe'' il NOME della colonna sul documento: NULL = questa famiglia una serie non ce l''ha. Il nome e non un booleano, cosi'' il presidio puo'' verificare che la colonna esista davvero. ⛔ IL RAMO «FAMIGLIA NON TROVATA» TACE, ED E'' BOOTSTRAP E NON FAIL-OPEN: in esercizio la FK fk_registri_fatturazione_famiglia garantisce la riga, e a rifiutare sarebbe lei; si raggiunge solo nel migrate di un database ricostruito da zero, dove il mirror dei registri gira prima di quello delle famiglie perche'' includeAll ordina per nome file — senza quel ramo il guard farebbe fallire il migrate. Lo stato finale lo verifica il pgTAP. ⚠️ Serie vuota o solo spazi = assenza: e'' cio'' che il form manda a campo non compilato. ⚠️ SECURITY INVOKER ed e'' motivato: si legge la sola vendite.famiglie_documento, che non ha la RLS (verificato 2026-09-01). ⛔ Il `reason` non porta il prefisso E_, riservato ai codici a catalogo (§12.5.1). ⚠️ La reason_key amministrazione.registri_fatturazione.serie_blocco.non_gestita e'' un DEBITO VERSO IL FE (§12.3). Piano: brief-db-registri-numerazione-chiave-del-contatore, sezione 5 (S-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
