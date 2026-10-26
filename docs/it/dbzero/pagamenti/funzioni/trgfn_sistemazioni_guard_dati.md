{% include-markdown "it/dbzero/pagamenti/manual/trgfn_sistemazioni_guard_dati.md" %}
# ⚙️ Funzione `trgfn_sistemazioni_guard_dati`

```sql
CREATE FUNCTION trgfn_sistemazioni_guard_dati()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_sistemazioni_guard_dati()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_emittente_origine vendite.fatture.emittente_soggetto_ruolo_id%TYPE;
    v_cliente_origine   anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_emittente_dest    vendite.fatture.emittente_soggetto_ruolo_id%TYPE;
    v_cliente_dest      anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_is_compensazione  pagamenti.centri_riscossione.is_compensazione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Che l'atto sia coerente con se stesso e con i documenti
    --   che nomina. NON decide chi puo' scriverlo: quello e' il
    --   guard di scope, montato accanto.
    --
    -- 🔴 Le fatture si leggono FUORI dalla row security
    --   (script.fn_get_fattura_intestazione, SECURITY DEFINER).
    --   Leggendole da qui, che siamo SECURITY INVOKER, il guard
    --   direbbe «e' di un altro cliente» anche quando il cliente
    --   e' lo stesso, solo perche' una delle due non si vede.
    --   E' il difetto del lotto 6, prevenuto invece che trovato.
    -- =========================================================

    -- ── 1. La destinazione vuole i documenti che le servono ──
    --    Il CHECK chk_sistemazioni_documenti fa da rete, ma un
    --    23514 non dice quale delle forme e' caduta.
    IF (NEW.destinazione = 'RIMBORSO'
        AND NEW.fattura_destinazione_id IS NOT NULL)
       OR (NEW.destinazione IN ('RIPORTO', 'COMPENSAZIONE')
           AND (NEW.fattura_destinazione_id IS NULL
                OR NEW.fattura_destinazione_id = NEW.fattura_origine_id))
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_sistemazioni_guard_dati',
            'E_SISTEMAZIONE_DOCUMENTI_INCOERENTI',
            jsonb_build_object(
                'detail', 'destinazione e documenti non compatibili',
                'campo',  'fattura_destinazione_id',
                'destinazione', NEW.destinazione,
                'fattura_origine_id', NEW.fattura_origine_id,
                'fattura_destinazione_id', NEW.fattura_destinazione_id
            ),
            NULL::uuid,
            NEW.destinazione::text
        );
    END IF;

    -- ── 1-bis. Il motivo, dove serve ────────────────────────
    --    ⭐ Due casi, e il secondo non e' una scelta di stile: un
    --    RIPORTO genera un fondo con origine MANUALE, e
    --    chk_fondi_source_motivo_obbligatorio lo pretende.
    --    Chiederlo QUI, alla registrazione, evita di rifiutare
    --    alla conferma una cosa che si poteva sistemare mentre
    --    l'operatore era ancora nel flusso.
    IF (NEW.stato = 'ANNULLATA' OR NEW.destinazione = 'RIPORTO')
       AND (NEW.motivo IS NULL OR btrim(NEW.motivo) = '')
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_sistemazioni_guard_dati',
            'E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO',
            jsonb_build_object(
                'detail', 'motivo obbligatorio su annullamento e su riporto',
                'campo',  'motivo',
                'stato', NEW.stato,
                'destinazione', NEW.destinazione
            ),
            NULL::uuid,
            CASE WHEN NEW.stato = 'ANNULLATA'
                 THEN 'una sistemazione annullata deve dire perche'''
                 ELSE 'un riporto crea un fondo, e i fondi manuali portano sempre la loro ragione'
            END
        );
    END IF;

    -- ── 2. L'intestazione della fattura di partenza ─────────
    SELECT i.emittente_soggetto_ruolo_id, i.cliente_soggetto_ruolo_id
      INTO v_emittente_origine, v_cliente_origine
      FROM script.fn_get_fattura_intestazione(NEW.fattura_origine_id) i;

    -- ⚠️ La FK garantisce che la fattura esista: un NULL qui vuol
    --   dire che il legame col billing account non risolve, cioe'
    --   un dato rotto a monte. Lettore: dbops.error_log.
    IF v_emittente_origine IS NULL OR v_cliente_origine IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_sistemazioni_guard_dati',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'intestazione della fattura di partenza non risolvibile',
                'fattura_origine_id', NEW.fattura_origine_id
            ),
            NULL::uuid,
            'pagamenti.trgfn_sistemazioni_guard_dati',
            'fattura_origine_id (la fattura non risolve emittente e cliente)'
        );
    END IF;

    -- ── 3. Cliente ed emittente DICHIARATI ──────────────────
    --    ⭐ Codice TECNICO: non li sceglie una persona in un
    --    modulo, li deriva chi costruisce l'atto. Se non
    --    corrispondono e' un difetto di programmazione, e il
    --    lettore del messaggio non e' l'operatore.
    IF NEW.emittente_soggetto_ruolo_id IS DISTINCT FROM v_emittente_origine
       OR NEW.cliente_soggetto_ruolo_id IS DISTINCT FROM v_cliente_origine
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_sistemazioni_guard_dati',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'emittente o cliente dichiarati diversi da quelli della fattura di partenza',
                'fattura_origine_id', NEW.fattura_origine_id,
                'emittente_dichiarato', NEW.emittente_soggetto_ruolo_id,
                'emittente_fattura',    v_emittente_origine,
                'cliente_dichiarato',   NEW.cliente_soggetto_ruolo_id,
                'cliente_fattura',      v_cliente_origine
            ),
            NULL::uuid,
            'pagamenti.trgfn_sistemazioni_guard_dati',
            'emittente_soggetto_ruolo_id e cliente_soggetto_ruolo_id (si derivano dalla fattura di partenza)'
        );
    END IF;

    -- ── 4. Il secondo documento, quando c'e' ────────────────
    --    ⭐ E' la regola che rende sensata la compensazione
    --    (D15-b): mettere insieme due documenti DELLO STESSO
    --    CLIENTE. Spostare denaro fra clienti diversi non e' una
    --    sistemazione, e' un errore di attribuzione.
    IF NEW.fattura_destinazione_id IS NOT NULL THEN
        SELECT i.emittente_soggetto_ruolo_id, i.cliente_soggetto_ruolo_id
          INTO v_emittente_dest, v_cliente_dest
          FROM script.fn_get_fattura_intestazione(NEW.fattura_destinazione_id) i;

        IF v_cliente_dest   IS DISTINCT FROM NEW.cliente_soggetto_ruolo_id
           OR v_emittente_dest IS DISTINCT FROM NEW.emittente_soggetto_ruolo_id
        THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'pagamenti.trgfn_sistemazioni_guard_dati',
                'E_SISTEMAZIONE_DOCUMENTI_NON_ABBINABILI',
                jsonb_build_object(
                    'detail', 'il documento di destinazione ha un''altra intestazione',
                    'campo',  'fattura_destinazione_id',
                    'fattura_destinazione_id', NEW.fattura_destinazione_id,
                    'cliente_atteso',   NEW.cliente_soggetto_ruolo_id,
                    'cliente_trovato',  v_cliente_dest,
                    'emittente_atteso',  NEW.emittente_soggetto_ruolo_id,
                    'emittente_trovato', v_emittente_dest
                ),
                NULL::uuid,
                NEW.fattura_destinazione_id::text
            );
        END IF;
    END IF;

    -- ── 5. Il centro della compensazione ────────────────────
    --    ⭐ La regola viveva su vendite_contabili, appesa a
    --    compensazione_id. Girato il verso (D15-e) quella colonna
    --    sparisce, e con lei il momento in cui poteva scattare:
    --    alla nascita della contabile non esiste ancora nessun
    --    atto che la citi. Qui invece il dato c'e' — la
    --    destinazione e' dell'atto.
    IF NEW.destinazione = 'COMPENSAZIONE' AND NEW.contabile_id IS NOT NULL THEN
        SELECT c.is_compensazione
          INTO v_is_compensazione
          FROM pagamenti.vendite_contabili vc
          JOIN pagamenti.centri_riscossione c
            ON c.id = vc.centro_riscossione_id
         WHERE vc.id = NEW.contabile_id;

        IF COALESCE(v_is_compensazione, false) IS FALSE THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'pagamenti.trgfn_sistemazioni_guard_dati',
                'E_CENTRO_NON_ABILITATO_COMPENSAZIONE',
                jsonb_build_object(
                    'detail', 'la contabile della compensazione non sta sul centro dedicato',
                    'campo',  'contabile_id',
                    'sistemazione_id', NEW.id,
                    'contabile_id', NEW.contabile_id
                ),
                NULL::uuid,
                NEW.contabile_id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION pagamenti.trgfn_sistemazioni_guard_dati()
IS 'Coerenza interna dell''atto di sistemazione: la destinazione vuole i documenti che le servono (un rimborso non ha un secondo documento, un riporto e una compensazione si'', e diverso dal primo); i due documenti sono dello stesso cliente e della stessa azienda (D15-b: compensare significa mettere insieme due documenti DI UN SOLO CLIENTE); cliente ed emittente dichiarati corrispondono alla fattura di partenza. ⭐ L''ultima regola ha un codice TECNICO apposta: quei due non li sceglie una persona in un modulo, li deriva chi costruisce l''atto — il codice si sceglie da CHI PUO'' RIMEDIARE. 🔴 Le fatture si leggono FUORI dalla row security (script.fn_get_fattura_intestazione): da SECURITY INVOKER il guard direbbe «e'' di un altro cliente» anche quando il cliente e'' lo stesso, solo perche'' una delle due non si vede. ⚠️ Ospita anche la regola del centro di compensazione, che su vendite_contabili non ha piu'' un momento in cui scattare: girato il verso del legame, alla nascita della contabile nessun atto la cita ancora. ⛔ NON decide chi puo'' scrivere: quello e'' trgfn_guard_emittente_scope, montato accanto su entrambe le colonne di fattura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
