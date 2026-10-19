# ⚙️ Funzione `fn_get_cliente_testata_documento`

```sql
CREATE FUNCTION fn_get_cliente_testata_documento(p_documento character varying, p_testata_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_cliente_testata_documento(p_documento character varying, p_testata_id bigint)
 RETURNS TABLE(soggetto_ruolo_id bigint, istanza_utility_id bigint)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore senza colonna
--   di vocabolario; p_testata_id e' POLIMORFO, l'id di sei testate
--   diverse (lo stesso contratto di script.fn_get_stato_testata_documento).
BEGIN
  -- =========================================================
  -- Scopo:
  --   Il cliente del documento, SENZA passare dalla RLS di
  --   testate e billing account.
  -- Contratto:
  --   - zero righe -> la testata non esiste;
  --   - una riga   -> soggetto_ruolo_id (NOT NULL sul modello:
  --     nativo NOT NULL su DDT e ordine, BA NOT NULL sugli
  --     altri) e istanza_utility_id (NULL sul DDT senza BA).
  -- =========================================================
  IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
    RETURN;   -- nessuna riga: il chiamante lo legge come «assente»
  END IF;

  IF p_documento = 'DDT_VENDITA' THEN
    -- Il destinatario c'e' sempre; col BA ne e' la copia (fk_ddt_ba_cliente).
    -- Senza BA (causale che non manda merce a un cliente) non c'e'
    -- una fornitura.
    RETURN QUERY
    SELECT d.destinatario_soggetto_ruolo_id, ba.istanza_utility_id
      FROM vendite.ddt d
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = d.billing_account_id
     WHERE d.id = p_testata_id;

  ELSIF p_documento = 'ORDINE_VENDITA' THEN
    RETURN QUERY
    SELECT o.soggetto_ruolo_id, ba.istanza_utility_id
      FROM vendite.ordini o
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = o.billing_account_id
     WHERE o.id = p_testata_id;

  ELSIF p_documento = 'PREVENTIVO' THEN
    RETURN QUERY
    SELECT ba.soggetto_ruolo_id, p.istanza_utility_id
      FROM vendite.preventivi p
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
     WHERE p.id = p_testata_id;

  ELSIF p_documento = 'OFFERTA_COMMERCIALE' THEN
    RETURN QUERY
    SELECT ba.soggetto_ruolo_id, o.istanza_utility_id
      FROM vendite.offerte_commerciali o
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = o.billing_account_id
     WHERE o.id = p_testata_id;

  ELSIF p_documento = 'CONTRATTO' THEN
    RETURN QUERY
    SELECT ba.soggetto_ruolo_id, c.istanza_utility_id
      FROM vendite.contratti c
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
     WHERE c.id = p_testata_id;

  ELSIF p_documento = 'FATTURA' THEN
    -- Lo stesso BA da cui fn_snapshot_indirizzi_fattura risolve.
    RETURN QUERY
    SELECT ba.soggetto_ruolo_id, ba.istanza_utility_id
      FROM vendite.fatture f
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = f.billing_account_id
     WHERE f.id = p_testata_id;

  ELSE
    -- Errore di CHIAMANTE, non di dato: come il gemello dello stato.
    PERFORM script.fn_log_and_raise_error(
      'script',
      'fn_get_cliente_testata_documento',
      'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('documento',  p_documento,
                         'testata_id', p_testata_id),
      NULL::uuid,
      COALESCE(p_documento, '<null>'));
  END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_get_cliente_testata_documento(p_documento character varying, p_testata_id bigint)
IS 'Lettore SECURITY DEFINER del cliente di un documento, l''ancora dei suoi indirizzi: (soggetto_ruolo_id, istanza_utility_id). DDT: destinatario e istanza del BA (NULL senza BA). ORDINE: soggetto_ruolo_id e istanza del BA. PREVENTIVO, OFFERTA, CONTRATTO: ruolo del BA e istanza nativa. FATTURA: ruolo e istanza del BA, come vendite.fn_snapshot_indirizzi_fattura. Col BA colonna nativa e BA coincidono per costruzione (fk_*_ba_cliente, fk_*_ba_coppia). E'' la stessa ancora che il backend leggeva da solo (get_ancora_indirizzi_documento). ⛔ SECURITY DEFINER come script.fn_get_stato_testata_documento: testate e billing_account hanno la RLS, e un guard che leggesse sotto RLS non distinguerebbe «non c''e''» da «non la vedo». Zero righe = testata assente. Selettore ignoto: E_DOC_TIPO_NON_GESTITO (TECNICO). Chiamanti: vendite.trgfn_doc_indirizzi_guard_cliente, vendite.fn_doc_indirizzo_default, vendite.trgfn_doc_indirizzi_seguono_cliente, script.fn_check_indirizzi_documento_cliente. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§7.2 c). ⭐ rev 2026-10-19 (20261019-42, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

---
{% include-markdown "signature-core.md" %}
