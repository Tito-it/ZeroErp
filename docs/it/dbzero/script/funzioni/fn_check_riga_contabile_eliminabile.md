{% include-markdown "it/dbzero/script/manual/fn_check_riga_contabile_eliminabile.md" %}
# ⚙️ Funzione `fn_check_riga_contabile_eliminabile`

```sql
CREATE FUNCTION fn_check_riga_contabile_eliminabile(p_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_riga_contabile_eliminabile(p_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di ELIMINARE una riga
--        contabile — cioe' portarla ad attivo = false, o cancellarla.
--        Funzione PURA (fn_check_*): nessuna scrittura, nessun raise
--        di dominio (salvo i due guard di chiamata).
-- Consumatori: pagamenti.trgfn_vendite_contabili_righe_guard_contenuto
--        (solleva il codice del PRIMO motivo, su UPDATE OF attivo e su
--        DELETE) e il backend, in LATERAL sulla lista delle righe
--        (elimina_blocco_reason / elimina_blocco_reason_key).
-- Ritorna: [] se la riga si puo' eliminare — la distinta e' MANUALE e
--        in BOZZA — altrimenti array ORDINATO di
--        {codice, reason, reason_key, dettaglio, valori}.
-- ⚠️ I motivi sono tutti sulla TESTATA: la riga in se' non ha niente da
--    dire — una riga POSTATA sta per costruzione sotto una CHIUSA, e la
--    ferma il motivo 1. Brief: brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga §2.2.
-- ⭐ Rev 2026-09-30 (D-2, D-3): il motivo 1 si sdoppia — prima
--    DISTINTA_ANNULLATA (righe_lavorabili = false), poi in alternativa
--    DISTINTA_FINALE. Brief: brief-db-righe-distinta-annullata-fuori-dalle-code §4.2.
DECLARE
    -- NUDO di proposito: l'array dei motivi non riflette nessuna colonna.
    v_motivi           jsonb := '[]'::jsonb;
    v_contabile_id     pagamenti.vendite_contabili.id%TYPE;
    v_codice           pagamenti.vendite_contabili.codice%TYPE;
    v_origine          pagamenti.vendite_contabili.origine%TYPE;
    v_stato            pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_is_final         pagamenti.vendite_contabili_stati.is_final%TYPE;
    v_righe_lavorabili pagamenti.vendite_contabili_stati.righe_lavorabili%TYPE;
BEGIN
    -- ⛔ Guard di PARAMETRO, e solleva: un id assente o <= 0 non lo
    --    produce nessuna interfaccia — e' il chiamante a essere rotto.
    --    TECNICO, e non E_PARAMETRO_INVALIDO, che e' un debito e non
    --    una sede (AGENTS.md).
    IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_riga_contabile_eliminabile',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_riga_id',
                               'valore',    p_riga_id),
            NULL::uuid,
            'script.fn_check_riga_contabile_eliminabile',
            'identificativo della riga contabile non valido');
    END IF;

    -- La riga e la sua testata, in una lettura sola. ⚠️ Sotto la row
    -- security: chi vede la riga vede la testata per la stessa
    -- catena di scope (via contabile), quindi «non trovata» qui
    -- vuol dire «non esiste» oppure «non e' tua» — e le due risposte
    -- devono restare indistinguibili.
    SELECT c.id, c.codice, c.origine, s.codice_interno, s.is_final,
           s.righe_lavorabili
      INTO v_contabile_id, v_codice, v_origine, v_stato, v_is_final,
           v_righe_lavorabili
      FROM pagamenti.vendite_contabili_righe r
      JOIN pagamenti.vendite_contabili c       ON c.id = r.contabile_id
      JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
     WHERE r.id = p_riga_id;

    -- ⛔ Non si risponde [] su una riga che non si legge: sarebbe
    --    «si puo' eliminare» detto di una cosa che non si vede, cioe'
    --    un fail-open silenzioso. Stesso codice del mirror del
    --    movimento, stessa frase, classe NON_TROVATO.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_riga_contabile_eliminabile',
            'E_RIGA_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_riga_id', p_riga_id),
            NULL::uuid,
            p_riga_id::text);
    END IF;

    -- MOTIVO 1a — le righe di questa distinta NON SI LAVORANO PIU'
    --    (righe_lavorabili = false: l'ANNULLATA). Rev 2026-09-30, D-2/D-3.
    -- ⭐ La domanda si fa al CATALOGO, non a is_final: CHIUSA e
    --    ANNULLATA sono entrambe finali e opposte per le righe.
    -- ⚠️ IS NOT TRUE: la colonna e' NOT NULL, ma se la testata non
    --    si leggesse la risposta resta il rifiuto (fail-closed).
    -- ⭐ Codice proprio (D-2): il rimedio e' diverso da quello di una
    --    chiusa — sotto un'annullata non c'e' niente da fare.
    IF v_righe_lavorabili IS NOT TRUE THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
            'reason',     'DISTINTA_ANNULLATA',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_annullata',
            'dettaglio',  jsonb_build_object('contabile_id',   v_contabile_id,
                                             'stato_distinta', v_stato),
            'valori',     jsonb_build_array(v_codice));

    -- MOTIVO 1b — la distinta e' FINALE ma le sue righe si lavorano
    --    ancora (oggi: la CHIUSA — tardiva, «Riprendi»): eliminare no.
    -- ⭐ Riuso di E_RIGA_CONTABILE_DISTINTA_FINALE con gli STESSI due
    --    valori del guard d'ingresso: e' la stessa condizione da una
    --    porta in piu', non un accumulo. Vale per ogni origine, e
    --    copre da sola la riga POSTATA (sta sotto una CHIUSA per
    --    costruzione): nessun motivo «riga registrata».
    -- ⚠️ ELSIF e non IF: sotto un'annullata il motivo 1a ha gia'
    --    detto la cosa giusta, e questo aggiungerebbe un rimedio
    --    sbagliato al `motivi` del contesto.
    ELSIF v_is_final IS TRUE THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_FINALE',
            'reason',     'DISTINTA_FINALE',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_finale',
            'dettaglio',  jsonb_build_object('contabile_id',   v_contabile_id,
                                             'stato_distinta', v_stato),
            'valori',     jsonb_build_array(
                              v_codice,
                              CASE WHEN v_stato = 'ANNULLATA'
                                   THEN 'annullata' ELSE 'chiusa' END));
    END IF;

    -- MOTIVO 2 — la distinta NON e' compilata a mano.
    -- Eliminare e' il rimedio a un errore di DIGITAZIONE, e su una
    -- GENERATA o una AUTOMATICA nessuno ha digitato: la generata la
    -- governa il giro che l'ha prodotta (fn_cancella_fondo_fattura,
    -- fn_annulla_sistemazione), l'automatica e' la copia di un file.
    -- ⚠️ Le due frasi sono le stesse di E_CONTABILE_RIAPERTURA_NON_MANUALE:
    --    un vocabolario solo per dire «da dove viene» la distinta.
    IF v_origine IS DISTINCT FROM 'MANUALE' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_NON_MANUALE',
            'reason',     'DISTINTA_NON_MANUALE',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_non_manuale',
            'dettaglio',  jsonb_build_object('contabile_id', v_contabile_id,
                                             'origine',      v_origine),
            'valori',     jsonb_build_array(
                              v_codice,
                              CASE v_origine
                                  WHEN 'AUTOMATICA' THEN 'arrivata da un file'
                                  WHEN 'GENERATA'   THEN 'prodotta dal sistema'
                                  ELSE v_origine
                              END));
    END IF;

    -- MOTIVO 3 — la MANUALE non e' piu' in BOZZA (D18).
    -- «Ho finito di inserire» congela il contenuto: si riapre, si
    -- elimina, si rivalida. ⚠️ Scritto SOLO per la manuale: su una
    -- generata «torna in bozza» e' un rimedio che non esiste, e il
    -- motivo 2 ha gia' detto la cosa giusta. ⚠️ Whitelist (= BOZZA) e
    -- non blacklist (<> VALIDATA): uno stato nuovo non finale cade
    -- nel rifiuto, non nel silenzio. ⚠️ E' la STESSA condizione che
    -- il guard applica sull'INSERT e sui fatti (porta 2 di
    -- trgfn_vendite_contabili_righe_guard_contenuto): li' non c'e'
    -- una riga da passare, quindi la scrive lui — il pgTAP le lega.
    IF v_origine = 'MANUALE'
       AND v_is_final IS NOT TRUE
       AND v_stato IS DISTINCT FROM 'BOZZA'
    THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_VALIDATA',
            'reason',     'DISTINTA_VALIDATA',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_validata',
            'dettaglio',  jsonb_build_object('contabile_id',   v_contabile_id,
                                             'stato_distinta', v_stato),
            'valori',     jsonb_build_array(v_codice));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_riga_contabile_eliminabile(p_riga_id bigint)
IS 'Pure check (§12.5.1): i motivi che impediscono di ELIMINARE una riga contabile — attivo = false, oppure DELETE. Ritorna [] se si puo'' (la distinta e'' MANUALE e in BOZZA), altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva (salvo i due guard di chiamata). ⭐ SEDE UNICA del predicato: pagamenti.trgfn_vendite_contabili_righe_guard_contenuto la CHIAMA su UPDATE OF attivo (true -> false) e su DELETE e solleva il codice del primo motivo con fn_raise_primo_motivo_se_presente; il backend la legge in LATERAL sulla lista delle righe (elimina_blocco_reason) per spegnere il cestino col perche'' — cosi'' tooltip e rifiuto non possono divergere (§12.5.2). ⚠️ L''ORDINE e'' il contratto: (1a) DISTINTA_ANNULLATA — la testata e'' in uno stato con righe_lavorabili = false (l''ANNULLATA), E_RIGA_CONTABILE_DISTINTA_ANNULLATA: le righe di un documento che non e'' mai successo si leggono soltanto (D-3), e il rimedio non e'' quello di una chiusa (D-2); (1b) in ALTERNATIVA, DISTINTA_FINALE — le altre finali, oggi la CHIUSA, per ogni origine: riusa E_RIGA_CONTABILE_DISTINTA_FINALE con gli stessi valori del guard d''ingresso e copre da sola la riga POSTATA (sta sotto una CHIUSA per costruzione: nessun motivo «riga registrata», sarebbe irraggiungibile); (2) DISTINTA_NON_MANUALE — GENERATA o AUTOMATICA: eliminare a mano e'' il rimedio a un errore di digitazione, e li'' nessuno ha digitato — la generata la governa il giro che l''ha prodotta; (3) DISTINTA_VALIDATA — la MANUALE non piu'' in BOZZA (D18): si riapre, si elimina, si rivalida. Il 3 e'' scritto SOLO per la manuale: su una generata «torna in bozza» non e'' un rimedio. ⭐ 1a si legge dalla bandiera di catalogo e non da is_final: CHIUSA e ANNULLATA sono entrambe finali e opposte per le righe. ⚠️ SECURITY INVOKER e legge sotto la row security: chi vede la riga vede la testata per la stessa catena di scope (via contabile). Riga non leggibile — inesistente o di un altro — solleva E_RIGA_CONTABILE_NON_TROVATA (404, no-leak): rispondere [] sarebbe un fail-open. ⛔ Guard di parametro su E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO), non su E_PARAMETRO_INVALIDO. ⛔ Il reason non porta il prefisso E_. ⚠️ Le reason_key pagamenti.righe.elimina_reason.* sono un DEBITO VERSO IL FE (§12.3): distinta_annullata nasce il 2026-09-30 e va nei locales it/en nello stesso giro. Brief: brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga §2.2 (D17), §4 P-1; brief-db-righe-distinta-annullata-fuori-dalle-code §4.2, §8.1 (D-2, D-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
