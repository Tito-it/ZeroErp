# ⚙️ Funzione `fn_check_registro_disattivabile`

```sql
CREATE FUNCTION fn_check_registro_disattivabile(p_registro_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

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
    -- ⭐ L'ORDINE E' QUELLO DEI TRIGGER, non uno di comodo. I
    --   BEFORE ROW scattano in ordine ALFABETICO di nome, e i
    --   guard si chiamano trg_registri_fatturazione_a10_<figlia>_…
    --   ⇒ i motivi seguono il NOME DELLA TABELLA FIGLIA, cosi' il
    --   primo motivo e' quello che il rifiuto nominerebbe davvero.
    --   Un ordine diverso farebbe dire al tooltip «ha fatture» e
    --   all'errore «ha DDT», sullo stesso registro.
    --
    -- ⛔ SU QUESTA TABELLA I GUARD SONO OTTO, ed erano tre fino al
    --   2026-08-31, sei fino al 2026-09-02 e sette fino al
    --   2026-09-17: ddt, ordini e resi hanno guadagnato
    --   `registro_id` col trasloco, `commesse` col changeSet
    --   20260902-07, e `pagamenti.vendite_contabili` — la
    --   distinta di incasso, PRIMA figlia fuori da `vendite` —
    --   col 20260915-21. Ogni volta l'automazione ATTIVO ha
    --   montato il guard DA SOLA a partire dalla FK, a ci_apply,
    --   senza annunciarlo — a dirlo e' stato il pgTAP §6, che
    --   confronta i montati con i coperti.
    --   ⚠️ Quello che sorprende resta il contatore: un registro
    --   che ha numerato anche UN SOLO documento ha una riga di
    --   progressivi viva, quindi non si spegne piu'. Il cestino e'
    --   percio' quasi sempre indisponibile — e senza un motivo a
    --   video l'operatore lo scopre premendo.
    --
    -- ⚠️ SECURITY DEFINER: si legge vendite.fatture, vendite.ddt,
    --   vendite.ordini, vendite.resi, vendite.commesse e
    --   pagamenti.vendite_contabili, che hanno la RLS. Sotto il
    --   perimetro di un operatore i documenti di un altro
    --   emittente sono invisibili, e la check concluderebbe «si
    --   puo' disattivare» PROPRIO nel caso da bloccare.
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

    -- ---- MOTIVO 1 — ha commesse ------------------------------
    -- ⛔ NUOVO dal 2026-09-02, e PRIMO perche' `commesse` precede
    --   `ddt` in ordine alfabetico: e' il guard che scatta per
    --   primo, quindi e' la frase che l'operatore vedrebbe.
    -- ⚠️ «ESISTONO» e non «esistono ATTIVE»: vendite.commesse non
    --   ha la colonna `attivo`, quindi il trigger cade nel ramo
    --   dell'ESISTENZA (_EXIST). Verificato su pg_attribute, e
    --   confermato dal messaggio reale del rifiuto.
    -- ⭐ Da qui discende una durezza che conviene sapere: una
    --   commessa non si cancella, quindi un registro che ne ha
    --   numerata anche una sola non si spegne piu'.
    SELECT count(*) INTO v_n
      FROM vendite.commesse cm
     WHERE cm.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_COMMESSE',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_commesse',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.commesse'));
    END IF;

    -- ---- MOTIVO 2 — ha documenti di trasporto ----------------
    -- ⛔ NUOVO dal 2026-08-31.
    -- ⚠️ «ESISTONO» e non «esistono ATTIVI»: vendite.ddt non ha la
    --   colonna `attivo`, quindi il trigger cade nel ramo
    --   dell'ESISTENZA (_EXIST). Verificato, non dedotto.
    SELECT count(*) INTO v_n
      FROM vendite.ddt d
     WHERE d.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_DDT',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_ddt',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.ddt'));
    END IF;

    -- ---- MOTIVO 3 — ha fatture -------------------------------
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

    -- ---- MOTIVO 4 — ha ordini --------------------------------
    -- ⛔ NUOVO dal 2026-08-31. _EXIST: vendite.ordini non ha `attivo`.
    SELECT count(*) INTO v_n
      FROM vendite.ordini o
     WHERE o.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_ORDINI',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_ordini',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.ordini'));
    END IF;

    -- ---- MOTIVO 5 — ha progressivi ---------------------------
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

    -- ---- MOTIVO 6 — ha resi ----------------------------------
    -- ⛔ NUOVO dal 2026-08-31. _EXIST: vendite.resi non ha `attivo`.
    SELECT count(*) INTO v_n
      FROM vendite.resi re
     WHERE re.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_RESI',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_resi',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'vendite.resi'));
    END IF;

    -- ---- MOTIVO 7 — ha mapping tipo documento ----------------
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

    -- ---- MOTIVO 8 — ha distinte di incasso -------------------
    -- ⛔ NUOVO dal 2026-09-18, e ULTIMO perche' `vendite_contabili`
    --   segue `tipi_doc_fiscale_registri` in ordine alfabetico: e'
    --   il guard che scatta per ultimo, quindi su un registro che
    --   ha anche il contatore vivo il rifiuto nomina i progressivi,
    --   non la distinta.
    -- ⭐ PRIMA figlia FUORI da `vendite`: la distinta contabile di
    --   incasso (`pagamenti.vendite_contabili`) e' numerata sul
    --   registro dal 2026-09-17 (20260915-21, famiglia DISTINTA,
    --   registri DIS-<sr>). Il quarto valore porta lo schema
    --   giusto, perche' e' la frase che il trigger compone con
    --   child_schema || '.' || child_table.
    -- ⚠️ «ESISTONO» e non «esistono ATTIVE»: pagamenti.vendite_contabili
    --   non ha la colonna `attivo` — ha uno `stato_id` (BOZZA,
    --   VALIDATA, …), che per il trigger non conta: cade nel ramo
    --   dell'ESISTENZA (_EXIST). Verificato con fn_col_exists, le
    --   stesse funzioni del trigger.
    -- ⭐ Durezza da sapere: una distinta numerata non si cancella,
    --   quindi un registro DIS-* che ne ha numerata anche una sola
    --   non si spegne piu'.
    SELECT count(*) INTO v_n
      FROM pagamenti.vendite_contabili vc
     WHERE vc.registro_id = p_registro_id;

    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
            'reason',     'HA_DISTINTE',
            'reason_key', 'amministrazione.registri_fatturazione.disattiva_blocco.ha_distinte',
            'dettaglio',  jsonb_build_object('registro_id', p_registro_id,
                                             'codice',      v_codice,
                                             'quante',      v_n),
            'valori',     jsonb_build_array('vendite.registri_fatturazione',
                                            'id',
                                            p_registro_id::text,
                                            'pagamenti.vendite_contabili'));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_registro_disattivabile(p_registro_id bigint)
IS 'Pure check (§12.5.1): i motivi che impediscono di DISATTIVARE un registro di numerazione. Ritorna [] se si puo'' disattivare, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva (salvo i due guard di chiamata). Consumatore: la lista dei registri, che spegne il cestino di riga e dice PERCHE'' invece di far scoprire il vincolo sbagliando. ⛔ SU vendite.registri_fatturazione I GUARD SONO OTTO — erano TRE fino al 2026-08-31 (col trasloco ddt, ordini e resi hanno guadagnato registro_id), SEI fino al 2026-09-02 (commesse, 20260902-07) e SETTE fino al 2026-09-17 (pagamenti.vendite_contabili, la distinta di incasso, 20260915-21: la PRIMA figlia fuori dallo schema vendite). Ogni volta l''automazione ATTIVO ha montato il guard di disattivazione DA SOLA a partire dalla FK, a ci_apply, senza annunciarlo — e ogni volta l''ha detto il test 6 del pgTAP, che confronta i guard MONTATI (pg_trigger) con quelli COPERTI: e'' il presidio che sostituisce quello del §12.5.2, qui inapplicabile perche'' a rifiutare e'' un trigger GENERICO e non una madre di dominio. ⚠️ Quello che sorprende resta il contatore: un registro che ha numerato anche UN SOLO documento ha una riga di progressivi viva, quindi non si spegne piu'' — il cestino e'' percio'' quasi sempre indisponibile. ⭐ NESSUN CODICE ERRORE NUOVO: la check nomina E_ATTIVO_BLOCK_CHILDREN_EXIST e E_ATTIVO_BLOCK_CHILDREN_ACTIVE, gia'' a catalogo con la loro policy — se per scriverla fosse servito un codice nuovo il difetto sarebbe stato a monte (§12.5.2). ⛔ E LA SCELTA FRA I DUE CODICI NON E'' STILISTICA: dbops.trgfn_prevent_deactivate_if_children guarda se la tabella FIGLIA ha la colonna `attivo` — se ce l''ha blocca sulle sole righe ATTIVE (_ACTIVE), altrimenti sulla loro ESISTENZA (_EXIST). Verificato: commesse, ddt, fatture, ordini, resi, tipi_doc_fiscale_registri e vendite_contabili NON hanno `attivo` (quindi _EXIST — la distinta ha uno stato_id, che per il trigger non conta), vendite.registri_fatturazione_progressivi ce l''ha (quindi _ACTIVE). ⚠️ Una check che avesse chiesto «documenti ATTIVI» avrebbe risposto «si puo'' disattivare» dove il trigger rifiuta: i due sarebbero divergiti in silenzio, che e'' esattamente il difetto per cui questa funzione esiste. ⭐ L''ORDINE DEI MOTIVI E'' QUELLO DEI TRIGGER, non uno di comodo: i BEFORE ROW scattano in ordine ALFABETICO di nome e i guard si chiamano trg_registri_fatturazione_a10_<figlia>_…, quindi i motivi seguono il NOME DELLA TABELLA FIGLIA (commesse, ddt, fatture, ordini, registri_fatturazione_progressivi, resi, tipi_doc_fiscale_registri, vendite_contabili). Un ordine diverso farebbe dire al tooltip «ha fatture» e all''errore «ha DDT», sullo stesso registro. ⭐ I `valori` compongono la STESSA frase che il trigger produrrebbe (tabella padre, colonna, valore, tabella figlia CON LO SCHEMA — per la distinta `pagamenti.vendite_contabili`), cosi'' il tooltip del pulsante e l''errore del rifiuto si leggono uguali. ⛔ L''ELENCO DELLE FIGLIE RESTA SCRITTO A MANO, e derivarlo da pg_trigger sarebbe peggio: ogni motivo porta una reason_key da tradurre, e un elenco derivato inventerebbe una chiave che nessuno ha tradotto — la superficie mostrerebbe la chiave nuda, cioe'' un difetto MUTO in produzione al posto di un test rosso in sviluppo. E'' un elenco parallelo TENUTO da un presidio, che e'' un''altra cosa da un elenco parallelo lasciato a se stesso. ⛔ I `reason` NON portano il prefisso E_, riservato ai codici a catalogo: il guardrail cerca i letterali E_* nei corpi delle funzioni e li leggerebbe come codici senza policy — regola costata un changeSet il 2026-08-31 (E_UN_ANNULLO -> RIGA_DI_ANNULLO). ⚠️ SECURITY DEFINER: si leggono vendite.fatture, ddt, ordini, resi, commesse e pagamenti.vendite_contabili, che hanno la RLS — da INVOKER i documenti di un altro emittente sarebbero invisibili e la risposta sarebbe «si puo'' disattivare» proprio nel caso da bloccare. ⚠️ Registro inesistente: si SOLLEVA E_VENDITE_CHIAMATA_NON_VALIDA invece di rispondere [], perche'' «si puo'' disattivare» su una riga che non esiste e'' una frase senza senso — stesso ramo della gemella script.fn_check_annullo_movimento_titolo_iva. ⚠️ Le OTTO reason_key sono un DEBITO VERSO IL FE (§12.3): sette sono nei locales, `ha_distinte` (2026-09-18) va aggiunta nello stesso giro, o il tooltip mostra la chiave nuda. Richiesta d''origine: brief-db-richieste-aperte-dal-backend-2, voce 2; ottavo guard: brief-db-distinta-numerata-sul-registro (P-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
