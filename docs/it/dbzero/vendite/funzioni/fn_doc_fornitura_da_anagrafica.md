# ⚙️ Funzione `fn_doc_fornitura_da_anagrafica`

```sql
CREATE FUNCTION fn_doc_fornitura_da_anagrafica(p_documento character varying, p_testata_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_doc_fornitura_da_anagrafica(p_documento character varying, p_testata_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore senza colonna
--   di vocabolario; p_testata_id e' POLIMORFO (l'id di due testate);
--   il boolean di ritorno e' un esito, non il riflesso di una colonna.
DECLARE
    v_schema   pg_catalog.pg_namespace.nspname%TYPE;
    v_testata  pg_catalog.pg_class.relname%TYPE;
    v_tabella  pg_catalog.pg_class.relname%TYPE;
    v_fk_col   pg_catalog.pg_attribute.attname%TYPE;
    v_istanza  anagrafiche.istanze_dati_precontrattuali.istanza_utility_id%TYPE;
    v_utility  anagrafiche.istanze_dati_precontrattuali.utility_id%TYPE;
    v_scritte  integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La scheda di fornitura del documento e' quella che
    --   l'anagrafica da' alla sua coppia (istanza, utility).
    --   Si toglie quella che c'e' e si riscrive.
    -- =========================================================
    IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_doc_fornitura_da_anagrafica', 'E_DOC_FORNITURA_PARAMETRO_MANCANTE',
            jsonb_build_object('documento', p_documento, 'testata_id', p_testata_id),
            NULL::uuid,
            'vendite.fn_doc_fornitura_da_anagrafica',
            'l''id del documento');
    END IF;

    SELECT s.schema_tabella, s.testata, s.tabella, s.colonna_fk
      INTO v_schema, v_testata, v_tabella, v_fk_col
      FROM vendite.fn_doc_fornitura_sede(p_documento) AS s;

    IF v_tabella IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_doc_fornitura_da_anagrafica', 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento, 'testata_id', p_testata_id),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    -- La coppia della testata. Testata assente (o fuori dalla RLS di
    -- chi chiama): niente da rifare.
    EXECUTE format(
        'SELECT t.istanza_utility_id, t.utility_id FROM %I.%I t WHERE t.id = $1',
        v_schema, v_testata)
       INTO v_istanza, v_utility
      USING p_testata_id;

    IF v_istanza IS NULL THEN
        RETURN false;
    END IF;

    -- 1. Via la scheda che c'e': descriveva un'altra fornitura, o
    --    e' la nascita e non c'e' niente.
    EXECUTE format('DELETE FROM %I.%I x WHERE x.%I = $1',
                   v_schema, v_tabella, v_fk_col)
      USING p_testata_id;

    -- 2. La scheda dell'anagrafica, se la coppia ne ha una.
    EXECUTE format(
        'INSERT INTO %I.%I (%I, istanza_utility_id, utility_id, '
        '                   istanza_dati_precontrattuali_id, classe_utenza_id, '
        '                   tipo_utenza_id, param_1_num, param_2_txt, meta) '
        'SELECT $1, $2, $3, '
        '       f.istanza_dati_precontrattuali_id, f.classe_utenza_id, '
        '       f.tipo_utenza_id, f.param_1_num, f.param_2_txt, f.meta '
        '  FROM vendite.fn_get_fornitura_da_anagrafica($2, $3) AS f',
        v_schema, v_tabella, v_fk_col)
      USING p_testata_id, v_istanza, v_utility;

    GET DIAGNOSTICS v_scritte = ROW_COUNT;
    RETURN v_scritte > 0;
END;
$function$

COMMENT ON FUNCTION vendite.fn_doc_fornitura_da_anagrafica(p_documento character varying, p_testata_id bigint)
IS 'Rifa'' la scheda di fornitura (1:1) di un documento (CONTRATTO | OFFERTA, vendite.fn_doc_fornitura_sede) dai dati precontrattuali della coppia (istanza, utility) della sua testata: toglie la scheda che c''e'' e scrive quella di vendite.fn_get_fornitura_da_anagrafica. Torna true se ha scritto; false se la testata non c''e'' (o non e'' visibile) o se la coppia non ha dati precontrattuali, e allora il documento resta senza scheda. La regola (D-5 e D-5-bis di Tid, 2026-10-12): la scheda descrive la fornitura, non una scelta commerciale; se la fornitura cambia si rifa'' da capo, e le correzioni fatte a mano sulla fornitura di prima non si portano. Regola unica per contratto e offerta, che la scheda ci fosse o no. Chi la chiama: la nascita del contratto (vendite.trgfn_contratti_snapshot_precontrattuali) e il cambio di cliente in bozza (vendite.trgfn_doc_fornitura_segue_cliente). Alla nascita le chiavi dell''operatore correggono poi la scheda (vendite.fn_create_contratto, D-7). Errori: id mancante E_DOC_FORNITURA_PARAMETRO_MANCANTE, selettore ignoto E_DOC_TIPO_NON_GESTITO (TECNICO entrambi). INVOKER: scrive sotto la RLS di chi chiama; la riga nuova passa dal guard della coppia e, sul contratto, dal guard tipo/classe. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§8.4). ⭐ rev 2026-10-19 (20261019-49, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

---
{% include-markdown "signature-core.md" %}
