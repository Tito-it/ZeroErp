{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_ddt_riconsegna.md" %}
# ⚙️ Funzione `fn_pgtap_crea_ddt_riconsegna`

```sql
CREATE FUNCTION fn_pgtap_crea_ddt_riconsegna(p_reso_id bigint, p_stato_codice_interno character varying, p_resi_riga_id bigint, p_quantita numeric, p_data date, p_causale_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_ddt_riconsegna(p_reso_id bigint, p_stato_codice_interno character varying DEFAULT 'CONSEGNATO'::character varying, p_resi_riga_id bigint DEFAULT NULL::bigint, p_quantita numeric DEFAULT NULL::numeric, p_data date DEFAULT NULL::date, p_causale_codice character varying DEFAULT 'VENDITA'::character varying)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint, quantita numeric, stato_doc_ddt_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP la BOLLA DI RI-CONSEGNA di un
--   reso per ri-consegna confermato, nello stato chiesto (default
--   CONSEGNATO), per la strada vera del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_ric AS
--   SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna(
--              (SELECT reso_id FROM tmp_r), p_resi_riga_id => (SELECT resi_riga_id FROM tmp_r),
--              p_quantita => 2, p_data => DATE '2026-09-01');
-- ⛔ Restituisce la PRIMA riga della bolla: con piu' righe il test
--   le legge da se'.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_stato_id   config.stati_doc_ddt.id%TYPE;
    v_abortito   config.stati_doc_ddt.is_abortito%TYPE;
    v_causale_id config.causali_trasporto.id%TYPE;
    v_righe      jsonb;      -- la grammatica della madre
    v_ddt        vendite.ddt.id%TYPE;
BEGIN
    -- 0. I parametri si giudicano PRIMA di costruire.
    SELECT s.id, s.is_abortito INTO v_stato_id, v_abortito
      FROM config.stati_doc_ddt s
     WHERE s.codice_interno = p_stato_codice_interno
       AND s.attivo IS TRUE;
    IF v_stato_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_riconsegna: nessuno stato attivo della bolla con codice_interno = %',
            coalesce(p_stato_codice_interno::text, 'NULL');
    END IF;
    IF v_abortito THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_riconsegna: % e'' uno stato abortito — la bolla di ri-consegna ha i legami e si annulla col verbo vendite.fn_annulla_ddt: chiedere EMESSO e annullare dal test',
            p_stato_codice_interno;
    END IF;

    SELECT c.id INTO v_causale_id
      FROM config.causali_trasporto c
     WHERE c.codice = p_causale_codice
       AND c.attivo IS TRUE;
    IF v_causale_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_riconsegna: nessuna causale di trasporto attiva con codice = %',
            coalesce(p_causale_codice::text, 'NULL');
    END IF;

    -- La quantita' vale per UNA riga del reso: le due si danno insieme.
    IF (p_resi_riga_id IS NULL) <> (p_quantita IS NULL) THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_ddt_riconsegna: p_resi_riga_id e p_quantita vanno insieme (senza, si ri-consegna tutto il reso)';
    END IF;

    -- 1. La bolla dalla madre.
    v_righe := CASE WHEN p_resi_riga_id IS NOT NULL THEN
                   jsonb_build_array(jsonb_build_object(
                       'resi_riga_id', p_resi_riga_id, 'qta', p_quantita))
               END;
    v_ddt := vendite.fn_genera_ddt_riconsegna(p_reso_id, v_righe, p_data);

    -- 2. Cio' che l'emissione pretende e la madre non ha portato.
    UPDATE vendite.ddt d
       SET causale_trasporto_id = v_causale_id
     WHERE d.id = v_ddt
       AND d.causale_trasporto_id IS NULL;

    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_ddt, ti.id, jsonb_build_object('display', 'pgTAP ' || ti.codice_interno)
      FROM config.tipi_indirizzi ti
     WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti(
               'DDT_VENDITA',
               (SELECT array_agg(di.tipo_indirizzo_id)::integer[]
                  FROM vendite.ddt_indirizzi di
                 WHERE di.ddt_id = v_ddt)))
    ON CONFLICT DO NOTHING;

    -- 3. Lo stato chiesto, per la matrice.
    IF v_stato_id IS DISTINCT FROM script.fn_stato_iniziale_id('config.stati_doc_ddt'::regclass) THEN
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt'::regclass, v_ddt, p_stato_codice_interno);
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT d.id, d.uid, dr.id, dr.quantita, d.stato_doc_ddt_id
      FROM vendite.ddt d
      JOIN LATERAL (
          SELECT r.id, r.quantita
            FROM vendite.ddt_righe r
           WHERE r.ddt_id = d.id
           ORDER BY r.riga_nr, r.id
           LIMIT 1) dr ON true
     WHERE d.id = v_ddt;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_ddt_riconsegna(p_reso_id bigint, p_stato_codice_interno character varying, p_resi_riga_id bigint, p_quantita numeric, p_data date, p_causale_codice character varying)
IS 'Fixture pgTAP: la BOLLA DI RI-CONSEGNA di un reso per ri-consegna confermato, nello stato chiesto (secondo parametro, default CONSEGNATO), per la strada vera del dominio. ⭐ Esiste per la TRAPPOLA D''ORDINE che i file ricopiavano dopo vendite.fn_genera_ddt_riconsegna: indirizzo e causale riscritti a mano, passaggi fino a consegnata. La bolla la fa la madre: tutto cio'' che il reso lascia da ri-consegnare, oppure p_quantita della riga p_resi_riga_id (i due insieme, o nessuno), alla data p_data (NULL = data operativa); la madre copia causale e indirizzi dalla bolla d''origine. Cio'' che l''emissione pretende e la madre non ha portato lo completa: la causale p_causale_codice (default VENDITA) solo se manca, gli indirizzi obbligatori dell''ambito DDT_VENDITA mancanti (come dbops.fn_pgtap_crea_ddt_da_ordine). Lo stato si raggiunge con dbops.fn_pgtap_porta_a_stato, sotto i guard veri; uno stato abortito si rifiuta prima di costruire (l''annullo di una bolla con legami e'' del verbo vendite.fn_annulla_ddt). Il reso lo costruisce dbops.fn_pgtap_crea_reso; le regole (reso confermato, tipo per ri-consegna, residuo) le giudica la madre. Restituisce la bolla, la PRIMA riga con la sua quantita'' base e lo stato. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper. Brief: brief-db-pgtap-reso-costruito (D-3), 2026-10-25.';
```

</div>

---
{% include-markdown "signature-core.md" %}
