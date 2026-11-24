{% include-markdown "it/dbzero/documenti/manual/fn_pubblica_template_documento_versione.md" %}
# ⚙️ Funzione `fn_pubblica_template_documento_versione`

```sql
CREATE FUNCTION fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date DEFAULT NULL::date)
 RETURNS TABLE(versione_id bigint, template_documento_id bigint, versioni_obsolete integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Pubblica una versione template documento in modo atomico. E'
--   l'unica strada per cui una versione esce dalla bozza.
--
-- Regole:
--   - la versione target deve esistere, essere BOZZA ed essere
--     accesa: una bozza spenta pubblicata non stamperebbe, e
--     chiuderebbe la versione che stampa;
--   - p_valido_dal e' obbligatorio;
--   - p_versione_contesto e' la forma dei dati che il builder del
--     backend produce per quel tipo di documento: la versione si
--     pubblica solo se dichiara di leggere quella forma
--     (documenti.fn_guard_versione_contesto).
--     Una BOZZA puo' dichiarare una forma che il builder non produce
--     ancora: il controllo e' qui, non sulla bozza;
--   - l'ordine delle date (p_valido_al non precede p_valido_dal) NON si
--     giudica qui: lo giudica il guard comune script.trgfn_guard_date_validita
--     sull'UPDATE della versione;
--   - prima della pubblicazione vengono rese OBSOLETE e chiuse a
--     p_valido_dal - 1 le versioni PUBBLICATE attive dello stesso
--     template con valido_dal < p_valido_dal e intervallo sovrapposto.
--     Una OBSOLETA stampa fino al suo valido_al: che cosa stampa lo
--     decide la validita' (documenti.vw_template_versioni_stampabili);
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede la
--     stessa azione dell'endpoint, documenti_template_manage
--     (script.fn_guard_azione: E_PERMESSO_NEGATO). La sessione del migratore
--     (dbops.fn_sessione_del_migratore) pubblica gli standard senza utente
--     e non passa dal guard: e' il software;
--   - le due scritture (la chiusura, la pubblicazione) passano sotto la
--     porta zeroerp.allow_template_versione_pubblicazione_override, che il
--     verbo scrive con l'id del modello: il guard dello stato
--     (trgfn_template_documenti_versioni_protect_pubblicata) la apre solo
--     con quel valore e col proprietario, e a porta aperta ammette solo
--     queste due forme. Una GUC accesa dal chiamante si spegne all'ingresso;
--     la porta si apre dopo la scelta delle versioni e si svuota prima di
--     uscire, anche in errore;
--   - una sovrapposizione che la chiusura non risolve (lo stesso inizio di
--     una versione fuori bozza, un inizio dentro una OBSOLETA, una
--     pubblicazione concorrente) la ferma il vincolo
--     ex_template_documenti_versioni_no_overlap_pubblicata: il verbo la
--     rende col suo codice, E_DOCUMENTI_VERSIONE_OVERLAP. Un'altra
--     violazione d'esclusione si rilancia com'e'.
DECLARE
    v_template_id  documenti.template_documenti_versioni.template_documento_id%TYPE;
    v_stato        documenti.template_documenti_versioni.stato%TYPE;
    v_attivo       documenti.template_documenti_versioni.attivo%TYPE;
    v_versione     documenti.template_documenti_versioni.versione%TYPE;
    v_modello      documenti.template_documenti.descrizione%TYPE;
    -- id di documenti.template_documenti_versioni: %TYPE[] non e' sintassi valida
    v_closed_ids   bigint[] := ARRAY[]::bigint[];
    -- un conteggio: nessuna colonna di cui sia il riflesso
    v_closed_count integer  := 0;
    -- il nome del vincolo violato, dalla diagnostica dell'errore
    v_vincolo      text;
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    -- 0. Il permesso, prima di ogni altra cosa. Il migrate pubblica gli
    --    standard in una sessione senza utente: e' il software, e non passa
    --    dal guard.
    IF NOT dbops.fn_sessione_del_migratore() THEN
        v_utente := script.fn_utente_di_sessione('documenti.fn_pubblica_template_documento_versione');
        PERFORM script.fn_guard_azione(v_utente, 'documenti_template_manage');
    END IF;

    -- La porta la apre solo il verbo: quella che il chiamante avesse acceso
    -- si spegne qui.
    PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', '', true);

    IF p_versione_id IS NULL OR p_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            'versione_id deve essere un intero positivo'
        );
    END IF;

    IF p_valido_dal IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object('campo', 'valido_dal', 'versione_id', p_versione_id),
            NULL::uuid,
            'valido_dal e'' obbligatorio'
        );
    END IF;

    SELECT v.template_documento_id, v.stato, v.attivo, v.versione, t.descrizione
      INTO v_template_id, v_stato, v_attivo, v_versione, v_modello
      FROM documenti.template_documenti_versioni v
      JOIN documenti.template_documenti t ON t.id = v.template_documento_id
     WHERE v.id = p_versione_id
     FOR UPDATE OF v;

    IF v_template_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_NOT_FOUND',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            p_versione_id::text
        );
    END IF;

    IF v_stato <> 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO',
            jsonb_build_object(
                'versione_id',   p_versione_id,
                'stato_corrente', v_stato
            ),
            NULL::uuid,
            p_versione_id::text, v_stato
        );
    END IF;

    -- Una bozza spenta non stampa: pubblicarla chiuderebbe la
    -- versione che stampa e lascerebbe il modello senza stampa.
    IF v_attivo IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_SPENTA',
            jsonb_build_object(
                'versione_id',           p_versione_id,
                'template_documento_id', v_template_id,
                'versione',              v_versione
            ),
            NULL::uuid,
            v_versione::text, v_modello::text
        );
    END IF;

    -- Il patto versione/forma dei dati: prima di toccare qualunque
    -- altra versione, cosi' un rifiuto non lascia niente a meta' da
    -- annullare. La riga e' gia' sotto FOR UPDATE: la forma letta dal
    -- guard non puo' cambiare fino al commit.
    PERFORM documenti.fn_guard_versione_contesto(p_versione_id, p_versione_contesto);

    -- Lock ordinato di tutte le versioni del template: evita race fra
    -- due pubblicazioni concorrenti dello stesso template.
    PERFORM 1
      FROM documenti.template_documenti_versioni v
     WHERE v.template_documento_id = v_template_id
     ORDER BY v.id
     FOR UPDATE;

    SELECT COALESCE(array_agg(c.id ORDER BY c.valido_dal, c.id), ARRAY[]::bigint[])
      INTO v_closed_ids
      FROM (
          SELECT v.id, v.valido_dal
            FROM documenti.template_documenti_versioni v
           WHERE v.template_documento_id = v_template_id
             AND v.id <> p_versione_id
             AND v.stato = 'PUBBLICATA'
             AND v.attivo IS TRUE
             AND v.valido_dal < p_valido_dal
             -- La finestra nuova e' [p_valido_dal, oltre). Una versione
             --   che parte PRIMA di p_valido_dal si sovrappone alla nuova
             --   se e solo se e' ancora aperta a p_valido_dal: p_valido_al
             --   non conta. Un daterange(p_valido_dal, p_valido_al) qui
             --   solleverebbe 22000 con le date invertite PRIMA che
             --   l'UPDATE incontri il guard comune delle date.
             AND v.validita && daterange(p_valido_dal, NULL, '[)')
           ORDER BY v.valido_dal, v.id
           FOR UPDATE
      ) c;

    -- Calcola subito: evita GET DIAGNOSTICS post-UPDATE.
    v_closed_count := COALESCE(array_length(v_closed_ids, 1), 0);

    -- Le due scritture del verbo, sotto la sua porta: la GUC vale l'id del
    -- modello. Si apre qui, dopo la scelta delle versioni, e si svuota prima
    -- di uscire:
    -- nel blocco EXCEPTION anche in errore, perche' il terzo argomento
    -- di set_config lega il valore alla transazione, non alla chiamata.
    BEGIN
        PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', v_template_id::text, true);

        IF v_closed_count > 0 THEN
            -- Una scrittura sola, stato e data insieme: a porta aperta il
            -- guard ammette solo questa forma (PUBBLICATA -> OBSOLETA,
            -- valido_al accorciato).
            UPDATE documenti.template_documenti_versioni
               SET stato     = 'OBSOLETA',
                   valido_al = p_valido_dal - 1
             WHERE id = ANY(v_closed_ids);
        END IF;

        -- A porta aperta il guard ammette solo BOZZA -> PUBBLICATA con
        -- le sole date cambiate.
        UPDATE documenti.template_documenti_versioni
           SET stato      = 'PUBBLICATA',
               valido_dal = p_valido_dal,
               valido_al  = p_valido_al
         WHERE id    = p_versione_id
           AND stato = 'BOZZA';

        IF NOT FOUND THEN
            PERFORM script.fn_log_and_raise_error(
                'documenti',
                'fn_pubblica_template_documento_versione',
                'E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO',
                jsonb_build_object(
                    'versione_id',    p_versione_id,
                    'stato_corrente', v_stato
                ),
                NULL::uuid,
                p_versione_id::text, v_stato
            );
        END IF;

        PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', '', true);
    EXCEPTION
        WHEN exclusion_violation THEN
            PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', '', true);
            GET STACKED DIAGNOSTICS v_vincolo = CONSTRAINT_NAME;
            IF v_vincolo IS DISTINCT FROM 'ex_template_documenti_versioni_no_overlap_pubblicata' THEN
                RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'documenti',
                'fn_pubblica_template_documento_versione',
                'E_DOCUMENTI_VERSIONE_OVERLAP',
                jsonb_build_object(
                    'versione_id',           p_versione_id,
                    'template_documento_id', v_template_id,
                    'valido_dal',            p_valido_dal,
                    'valido_al',             p_valido_al
                ),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]
            );
        WHEN OTHERS THEN
            PERFORM set_config('zeroerp.allow_template_versione_pubblicazione_override', '', true);
            RAISE;
    END;

    versione_id           := p_versione_id;
    template_documento_id := v_template_id;
    versioni_obsolete     := v_closed_count;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_versione_contesto integer, p_valido_al date)
IS 'Pubblica una versione template BOZZA, ed è l''unica strada per cui una versione esce dalla bozza. SECURITY DEFINER: in prima riga chiede l''azione documenti_template_manage all''utente di sessione (script.fn_guard_azione: E_PERMESSO_NEGATO), la stessa dell''endpoint; la sessione del migratore (dbops.fn_sessione_del_migratore) pubblica gli standard senza utente e non passa dal guard. Nella stessa transazione chiude le versioni PUBBLICATE precedenti sovrapposte: OBSOLETE con fine al giorno prima della nuova, e stampabili fino a quel giorno (documenti.vw_template_versioni_stampabili). Le due scritture passano dalla porta zeroerp.allow_template_versione_pubblicazione_override, che il verbo scrive con l''id del modello e svuota prima di uscire, anche in errore; una GUC accesa dal chiamante si spegne all''ingresso. Il guard dello stato (documenti.trgfn_template_documenti_versioni_protect_pubblicata) la apre solo con quel valore e col proprietario. Rifiuti: parametri mancanti (E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO), versione inesistente (E_DOCUMENTI_VERSIONE_NOT_FOUND), non in bozza (E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO), bozza spenta (E_DOCUMENTI_VERSIONE_PUBBLICA_SPENTA: non stamperebbe, e chiuderebbe la versione che stampa). p_versione_contesto (obbligatorio) è la forma dei dati che il builder produce: la versione si pubblica solo se dichiara di leggere quella forma (documenti.fn_guard_versione_contesto: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA). L''ordine delle date lo giudica il guard comune script.trgfn_guard_date_validita sull''UPDATE della versione. Una sovrapposizione che la chiusura non risolve: E_DOCUMENTI_VERSIONE_OVERLAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
