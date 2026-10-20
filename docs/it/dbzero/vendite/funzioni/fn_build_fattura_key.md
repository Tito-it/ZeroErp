{% include-markdown "it/dbzero/vendite/manual/fn_build_fattura_key.md" %}
# ⚙️ Funzione `fn_build_fattura_key`

```sql
CREATE FUNCTION fn_build_fattura_key(p_attivita_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_build_fattura_key(p_attivita_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: chiave logica di aggregazione del documento a partire da una
--        attivita' fatturabile. Da D-7/D-B comprende anche le
--        condizioni di pagamento: due attivita' con termini diversi
--        finiscono su due fatture.
-- Regole: le condizioni si risolvono con la catena UNICA
--         (fn_resolve_termini_pagamento, 3b.1) — questa e' la
--         chiamata che chiude C-13, perche' una catena riscritta e
--         mai invocata resta un secondo risolutore in attesa d'uso.
-- rev 2026-08-18 (brief nota di credito, N2b): il registro si
--         risolve passando ANCHE utility ed emittente.
-- rev 2026-08-18 (brief nota di credito, N3): la chiave porta la
--         NATURA e la SERIE. E' cio' che impedisce a un'attivita'
--         di rettifica di finire nella fattura ordinaria: undici
--         elementi, e da qui in giu' vanno usati tutti e undici.
-- rev 2026-08-26 (brief-db-registro-e-data-prevista-in-competenza,
--         L3): la catena del SEZIONALE non si risolve piu' qui.
--         Una riga sola — fn_resolve_registro_documento — al posto
--         di COALESCE sul parent, ba.utility_id,
--         fn_get_emittente_fiscale_id e fn_get_registro_id.
--         ⭐ E' questo che rende la «data prevista» delle viste una
--         LETTURA e non una profezia: stessa funzione, non due
--         implementazioni che oggi si comportano uguale.
DECLARE
    v_ba_id               anagrafiche.billing_account.id%TYPE;
    v_ba_fattura_id       anagrafiche.billing_account.id%TYPE;
    v_tipo_doc_fiscale_id config.tipi_doc_fiscale.id%TYPE;
    v_natura_doc_id       config.nature_doc_fiscale.id%TYPE;
    v_valuta_id           config.valute.id%TYPE;
    v_utility_id          config.utilities.id%TYPE;
    v_emittente_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_reseller_id         anagrafiche.soggetti_ruoli.id%TYPE;
    v_registro_id         vendite.registri_fatturazione.id%TYPE;
    v_serie               vendite.fatture.serie%TYPE;
    v_termine_id          config.termini_pagamento.id%TYPE;
    v_modalita_id         config.modalita_pagamento.id%TYPE;
BEGIN
    -- Guard: parametro obbligatorio
    IF p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_fattura_key', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_attivita_id', 'valore', p_attivita_id),
            NULL::uuid, 'p_attivita_id obbligatorio e > 0'
        );
    END IF;

    -- Dall'attivita' escono SOLO le cose che sono sue: il billing
    -- account della riga, il tipo documento, la natura, la valuta.
    -- ⛔ IL JOIN SU billing_account RESTA, ma non per leggere la
    --    utility (la da' il resolver): e' il GUARD che produce
    --    E_VALORE_MANCANTE quando il BA non esiste o non e'
    --    visibile sotto RLS. Toglierlo sposterebbe quell'errore su
    --    un codice diverso e piu' avanti.
    SELECT a.billing_account_id,
           a.tipo_doc_fiscale_id,
           a.natura_doc_id,
           a.valuta_id
      INTO v_ba_id, v_tipo_doc_fiscale_id, v_natura_doc_id, v_valuta_id
      FROM vendite.attivita_fatturabili a
      JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id
     WHERE a.id = p_attivita_id;

    IF v_ba_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_fattura_key', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id),
            NULL::uuid, concat('attivita o BA non trovati per id ', p_attivita_id)
        );
    END IF;

    -- ⭐ LA CATENA DEL SEZIONALE, IN UNA RIGA E IN UN POSTO SOLO.
    --    I due ancoraggi (BA di fatturazione dal PADRE, utility
    --    dalla RIGA) vivono dentro il resolver: qui non si
    --    ricopiano piu'. E' la stessa funzione che usano le viste
    --    della dashboard per la colonna «data prevista».
    SELECT r.ba_fatturazione_id, r.utility_id, r.emittente_soggetto_ruolo_id,
           r.registro_id, r.serie
      INTO v_ba_fattura_id, v_utility_id, v_emittente_id,
           v_registro_id, v_serie
      FROM vendite.fn_resolve_registro_documento(
               p_billing_account_id_riga => v_ba_id,
               p_tipo_doc_fiscale_id     => v_tipo_doc_fiscale_id,
               p_natura_doc_id           => v_natura_doc_id) r;

    -- ⛔ I CANCELLI DEL PERCORSO DI SCRITTURA.
    --    Il resolver NON solleva — e' cio' che lo rende usabile da
    --    una vista — ma qui si sta COSTRUENDO un documento, e un
    --    buco di configurazione deve fermare.
    --    ⭐ Si richiamano le funzioni che sollevano invece di
    --    riscrivere i messaggi: una copia diverge appena qualcuno
    --    tocca l'originale. Costa una seconda risoluzione SOLO
    --    quando si sta gia' andando in errore.
    --    ⚠️ L'ordine conta: prima l'emittente, poi il registro —
    --    lo stesso ordine della catena. Invertendoli, un BA senza
    --    emittente mappato leggerebbe «registro non risolto».
    IF v_emittente_id IS NULL THEN
        v_emittente_id := anagrafiche.fn_get_emittente_fiscale_id(v_ba_fattura_id);
    END IF;

    IF v_registro_id IS NULL THEN
        SELECT g.registro_id, g.serie
          INTO v_registro_id, v_serie
          FROM vendite.fn_get_registro_id(
                   p_tipo_doc_fiscale_id         => v_tipo_doc_fiscale_id,
                   p_natura_doc_id               => v_natura_doc_id,
                   p_utility_id                  => v_utility_id,
                   p_emittente_soggetto_ruolo_id => v_emittente_id) g;
    END IF;

    -- Reseller dal mapping BA → reseller (opzionale)
    SELECT rb.reseller_soggetto_ruolo_id
      INTO v_reseller_id
      FROM anagrafiche.resellers_billing_account rb
     WHERE rb.billing_account_id = v_ba_fattura_id
     ORDER BY rb.id
     LIMIT 1;

    -- Condizioni di pagamento: catena unica (3b.1).
    SELECT t.termine_pagamento_id, t.modalita_pagamento_id
      INTO v_termine_id, v_modalita_id
      FROM vendite.fn_resolve_termini_pagamento(p_attivita_id) t;

    RETURN jsonb_build_object(
        'billing_account_id', v_ba_fattura_id,
        'tipo_doc_fiscale_id', v_tipo_doc_fiscale_id,
        'natura_doc_id', v_natura_doc_id,
        'valuta_id', v_valuta_id,
        'emittente_soggetto_ruolo_id', v_emittente_id,
        'reseller_soggetto_ruolo_id', v_reseller_id,
        'utility_id', v_utility_id,
        'registro_id', v_registro_id,
        'serie', v_serie,
        'termine_pagamento_id', v_termine_id,
        'modalita_pagamento_id', v_modalita_id
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_build_fattura_key(p_attivita_id bigint)
IS 'Chiave logica di aggregazione del documento a partire da un''attivita'' fatturabile: due attivita'' con la stessa chiave finiscono sulla stessa fattura. Undici elementi dal 2026-08-18, e da qui in giu'' vanno usati tutti e undici — chi separa nella chiave e non separa nel lookup annulla le due meta'' e fa tornare le attivita'' nella stessa fattura. rev 2026-08-18 (brief-design-note-credito-resi N2b): il registro si risolve passando ANCHE utility ed emittente, senza i quali i sezionali intestati erano irraggiungibili. rev 2026-08-18 (N3): la chiave porta natura_doc_id e serie. ⭐ E'' qui che la separazione fisica della nota di credito finisce: lotto, testata, registro e numerazione si separano da soli, senza una riga di codice scritta per la NC. ⚠️ Da questo momento un LOTTO puo'' contenere documenti di natura diversa: chi lo legge non deve piu'' assumere «sono tutte fatture». rev 2026-08-26 (brief-db-registro-e-data-prevista-in-competenza, L3): la catena del SEZIONALE non si risolve piu'' qui — una sola chiamata a vendite.fn_resolve_registro_documento sostituisce il COALESCE sul parent_account_id, la lettura di ba.utility_id, anagrafiche.fn_get_emittente_fiscale_id e vendite.fn_get_registro_id. ⭐ E'' questo che rende la colonna «data prevista» delle viste di competenza una LETTURA e non una profezia: la lista e il documento non coincidono perche'' due implementazioni si comportano uguale, ma perche'' e'' la STESSA funzione. ⛔ Il JOIN su anagrafiche.billing_account resta, ma come GUARD e non per leggere la utility: e'' la condizione che produce E_VALORE_MANCANTE quando il billing account non esiste o non e'' visibile sotto RLS. ⛔ I due cancelli restano QUI perche'' il resolver non ferma (e non deve: e'' cio'' che lo rende usabile da una vista) — emittente NULL richiama anagrafiche.fn_get_emittente_fiscale_id, registro NULL richiama l''involucro vendite.fn_get_registro_id, cosi'' i messaggi restano identici e la seconda risoluzione si paga solo quando si sta gia'' andando in errore. ⚠️ L''ordine dei due cancelli e'' portante: prima l''emittente, poi il registro — invertendoli un BA senza emittente mappato leggerebbe «registro non risolto» invece di «emittente di default mancante».';
```

</div>

---
{% include-markdown "signature-core.md" %}
