# ⚙️ Funzione `fn_doc_indirizzo_default`

```sql
CREATE FUNCTION fn_doc_indirizzo_default(p_documento character varying, p_testata_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_doc_indirizzo_default(p_documento character varying, p_testata_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (20261020-50, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi e' il codice della sorgente del documento
--   (p_documento): la colonna ambito di fn_doc_indirizzi_sede e'
--   ritirata; p_documento ancorato. p_testata_id resta nudo: e'
--   polimorfo (testate di tabelle diverse).

-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore senza colonna
--   di vocabolario; p_testata_id e' POLIMORFO (l'id di cinque testate);
--   il boolean di ritorno e' un esito, non il riflesso di una colonna.
DECLARE
    v_schema        pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella       pg_catalog.pg_class.relname%TYPE;
    v_fk_col        pg_catalog.pg_attribute.attname%TYPE;
    v_ambito        config.tipi_indirizzi_allowed.ambito%TYPE;
    v_ruolo         anagrafiche.soggetti_ruoli.id%TYPE;
    v_istanza       anagrafiche.indirizzi.istanza_utility_id%TYPE;
    v_slot_id       config.tipi_indirizzi_allowed.tipo_indirizzo_id%TYPE;
    v_slot_cod      config.tipi_indirizzi.codice_interno%TYPE;
    v_ripiego_cod   config.tipi_indirizzi.codice_interno%TYPE;
    v_occupato      boolean;
    v_snapshot      vendite.ddt_indirizzi.snapshot%TYPE;
    v_orig_ind      anagrafiche.indirizzi.id%TYPE;
    v_orig_ruolo    anagrafiche.soggetti_ruoli.id%TYPE;
    v_scritte       integer;
BEGIN
    IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_doc_indirizzo_default', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'testata_id', 'valore', p_testata_id),
            NULL::uuid, 'testata_id obbligatorio (>0)');
    END IF;

    -- rev 2026-10-20 (G-6): l'ambito e' il documento stesso.
    v_ambito := p_documento;

    SELECT s.schema_tabella, s.tabella, s.colonna_fk
      INTO v_schema, v_tabella, v_fk_col
      FROM script.fn_doc_indirizzi_sede(p_documento) AS s;

    IF v_tabella IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_doc_indirizzo_default', 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento, 'testata_id', p_testata_id),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    -- Lo slot di default dell'ambito, e il suo ripiego. Nessuna riga:
    -- l'ambito non ha slot di default (la fattura, il DDT d'acquisto).
    SELECT a.tipo_indirizzo_id, t.codice_interno, r.codice_interno
      INTO v_slot_id, v_slot_cod, v_ripiego_cod
      FROM config.tipi_indirizzi_allowed a
      JOIN config.tipi_indirizzi t ON t.id = a.tipo_indirizzo_id
      LEFT JOIN config.tipi_indirizzi r ON r.id = a.ripiego_tipo_indirizzo_id
     WHERE a.ambito = v_ambito
       AND a.slot_default
       AND a.attivo;

    IF v_slot_id IS NULL THEN
        RETURN false;
    END IF;

    -- Il cliente. Testata assente o senza ruolo: niente da scrivere.
    SELECT c.soggetto_ruolo_id, c.istanza_utility_id
      INTO v_ruolo, v_istanza
      FROM script.fn_get_cliente_testata_documento(p_documento, p_testata_id) AS c;

    IF v_ruolo IS NULL THEN
        RETURN false;
    END IF;

    -- Slot gia' pieno (la cascata dalla sorgente, una scelta
    -- dell'operatore): vince sempre.
    EXECUTE format(
        'SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = $1 AND tipo_indirizzo_id = $2)',
        v_schema, v_tabella, v_fk_col)
       INTO v_occupato
      USING p_testata_id, v_slot_id;

    IF v_occupato THEN
        RETURN false;
    END IF;

    -- Dal tipo dello slot, poi dal ripiego: la catena unica di
    -- risoluzione, con la precedenza all'istanza del documento.
    SELECT r.snapshot, r.origine_indirizzo_id, r.origine_soggetto_ruolo_id
      INTO v_snapshot, v_orig_ind, v_orig_ruolo
      FROM script.fn_resolve_indirizzo_documento(v_ruolo, v_istanza, v_slot_cod) AS r;

    IF v_snapshot IS NULL AND v_ripiego_cod IS NOT NULL THEN
        SELECT r.snapshot, r.origine_indirizzo_id, r.origine_soggetto_ruolo_id
          INTO v_snapshot, v_orig_ind, v_orig_ruolo
          FROM script.fn_resolve_indirizzo_documento(v_ruolo, v_istanza, v_ripiego_cod) AS r;
    END IF;

    IF v_snapshot IS NULL THEN
        RETURN false;
    END IF;

    -- ON CONFLICT DO NOTHING: una scrittura concorrente sullo stesso
    -- slot vince, come la cascata.
    EXECUTE format(
        'INSERT INTO %I.%I (%I, tipo_indirizzo_id, snapshot, '
        '                   origine_indirizzo_id, origine_soggetto_ruolo_id) '
        'VALUES ($1, $2, $3, $4, $5) '
        'ON CONFLICT (%I, tipo_indirizzo_id) DO NOTHING',
        v_schema, v_tabella, v_fk_col, v_fk_col)
      USING p_testata_id, v_slot_id, v_snapshot, v_orig_ind, v_orig_ruolo;

    GET DIAGNOSTICS v_scritte = ROW_COUNT;
    RETURN v_scritte > 0;
END;
$function$

COMMENT ON FUNCTION vendite.fn_doc_indirizzo_default(p_documento character varying, p_testata_id bigint)
IS 'Riempie lo slot di default di un documento (DDT | ORDINE | PREVENTIVO | OFFERTA | CONTRATTO; FATTURA non ha slot di default) dall''anagrafica del suo cliente, SOLO se lo slot e'' vuoto: la cascata dalla sorgente e la scelta dell''operatore vincono sempre. Lo slot e il ripiego sono dati: config.tipi_indirizzi_allowed.slot_default e ripiego_tipo_indirizzo_id. Risoluzione con script.fn_resolve_indirizzo_documento (RUOLO con precedenza all''istanza, poi SOGGETTO), prima sul tipo dello slot e poi sul ripiego; cliente da script.fn_get_cliente_testata_documento. Torna true se ha scritto. Nessun errore se non c''e'' niente da scrivere: un default mancante non e'' un errore, l''obbligo lo dice l''emissione. INVOKER: scrive sotto la RLS di chi chiama. Chi la chiama (decisione di Tid del 2026-10-11): alla creazione chi crea — il backend dopo le sue INSERT e dopo i verbi con cascata, vendite.fn_create_contratto dentro di se'' —, al cambio di cliente in bozza vendite.trgfn_doc_indirizzi_seguono_cliente. Sostituisce l''helper Python auto_assegna_indirizzo_default. ⚠️ Rispetto al Python lo slot si riempie dal suo tipo e dal suo ripiego, non dalla catena fissa CON -> FATT: identico su tutti gli ambiti di oggi (slot CON, ripiego FATT). Brief: brief-db-indirizzi-documento-seguono-il-cliente (D-2, §7.2). ⭐ rev 2026-10-19 (20261019-47, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato). Rev 2026-10-20 (20261020-50, brief-db-grammatica-unica-documenti 2d, G-6): l''ambito degli indirizzi e'' il codice della sorgente del documento (p_documento).';
```

</div>

---
{% include-markdown "signature-core.md" %}
