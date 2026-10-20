{% include-markdown "it/dbzero/script/manual/fn_check_contabile_validabile.md" %}
# ⚙️ Funzione `fn_check_contabile_validabile`

```sql
CREATE FUNCTION fn_check_contabile_validabile(p_contabile_id bigint, p_importo_dichiarato numeric)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_contabile_validabile(p_contabile_id bigint, p_importo_dichiarato numeric)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di portare una distinta
--        contabile a VALIDATA — «ho finito di inserire» (D14-a-bis).
--        Funzione PURA (fn_check_*): nessuna scrittura, nessun raise di
--        dominio (salvo i due guard di chiamata).
-- Consumatori: pagamenti.trgfn_vendite_contabili_guard_validazione
--        (solleva il codice del PRIMO motivo entrando in VALIDATA) e il
--        backend, nel dettaglio della distinta (can_validare /
--        validazione_blocco_reason / _reason_key / _dettaglio).
-- Ritorna: [] se si puo' validare, altrimenti array ORDINATO di
--        {codice, reason, reason_key, dettaglio, valori}.
-- ⭐ p_importo_dichiarato e' un PARAMETRO e non si rilegge per id: il
--    guard gira BEFORE ROW e il valore che sta entrando non e' ancora
--    nella tabella. Chi chiama passa quello che vede (il guard
--    NEW.importo_dichiarato, il backend c.importo_dichiarato). NULL =
--    «non dichiara niente»: e' un valore legittimo, quindi nessun
--    DEFAULT — dimenticarlo deve non compilare.
-- Brief: brief-db-validata-e-registrazione-tardiva §2.1 (D20-a), §4 P-3.
DECLARE
    v_motivi       jsonb := '[]'::jsonb;
    v_codice       pagamenti.vendite_contabili.codice%TYPE;
    v_non_lavorate integer;
    -- Gli id delle righe non lavorate: elemento di un jsonb costruito
    -- qui, non una colonna — resta nudo.
    v_righe_ids    jsonb;
    v_somma        pagamenti.vendite_contabili_righe.importo%TYPE;
BEGIN
    -- ⛔ Guard di PARAMETRO, e solleva: un id assente o <= 0 non lo
    --    produce nessuna interfaccia — e' il chiamante a essere rotto.
    --    TECNICO, e non E_PARAMETRO_INVALIDO, che e' un debito e non
    --    una sede (AGENTS.md).
    IF p_contabile_id IS NULL OR p_contabile_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_contabile_validabile',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_contabile_id',
                               'valore',    p_contabile_id),
            NULL::uuid,
            'script.fn_check_contabile_validabile',
            'identificativo della distinta contabile non valido');
    END IF;

    -- La testata, per il codice che entra nelle frasi. ⚠️ Sotto la row
    -- security: «non trovata» vuol dire «non esiste» oppure «non e'
    -- tua», e le due risposte devono restare indistinguibili.
    SELECT c.codice
      INTO v_codice
      FROM pagamenti.vendite_contabili c
     WHERE c.id = p_contabile_id;

    -- ⛔ Non si risponde [] su una distinta che non si legge: sarebbe
    --    «si puo' validare» detto di una cosa che non si vede, cioe'
    --    un fail-open silenzioso. Stesso codice e stessa frase della
    --    madre del posting.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_contabile_validabile',
            'E_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_id', p_contabile_id),
            NULL::uuid,
            p_contabile_id::text);
    END IF;

    -- MOTIVO 1 — righe attive che nessuno ha ancora guardato.
    -- ⭐ Quali stati siano «non lavorati» lo dice il CATALOGO
    --    (vendite_contabili_righe_stati.lavorata, D20-a), non un elenco
    --    scritto qui: IMPORTATA e DA_ABBINARE sono false. La sospesa
    --    E' stata guardata — ha un motivo, e con D20-b ha un futuro.
    -- ⚠️ `IS NOT TRUE` e non `= false`: uno stato nuovo con la
    --    bandiera a NULL non esiste (NOT NULL), ma se esistesse
    --    cadrebbe nel rifiuto, non nel silenzio.
    -- ℹ️ Il dettaglio porta gli id e non la chiave `campo`: non c'e'
    --    UN campo da accendere, ci sono N righe.
    SELECT COUNT(*)::integer,
           jsonb_agg(cr.id ORDER BY cr.id)
      INTO v_non_lavorate, v_righe_ids
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
     WHERE cr.contabile_id = p_contabile_id
       AND cr.attivo IS TRUE
       AND st.lavorata IS NOT TRUE;

    IF v_non_lavorate > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE',
            'reason',     'RIGHE_NON_LAVORATE',
            'reason_key', 'pagamenti.distinte.validazione_reason.righe_non_lavorate',
            'dettaglio',  jsonb_build_object(
                              'contabile_id',        p_contabile_id,
                              'quante',              v_non_lavorate,
                              'contabile_righe_ids', v_righe_ids),
            'valori',     jsonb_build_array(v_codice, v_non_lavorate::text));
    END IF;

    -- MOTIVO 2 — la quadratura col dichiarato, quando c'e' (D12-e).
    -- ⚠️ TUTTE le righe attive, SCARTATA compresa: quel denaro e'
    --    arrivato. Se le scartate uscissero dalla somma, il primo
    --    scarto romperebbe una distinta sana.
    -- ⭐ Riuso di E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA con gli
    --    STESSI tre valori del guard che lo sollevava prima: e' la
    --    stessa condizione, spostata nella sede unica. Il dettaglio
    --    porta `campo`: qui UN campo da accendere c'e'.
    IF p_importo_dichiarato IS NOT NULL THEN
        SELECT COALESCE(SUM(cr.importo), 0)
          INTO v_somma
          FROM pagamenti.vendite_contabili_righe cr
         WHERE cr.contabile_id = p_contabile_id
           AND cr.attivo IS TRUE;

        IF v_somma IS DISTINCT FROM p_importo_dichiarato THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA',
                'reason',     'TOTALE_NON_QUADRA',
                'reason_key', 'pagamenti.distinte.validazione_reason.totale_non_quadra',
                'dettaglio',  jsonb_build_object(
                                  'campo',              'importo_dichiarato',
                                  'contabile_id',       p_contabile_id,
                                  'importo_dichiarato', p_importo_dichiarato,
                                  'somma_righe',        v_somma),
                'valori',     jsonb_build_array(
                                  v_codice,
                                  p_importo_dichiarato::text,
                                  v_somma::text));
        END IF;
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_contabile_validabile(p_contabile_id bigint, p_importo_dichiarato numeric)
IS 'Pure check (§12.5.1): i motivi che impediscono di portare una distinta contabile a VALIDATA — «ho finito di inserire» (D14-a-bis). Ritorna [] se si puo'', altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva (salvo i due guard di chiamata). ⭐ SEDE UNICA del predicato: pagamenti.trgfn_vendite_contabili_guard_validazione la CHIAMA entrando in VALIDATA e solleva il codice del primo motivo con fn_raise_primo_motivo_se_presente; il backend la legge nel dettaglio della distinta (can_validare, validazione_blocco_*) per spegnere «Porta a VALIDATA» col perche'' — cosi'' tooltip e rifiuto non possono divergere (§12.5.2). ⚠️ L''ORDINE e'' il contratto: (1) RIGHE_NON_LAVORATE — righe attive in uno stato con lavorata = false (IMPORTATA, DA_ABBINARE: la domanda si fa al catalogo, D20-a), codice E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE, dettaglio con quante e gli id; (2) TOTALE_NON_QUADRA — solo se p_importo_dichiarato non e'' NULL e la somma delle righe attive (SCARTATA compresa) non corrisponde: riuso di E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA con gli stessi tre valori di prima, dettaglio con campo = importo_dichiarato. ⭐ Il dichiarato e'' un PARAMETRO e non si rilegge per id: il guard gira BEFORE ROW e il valore che sta entrando non e'' ancora nella tabella — una check che lo rileggesse verificherebbe il totale di ieri. Chi chiama passa quello che vede (NEW.importo_dichiarato nel guard, c.importo_dichiarato nel backend). Nessun DEFAULT: NULL e'' «non dichiara niente» (D12), un valore legittimo, e dimenticarlo deve non compilare. ⚠️ SECURITY INVOKER sotto la row security: una distinta che non si legge — inesistente o di un altro — solleva E_CONTABILE_NON_TROVATA (404, no-leak); rispondere [] sarebbe un fail-open. ⛔ Guard di parametro su E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO). ⛔ Il reason non porta il prefisso E_. ⚠️ Le reason_key pagamenti.distinte.validazione_reason.* sono un DEBITO VERSO IL FE (FE-6). Brief: brief-db-validata-e-registrazione-tardiva §2.1 (D20-a), §4 P-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
