{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_cliente_sorgente.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_cliente_sorgente`

```sql
CREATE FUNCTION trgfn_ddt_guard_cliente_sorgente()
```

**Definizione completa:**

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
-- Uso: BEFORE INSERT OR UPDATE, fascia _z10_ (dopo il normalize).
DECLARE
    v_sorgente   config.sorgenti.codice_interno%TYPE;
    v_ba_src     vendite.ddt.billing_account_id%TYPE;
    v_src_label  text;
    v_doc_label  text;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS NOT DISTINCT FROM OLD.billing_account_id
       AND NEW.sorgente_tipo_id   IS NOT DISTINCT FROM OLD.sorgente_tipo_id
       AND NEW.sorgente_uid       IS NOT DISTINCT FROM OLD.sorgente_uid THEN
        RETURN NEW;
    END IF;

    v_doc_label := 'DDT ' || COALESCE(NEW.numero, '#' || NEW.id::text);

    -- 1. La sorgente di testata.
    IF NEW.sorgente_tipo_id IS NOT NULL AND NEW.sorgente_uid IS NOT NULL THEN
        SELECT s.codice_interno INTO v_sorgente
          FROM config.sorgenti s
         WHERE s.id = NEW.sorgente_tipo_id;

        IF v_sorgente = 'ORDINE_VENDITA' THEN
            SELECT o.billing_account_id,
                   'ordine ' || COALESCE(o.numero, '#' || o.id::text)
              INTO v_ba_src, v_src_label
              FROM vendite.ordini o
             WHERE o.uid = NEW.sorgente_uid;
        ELSIF v_sorgente = 'RESO_VENDITA' THEN
            SELECT r.billing_account_id,
                   'reso ' || COALESCE(r.numero, '#' || r.id::text)
              INTO v_ba_src, v_src_label
              FROM vendite.resi r
             WHERE r.uid = NEW.sorgente_uid;
        END IF;

        -- Dichiarata e non trovata, o invisibile sotto RLS: fail-
        -- closed (rev 2026-10-10). Prima passava «niente da
        -- confrontare», e una bolla poteva nascere dall'ordine di un
        -- altro emittente col BA del proprio.
        IF v_sorgente IN ('ORDINE_VENDITA', 'RESO_VENDITA')
           AND v_src_label IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME::text, 'E_DOC_SORGENTE_NON_TROVATA',
                jsonb_build_object(
                    'campo',        'sorgente_uid',
                    'ddt_id',       NEW.id,
                    'sorgente',     v_sorgente,
                    'sorgente_uid', NEW.sorgente_uid),
                NEW.tx_id,
                v_doc_label,
                CASE v_sorgente WHEN 'ORDINE_VENDITA' THEN 'ordine' ELSE 'reso' END);
        END IF;

        IF v_src_label IS NOT NULL
           AND v_ba_src IS DISTINCT FROM NEW.billing_account_id THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', TG_NAME::text, 'E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
                jsonb_build_object(
                    'campo',              'billing_account_id',
                    'ddt_id',             NEW.id,
                    'billing_account_id', NEW.billing_account_id,
                    'sorgente',           v_sorgente,
                    'sorgente_uid',       NEW.sorgente_uid,
                    'billing_account_sorgente', v_ba_src),
                NEW.tx_id,
                v_doc_label,
                v_src_label);
        END IF;
    END IF;

    -- 2. Il BA di un DDT che evade gia' righe d'ordine non cambia:
    --    quelle righe hanno il BA di prima.
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id THEN
        SELECT 'ordine ' || COALESCE(o.numero, '#' || o.id::text)
          INTO v_src_label
          FROM vendite.ddt_righe dr
          JOIN vendite.ordini_righe_fulfillment ful ON ful.ddt_riga_id = dr.id
          JOIN vendite.ordini_righe orr ON orr.id = ful.ordine_riga_id
          JOIN vendite.ordini o ON o.id = orr.ordine_id
         WHERE dr.ddt_id = NEW.id
         ORDER BY ful.id
         LIMIT 1;
        IF FOUND THEN
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
                v_src_label);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_cliente_sorgente()
IS 'Guard BEFORE INSERT OR UPDATE su vendite.ddt, fascia _z10_ (dopo trgfn_ddt_normalize): il DDT ha il billing account del documento da cui nasce (D-6 di brief-db-esecutivi-ba-coppia, «un esecutivo derivato ha il BA della sua sorgente»). (1) sorgente di testata ORDINE_VENDITA -> BA dell''ordine, RESO_VENDITA -> BA del reso, NULL compreso; (2) su UPDATE il BA non cambia se il DDT evade gia'' righe d''ordine (quelle righe hanno il BA di prima: si rifiuta il cambio, senza ricopiare il predicato del guard del fulfillment). E_DOC_CLIENTE_DIVERSO_DA_SORGENTE, VARIADIC documento e sorgente leggibili. Ordine e reso letti come INVOKER, come il normalize. rev 2026-10-10 (§10.2 domanda 3, Tid): una sorgente ORDINE_VENDITA o RESO_VENDITA dichiarata e non trovata — inesistente o invisibile sotto RLS, che rispondono uguale — e'' E_DOC_SORGENTE_NON_TROVATA (fail-closed: prima passava, e una bolla poteva dichiarare l''ordine di un altro emittente col BA del proprio). Una sorgente di un altro tipo resta fuori dal confronto. La terza porta, il fulfillment, e'' in vendite.trgfn_ordini_ful_guard_consistenza; il reso ha vendite.trgfn_resi_guard_cliente_ddt.';
```

---
{% include-markdown "signature-core.md" %}
