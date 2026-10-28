{% include-markdown "it/dbzero/vendite/manual/fn_applica_fondi_lotto.md" %}
# ⚙️ Funzione `fn_applica_fondi_lotto`

```sql
CREATE FUNCTION fn_applica_fondi_lotto(p_lotto_id bigint, p_tipo_fondo_codice_interno character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_applica_fondi_lotto(p_lotto_id bigint, p_tipo_fondo_codice_interno character varying)
 RETURNS TABLE(fatture_count integer, fondi_applicati integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_id   vendite.tipi_fondi_fattura.id%TYPE;
    v_fatture   INTEGER := 0;
    v_applicati INTEGER := 0;
BEGIN
    -- ===== Guard parametri =====
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_tipo_fondo_codice_interno IS NULL OR btrim(p_tipo_fondo_codice_interno) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_codice_interno', 'valore', p_tipo_fondo_codice_interno),
            NULL::uuid, 'p_tipo_fondo_codice_interno obbligatorio e non vuoto');
    END IF;

    -- ===== Il tipo di fondo: stessa risoluzione della sorella =====
    -- ⚠️ Due copie di questo lookup sarebbero due copie di una
    --    regola banale ma vera («attivo, il primo per id»): sono
    --    quattro righe e la duplicazione e' accettata di
    --    proposito, perche' estrarla creerebbe una funzione che
    --    esiste solo per essere chiamata due volte. Se diventano
    --    tre, si estrae.
    SELECT t.id INTO v_tipo_id
      FROM vendite.tipi_fondi_fattura t
     WHERE t.codice_interno = p_tipo_fondo_codice_interno
       AND t.attivo IS TRUE
     ORDER BY t.id
     LIMIT 1;

    IF v_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_lotto', 'E_TIPO_FONDO_NOT_FOUND',
            jsonb_build_object('codice_interno', p_tipo_fondo_codice_interno),
            NULL::uuid, p_tipo_fondo_codice_interno);
    END IF;

    -- =========================================================
    -- Una riga per FATTURA: ogni figlia riceve i suoi fondi.
    -- ⚠️ Nessun DISTINCT sulla chiave qui — sarebbe assegnare
    --    tutto a una figlia sola e lasciare le altre a secco.
    -- =========================================================
    WITH scope AS (
        SELECT * FROM vendite.fn_get_scope_fatture_lotto(p_lotto_id)
    ), giro AS (
        SELECT vendite.fn_applica_fondi_fattura(
                   s.billing_account_id,
                   s.utility_id,
                   s.tipo_doc_fiscale_id,
                   s.emittente_soggetto_ruolo_id,
                   s.valuta_id,
                   s.fattura_id,
                   v_tipo_id) AS applicati
          FROM scope s
    )
    SELECT (SELECT count(*)::INTEGER FROM scope),
           COALESCE((SELECT SUM(g.applicati)::INTEGER FROM giro g), 0)
      INTO v_fatture, v_applicati;

    RETURN QUERY SELECT v_fatture, v_applicati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_applica_fondi_lotto(p_lotto_id bigint, p_tipo_fondo_codice_interno character varying)
IS 'Madre DB del giro di applicazione dei fondi per un lotto: legge lo scope da vendite.fn_get_scope_fatture_lotto e chiama fn_applica_fondi_fattura una volta per FATTURA. Ritorna fatture_count e fondi_applicati. ⚠️ Itera sulle fatture e non sulle chiavi come la sorella di generazione, e non e'' un''asimmetria da correggere: le sorgenti si trovano per chiave e non appartengono al lotto, mentre ogni figlia riceve i SUOI fondi e cambia il proprio totale — deduplicare per chiave qui vorrebbe dire assegnare tutto a una figlia sola e lasciare le altre senza. ⭐ Qui il parziale costa piu'' che altrove: ogni chiamata riuscita ha gia'' portato una source ad ASSEGNATO e cambiato il totale di una fattura, e un lotto in cui alcune figlie hanno il fondo e altre no non ha nessuna meta'' sbagliata di per se'', quindi niente lo segnala. Una funzione = uno statement = una transazione chiude il caso per costruzione, comunque il chiamante scriva la query. ℹ️ Chiave a nove elementi, guard di capienza e FOR UPDATE SKIP LOCKED restano dentro fn_applica_fondi_fattura, che e'' l''unico posto in cui il fondo muove denaro: questa e'' orchestrazione. R-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
