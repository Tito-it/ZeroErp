{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_fattura_header.md" %}
# ⚙️ Funzione `fn_get_or_create_fattura_header`

```sql
CREATE FUNCTION fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-24 (20261024-17, brief-modello-documento-vendita N-1/P-2):
--   lo stato iniziale non si scrive piu' qui: lo mette il trigger della
--   nascita (script.trgfn_doc_stato_iniziale), letto dal vocabolario.
-- Scopo: recupera o crea la testata DRAFT della fattura a cui
--        l'attivita' appartiene, dentro il lotto dato.
-- Regole: il `WHERE` del lookup e la INSERT devono nominare gli
--         STESSI elementi della chiave prodotta da
--         fn_build_fattura_key (§6). Se la chiave separa e il
--         lookup no, le due meta' si annullano e le attivita'
--         tornano nella stessa fattura.
-- rev 2026-08-04 (D-M): la INSERT sul ponte non nomina piu'
--         `esclusa`: era l'unico punto che la scriveva, e ci
--         scriveva la costante FALSE.
-- rev 2026-08-18 (brief nota di credito, N3): la chiave ha
--         undici elementi. Natura e serie entrano nel WHERE E
--         nella INSERT. ⚠️ La serie in particolare non era MAI
--         stata scritta da qui: restava NULL e la numerazione
--         cadeva sul serie_default del registro.
-- rev 2026-08-25 (DB-6, cantiere numerazione-data-documento):
--         la data non e' piu' `current_date`. ⛔ Questa e' l'unica
--         riga in tutto il repo che scrive vendite.fatture.data.
-- rev 2026-08-26 (DB-7 + DB-13, cantiere limite-emissione):
--         la SERIE entra fra gli argomenti della data — il clamp
--         legge il contatore di (registro, serie) e senza la
--         serie leggerebbe quello di un'altra sequenza — e la
--         COMPETENZA viene SCRITTA sulla fattura, perche' e' una
--         proprieta' del documento e non del lotto che lo produce.
DECLARE
    v_key          JSONB;
    v_fattura_id   vendite.fatture.id%TYPE;
    v_registro_id  vendite.registri_fatturazione.id%TYPE;
    v_ba_id        anagrafiche.billing_account.id%TYPE;
    v_tipo_doc_id  config.tipi_doc_fiscale.id%TYPE;
    v_natura_id    config.nature_doc_fiscale.id%TYPE;
    v_valuta_id    config.valute.id%TYPE;
    v_utility_id   config.utilities.id%TYPE;
    v_emittente_id anagrafiche.soggetti_ruoli.id%TYPE;
    v_reseller_id  anagrafiche.soggetti_ruoli.id%TYPE;
    v_serie        vendite.fatture.serie%TYPE;
    v_termine_id   config.termini_pagamento.id%TYPE;
    v_modalita_id  config.modalita_pagamento.id%TYPE;
    -- rev 2026-08-25: i tre ingredienti della data.
    v_competenza_mese vendite.fatturazione_lotti.competenza_mese%TYPE;
    v_data_dichiarata vendite.fatturazione_lotti.data_documento%TYPE;
    v_data            vendite.fatture.data%TYPE;
BEGIN
    -- ⭐ rev 2026-08-26: guard UNO PER PARAMETRO, e codice TECNICO
    --    di dominio. Prima era un E_PARAMETRO_INVALIDO solo con
    --    dentro `p_lotto_id e p_attivita_id obbligatori e > 0`:
    --    nomi di variabili PL/pgSQL nella frase che legge una
    --    persona. Il codice sceglie la frase, ma il valore che ci
    --    si infila dentro lo sceglie chi solleva.
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_or_create_fattura_header',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'lotto_id obbligatorio e maggiore di zero',
                'p_lotto_id', p_lotto_id),
            NULL::uuid,
            'vendite.fn_get_or_create_fattura_header',
            'p_lotto_id (obbligatorio, maggiore di zero)');
    END IF;

    IF p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_or_create_fattura_header',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'attivita_id obbligatorio e maggiore di zero',
                'p_attivita_id', p_attivita_id),
            NULL::uuid,
            'vendite.fn_get_or_create_fattura_header',
            'p_attivita_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Chiave documento dall'attivita': undici elementi, e da qui
    -- in giu' vanno usati tutti e undici.
    v_key := vendite.fn_build_fattura_key(p_attivita_id);
    v_ba_id        := (v_key->>'billing_account_id')::BIGINT;
    v_tipo_doc_id  := (v_key->>'tipo_doc_fiscale_id')::BIGINT;
    v_natura_id    := (v_key->>'natura_doc_id')::BIGINT;
    v_valuta_id    := (v_key->>'valuta_id')::INTEGER;
    v_emittente_id := (v_key->>'emittente_soggetto_ruolo_id')::BIGINT;
    v_reseller_id  := NULLIF(v_key->>'reseller_soggetto_ruolo_id', '')::BIGINT;
    v_utility_id   := NULLIF(v_key->>'utility_id', '')::INTEGER;
    v_registro_id  := (v_key->>'registro_id')::BIGINT;
    v_serie        := NULLIF(v_key->>'serie', '')::VARCHAR;
    v_termine_id   := NULLIF(v_key->>'termine_pagamento_id', '')::BIGINT;
    v_modalita_id  := NULLIF(v_key->>'modalita_pagamento_id', '')::INTEGER;

    -- Completezza della chiave: si pretendono solo gli elementi
    -- che NON possono legittimamente mancare. utility_id entra
    -- nell'elenco perche' anagrafiche.billing_account.utility_id e'
    -- NOT NULL: se qui arriva vuoto, la chiave e' rotta, non
    -- «senza utility». Stesso ragionamento per natura_doc_id, che
    -- e' NOT NULL su attivita_fatturabili. Termine e modalita'
    -- restano fuori, e non e' una dimenticanza: la modalita' e'
    -- NULL nella maggioranza dei casi (nessun default inventato,
    -- finirebbe sulla FatturaPA) e il termine ha il default
    -- TP_1RATA della catena — la sua assenza la presidia la Fase 4
    -- al momento di generare le rate. E la SERIE resta fuori
    -- perche' NULL e' il suo valore normale: significa «vale il
    -- serie_default del registro».
    IF v_ba_id IS NULL OR v_tipo_doc_id IS NULL OR v_natura_id IS NULL
       OR v_valuta_id IS NULL
       OR v_emittente_id IS NULL OR v_utility_id IS NULL OR v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_fattura_header', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id, 'chiave', v_key),
            NULL::uuid, concat('chiave documento incompleta per attivita_id ', p_attivita_id)
        );
    END IF;

    -- Cerca fattura gia' nel lotto con la stessa chiave.
    -- ⚠️ IS NOT DISTINCT FROM sui QUATTRO elementi nullable: con
    -- `=` il NULL non combacia mai, quindi ogni giro aprirebbe una
    -- fattura nuova per i casi — che sono la maggioranza — in cui
    -- reseller, modalita' o serie non ci sono. E' la stessa
    -- trappola dei NULL gia' pagata in 3b.0-b sul WHERE della
    -- commessa e in 3b.4-bis sull'indice d'ambito, terza forma.
    -- La NATURA invece usa `=`: e' NOT NULL, e un confronto
    -- permissivo nasconderebbe sotto una uguaglianza un valore che
    -- non puo' mancare.
    SELECT f.id INTO v_fattura_id
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
       AND f.billing_account_id = v_ba_id
       AND f.tipo_doc_fiscale_id = v_tipo_doc_id
       AND f.natura_doc_id = v_natura_id
       AND f.valuta_id = v_valuta_id
       AND f.emittente_soggetto_ruolo_id = v_emittente_id
       AND f.reseller_soggetto_ruolo_id IS NOT DISTINCT FROM v_reseller_id
       AND f.utility_id IS NOT DISTINCT FROM v_utility_id
       AND f.registro_id = v_registro_id
       AND f.serie IS NOT DISTINCT FROM v_serie
       AND f.termine_pagamento_id IS NOT DISTINCT FROM v_termine_id
       AND f.modalita_pagamento_id IS NOT DISTINCT FROM v_modalita_id
     ORDER BY f.id LIMIT 1;

    IF v_fattura_id IS NOT NULL THEN RETURN v_fattura_id; END IF;

    -- ─── rev 2026-08-25 (DB-6): LA DATA ───────────────────────
    -- ⭐ Il lotto si legge QUI e non in testa: questa funzione gira
    --    una volta per ATTIVITA', e nella stragrande maggioranza
    --    dei giri esce dalla riga qui sopra con la testata gia'
    --    creata. In testa, sarebbe una query in piu' per ogni
    --    attivita' di ogni lotto, per un valore che serve solo
    --    alla prima.
    -- ⚠️ fatturazione_lotti ha la RLS (ef_whitelist, FOR ALL) e
    --    questa funzione e' SECURITY INVOKER: un lotto fuori dal
    --    perimetro di chi opera si legge come «non c'e'». E'
    --    fail-closed ed e' la risposta giusta — non si crea una
    --    testata dentro un lotto che non si puo' vedere.
    SELECT fl.competenza_mese, fl.data_documento
      INTO v_competenza_mese, v_data_dichiarata
      FROM vendite.fatturazione_lotti fl
     WHERE fl.id = p_lotto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_fattura_header', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id,
                               'attivita_id', p_attivita_id),
            NULL::uuid, p_lotto_id::text
        );
    END IF;

    -- ⭐ La regola sta nel registro (e la dichiarazione sul lotto
    --    la scavalca): qui non si decide niente, si chiede.
    -- ⚠️ rev 2026-08-26: LA SERIE E' UN ARGOMENTO, e non e' un
    --    dettaglio — il clamp legge il contatore di
    --    (registro, SERIE), e senza di essa leggerebbe quello di
    --    un'altra sequenza rispondendo «nessun pavimento».
    v_data := vendite.fn_calcola_data_documento(
                  v_registro_id, v_competenza_mese, v_serie, v_data_dichiarata);

    -- Crea fattura + link lotto. Le colonne di testata sono il
    -- secondo specchio: quello che la chiave ha deciso, qui si
    -- scrive. ⚠️ `serie` compresa: e' la meta' che mancava.
    -- ⭐ rev 2026-08-26 (DB-13): `competenza_mese` viene SCRITTA.
    --    Il valore e' gia' in mano — si legge dal lotto due righe
    --    piu' su per calcolare la data — quindi la colonna costa
    --    una parola nella lista, non una query. Si scrive ALLA
    --    NASCITA e non si insegue: la fattura nasce dentro UN
    --    lotto, che non e' ambiguo.
    INSERT INTO vendite.fatture (registro_id, data, competenza_mese,
        tipo_doc_fiscale_id, natura_doc_id,
        serie,
        emittente_soggetto_ruolo_id, billing_account_id, reseller_soggetto_ruolo_id,
        utility_id, valuta_id, tasso_cambio,
        termine_pagamento_id, modalita_pagamento_id, meta)
    VALUES (v_registro_id, v_data, v_competenza_mese,
        v_tipo_doc_id, v_natura_id,
        v_serie,
        v_emittente_id, v_ba_id, v_reseller_id,
        v_utility_id, v_valuta_id, 1,
        v_termine_id, v_modalita_id, jsonb_build_object('lotto_id', p_lotto_id))
    RETURNING id INTO v_fattura_id;

    INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, meta)
    VALUES (p_lotto_id, v_fattura_id, jsonb_build_object('origine', 'bozza'));

    RETURN v_fattura_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_fattura_header(p_lotto_id bigint, p_attivita_id bigint)
IS 'Recupera o crea la testata DRAFT della fattura a cui l''attivita'' appartiene, dentro il lotto dato. Il WHERE del lookup e la INSERT nominano gli STESSI elementi della chiave di fn_build_fattura_key: se la chiave separa e il lookup no, le due meta'' si annullano e le attivita'' tornano nella stessa fattura. rev 2026-08-18 (brief-design-note-credito-resi N3): la chiave ha undici elementi, natura e serie compresi. ⚠️ `serie` non era MAI stata scritta da questa INSERT — restava NULL e fn_assign_numero_fattura cadeva sul serie_default del registro: calcolarla senza scriverla avrebbe dato alla nota di credito un numero VALIDO nella serie delle fatture, cioe'' un difetto che non solleva nulla e si scopre guardando un registro IVA. Confronto: `=` sulla natura (NOT NULL), IS NOT DISTINCT FROM sui quattro nullable. ⭐ rev 2026-08-25 (cantiere numerazione-data-documento): la data non e'' piu'' `current_date` ma vendite.fn_calcola_data_documento. ⛔ Questa e'' l''UNICA riga in tutto il repo che scrive vendite.fatture.data — e dal 2026-08-26 anche l''unica che scrive vendite.fatture.competenza_mese — verificato su pg_proc, su backend/ e sulla doc auto-gen: cambiarla qui cambia il comportamento ovunque, ed e'' anche il motivo per cui il difetto di `current_date` era rimasto invisibile (non c''era un secondo posto in cui vedere due implementazioni divergenti). ⭐ rev 2026-08-26 (cantiere limite-emissione, DB-7 e DB-13), TRE modifiche: (1) la SERIE entra fra gli argomenti della data — il clamp legge il contatore di (registro, SERIE) e senza la serie leggerebbe quello di un''ALTRA sequenza, rispondendo «nessun pavimento» proprio dove il cancello rifiuta; (2) la INSERT scrive `competenza_mese`, che serve al cancello per applicare il limite di emissione senza dover leggere il lotto sotto RLS — il valore e'' gia'' in mano, si legge dal lotto due righe piu'' su per calcolare la data, quindi costa una parola nella lista e non una query. ⚠️ Si scrive ALLA NASCITA e non si insegue: la fattura nasce dentro UN lotto, e se piu'' tardi entrera'' in un secondo lotto con un''altra competenza la colonna resta quella di nascita; (3) i guard di parametro passano da E_PARAMETRO_INVALIDO — che portava `p_lotto_id e p_attivita_id obbligatori e > 0` nella frase letta da una persona — a E_VENDITE_CHIAMATA_NON_VALIDA, UNO PER PARAMETRO. ⭐ Il lotto si legge DOPO il lookup e non in testa: la funzione gira una volta per attivita'' e quasi sempre trova la testata gia'' creata. ⚠️ vendite.fatturazione_lotti ha la RLS e questa funzione e'' SECURITY INVOKER: un lotto fuori perimetro si legge come «non c''e''» e si esce con E_LOTTO_NON_TROVATO. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-7 e DB-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
