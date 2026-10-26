# ⚙️ Funzione `fn_check_indirizzi_documento_cliente`

```sql
CREATE FUNCTION fn_check_indirizzi_documento_cliente(p_documento character varying, p_testata_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_indirizzi_documento_cliente(p_documento character varying, p_testata_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore senza colonna
--   di vocabolario; p_testata_id e' POLIMORFO (l'id di sei testate);
--   il jsonb di ritorno e' l'array dei motivi.
-- ⚠️ v_tipi nudo: un array di codici (colonna%TYPE[] non esiste).
DECLARE
    v_schema      pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella     pg_catalog.pg_class.relname%TYPE;
    v_fk_col      pg_catalog.pg_attribute.attname%TYPE;
    v_ruolo       anagrafiche.soggetti_ruoli.id%TYPE;
    v_istanza     anagrafiche.indirizzi.istanza_utility_id%TYPE;
    v_tipi        text[];
    v_primo_descr config.tipi_indirizzi.descrizione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il documento porta un indirizzo d'anagrafica che non e'
    --   del suo cliente? Funzione PURA: non solleva, non scrive.
    -- Ritorna: [] se tutti gli indirizzi sono del cliente (o
    --   una-tantum); altrimenti un motivo, con l'elenco dei tipi.
    -- =========================================================
    IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_indirizzi_documento_cliente', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'testata_id', 'valore', p_testata_id),
            NULL::uuid, 'testata_id obbligatorio (>0)');
    END IF;

    SELECT s.schema_tabella, s.tabella, s.colonna_fk
      INTO v_schema, v_tabella, v_fk_col
      FROM script.fn_doc_indirizzi_sede(p_documento) AS s;

    IF v_tabella IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_indirizzi_documento_cliente', 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento, 'testata_id', p_testata_id),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    SELECT c.soggetto_ruolo_id, c.istanza_utility_id
      INTO v_ruolo, v_istanza
      FROM script.fn_get_cliente_testata_documento(p_documento, p_testata_id) AS c;

    -- I tipi le cui righe non sono del cliente, in ordine di codice;
    -- il primo, leggibile, va nella frase.
    EXECUTE format(
        'SELECT array_agg(t.codice_interno::text ORDER BY t.codice_interno), '
        '       (array_agg(t.descrizione ORDER BY t.codice_interno))[1] '
        '  FROM %I.%I x '
        '  JOIN config.tipi_indirizzi t ON t.id = x.tipo_indirizzo_id '
        ' WHERE x.%I = $1 '
        '   AND script.fn_indirizzo_documento_fuori_cliente('
        '           x.origine_indirizzo_id, x.origine_soggetto_ruolo_id, $2, $3) IS NOT NULL',
        v_schema, v_tabella, v_fk_col)
       INTO v_tipi, v_primo_descr
      USING p_testata_id, v_ruolo, v_istanza;

    IF v_tipi IS NOT NULL THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_INDIRIZZO_DOC_NON_DEL_CLIENTE',
            'reason',     'INDIRIZZO_NON_DEL_CLIENTE',
            'reason_key', 'common.azione_reason.indirizzo_non_del_cliente',
            'dettaglio',  jsonb_build_object('campo', 'tipo_indirizzo_id',
                                             'tipi',  to_jsonb(v_tipi)),
            'valori',     jsonb_build_array(v_primo_descr)));
    END IF;

    RETURN '[]'::jsonb;
END;
$function$

COMMENT ON FUNCTION script.fn_check_indirizzi_documento_cliente(p_documento character varying, p_testata_id bigint)
IS 'Motivo d''emissione (D-3 di brief-db-indirizzi-documento-seguono-il-cliente): il documento porta un indirizzo d''anagrafica che non e'' del suo cliente. PURA: non solleva, non scrive. Ritorna [] o un motivo {codice E_INDIRIZZO_DOC_NON_DEL_CLIENTE, reason INDIRIZZO_NON_DEL_CLIENTE, reason_key common.azione_reason.indirizzo_non_del_cliente, dettaglio {campo tipo_indirizzo_id, tipi [codici]}, valori [il primo tipo leggibile]}. Predicato script.fn_indirizzo_documento_fuori_cliente, lo stesso del guard di scrittura e del cambio di cliente; cliente da script.fn_get_cliente_testata_documento. Documento: DDT | ORDINE | PREVENTIVO | OFFERTA | CONTRATTO | FATTURA (script.fn_doc_indirizzi_sede). Lettori: script.fn_check_ddt_emittibile (punto 4-bis), script.fn_check_preventivo_emettibile (motivo 3), script.fn_available_actions_offerta e vendite.trgfn_offerte_commerciali_guard_transizione (verso EMESSA), script.fn_available_actions_contratto e vendite.trgfn_contratti_guard_transizione_stato (verso ATTIVO). ⚠️ La reason_key e'' un debito verso il frontend (locales). ⭐ rev 2026-10-19 (20261019-46, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
