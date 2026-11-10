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
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
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
    --   ORDINATO di {codice, reason, reason_key, dettaglio}
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
                                             'quante',      v_n));
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
                                             'quante',      v_n));
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
                                             'quante',      v_n));
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
                                             'quante',      v_n));
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
                                             'quante',      v_n));
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
                                             'quante',      v_n));
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
                                             'quante',      v_n));
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
    --   registri DIS-<sr>).
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
                                             'quante',      v_n));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_registro_disattivabile(p_registro_id bigint)
IS 'Pure check: i motivi che impediscono di disattivare un registro di numerazione (vendite.registri_fatturazione). Ritorna [] se si puo'' disattivare, altrimenti l''array ordinato dei motivi {codice, reason, reason_key, dettaglio}; nomina i codici e non solleva, salvo E_VENDITE_CHIAMATA_NON_VALIDA per una chiamata senza registro o con un registro che non esiste. La consuma la lista dei registri, che spegne il cestino di riga e dice perche''. Ogni motivo e'' una tabella figlia su cui l''automazione ATTIVO monta il guard di disattivazione (dbops.trgfn_prevent_deactivate_if_children), con il codice che quel guard solleverebbe: E_ATTIVO_BLOCK_CHILDREN_ACTIVE per vendite.registri_fatturazione_progressivi, che ha la colonna attivo e blocca sulle sole righe attive; E_ATTIVO_BLOCK_CHILDREN_EXIST per commesse, ddt, fatture, ordini, resi, tipi_doc_fiscale_registri e pagamenti.vendite_contabili, che non ce l''hanno e bloccano sull''esistenza. Un motivo che chiedesse righe attive dove il guard conta l''esistenza direbbe «si puo'' disattivare» dove il guard rifiuta. L''ordine dei motivi e'' quello dei guard, che scattano in ordine alfabetico di nome, cioe'' della tabella figlia: il primo motivo e'' il rifiuto che l''operatore vedrebbe. Le frasi dei due codici non hanno valori; il dettaglio porta registro, codice e quante righe. L''elenco delle figlie e'' scritto a mano perche'' ogni motivo ha una reason_key tradotta, e il pgTAP confronta i guard montati con quelli coperti. I reason non portano il prefisso E_, riservato ai codici a catalogo. SECURITY DEFINER: le tabelle dei documenti hanno la RLS, e un conteggio sotto RLS risponderebbe «si puo'' disattivare» a chi non vede i documenti di un altro emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
