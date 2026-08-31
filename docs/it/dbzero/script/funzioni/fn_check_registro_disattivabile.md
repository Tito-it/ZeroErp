# ⚙️ Funzione `fn_check_registro_disattivabile`

```sql
CREATE FUNCTION fn_check_registro_disattivabile(p_registro_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_registro_disattivabile(p_registro_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi  jsonb := '[]'::jsonb;
    v_codice  vendite.registri_fatturazione.codice%TYPE;
    v_n       bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di DISATTIVARE un
    --   registro di numerazione. Funzione PURA (fn_check_*):
    --   nessuna scrittura, e nessun raise di dominio.
    --   Consumatori: la lista dei registri, che spegne il cestino
    --   di riga e dice perche' invece di far scoprire il vincolo
    --   sbagliando.
    --
    -- Ritorna: [] se si puo' disattivare; altrimenti array
    --   ORDINATO di {codice, reason, reason_key, dettaglio, valori}
    --   (§12.5.1). ⚠️ L'ordine e' il contratto: la superficie
    --   mostra il primo.
    --
    -- ⛔ SU QUESTA TABELLA I GUARD SONO TRE, e il secondo e' quello
    --   che sorprende: un registro che ha numerato anche UN SOLO
    --   documento ha una riga di contatore viva, quindi non si
    --   spegne piu'. Il cestino e' percio' quasi sempre
    --   indisponibile — e senza un motivo a video l'operatore lo
    --   scopre premendo.
    --
    -- ⚠️ SECURITY DEFINER: si legge vendite.fatture, che ha la RLS.
    --   Sotto il perimetro di un operatore le fatture di un altro
    --   emittente sono invisibili, e la check concluderebbe «si puo'
    --   disattivare» PROPRIO nel caso da bloccare.
    -- =========================================================

    -- Guard di parametro: un id assente o non positivo non esce da
    -- nessuna interfaccia, lo produce un chiamante rotto.
    IF p_registro_id IS NULL OR p_registro_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_registro_disattivabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_registro_id',
                               'valore', p_registro_id),
            NULL::uuid,
            'script.fn_check_registro_disattivabile',
            'identificativo del registro non valido');
    END IF;

    SELECT r.codice INTO v_codice
      FROM vendite.registri_fatturazione r
     WHERE r.id = p_registro_id;

    -- ⚠️ Qui «non esiste» e' davvero «non esiste»: la funzione e'
    --   DEFINER, quindi non c'e' il caso «non lo vedo».
    -- ⭐ E non si risponde []: sarebbe «si puo' disattivare», che su
    --   una riga inesistente e' una frase senza senso. Stesso ramo
    --   della gemella script.fn_check_annullo_movimento_titolo_iva.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_registro_disattivabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('registro_id', p_registro_id),
            NULL::uuid,
            'script.fn_check_registro_disattivabile',
            concat('registro ', p_registro_id, ' inesistente'));
    END IF;

    -- ---- MOTIVO 1 — ha fatture -------------------------------
    -- ⛔ «ESISTONO», non «esistono ATTIVE»: vendite.fatture NON HA
    --   la colonna `attivo`, quindi dbops.trgfn_prevent_deactivate_if_children
    --   cade nel ramo dell'ESISTENZA e solleva
    --   E_ATTIVO_BLOCK_CHILDREN_EXIST. Una check che chiedesse
    --   «attive» direbbe «si puo' disattivare» dove il trigger
    --   rifiuta: i due divergerebbero in silenzio, ed e' il difetto
    --   che questa funzione esiste per non avere.
    SELECT count(*) INTO v_n
      FROM vendite.fatture f
     WHERE f.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_FATTURE',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_fatture',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            -- ⭐ I quattro valori compongono ESATTAMENTE la frase che il
            --   trigger produrrebbe: «Non si puo' disattivare %s (%s = %s):
            --   ci sono ancora righe collegate in %s.»
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.fatture'));
    END IF;

    -- ---- MOTIVO 2 — ha progressivi ---------------------------
    -- ⭐ E' quello che sorprende: basta UN documento numerato perche'
    --   esista una riga di contatore, e da li' il registro non si
    --   spegne piu'.
    -- ⚠️ Qui «ATTIVE» e' corretto — vendite.registri_fatturazione_progressivi
    --   la colonna `attivo` ce l'ha — quindi il codice e' _ACTIVE e non
    --   _EXIST: i progressivi gia' spenti non bloccano, ed e' il pattern
    --   «figli prima, padre poi».
    SELECT count(*) INTO v_n
      FROM vendite.registri_fatturazione_progressivi p
     WHERE p.registro_id = p_registro_id
       AND p.attivo IS TRUE;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_ACTIVE',
            'reason',     'HA_PROGRESSIVI',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_progressivi',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.registri_fatturazione_progressivi'));
    END IF;

    -- ---- MOTIVO 3 — ha mapping tipo documento ----------------
    -- ⚠️ Anche qui ESISTENZA e non «attive»: vendite.tipi_doc_fiscale_registri
    --   non ha la colonna `attivo`.
    SELECT count(*) INTO v_n
      FROM vendite.tipi_doc_fiscale_registri m
     WHERE m.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_MAPPING_TIPO_DOC',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_mapping_tipo_doc',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.tipi_doc_fiscale_registri'));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_registro_disattivabile(p_registro_id bigint)
IS 'Pure check (§12.5.1): i motivi che impediscono di DISATTIVARE un registro di numerazione. Ritorna [] se si puo'' disattivare, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva (salvo i due guard di chiamata). Consumatore: la lista dei registri, che spegne il cestino di riga e dice PERCHE'' invece di far scoprire il vincolo sbagliando. ⛔ Su vendite.registri_fatturazione i guard di disattivazione sono TRE (fatture, progressivi, mapping tipo documento), e il secondo e'' quello che sorprende: un registro che ha numerato anche UN SOLO documento ha una riga di contatore viva, quindi non si spegne piu''. Il cestino e'' percio'' quasi sempre indisponibile, e senza un motivo a video l''operatore lo scopre premendo. ⭐ NESSUN CODICE ERRORE NUOVO: la check nomina E_ATTIVO_BLOCK_CHILDREN_EXIST e E_ATTIVO_BLOCK_CHILDREN_ACTIVE, gia'' a catalogo con la loro policy — se per scriverla fosse servito un codice nuovo il difetto sarebbe stato a monte (§12.5.2). ⛔ E LA SCELTA FRA I DUE CODICI NON E'' STILISTICA: dbops.trgfn_prevent_deactivate_if_children guarda se la tabella FIGLIA ha la colonna `attivo` — se ce l''ha blocca sulle sole righe ATTIVE (_ACTIVE), altrimenti sulla loro ESISTENZA (_EXIST). Verificato il 2026-08-31: vendite.fatture e vendite.tipi_doc_fiscale_registri NON hanno `attivo` (quindi _EXIST, e il predicato e'' «esistono», non «esistono attive»), vendite.registri_fatturazione_progressivi ce l''ha (quindi _ACTIVE). ⚠️ Una check che avesse chiesto «fatture ATTIVE» avrebbe risposto «si puo'' disattivare» dove il trigger rifiuta: i due sarebbero divergiti in silenzio, che e'' esattamente il difetto per cui questa funzione esiste. ⭐ I `valori` compongono la STESSA frase che il trigger produrrebbe (tabella padre, colonna, valore, tabella figlia), cosi'' il tooltip del pulsante e l''errore del rifiuto si leggono uguali. ⛔ I `reason` NON portano il prefisso E_, riservato ai codici a catalogo: il guardrail cerca i letterali E_* nei corpi delle funzioni e li leggerebbe come codici senza policy — regola costata un changeSet il 2026-08-31 (E_UN_ANNULLO -> RIGA_DI_ANNULLO). ⚠️ SECURITY DEFINER: si legge vendite.fatture, che ha la RLS — da INVOKER le fatture di un altro emittente sarebbero invisibili e la risposta sarebbe «si puo'' disattivare» proprio nel caso da bloccare. ⚠️ Registro inesistente: si SOLLEVA E_VENDITE_CHIAMATA_NON_VALIDA invece di rispondere [], perche'' «si puo'' disattivare» su una riga che non esiste e'' una frase senza senso — stesso ramo della gemella script.fn_check_annullo_movimento_titolo_iva. ⚠️ Le tre reason_key sono un DEBITO VERSO IL FE (§12.3): vanno aggiunte ai locales nello stesso giro, o scripts/check_i18n_keys.py fallisce. Richiesta: brief-db-richieste-aperte-dal-backend-2, voce 2.';
```

---
{% include-markdown "signature-core.md" %}
