{% include-markdown "it/dbzero/vendite/manual/trgfn_guard_fatturazione_immediata_immutabile.md" %}
# ⚙️ Funzione `trgfn_guard_fatturazione_immediata_immutabile`

```sql
CREATE FUNCTION trgfn_guard_fatturazione_immediata_immutabile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: impedire il cambio del flag di instradamento corsia su un
--        documento gia' inviato in commessa, dove sarebbe inerte.
-- Uso:   BEFORE UPDATE OF fatturazione_immediata FOR EACH ROW
--        WHEN (NEW.fatturazione_immediata IS DISTINCT FROM
--              OLD.fatturazione_immediata)
--        EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('<CODICE_INTERNO_SORGENTE>')
-- brief-db-emissione-fattura-per-documento-sorgente PARTE B, D-7.
DECLARE
    v_sorgente_codice  config.sorgenti.codice_interno%TYPE;
    v_sorgente_tipo_id vendite.commesse_sorgenti.sorgente_tipo_id%TYPE;
    v_commessa_id      vendite.commesse_sorgenti.commessa_id%TYPE;
BEGIN
    -- Guard di configurazione del trigger: l'argomento e'
    -- obbligatorio (senza, il guard sarebbe un no-op silenzioso).
    IF TG_NARGS < 1 OR btrim(COALESCE(TG_ARGV[0], '')) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'TG_ARGV[0]', 'tabella', TG_TABLE_NAME),
            NULL::uuid,
            'TG_ARGV[0] (codice_interno sorgente) obbligatorio'
        );
    END IF;

    v_sorgente_codice := btrim(TG_ARGV[0]);

    -- Sorgente per codice_interno (immutabile), MAI per codice
    -- (mutabile) — linee-guida-sql §6c/§6d.
    -- NB: nessun filtro su attivo. Il legame documento->commessa
    -- esiste anche se la sorgente venisse disattivata, e il guard
    -- deve continuare a proteggerlo.
    SELECT s.id
      INTO v_sorgente_tipo_id
      FROM config.sorgenti s
     WHERE s.codice_interno = v_sorgente_codice
     LIMIT 1;

    IF v_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_CODICE',
            jsonb_build_object('codice', v_sorgente_codice, 'tabella', TG_TABLE_NAME),
            NULL::uuid, v_sorgente_codice, 'config.sorgenti'
        );
    END IF;

    -- Il documento sta in una commessa APERTA? Solo una commessa aperta blocca
    -- il flag: il link resta come storia dopo la chiusura e l'annullo della
    -- commessa, e un documento la cui commessa e' stata annullata torna da
    -- mandare. La domanda «quale commessa aperta» ha una sede sola, il
    -- building block. Il documento si passa con tutte e due le sue chiavi:
    -- il link ne tiene una sola, quella del key_selector del tipo, e la
    -- regola d'incontro la trova senza leggere il key_selector.
    v_commessa_id := vendite.fn_commessa_viva_di_sorgente(
                         v_sorgente_tipo_id, NEW.id, NEW.uid);

    IF v_commessa_id IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_FATT_IMMEDIATA_NON_MODIFICABILE',
            jsonb_build_object(
                'tabella',       TG_TABLE_NAME,
                'documento_id',  NEW.id,
                'documento_uid', NEW.uid,
                'sorgente',      v_sorgente_codice,
                'commessa_id',   v_commessa_id,
                'valore_attuale', OLD.fatturazione_immediata,
                'valore_richiesto', NEW.fatturazione_immediata
            ),
            NULL::uuid,
            NEW.id::text, v_sorgente_codice
        );
    END IF;

    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile()
IS 'Guard generico (BEFORE UPDATE OF fatturazione_immediata): blocca il cambio del flag di instradamento corsia su un documento che sta in una commessa APERTA. Sorgente passata come codice_interno in TG_ARGV[0]. La commessa aperta la dice vendite.fn_commessa_viva_di_sorgente, a cui il guard passa il tipo con l''id e l''uid del documento: il link tiene una sola delle due chiavi, quella del key_selector del tipo, e la regola d''incontro la trova. Finche'' il documento e'' in una commessa aperta il flag e'' inerte: e'' nella chiave di dedup di vendite.fn_get_or_create_commessa, e si sposterebbe l''intera commessa multi-sorgente. Il link resta come storia dopo la chiusura o l''annullo della commessa: quando la commessa del documento e'' annullata, il documento torna da mandare e il flag torna modificabile. Il caso «cambio idea dopo» e'' coperto dall''emissione mirata per gruppo fatturabile. Errore: E_FATT_IMMEDIATA_NON_MODIFICABILE, che nomina il documento col suo id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
