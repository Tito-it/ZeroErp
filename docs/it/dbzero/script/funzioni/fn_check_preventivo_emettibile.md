{% include-markdown "it/dbzero/script/manual/fn_check_preventivo_emettibile.md" %}
# ⚙️ Funzione `fn_check_preventivo_emettibile`

```sql
CREATE FUNCTION fn_check_preventivo_emettibile(p_preventivo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_preventivo_emettibile(p_preventivo_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'EMISSIONE di un
--   preventivo. Funzione PURA (fn_check_*): non solleva, non
--   scrive. Consumatori: vendite.trgfn_preventivi_guard_transizione
--   (che solleva il codice del primo motivo) e
--   script.fn_available_actions_preventivo (che spegne il bottone).
--   Gemella di fn_check_preventivo_annullabile.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I9 / §R-3.
--   rev 2026-09-24: + MOTIVO 2, i prezzi non autorizzati, dal building
--   block script.fn_check_prezzi_autorizzati
--   (brief-db-preventivi-congelamento-pricing, D-1/D-2).
-- Ritorna: [] se emettibile; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
    v_motivi   jsonb := '[]'::jsonb;
    v_uid      vendite.preventivi.uid%TYPE;
    v_numero   vendite.preventivi.numero%TYPE;
    v_riga_id  vendite.preventivi_righe.id%TYPE;
    v_riga_des vendite.preventivi_righe.descrizione%TYPE;
BEGIN
    IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_preventivo_emettibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'preventivo_id', 'valore', p_preventivo_id),
            NULL::uuid, 'preventivo_id obbligatorio (>0)');
    END IF;

    -- ⭐ `p.numero` sulla SELECT che c'era gia': serve a COMPORRE la frase
    --   («Preventivo %s: la riga «%s» ...»), non a decidere.
    SELECT p.uid, p.numero INTO v_uid, v_numero
      FROM vendite.preventivi p
     WHERE p.id = p_preventivo_id;

    IF v_uid IS NULL THEN
        RETURN v_motivi;   -- preventivo inesistente: decide il chiamante
    END IF;

    -- MOTIVO 1 — VALORE DELLA RIGA: una riga che entra nel
    --   riepilogo IVA deve portare un'aliquota.
    --
    -- ⭐ IL PREDICATO E' QUELLO DEL CONSUMATORE, copiato da
    --   vendite.fn_ricalcola_riepilogo_iva_preventivo:
    --   attivo IS TRUE AND quantita > 0. Quella funzione calcola
    --   l'imposta con COALESCE(fn_get_aliquota_iva(iva_id,...), 0),
    --   quindi una riga senza aliquota finisce in
    --   vendite.preventivi_riepiloghi_iva con imponibile pieno e
    --   imposta zero.
    --
    -- ⚠️ `quantita > 0` NON e' ridondante come lo sarebbe sugli
    --   ordini: preventivi_righe.quantita e' NULLABILE e non ha
    --   CHECK di positivita' (ordini_righe ha
    --   chk_ordini_v_r_qta_pos). Senza, si bloccherebbe un
    --   preventivo per una riga che nel riepilogo non entra mai.
    --
    -- ⚠️ `attivo IS TRUE` e non `attivo`: la colonna e' NULLABILE
    --   qui (su ordini_righe e' NOT NULL), e il NULL va escluso
    --   esattamente come lo esclude il consumatore.
    --
    -- ⚠️ `prezzo_unitario IS NOT NULL` e' oggi sempre vero (colonna
    --   NOT NULL): si scrive perche' e' la forma vera della regola
    --   — dove c'e' un prezzo serve l'aliquota — ed e' gia'
    --   successo che una colonna prezzo diventasse facoltativa
    --   (20260819-13 su vendite.ddt_righe_componenti).
    --
    -- ⛔ Nel dettaglio va la DESCRIZIONE e non un numero di riga:
    --   preventivi_righe NON HA riga_nr, e `ordine` e' una chiave
    --   di ordinamento con default 0 — un messaggio che dicesse
    --   «la riga 0» non aiuterebbe nessuno. L'id resta per chi
    --   diagnostica.
    --
    -- ⚠️ ORDER BY prima del LIMIT: senza, quale riga esca dipende
    --   dal piano del planner e il messaggio nominerebbe una riga
    --   diversa a ogni corsa.
    SELECT pr.id, pr.descrizione
      INTO v_riga_id, v_riga_des
      FROM vendite.preventivi_righe pr
     WHERE pr.preventivo_id = p_preventivo_id
       AND pr.attivo IS TRUE
       AND pr.quantita > 0
       AND pr.prezzo_unitario IS NOT NULL
       AND pr.iva_id IS NULL
     ORDER BY pr.ordine NULLS LAST, pr.id
     LIMIT 1;

    IF v_riga_id IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PREV_RIGA_IVA_MANCANTE',
            'reason',     'RIGA_SENZA_ALIQUOTA',
            'reason_key', 'vendite.preventivi.azione_reason.iva_mancante',
            'dettaglio',  jsonb_build_object(
                              'riga_id',     v_riga_id,
                              'descrizione', v_riga_des),
            -- ⚠️ preventivi_righe non ha riga_nr e `ordine` ha default 0: nella
            --   frase va la DESCRIZIONE, ed e' la stessa scelta gia' dichiarata
            --   nel commento di trgfn_preventivi_guard_transizione.
            'valori',     jsonb_build_array(COALESCE(v_numero, p_preventivo_id::text),
                                            COALESCE(v_riga_des, 'senza descrizione')));
    END IF;

    -- MOTIVO 2 (rev 2026-09-24) — PREZZI NON AUTORIZZATI: un preventivo
    --   con un prezzo in attesa di approvazione o rifiutato dal
    --   responsabile non si emette (D-1, D-2).
    -- ⭐ Il predicato NON sta qui: sta nel building block comune ai cinque
    --   documenti di vendita. Questa funzione decide solo che l'EMISSIONE
    --   lo chiede. Dopo l'aliquota: quel motivo si corregge sulla riga,
    --   questo spesso si aspetta.
    v_motivi := v_motivi
             || script.fn_check_prezzi_autorizzati('vendite.preventivi'::regclass,
                                                   p_preventivo_id);

    -- MOTIVO 3 (rev 2026-10-11, brief-db-indirizzi-documento-seguono-il-
    --   cliente, D-3 di Tid) — INDIRIZZI DEL CLIENTE: il cliente del
    --   preventivo (la coppia BA/istanza) si cambia in bozza, e un
    --   indirizzo d'anagrafica del cliente di prima, o di una fornitura
    --   che il preventivo non ha piu', non va al cliente.
    -- ⭐ Il predicato sta in script.fn_check_indirizzi_documento_cliente,
    --   lo stesso del guard di scrittura. Dopo i prezzi: quei motivi
    --   riguardano le righe, questo la testata.
    v_motivi := v_motivi
             || script.fn_check_indirizzi_documento_cliente('PREVENTIVO', p_preventivo_id);

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_preventivo_emettibile(p_preventivo_id bigint)
IS 'Single source dei motivi che impediscono l''EMISSIONE di un preventivo. Ritorna [] se emettibile, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio}. PURA: non solleva e non scrive. Consumatori: vendite.trgfn_preventivi_guard_transizione (solleva il codice del primo motivo) e script.fn_available_actions_preventivo (spegne il bottone ed espone la reason). ⭐ Oggi UN motivo: E_PREV_RIGA_IVA_MANCANTE, una riga attiva con quantita e prezzo ma senza aliquota. Chiude un difetto silenzioso gemello di quelli sanati sul DDT (2026-08-28) e sull''ordine (2026-08-29): fn_ricalcola_riepilogo_iva_preventivo aggrega le righe attive con quantita > 0 e calcola l''imposta con COALESCE(fn_get_aliquota_iva(iva_id, stato), 0), quindi una riga senza aliquota finisce in vendite.preventivi_riepiloghi_iva con imponibile pieno e imposta zero. ⭐ IL PREDICATO E'' COPIATO DAL CONSUMATORE (attivo IS TRUE AND quantita > 0): il vincolo deve avere lo stesso perimetro di cio'' che protegge. ⚠️ E NON e'' una copia della gemella sugli ordini, perche'' i due documenti divergono su tre punti strutturali: preventivi_righe non ha riga_nr (nel messaggio va la DESCRIZIONE, non «la riga 0» che darebbe la colonna `ordine`), quantita e'' nullable e senza CHECK di positivita'' (sugli ordini c''e'' chk_ordini_v_r_qta_pos, quindi li'' il filtro sarebbe ridondante), attivo e'' nullable (su ordini_righe e'' NOT NULL). ⛔ NON contiene il motivo «documento senza righe»: quello vive nella porta vendite.fn_cambia_stato_preventivo ed e'' un''asimmetria gia'' dichiarata, non una regola dell''emissione. Piano: brief-db-be-iva-risolutore-e-regime-cliente, I9. ⭐ rev 2026-09-24: + MOTIVO 2, i prezzi non autorizzati (E_DOC_PREZZO_PENDENTE, E_DOC_PREZZO_RIFIUTATO) su righe e componenti BoM attivi, dal building block script.fn_check_prezzi_autorizzati: il predicato sta li'''', qui si decide solo che l''''emissione lo chiede. Sommati dopo il motivo dell''''aliquota. Brief: brief-db-preventivi-congelamento-pricing (D-1, D-2). rev 2026-10-11: + MOTIVO 3, E_INDIRIZZO_DOC_NON_DEL_CLIENTE (reason INDIRIZZO_NON_DEL_CLIENTE, reason_key common.azione_reason.indirizzo_non_del_cliente) da script.fn_check_indirizzi_documento_cliente(''PREVENTIVO'', id): un indirizzo d''anagrafica del cliente di prima, o di un''altra fornitura, ferma l''emissione. Dopo i prezzi. Brief: brief-db-indirizzi-documento-seguono-il-cliente (D-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
