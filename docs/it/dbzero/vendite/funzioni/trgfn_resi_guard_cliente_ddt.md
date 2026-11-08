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
-- Scopo: il reso nasce da una bolla di vendita, e ha il billing
--   account di quella bolla, NULL compreso.
--   Su INSERT e su ogni UPDATE che tocca billing account o sorgente,
--   in qualunque stato: il billing account della bolla e' bloccato
--   fuori bozza, quindi quello del reso non cambia mai.
--   Una provenienza di un altro tipo e' E_RESO_SORGENTE_NON_DDT; una
--   bolla che non si trova (o non si vede) e' E_DOC_SORGENTE_NON_TROVATA.
--   La bolla ha chiave id: si cerca per sorgente_id (chk_resi_sorgente_forma
--   vuole sorgente_uid vuota).
-- Uso: BEFORE INSERT OR UPDATE, fascia _z10_ (dopo il normalize).
DECLARE
    v_ba_ddt   vendite.ddt.billing_account_id%TYPE;
    v_ddt_lbl  text;
    v_reso_lbl text;
    v_tipo     config.sorgenti.codice_interno%TYPE;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS NOT DISTINCT FROM OLD.billing_account_id
       AND NEW.sorgente_tipo_id   IS NOT DISTINCT FROM OLD.sorgente_tipo_id
       AND NEW.sorgente_uid       IS NOT DISTINCT FROM OLD.sorgente_uid
       AND NEW.sorgente_id        IS NOT DISTINCT FROM OLD.sorgente_id THEN
        RETURN NEW;
    END IF;

    v_reso_lbl := 'reso ' || COALESCE(NEW.numero, '#' || NEW.id::text);

    SELECT s.codice_interno INTO v_tipo
      FROM config.sorgenti s
     WHERE s.id = NEW.sorgente_tipo_id;

    IF v_tipo IS DISTINCT FROM 'DDT_VENDITA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_RESO_SORGENTE_NON_DDT',
            jsonb_build_object(
                'campo',            'sorgente_tipo_id',
                'reso_id',          NEW.id,
                'sorgente_tipo_id', NEW.sorgente_tipo_id,
                'sorgente',         v_tipo),
            NEW.tx_id,
            v_reso_lbl,
            COALESCE(v_tipo, '#' || COALESCE(NEW.sorgente_tipo_id::text, '?')));
    END IF;

    SELECT d.billing_account_id, 'DDT ' || COALESCE(d.numero, '#' || d.id::text)
      INTO v_ba_ddt, v_ddt_lbl
      FROM vendite.ddt d
     WHERE d.id = NEW.sorgente_id;

    -- Bolla dichiarata e non trovata, o invisibile sotto RLS: fail-closed.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_SORGENTE_NON_TROVATA',
            jsonb_build_object(
                'campo',        'sorgente_id',
                'reso_id',      NEW.id,
                'sorgente',     'DDT_VENDITA',
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
IS 'Guard BEFORE INSERT OR UPDATE su vendite.resi, fascia _z10_ (dopo vendite.trgfn_resi_normalize): il reso nasce da una bolla di vendita e ne ha il billing account, NULL compreso. Una provenienza di un altro tipo e'' E_RESO_SORGENTE_NON_DDT; un billing account diverso e'' E_DOC_CLIENTE_DIVERSO_DA_SORGENTE, come bolla e fulfillment; una bolla dichiarata e non trovata, inesistente o invisibile sotto RLS, e'' E_DOC_SORGENTE_NON_TROVATA (su INSERT parla prima vendite.trgfn_resi_guard_ddt_consegnato). La bolla ha chiave id e si cerca per sorgente_id (chk_resi_sorgente_forma vuole sorgente_uid vuota). Non e'' un doppione del guard unico della provenienza (script.trgfn_guard_sorgente): quello verifica che la bolla esista quando si scrive la sorgente, questo fa valere il tipo, scatta anche quando cambia il solo billing account, e se non vede la bolla rifiuta invece di non confrontare. Vale in qualunque stato: il billing account della bolla e'' bloccato fuori bozza e la bolla di un reso e'' consegnata. La bolla si legge come INVOKER, come nel normalize.';
```

</div>

---
{% include-markdown "signature-core.md" %}
