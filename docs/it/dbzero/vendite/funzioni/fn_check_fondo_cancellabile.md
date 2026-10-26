{% include-markdown "it/dbzero/vendite/manual/fn_check_fondo_cancellabile.md" %}
# ⚙️ Funzione `fn_check_fondo_cancellabile`

```sql
CREATE FUNCTION fn_check_fondo_cancellabile(p_source_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_fondo_cancellabile(p_source_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_stato        vendite.fatture_fondi_fattura_source.stato%TYPE;
    v_figlia_id    vendite.fatture_fondi_fattura_source.fattura_figlia_id%TYPE;
    v_stato_postata_id pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_stato_chiusa_id  pagamenti.vendite_contabili_stati.id%TYPE;
    v_congela      config.stati_doc_fiscale.congela_fiscale%TYPE;
    v_allow_reset  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire PERCHE' un atto di fondo fattura non si puo'
    --   cancellare — oppure NULL, che vuol dire «si puo'».
    --   Funzione di CRITERIO: non scrive niente e non solleva
    --   errori di dominio. I due consumatori ci costruiscono
    --   sopra reazioni opposte (§9.7-b del brief).
    --
    -- ⚠️ L'ORDINE dei motivi non e' estetico: si dice per primo
    --   cio' che e' definitivo, e per ULTIMO l'unico che ha un
    --   rimedio compibile (SISTEMAZIONE_ATTIVA). Al contrario si
    --   manderebbe l'operatore a fare un gesto che poi fallisce.
    -- =========================================================

    -- ⛔ Guard di PARAMETRO, e solleva: un id assente o <= 0 non
    --    lo produce nessuna interfaccia — e' il chiamante a essere
    --    rotto. TECNICO, e non E_PARAMETRO_INVALIDO, che e' un
    --    debito e non una sede (AGENTS.md).
    IF p_source_id IS NULL OR p_source_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_check_fondo_cancellabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_source_id',
                               'valore',    p_source_id),
            NULL::uuid,
            'vendite.fn_check_fondo_cancellabile',
            'l''identificativo dell''atto di fondo, che deve essere valorizzato e maggiore di zero');
    END IF;

    -- ── 0. L'atto esiste, ed e' di chi lo sta chiedendo ─────
    -- ⚠️ Dal 2026-08-31 la tabella ha la row security (D-20):
    --   «non esiste» e «non e' tuo» danno la stessa risposta, di
    --   proposito — distinguerle direbbe a chi e' fuori perimetro
    --   che quell'atto c'e'. Stessa scelta di E_FATTURA_NON_TROVATA
    --   e di E_SISTEMAZIONE_NON_TROVATA.
    SELECT s.stato, s.fattura_figlia_id
      INTO v_stato, v_figlia_id
      FROM vendite.fatture_fondi_fattura_source s
     WHERE s.id = p_source_id;

    IF NOT FOUND THEN
        RETURN 'ATTO_NON_TROVATO';
    END IF;

    -- ── 1. L'atto e' gia' un FATTO ─────────────────────────
    -- Il trasferimento e' stato registrato in contabilita': non
    -- si disfa cancellando l'atto che lo ha prodotto.
    IF v_stato = 'ESEGUITO' THEN
        RETURN 'ATTO_ESEGUITO';
    END IF;

    -- ── 2. Una riga contabile dell'atto e' REGISTRATA ──────
    -- ⚠️ E' l'ANOMALIA: l'invariante vuole che in quel caso
    --   l'atto sia gia' ESEGUITO. Se non lo e', qualcosa e'
    --   andato storto e non si cancella denaro registrato per
    --   rimettere le cose a posto.
    -- ⛔ Lo stato si risolve PRIMA e con un guard: un LEFT JOIN
    --   su un codice interno assente direbbe «nessuna riga
    --   registrata», cioe' fail-open sul caso piu' grave.
    SELECT s.id INTO v_stato_postata_id
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.codice_interno = 'POSTATA' AND s.attivo IS TRUE
     ORDER BY s.id LIMIT 1;

    IF v_stato_postata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_check_fondo_cancellabile', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'POSTATA'), NULL::uuid,
            'lo stato POSTATA delle righe contabili');
    END IF;

    IF EXISTS (SELECT 1
                 FROM pagamenti.vendite_contabili_righe cr
                WHERE cr.fondo_source_id = p_source_id
                  AND cr.stato_id = v_stato_postata_id)
    THEN
        RETURN 'RIGA_REGISTRATA';
    END IF;

    -- ── 3. La riga sta in una distinta CHIUSA ──────────────
    -- ⚠️ Qui NON si filtra `attivo`, e non e' una svista: una
    --   riga archiviata in una distinta chiusa resta un fatto, e
    --   con la FK impedirebbe comunque la cancellazione
    --   dell'atto. Meglio un blocco che lo dice che una
    --   violazione di vincolo che lo scopre.
    SELECT s.id INTO v_stato_chiusa_id
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.codice_interno = 'CHIUSA' AND s.attivo IS TRUE
     ORDER BY s.id LIMIT 1;

    IF v_stato_chiusa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_check_fondo_cancellabile', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'CHIUSA'), NULL::uuid,
            'lo stato CHIUSA delle distinte contabili');
    END IF;

    IF EXISTS (SELECT 1
                 FROM pagamenti.vendite_contabili_righe cr
                 JOIN pagamenti.vendite_contabili c ON c.id = cr.contabile_id
                WHERE cr.fondo_source_id = p_source_id
                  AND c.stato_id = v_stato_chiusa_id)
    THEN
        RETURN 'CONTABILE_CHIUSA';
    END IF;

    -- ── 4. La figlia e' congelata (G-3) ────────────────────
    -- ⭐ Non si aggiunge una regola: si finisce di applicarne una
    --   che c'e' gia'. Il fondo era l'UNICO satellite della
    --   fattura non congelato (D-6), ed era un'osservazione senza
    --   conseguenze finche' nessuno poteva toglierlo di mezzo a
    --   mano. Adesso che qualcuno puo', vale la soglia di casa.
    -- ⭐ E la soglia e' un DATO (congela_fiscale), non la lista
    --   'DRAFT','EMESSA': dal 20260830-02 quella lista non e' piu'
    --   la sede, e riscriverla qui ne rimetterebbe in circolo una
    --   copia.
    IF v_figlia_id IS NOT NULL THEN
        -- Bypass di manutenzione, stesso contratto della guardia
        -- dei satelliti: fn_cleanup_fatture_by_ids lo imposta per
        -- il ritorno di un lotto in bozza. ⭐ E' cio' che tiene
        -- separate le due porte — il gesto di una persona questa
        -- GUC non ce l'ha e non puo' darsela.
        v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);

        IF COALESCE(lower(v_allow_reset), 'off') NOT IN ('on', 'true', '1') THEN
            -- ⚠️ LEFT JOIN, e la distinzione e' portante: la riga
            --   che NON si legge e la riga SENZA STATO sono due
            --   casi diversi, e il modello li ammette entrambi
            --   (vendite.fatture.stato_doc_fiscale_id e' NULLABILE).
            SELECT s.congela_fiscale
              INTO v_congela
              FROM vendite.fatture f
              LEFT JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
             WHERE f.id = v_figlia_id;

            -- (a) LA FIGLIA NON SI LEGGE — cancellata, oppure
            --     invisibile sotto la row security. Da qui non si
            --     puo' certificare che sia ancora lavorabile, e un
            --     satellite non si tocca su un documento che non si
            --     sa leggere. FAIL-CLOSED.
            IF NOT FOUND THEN
                RETURN 'FIGLIA_CONGELATA';
            END IF;

            -- (b) LA FIGLIA SI LEGGE MA NON HA STATO. ⭐ Qui NON
            --     si blocca, e non e' una scelta nuova: e'
            --     esattamente cio' che decide gia'
            --     trgfn_fattura_satellite_guard_congelamento sullo
            --     stesso caso («fattura senza stato: non e' questo
            --     il guard che deve occuparsene»). Due risposte
            --     diverse alla stessa domanda sono la divergenza
            --     che questo cantiere sta chiudendo.
            -- ⚠️ Trovato dal collaudo, non dal ragionamento: la
            --     prima stesura faceva COALESCE(v_congela, TRUE) e
            --     rendeva rossi sette test di
            --     db/pgtap/vendite/test-fondi-fattura.sql, la cui
            --     figlia nasce senza stato.
            IF COALESCE(v_congela, FALSE) THEN
                RETURN 'FIGLIA_CONGELATA';
            END IF;
        END IF;
    END IF;

    -- ── 5. Un atto di sistemazione lo trattiene ────────────
    -- ⭐ ULTIMO di proposito: e' l'unico motivo con un rimedio
    --   che l'operatore puo' compiere davvero (annullare la
    --   sistemazione, e il fondo cade con lei — D-25). Dirlo
    --   davanti a un blocco definitivo manderebbe a fare un gesto
    --   destinato a fallire.
    -- ⚠️ Non e' una regola nuova: e' la FK fk_sistemazioni_fondo_source
    --   (NO ACTION) detta PRIMA che scatti. Senza, il gesto
    --   riceverebbe un 23503 nudo.
    IF EXISTS (SELECT 1
                 FROM pagamenti.sistemazioni si
                WHERE si.fondo_source_id = p_source_id)
    THEN
        RETURN 'SISTEMAZIONE_ATTIVA';
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_fondo_cancellabile(p_source_id bigint)
IS 'PERCHE'' un atto di fondo fattura non si puo'' cancellare — oppure NULL, che vuol dire «si puo''». Vocabolario CHIUSO: ATTO_NON_TROVATO, ATTO_ESEGUITO, RIGA_REGISTRATA, CONTABILE_CHIUSA, FIGLIA_CONGELATA, SISTEMAZIONE_ATTIVA. ⛔ Esiste perche'' non si estrae la funzione ma il PREDICATO: i due consumatori vogliono dallo stesso criterio cose opposte — fn_reset_fondi_fattura SEGNALA E PROSEGUE (giro tecnico su N atti, un''eccezione fermerebbe il reset di un lotto), fn_cancella_fondo_fattura RIFIUTA E LO DICE (gesto di una persona su un atto, e li'' il silenzio e'' il difetto). Due copie del criterio direbbero, senza nessun errore, che un atto e'' intoccabile mentre il reset lo cancella. ⚠️ L''ORDINE dei motivi e'' portante: SISTEMAZIONE_ATTIVA si dice per ultimo perche'' e'' l''unico con un rimedio compibile, e anticiparlo manderebbe a fare un gesto destinato a fallire. ⭐ La quarta condizione (G-3) legge config.stati_doc_fiscale.congela_fiscale e NON la lista DRAFT/EMESSA: dal changeSet 20260830-02 la soglia e'' un DATO, e riscrivere la lista qui ne rimetterebbe in circolo una copia. Distingue due casi che il modello ammette entrambi: la figlia che NON SI LEGGE (cancellata, o invisibile sotto la row security) vale CONGELATA — da qui non si puo'' certificare che sia lavorabile — mentre la figlia che si legge ma non ha stato NON blocca, ed e'' la stessa decisione che trgfn_fattura_satellite_guard_congelamento prende gia'' sullo stesso caso. ⚠️ Confonderle in un COALESCE(..., TRUE) rendeva rossi sette test di test-fondi-fattura.sql, la cui figlia nasce senza stato. ⭐ Il bypass zeroerp.maintenance_reset_lotto_draft spegne la SOLA quarta condizione, stesso contratto di trgfn_fattura_satellite_guard_congelamento: e'' cosi'' che il gesto di una persona e la pulizia di un lotto restano due porte diverse. ⚠️ ATTO_NON_TROVATO e SISTEMAZIONE_ATTIVA non erano nei quattro motivi del brief: il primo nasce con la row security di D-20 (dove «non esiste» e «non e'' tuo» devono dare la stessa risposta), il secondo e'' la FK fk_sistemazioni_fondo_source detta prima che scatti, cioe'' un 23503 nudo evitato. ⚠️ SECURITY INVOKER come tutta la famiglia: le due letture su pagamenti.vendite_contabili* possono in teoria essere cieche sotto RLS, e in quel caso la rete e'' la FK — la cancellazione fallirebbe forte invece di riuscire in silenzio; un SECURITY DEFINER spegnerebbe ATTO_NON_TROVATO. D-21 di brief-db-fondo-fattura-ricalcolo-e-governo §9.5-a e §9.7-b.';
```

</div>

---
{% include-markdown "signature-core.md" %}
