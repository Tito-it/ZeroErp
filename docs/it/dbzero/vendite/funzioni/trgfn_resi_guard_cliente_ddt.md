{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_cliente_ddt.md" %}
# ⚙️ Funzione `trgfn_resi_guard_cliente_ddt`

```sql
CREATE FUNCTION trgfn_resi_guard_cliente_ddt()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_cliente_ddt()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il reso ha il billing account del DDT da cui nasce,
--   NULL compreso (D-3 e D-6 di brief-db-esecutivi-ba-coppia).
--   Su INSERT e su ogni UPDATE che tocca BA o sorgente, in
--   qualunque stato: il BA del DDT sorgente e' bloccato fuori
--   bozza, quindi quello del reso non cambia mai.
--   rev 2026-10-10 (§10.2 domanda 3): un DDT sorgente che non si
--   trova (o non si vede) e' un errore, non «niente da confrontare».
-- Uso: BEFORE INSERT OR UPDATE, fascia _z10_ (dopo il normalize).
DECLARE
    v_ba_ddt   vendite.ddt.billing_account_id%TYPE;
    v_ddt_lbl  text;
    v_reso_lbl text;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS NOT DISTINCT FROM OLD.billing_account_id
       AND NEW.sorgente_tipo_id   IS NOT DISTINCT FROM OLD.sorgente_tipo_id
       AND NEW.sorgente_uid       IS NOT DISTINCT FROM OLD.sorgente_uid
       AND NEW.sorgente_id        IS NOT DISTINCT FROM OLD.sorgente_id THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM config.sorgenti s
                    WHERE s.id = NEW.sorgente_tipo_id
                      AND s.codice_interno = 'DDT_VENDITA') THEN
        RETURN NEW;
    END IF;

    v_reso_lbl := 'reso ' || COALESCE(NEW.numero, '#' || NEW.id::text);

    SELECT d.billing_account_id, 'DDT ' || COALESCE(d.numero, '#' || d.id::text)
      INTO v_ba_ddt, v_ddt_lbl
      FROM vendite.ddt d
     WHERE (d.id = NEW.sorgente_id OR d.uid = NEW.sorgente_uid);

    -- DDT dichiarato e non trovato, o invisibile sotto RLS: fail-
    -- closed (rev 2026-10-10). Prima passava.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_SORGENTE_NON_TROVATA',
            jsonb_build_object(
                'campo',        'sorgente_uid',
                'reso_id',      NEW.id,
                'sorgente',     'DDT_VENDITA',
                'sorgente_uid', NEW.sorgente_uid,
                'sorgente_id',  NEW.sorgente_id),
            NEW.tx_id,
            v_reso_lbl,
            'DDT');
    END IF;

    IF v_ba_ddt IS DISTINCT FROM NEW.billing_account_id THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
            jsonb_build_object(
                'campo',                  'billing_account_id',
                'reso_id',                NEW.id,
                'billing_account_id',     NEW.billing_account_id,
                'sorgente_uid',           NEW.sorgente_uid,
                'sorgente_id',            NEW.sorgente_id,
                'billing_account_ddt',    v_ba_ddt),
            NEW.tx_id,
            v_reso_lbl,
            v_ddt_lbl);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_cliente_ddt()
IS '⭐ rev 2026-11-06 (20261106-35, brief-db-sorgente-documento-e-riga §7.2 lotto 0 giro 0.3): la bolla del reso nelle due grammatiche: il cambio si vede anche su sorgente_id, la bolla si cerca con (d.id = NEW.sorgente_id OR d.uid = NEW.sorgente_uid), il dettaglio dell''errore porta anche sorgente_id. Dal lotto T il reso porta l''id della bolla. Guard BEFORE INSERT OR UPDATE su vendite.resi, fascia _z10_ (dopo trgfn_resi_normalize): il reso ha il billing account del DDT sorgente (DDT_VENDITA), NULL compreso (D-3, D-6 di brief-db-esecutivi-ba-coppia). E_DOC_CLIENTE_DIVERSO_DA_SORGENTE, come DDT e fulfillment. In qualunque stato: il BA del DDT sorgente e'' bloccato fuori bozza e il DDT di un reso e'' consegnato, quindi il BA del reso non cambia mai — per questo il reso non ha un lock fuori bozza sul cliente. DDT letto come INVOKER, come il normalize. rev 2026-10-10 (§10.2 domanda 3, Tid): DDT sorgente dichiarato e non trovato — inesistente o invisibile sotto RLS — e'' E_DOC_SORGENTE_NON_TROVATA (fail-closed; su INSERT parla prima vendite.trgfn_resi_guard_ddt_consegnato, su un UPDATE della sorgente solo questo guard).';
```

</div>

---
{% include-markdown "signature-core.md" %}
