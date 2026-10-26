{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_riepilogo_iva_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_riepilogo_iva_fattura`

```sql
CREATE FUNCTION fn_ricalcola_riepilogo_iva_fattura(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id bigint)
 RETURNS TABLE(deleted_rows integer, inserted_rows integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_deleted_rows  INTEGER := 0;
    v_inserted_rows INTEGER := 0;
    v_stato_id      vendite.fatture.stato_doc_fiscale_id%TYPE;
    v_codice_interno config.stati_doc_fiscale.codice_interno%TYPE;
    v_congela_fiscale config.stati_doc_fiscale.congela_fiscale%TYPE;
    v_stato_emittente_id anagrafiche.soggetti.stato_id%TYPE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    SELECT f.stato_doc_fiscale_id INTO v_stato_id FROM vendite.fatture f WHERE f.id = p_fattura_id;

    -- ⚠️ L'esistenza si misura con NOT FOUND, non con l'IS NULL di
    --    una colonna NULLABILE. `stato_doc_fiscale_id` puo' essere
    --    NULL su una fattura che esiste: il codice precedente la
    --    dichiarava «non trovata» e mandava a cercare un documento
    --    che invece era li'.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id), NULL::uuid, p_fattura_id::text);
    END IF;

    -- La fattura c'e' ma non ha stato: e' un'altra cosa, e va detta
    -- come tale. Senza stato non si puo' decidere se il ricalcolo
    -- sia ammesso, quindi non si procede.
    IF v_stato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_VALORE_MANCANTE',
            jsonb_build_object('fattura_id', p_fattura_id, 'campo', 'stato_doc_fiscale_id'),
            NULL::uuid, concat('stato_doc_fiscale_id della fattura ', p_fattura_id));
    END IF;

    SELECT s.codice_interno, s.congela_fiscale
      INTO v_codice_interno, v_congela_fiscale
      FROM config.stati_doc_fiscale s
     WHERE s.id = v_stato_id;

    -- ⭐ LA SOGLIA E' UN DATO, non una lista qui dentro
    --    (rev 2026-08-29, D15 del brief IVA). Due finestre di
    --    congelamento sullo stesso documento sono due verita' che
    --    divergono in silenzio.
    -- ⚠️ `IS NULL OR`: senza, uno stato non risolvibile renderebbe
    --    l'espressione NULL e l'IF non scatterebbe. Oggi il ramo e'
    --    irraggiungibile: si tiene perche' costa zero.
    -- ⚠️ Il COALESCE e' la difesa gemella sulla colonna nuova: un
    --    dubbio su uno snapshot fiscale si risolve NON ricalcolando.
    IF v_codice_interno IS NULL OR COALESCE(v_congela_fiscale, true) THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_codice_interno,
                               'stato_doc_fiscale_id', v_stato_id, 'fattura_id', p_fattura_id),
            NULL::uuid, concat('ricalcolo IVA non ammesso per stato ', COALESCE(v_codice_interno, '(non risolvibile)')));
    END IF;

    -- Recupero stato emittente per override aliquota IVA
    SELECT s.stato_id INTO v_stato_emittente_id
      FROM vendite.fatture f
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
     WHERE f.id = p_fattura_id;

    DELETE FROM vendite.fatture_riepiloghi_iva WHERE fattura_id = p_fattura_id;
    GET DIAGNOSTICS v_deleted_rows = ROW_COUNT;

    -- ⭐ LE RIGHE SI RIALLINEANO PRIMA DI ESSERE AGGREGATE (D30).
    --    Questa funzione, per costruzione, vede SOLO documenti
    --    non congelati: il guard qui sopra rifiuta gli altri.
    --    Su un documento che puo' ancora cambiare la risposta
    --    giusta e' il catalogo di ADESSO — e' la stessa regola
    --    che segue il trigger di riga, che riscrive l'aliquota
    --    a ogni scrittura. Lo snapshot diventa una fotografia
    --    quando il documento smette di essere scritto, non
    --    perche' qualcuno smette di leggerlo.
    -- ⚠️ `IS DISTINCT FROM`: senza, ogni ricalcolo toccherebbe
    --    tutte le righe e produrrebbe una riga di storico per
    --    ognuna. Cosi' si muove solo cio' che e' davvero
    --    cambiato, e quel movimento e' proprio il fatto che
    --    vale la pena registrare.
    UPDATE vendite.fatture_righe r
       SET aliquota_iva = config.fn_get_aliquota_iva(r.iva_id, v_stato_emittente_id)
     WHERE r.fattura_id = p_fattura_id
       AND r.iva_id IS NOT NULL
       AND r.aliquota_iva IS DISTINCT FROM
           config.fn_get_aliquota_iva(r.iva_id, v_stato_emittente_id);

    -- ⭐ rev 2026-10-01 (D-8 di brief-db-esigibilita-iva-per-cassa-
    --    emittente): anche ESIGIBILITA' e SCISSIONE si riallineano
    --    prima di essere aggregate, per la stessa ragione dell'aliquota
    --    (D30). La riga le deriva quando viene scritta; il regime
    --    dell'emittente, la scissione o la partita IVA del cliente
    --    possono cambiare dopo, e il riepilogo RAGGRUPPA per
    --    (iva, natura, esigibilita, split). Il regime e' quello che la
    --    testata stampa: vendite.fn_esigibilita_iva_fattura legge lo
    --    snapshot dell'intestazione, se c'e'. Cosi' il ricalcolo del
    --    passo EMESSA della pipeline, l'ultimo prima del congelamento,
    --    lascia righe e testata sullo stesso regime.
    -- ⚠️ CTE + `IS DISTINCT FROM` per lo stesso motivo dell'UPDATE qui
    --    sopra: si tocca solo la riga che cambia davvero. Il trigger di
    --    riga ricalcola la stessa coppia dalla stessa funzione.
    WITH derivata AS (
        SELECT r.id, e.esigibilita, e.split_payment
          FROM vendite.fatture_righe r
          CROSS JOIN LATERAL vendite.fn_esigibilita_iva_fattura(r.fattura_id, r.iva_id) e
         WHERE r.fattura_id = p_fattura_id
    )
    UPDATE vendite.fatture_righe r
       SET esigibilita   = d.esigibilita,
           split_payment = d.split_payment
      FROM derivata d
     WHERE r.id = d.id
       AND (   r.esigibilita   IS DISTINCT FROM d.esigibilita
            OR r.split_payment IS DISTINCT FROM d.split_payment);

    -- ⭐ rev 2026-10-22 (20261022-08, D-3 di Tid): la GUARDIA sulla riga
    --    SENZA codice IVA. Prima `config.fn_get_aliquota_iva` sollevava
    --    qui un errore tecnico («p_iva_id obbligatorio e > 0»), lontano
    --    da chi emette e senza dire quale riga. Ora quella riga entra nel
    --    riepilogo della bozza con l'aliquota vuota, e la fattura NON SI
    --    EMETTE: entrando in EMESSA vendite.trgfn_fatture_guard_stato
    --    solleva E_FATTURA_RIGA_IVA_MANCANTE con riga e descrizione
    --    (script.fn_check_fattura_emettibile, 20261022-06/-07). E' la
    --    forma decisa il 2026-08-29 per i preventivi (§R-3 del brief IVA):
    --    la guardia entra solo INSIEME al cancello, mai da sola — senza
    --    cancello sarebbe uno zero muto su un documento fiscale.
    -- ⚠️ `MAX` e non un valore per riga: il gruppo non comprende
    --    l'aliquota, e non puo' — lo impedisce uq_fatture_r_iva_key.
    --    Dentro un gruppo l'aliquota e' una sola per costruzione
    --    (funzione di codice IVA e stato emittente, costanti sulla
    --    fattura); se divergesse, `MAX` la collassa. Residuo
    --    dichiarato nel brief.
    -- ⚠️ La sottoquery serve SOLO a poter usare l'aliquota due
    --    volte senza ripetere l'espressione: la formula di
    --    imponibile, imposta e arrotondamento e' identica a prima.
    INSERT INTO vendite.fatture_riepiloghi_iva
        (fattura_id, iva_id, natura_id, esigibilita, split_payment,
         imponibile, imposta, arrotondamento, aliquota_iva)
    SELECT g.fattura_id, g.iva_id, g.natura_id, g.esigibilita, g.split_payment,
           ROUND(g.imponibile_grezzo, 2),
           ROUND(ROUND(g.imponibile_grezzo, 2) * (COALESCE(g.aliquota, 0)::NUMERIC / 100::NUMERIC), 2),
           g.imponibile_grezzo - ROUND(g.imponibile_grezzo, 2),
           g.aliquota
      FROM (
          SELECT r.fattura_id,
                 r.iva_id,
                 n.id AS natura_id,
                 r.esigibilita,
                 r.split_payment,
                 SUM(COALESCE(r.imponibile_riga, 0)) AS imponibile_grezzo,
                 MAX(CASE WHEN r.iva_id IS NOT NULL
                          THEN config.fn_get_aliquota_iva(r.iva_id, v_stato_emittente_id)
                     END) AS aliquota
            FROM vendite.fatture_righe r
            LEFT JOIN config.iva i ON i.id = r.iva_id
            LEFT JOIN config.iva_natura n ON n.codice = r.iva_natura
           WHERE r.fattura_id = p_fattura_id
           GROUP BY r.fattura_id, r.iva_id, n.id, r.esigibilita, r.split_payment
      ) g;
    GET DIAGNOSTICS v_inserted_rows = ROW_COUNT;

    RETURN QUERY SELECT v_deleted_rows, v_inserted_rows;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id bigint)
IS 'Ricalcola i riepiloghi IVA di una fattura (DELETE + INSERT per fattura_id), raggruppando le righe per codice IVA/natura/esigibilita/split, e scrive l''aliquota sul riepilogo accanto a imponibile e imposta. ⭐ rev 2026-08-29 bis (D30 del brief IVA): PRIMA di aggregare, la funzione RIALLINEA vendite.fatture_righe.aliquota_iva al catalogo di adesso. La revisione precedente leggeva l''aliquota dalla riga con un COALESCE, per «preservare l''aliquota di allora»: era sbagliato, e il motivo e'' scritto sette righe piu'' su nella funzione stessa. Questa funzione, per costruzione, vede SOLO documenti NON congelati - il guard su congela_fiscale rifiuta gli altri - quindi quel COALESCE non poteva mai proteggere un documento emesso: agiva solo sulle bozze, cioe'' esattamente dove il catalogo di adesso e'' la risposta giusta. E produceva la divergenza che il commento di trgfn_fatture_righe_guard_normalize dichiara inaccettabile: quel trigger riscrive l''aliquota della riga a OGNI scrittura, quindi con il COALESCE riga e riepilogo dello stesso documento potevano portare aliquote diverse, e nessuno se ne sarebbe accorto finche'' non quadrava un totale. Il test pgTAP test-ricalcola-riepiloghi-iva («Override iva_stati applicato») lo ha smentito in un giorno. ⭐ La regola vera: lo snapshot dell''aliquota diventa una FOTOGRAFIA quando il documento smette di essere scritto, non perche'' qualcuno smette di leggerlo. Le colonne aggiunte da 20260829-39 servono a chi rigenera un documento GIA'' CONGELATO - un percorso che oggi non esiste, perche'' questa funzione lo rifiuta - e quel percorso, il giorno che nascera'', dovra'' leggere la riga e non il catalogo. ⚠️ Il riallineamento e'' guardato da IS DISTINCT FROM: senza, ogni ricalcolo toccherebbe tutte le righe e genererebbe una riga di storico per ognuna. ⚠️ E l''aggregazione continua a chiamare config.fn_get_aliquota_iva invece di leggere r.aliquota_iva, che dopo il riallineamento porta lo stesso valore: su una riga SENZA codice IVA la funzione SOLLEVA mentre la colonna sarebbe NULL e diventerebbe uno zero muto - trasformare un errore in uno zero su una funzione fiscale non si fa di contrabbando dentro un altro lavoro (difetto §R-3, si chiude dove vive). ⚠️ L''aliquota e'' aggregata con MAX perche'' il gruppo non la comprende e non puo'': lo impedisce uq_fatture_r_iva_key, l''unica sulla tabella; dentro un gruppo il valore e'' uno solo per costruzione, ma se divergesse MAX lo collassa - caso COLLASSATO, non risolto, residuo dichiarato nel brief. ⚠️ La formula di imponibile, imposta e arrotondamento e'' IDENTICA a quella del 2026-08-02, parentesi e arrotondamenti compresi: nessun documento si sposta di un centesimo. ⭐ rev 2026-08-29 (D15): la soglia di congelamento si legge da config.stati_doc_fiscale.congela_fiscale, e il COALESCE(v_congela_fiscale, true) e'' fail-closed. 📌 Strascico noto: il codice sollevato resta E_PARAMETRO_INVALIDO, mentre «documento congelato» e'' un conflitto di stato. rev 2026-08-02: l''esistenza si misura con NOT FOUND (stato_doc_fiscale_id e'' nullabile). ⭐ rev 2026-10-01 (D-8 di brief-db-esigibilita-iva-per-cassa-emittente): prima di aggregare riallinea anche esigibilita e split_payment delle righe, da vendite.fn_esigibilita_iva_fattura (regime congelato nello snapshot dell''intestazione se c''e'', cliente vivo), solo dove cambiano. E'' il passo che, nella pipeline, lascia righe e testata sullo stesso regime prima del congelamento. Rev 2026-10-22 (20261022-08, D-3 di Tid; §9.9 di brief-be-utenti-di-sviluppo): GUARDIA sulla riga senza codice IVA — entra nel riepilogo della bozza con l''aliquota vuota invece di sollevare E_PARAMETRO_INVALIDO da config.fn_get_aliquota_iva; la fattura non si emette (vendite.trgfn_fatture_guard_stato, E_FATTURA_RIGA_IVA_MANCANTE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
