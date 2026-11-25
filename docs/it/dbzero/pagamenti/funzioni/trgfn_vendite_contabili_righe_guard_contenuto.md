{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_contenuto.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_righe_guard_contenuto`

```sql
CREATE FUNCTION trgfn_vendite_contabili_righe_guard_contenuto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_contenuto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- NUDO di proposito: l'array non riflette nessuna colonna.
    v_motivi     jsonb;
    v_testata_id pagamenti.vendite_contabili.id%TYPE;
    v_codice     pagamenti.vendite_contabili.codice%TYPE;
    v_origine    pagamenti.vendite_contabili.origine%TYPE;
    v_stato      pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_is_final   pagamenti.vendite_contabili_stati.is_final%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Custodire il CONTENUTO di una distinta contabile: chi
    --   puo' togliere, aggiungere o cambiare una riga, e quando.
    --
    --   PORTA 1 — ELIMINAZIONE (D17): attivo true -> false, e
    --     DELETE. Ammessa solo su una MANUALE in BOZZA. Il
    --     predicato NON sta qui: sta in
    --     script.fn_check_riga_contabile_eliminabile, che si
    --     chiama e di cui si solleva il PRIMO motivo.
    --   PORTA 2 — CONGELAMENTO (D18): INSERT, riattivazione,
    --     spostamento, e UPDATE di un FATTO (importo, le tre
    --     date, riferimento_ente) sotto una MANUALE che non e'
    --     piu' in BOZZA. Le DECISIONI (stato, abbinamento,
    --     forzatura, motivi, meta) restano libere: il trigger
    --     e' UPDATE OF sui soli fatti, e su quelle non scatta.
    --
    -- Uso: BEFORE INSERT OR UPDATE OF attivo, contabile_id,
    --      importo, data_pagamento, data_valuta,
    --      data_operazione, riferimento_ente OR DELETE
    --      FOR EACH ROW
    -- =========================================================

    -- ── PORTA 1a — DELETE fisico ─────────────────────────────
    IF TG_OP = 'DELETE' THEN
        -- ⭐ La primitiva del giro dei fondi
        --    (vendite.fn_applica_cancellazione_fondo_fattura) cancella
        --    FISICAMENTE le righe del suo atto sotto una GENERATA, e ha
        --    gia' letto il SUO criterio (fn_check_fondo_cancellabile).
        --    La porta ha due condizioni in AND (D-V1, giro 8): la GUC
        --    vale l'id dell'atto della riga (SULLA RIGA), e chi scrive
        --    e' il proprietario, cioe' la primitiva DEFINER. L'app che
        --    accende la GUC da se' non apre niente.
        -- ⚠️ SOLO qui: sulla disattivazione nessuna madre passa.
        IF OLD.fondo_source_id IS NOT NULL
           AND NULLIF(current_setting('zeroerp.allow_contabile_riga_delete_override', true), '')
               = OLD.fondo_source_id::text
           AND script.fn_is_proprietario_tabella(TG_RELID) THEN
            RETURN OLD;
        END IF;

        v_motivi := script.fn_check_riga_contabile_eliminabile(OLD.id);

        -- ⚠️ Nessun `campo`: CONFLITTO_STATO, non c'e' un input da
        --    accendere. `reason` viaggia nel contesto per il
        --    frontend (§12.5.1); `motivi` lo mette l'helper.
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database',
            'pagamenti.trgfn_vendite_contabili_righe_guard_contenuto',
            v_motivi,
            NULL,
            OLD.tx_id,
            jsonb_build_object(
                'contabile_riga_id', OLD.id,
                'contabile_id',      OLD.contabile_id,
                'operazione',        TG_OP,
                'reason',            v_motivi -> 0 ->> 'reason'));

        RETURN OLD;
    END IF;

    -- ── PORTA 1b — attivo true -> false ──────────────────────
    -- ⚠️ Solo la DISATTIVAZIONE e' un'eliminazione. La
    --    riattivazione e' un ingresso di contenuto, e la guarda
    --    la porta 2 (sotto una FINALE la guarda gia'
    --    guard_distinta_finale, che e' la sua sede).
    IF TG_OP = 'UPDATE'
       AND OLD.attivo IS TRUE
       AND NEW.attivo IS NOT TRUE
    THEN
        v_motivi := script.fn_check_riga_contabile_eliminabile(OLD.id);

        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database',
            'pagamenti.trgfn_vendite_contabili_righe_guard_contenuto',
            v_motivi,
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'contabile_riga_id', NEW.id,
                'contabile_id',      NEW.contabile_id,
                'operazione',        TG_OP,
                'reason',            v_motivi -> 0 ->> 'reason'));

        -- ⚠️ Nessun RETURN qui: passata la check la distinta di
        --    PARTENZA e' MANUALE in BOZZA, ma nello stesso UPDATE
        --    la riga potrebbe anche SPOSTARSI — e la testata di
        --    arrivo la guarda la porta 2.
    END IF;

    -- ── PORTA 2 — CONGELAMENTO sotto VALIDATA (D18) ──────────
    -- Un UPDATE OF scatta anche a valore invariato (il backend
    -- scrive piu' colonne in una SET): se nessuno dei fatti e'
    -- cambiato non c'e' contenuto che si muove.
    IF TG_OP = 'UPDATE'
       AND NEW.contabile_id     IS NOT DISTINCT FROM OLD.contabile_id
       AND NEW.attivo           IS NOT DISTINCT FROM OLD.attivo
       AND NEW.importo          IS NOT DISTINCT FROM OLD.importo
       AND NEW.data_pagamento   IS NOT DISTINCT FROM OLD.data_pagamento
       AND NEW.data_valuta      IS NOT DISTINCT FROM OLD.data_valuta
       AND NEW.data_operazione  IS NOT DISTINCT FROM OLD.data_operazione
       AND NEW.riferimento_ente IS NOT DISTINCT FROM OLD.riferimento_ente
    THEN
        RETURN NEW;
    END IF;

    -- Le testate da guardare: quella di ARRIVO sempre; quella di
    -- PARTENZA se la riga si sposta (uscire da una distinta
    -- validata ne cambia il contenuto quanto entrarci).
    FOR v_testata_id IN
        SELECT DISTINCT t.id
          FROM unnest(ARRAY[
                   NEW.contabile_id,
                   CASE WHEN TG_OP = 'UPDATE' THEN OLD.contabile_id END
               ]) AS t(id)
         WHERE t.id IS NOT NULL
    LOOP
        -- 🔴 Stato e origine FUORI dalla row security
        --    (script.fn_get_contabile_stato_origine, 2026-11-03): la
        --    riga si vede anche dalla FATTURA, e chi la vede cosi' non
        --    vede la sua distinta — letta sotto RLS, v_origine era NULL
        --    e la porta taceva. Il CODICE resta sotto RLS (solo per il
        --    messaggio): chi non vede la distinta ne legge l'id.
        SELECT d.origine, s.codice_interno, s.is_final
          INTO v_origine, v_stato, v_is_final
          FROM script.fn_get_contabile_stato_origine(v_testata_id) d
          JOIN pagamenti.vendite_contabili_stati s ON s.id = d.stato_id;

        SELECT c.codice
          INTO v_codice
          FROM pagamenti.vendite_contabili c
         WHERE c.id = v_testata_id;

        -- ⛔ SOLO LA MANUALE (prima di tutto): il sync dei fondi
        --    inserisce e aggiorna righe sotto GENERATE gia'
        --    VALIDATE, e una sistemazione sotto una GENERATA in
        --    BOZZA. ⚠️ Sotto una FINALE si tace: parla
        --    guard_distinta_finale. ⚠️ Whitelist (= BOZZA), non
        --    blacklist: uno stato nuovo cade nel rifiuto.
        -- ⚠️ E' il MOTIVO 3 di fn_check_riga_contabile_eliminabile,
        --    scritto qui perche' sull'INSERT non c'e' una riga da
        --    passare alla check: il pgTAP lega le due porte.
        IF v_origine = 'MANUALE'
           AND v_is_final IS NOT TRUE
           AND v_stato IS DISTINCT FROM 'BOZZA'
        THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'pagamenti.trgfn_vendite_contabili_righe_guard_contenuto',
                'E_RIGA_CONTABILE_DISTINTA_VALIDATA',
                jsonb_build_object(
                    'contabile_riga_id', NEW.id,
                    'contabile_id',      v_testata_id,
                    'contabile_codice',  v_codice,
                    'stato_distinta',    v_stato,
                    'operazione',        TG_OP,
                    'reason',            'DISTINTA_VALIDATA'),
                NEW.tx_id,
                COALESCE(v_codice, v_testata_id::text));
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_contenuto()
IS 'Il guard del CONTENUTO della distinta contabile: chi puo'' togliere, aggiungere o cambiare una riga, e quando. DUE PORTE. (1) ELIMINAZIONE: attivo true -> false, e DELETE — ammessa solo su una MANUALE in BOZZA. Il predicato non sta qui: sta in script.fn_check_riga_contabile_eliminabile, che il guard chiama sollevando il PRIMO motivo con fn_raise_primo_motivo_se_presente, cosi'' tooltip del cestino e rifiuto non possono divergere. (2) CONGELAMENTO: INSERT, riattivazione, spostamento da/verso un''altra distinta e UPDATE di un FATTO (importo, data_pagamento, data_valuta, data_operazione, riferimento_ente) sono rifiutati sotto una MANUALE che non e'' piu'' in BOZZA — E_RIGA_CONTABILE_DISTINTA_VALIDATA. Origine e stato della distinta la porta 2 li legge FUORI dalla row security, con script.fn_get_contabile_stato_origine: una riga si vede anche dalla FATTURA, e chi la vede cosi'' non vede la sua distinta. Il codice della distinta si legge sotto RLS, solo per il messaggio. ⭐ Le DECISIONI restano libere anche a distinta validata (stato_id, fattura_id, billing_account_id, scadenza_id, forzata, motivo_forzatura, motivo_sospeso, meta): l''abbinamento non tocca la quadratura e la madre del posting muove lo stato delle righe mentre la distinta e'' ancora VALIDATA — per questo il trigger e'' UPDATE OF sui soli fatti e su quelle non scatta. ⛔ La porta 2 e'' SOLO della MANUALE: fn_sync_contabili_fondo_fattura inserisce e aggiorna righe sotto GENERATE che nascono VALIDATE, fn_conferma_sistemazione sotto una GENERATA in BOZZA; GENERATA e AUTOMATICA non le congela questo guard. ⚠️ La condizione della porta 2 e'' il motivo 3 della check, scritta due volte perche'' sull''INSERT non c''e'' una riga da passare: copia dichiarata, legata dal pgTAP. ⭐ Il DELETE FISICO passa dalla stessa check, e la riga POSTATA riceve il messaggio giusto PRIMA della FK del movimento. 🔴 Una sola strada la apre: vendite.fn_applica_cancellazione_fondo_fattura — sede unica dei DELETE del giro dei fondi, primitiva riservata dietro i verbi DEFINER — cancella fisicamente le righe del suo atto sotto una GENERATA, dove la check risponde DISTINTA_NON_MANUALE, e apre la porta con la GUC transazionale zeroerp.allow_contabile_riga_delete_override uguale all''id dell''atto, richiudendola subito dopo. Il guard la onora SOLO su DELETE, solo sulle righe di quell''atto (fondo_source_id) e solo se chi scrive e'' il proprietario della tabella (script.fn_is_proprietario_tabella): l''app che accende la GUC da se'' non apre niente. ⚠️ Ordine alfabetico dei BEFORE ROW: parla PRIMA degli altri guard di riga; sotto una FINALE la porta 2 tace e lascia il messaggio a guard_distinta_finale, che e'' la sua sede. ⚠️ Residuo dichiarato: sotto una distinta ANNULLATA (righe_lavorabili = false) nessuna scrittura passa — la quinta mossa di guard_distinta_finale rifiuta ogni UPDATE con E_RIGA_CONTABILE_DISTINTA_ANNULLATA, e su attivo -> false e DELETE parla gia'' qui la check (motivo DISTINTA_ANNULLATA, prima di DISTINTA_FINALE); sotto una CHIUSA l''importo di una riga — anche POSTATA — resta modificabile da SQL, perche'' li'' le righe si lavorano ancora (tardiva, «Riprendi») e guard_distinta_finale lascia di proposito le altre scritture.';
```

</div>

---
{% include-markdown "signature-core.md" %}
