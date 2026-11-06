{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_cliente_sorgente.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_cliente_sorgente`

```sql
CREATE FUNCTION trgfn_ddt_guard_cliente_sorgente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_cliente_sorgente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il DDT ha il billing account del documento da cui
--   nasce (D-6 di brief-db-esecutivi-ba-coppia): «un esecutivo
--   derivato ha il BA della sua sorgente».
--   1. sorgente di testata ORDINE_VENDITA -> BA dell'ordine;
--      RESO_VENDITA -> BA del reso (NULL compreso). Una sorgente
--      di quei due tipi che non si trova (o non si vede) e' un
--      errore (rev 2026-10-10, domanda 3 del §10.2);
--   2. su UPDATE, il BA non cambia se il DDT evade gia' righe
--      d'ordine (la terza porta, il fulfillment, ha il guard in
--      vendite.trgfn_ordini_ful_guard_consistenza).
--   ⭐ rev 2026-10-11 (brief-db-testata-dopo-emissione §11,
--   R-DB-1): i vincoli li dice vendite.fn_ddt_vincoli_cliente,
--   la stessa funzione da cui la capability spegne il campo.
--   Qui si solleva soltanto.
-- Uso: BEFORE INSERT OR UPDATE, fascia _z10_ (dopo il normalize).
DECLARE
    v_ba_cambia  boolean;
    v_vincolo    record;
    v_doc_label  text;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS NOT DISTINCT FROM OLD.billing_account_id
       AND NEW.sorgente_tipo_id   IS NOT DISTINCT FROM OLD.sorgente_tipo_id
       AND NEW.sorgente_uid       IS NOT DISTINCT FROM OLD.sorgente_uid
       AND NEW.sorgente_id        IS NOT DISTINCT FROM OLD.sorgente_id THEN
        RETURN NEW;
    END IF;

    v_doc_label := 'DDT ' || COALESCE(NEW.numero, '#' || NEW.id::text);
    v_ba_cambia := TG_OP = 'UPDATE'
                   AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id;

    -- Il fulfillment conta solo se il BA cambia su UPDATE: l'id
    -- si passa solo allora (su INSERT non ci sono righe evase).
    FOR v_vincolo IN
        SELECT v.vincolo, v.sorgente, v.billing_account_id, v.etichetta
          FROM vendite.fn_ddt_vincoli_cliente(
                 CASE WHEN v_ba_cambia THEN NEW.id END,
                 NEW.sorgente_tipo_id,
                 NEW.sorgente_uid,
                 NEW.sorgente_id) AS v
    LOOP
        -- 1. La sorgente di testata.
        IF v_vincolo.vincolo = 'SORGENTE' THEN
            -- Dichiarata e non trovata, o invisibile sotto RLS: fail-
            -- closed (rev 2026-10-10). Prima passava «niente da
            -- confrontare», e una bolla poteva nascere dall'ordine di un
            -- altro emittente col BA del proprio.
            IF v_vincolo.etichetta IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', TG_NAME::text, 'E_DOC_SORGENTE_NON_TROVATA',
                    jsonb_build_object(
                        'campo',        'sorgente_uid',
                        'ddt_id',       NEW.id,
                        'sorgente',     v_vincolo.sorgente,
                        'sorgente_uid', NEW.sorgente_uid,
                        'sorgente_id',  NEW.sorgente_id),
                    NEW.tx_id,
                    v_doc_label,
                    CASE v_vincolo.sorgente WHEN 'ORDINE_VENDITA' THEN 'ordine' ELSE 'reso' END);
            END IF;

            IF v_vincolo.billing_account_id IS DISTINCT FROM NEW.billing_account_id THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', TG_NAME::text, 'E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
                    jsonb_build_object(
                        'campo',              'billing_account_id',
                        'ddt_id',             NEW.id,
                        'billing_account_id', NEW.billing_account_id,
                        'sorgente',           v_vincolo.sorgente,
                        'sorgente_uid',       NEW.sorgente_uid,
                        'sorgente_id',        NEW.sorgente_id,
                        'billing_account_sorgente', v_vincolo.billing_account_id),
                    NEW.tx_id,
                    v_doc_label,
                    v_vincolo.etichetta);
            END IF;
        END IF;

        -- 2. Il BA di un DDT che evade gia' righe d'ordine non cambia:
        --    quelle righe hanno il BA di prima.
        IF v_vincolo.vincolo = 'FULFILLMENT' AND v_ba_cambia THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME::text, 'E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
                jsonb_build_object(
                    'campo',                 'billing_account_id',
                    'ddt_id',                NEW.id,
                    'billing_account_id_da', OLD.billing_account_id,
                    'billing_account_id_a',  NEW.billing_account_id,
                    'regola',                'DDT_CHE_EVADE_ORDINI'),
                NEW.tx_id,
                v_doc_label,
                v_vincolo.etichetta);
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_cliente_sorgente()
IS '⭐ rev 2026-11-06 (20261106-29, brief-db-sorgente-documento-e-riga §7.2 lotto 0 giro 0.3): la sorgente di testata nelle due grammatiche: il cambio si vede anche su sorgente_id, i vincoli li dice vendite.fn_ddt_vincoli_cliente con la chiave intera (tipo, uid, id), il dettaglio dell''errore porta anche sorgente_id. Dal lotto T la bolla porta l''id dell''ordine o del reso. Guard BEFORE INSERT OR UPDATE su vendite.ddt, fascia _z10_ (dopo trgfn_ddt_normalize): il DDT ha il billing account del documento da cui nasce (D-6 di brief-db-esecutivi-ba-coppia, «un esecutivo derivato ha il BA della sua sorgente»). (1) sorgente di testata ORDINE_VENDITA -> BA dell''ordine, RESO_VENDITA -> BA del reso, NULL compreso; (2) su UPDATE il BA non cambia se il DDT evade gia'' righe d''ordine (quelle righe hanno il BA di prima: si rifiuta il cambio, senza ricopiare il predicato del guard del fulfillment). E_DOC_CLIENTE_DIVERSO_DA_SORGENTE, VARIADIC documento e sorgente leggibili. Ordine e reso letti come INVOKER, come il normalize. rev 2026-10-10 (§10.2 domanda 3, Tid): una sorgente ORDINE_VENDITA o RESO_VENDITA dichiarata e non trovata — inesistente o invisibile sotto RLS, che rispondono uguale — e'' E_DOC_SORGENTE_NON_TROVATA (fail-closed: prima passava, e una bolla poteva dichiarare l''ordine di un altro emittente col BA del proprio). Una sorgente di un altro tipo resta fuori dal confronto. La terza porta, il fulfillment, e'' in vendite.trgfn_ordini_ful_guard_consistenza; il reso ha vendite.trgfn_resi_guard_cliente_ddt. rev 2026-10-11 (brief-db-testata-dopo-emissione §11, R-DB-1): il predicato («da dove viene il cliente della bolla») esce dal corpo in vendite.fn_ddt_vincoli_cliente, che legge anche la capability script.fn_available_actions_ddt per spegnere billing_account_id: guard e capability non possono rispondere in due modi. Codici, contesto e valori della frase invariati; il fulfillment si legge solo quando il BA cambia su UPDATE, come prima.';
```

</div>

---
{% include-markdown "signature-core.md" %}
