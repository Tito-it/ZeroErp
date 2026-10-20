{% include-markdown "it/dbzero/script/manual/fn_get_testata_id_di_riga.md" %}
# ⚙️ Funzione `fn_get_testata_id_di_riga`

```sql
CREATE FUNCTION fn_get_testata_id_di_riga(p_documento character varying, p_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_testata_id_di_riga(p_documento character varying, p_riga_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: p_riga_id e il ritorno sono POLIMORFI
--   (l'id di sei tabelle di righe, l'id di sei testate): non c'e'
--   UNA colonna da ancorare.
DECLARE
  v_testata_id bigint;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Rispondere a «di quale testata e' questa riga?» SENZA
  --   passare dalla RLS delle righe. Serve al lock delle
  --   tabelle NIPOTI (vendite.trgfn_doc_righe_lock_fuori_bozza
  --   montato a livello RIGA): componenti e rientri hanno la
  --   FK verso la riga, non verso la testata.
  --
  -- Contratto:
  --   - NULL     -> la riga NON esiste (cascade partito dalla
  --     riga, o FK che parlera'). Il chiamante la tratta come
  --     il gemello tratta la testata assente: passa.
  --   - un id    -> la testata della riga (la FK e' NOT NULL
  --     su tutte e sei le tabelle).
  --
  -- ⛔ Elenco CHIUSO di tabelle, scelto dal tipo di documento:
  --    nessun nome arriva dal chiamante, nessun SQL dinamico.
  --    Un DEFINER che leggesse una tabella qualunque per id
  --    sarebbe una porta su ogni colonna bigint del database.
  -- =========================================================
  IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
    RETURN NULL;   -- il chiamante lo legge come «assente»
  END IF;

  IF p_documento = 'CONTRATTO' THEN
    SELECT r.contratto_id INTO v_testata_id
      FROM vendite.contratti_righe r
     WHERE r.id = p_riga_id;

  ELSIF p_documento = 'OFFERTA_COMMERCIALE' THEN
    SELECT e.offerta_id INTO v_testata_id
      FROM vendite.offerte_commerciali_eccezioni e
     WHERE e.id = p_riga_id;

  ELSIF p_documento = 'PREVENTIVO' THEN
    -- rev 2026-10-08 (brief-db-righe-e-componenti-le-altre-famiglie
    -- §2.2): PREVENTIVO, ORDINE e DDT, per il lock dei loro componenti.
    SELECT r.preventivo_id INTO v_testata_id
      FROM vendite.preventivi_righe r
     WHERE r.id = p_riga_id;

  ELSIF p_documento = 'ORDINE_VENDITA' THEN
    SELECT r.ordine_id INTO v_testata_id
      FROM vendite.ordini_righe r
     WHERE r.id = p_riga_id;

  ELSIF p_documento = 'DDT_VENDITA' THEN
    SELECT r.ddt_id INTO v_testata_id
      FROM vendite.ddt_righe r
     WHERE r.id = p_riga_id;

  ELSIF p_documento = 'RESO_VENDITA' THEN
    SELECT r.reso_id INTO v_testata_id
      FROM vendite.resi_righe r
     WHERE r.id = p_riga_id;

  ELSE
    -- Errore di CHIAMANTE, non di dato: nessuna persona sceglie
    -- questo valore (stesso codice del gemello
    -- script.fn_get_stato_testata_documento).
    PERFORM script.fn_log_and_raise_error(
      'script',
      'fn_get_testata_id_di_riga',
      'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('documento', p_documento,
                         'riga_id',   p_riga_id),
      NULL::uuid,
      COALESCE(p_documento, '<null>'));
  END IF;

  RETURN v_testata_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_testata_id_di_riga(p_documento character varying, p_riga_id bigint)
IS 'Lettore SECURITY DEFINER della testata di una riga di documento: risponde a «di quale testata e'' questa riga?» senza passare dalla RLS delle righe. Nasce il 2026-10-05 per vendite.trgfn_doc_righe_lock_fuori_bozza montato a livello RIGA, cioe'' sulle tabelle NIPOTI (componenti di una riga di contratto o di offerta, rientri di una riga di reso), che hanno la FK verso la riga e non verso la testata. ⛔ SECURITY DEFINER del PROPRIETARIO, non di un superuser: le righe hanno RLS, e un guard che le leggesse da invoker non distinguerebbe «la riga non c''e'' piu''» (cascade) da «non la vedo», diventando fail-open per chi sta fuori perimetro — la stessa ragione del gemello script.fn_get_stato_testata_documento. CONTRATTO: NULL = riga assente; un id = la sua testata (la FK e'' NOT NULL). PERIMETRO: legge una colonna di una riga da un elenco CHIUSO di tabelle scelto dal tipo — CONTRATTO (vendite.contratti_righe.contratto_id), OFFERTA (vendite.offerte_commerciali_eccezioni.offerta_id), RESO (vendite.resi_righe.reso_id), PREVENTIVO (vendite.preventivi_righe.preventivo_id), ORDINE (vendite.ordini_righe.ordine_id), DDT (vendite.ddt_righe.ddt_id); nessun nome di tabella dal chiamante, nessun SQL dinamico. Qualunque altro tipo e'' un errore di chiamante (E_DOC_TIPO_NON_GESTITO, TECNICO). Un tipo nuovo entra col suo primo adottante. Brief: brief-db-righe-esclusione-solo-non-si-vende (§8.2 B3). rev 2026-10-08 (brief-db-righe-e-componenti-le-altre-famiglie §2.2): + PREVENTIVO, ORDINE, DDT, per il lock dei componenti delle tre famiglie fuori bozza. ⭐ rev 2026-10-19 (20261019-41, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
