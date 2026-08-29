# ⚙️ Funzione `fn_check_preventivo_emettibile`

```sql
CREATE FUNCTION fn_check_preventivo_emettibile(p_preventivo_id bigint)
```

**Definizione completa:**

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
-- Ritorna: [] se emettibile; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
    v_motivi   jsonb := '[]'::jsonb;
    v_uid      vendite.preventivi.uid%TYPE;
    v_riga_id  vendite.preventivi_righe.id%TYPE;
    v_riga_des vendite.preventivi_righe.descrizione%TYPE;
BEGIN
    IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_preventivo_emettibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'preventivo_id', 'valore', p_preventivo_id),
            NULL::uuid, 'preventivo_id obbligatorio (>0)');
    END IF;

    SELECT p.uid INTO v_uid
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
                              'descrizione', v_riga_des));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_preventivo_emettibile(p_preventivo_id bigint)
IS 'Single source dei motivi che impediscono l''EMISSIONE di un preventivo. Ritorna [] se emettibile, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio}. PURA: non solleva e non scrive. Consumatori: vendite.trgfn_preventivi_guard_transizione (solleva il codice del primo motivo) e script.fn_available_actions_preventivo (spegne il bottone ed espone la reason). ⭐ Oggi UN motivo: E_PREV_RIGA_IVA_MANCANTE, una riga attiva con quantita e prezzo ma senza aliquota. Chiude un difetto silenzioso gemello di quelli sanati sul DDT (2026-08-28) e sull''ordine (2026-08-29): fn_ricalcola_riepilogo_iva_preventivo aggrega le righe attive con quantita > 0 e calcola l''imposta con COALESCE(fn_get_aliquota_iva(iva_id, stato), 0), quindi una riga senza aliquota finisce in vendite.preventivi_riepiloghi_iva con imponibile pieno e imposta zero. ⭐ IL PREDICATO E'' COPIATO DAL CONSUMATORE (attivo IS TRUE AND quantita > 0): il vincolo deve avere lo stesso perimetro di cio'' che protegge. ⚠️ E NON e'' una copia della gemella sugli ordini, perche'' i due documenti divergono su tre punti strutturali: preventivi_righe non ha riga_nr (nel messaggio va la DESCRIZIONE, non «la riga 0» che darebbe la colonna `ordine`), quantita e'' nullable e senza CHECK di positivita'' (sugli ordini c''e'' chk_ordini_v_r_qta_pos, quindi li'' il filtro sarebbe ridondante), attivo e'' nullable (su ordini_righe e'' NOT NULL). ⛔ NON contiene il motivo «documento senza righe»: quello vive nella porta vendite.fn_cambia_stato_preventivo ed e'' un''asimmetria gia'' dichiarata, non una regola dell''emissione. Piano: brief-db-be-iva-risolutore-e-regime-cliente, I9.';
```

---
{% include-markdown "signature-core.md" %}
