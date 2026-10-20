{% include-markdown "it/dbzero/vendite/manual/fn_get_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_get_arrotondamento_scope`

```sql
CREATE FUNCTION fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_modalita_pagamento_id integer DEFAULT NULL::integer)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: saldo di arrotondamento accumulato nell'ambito. Da D-N
--        l'ambito comprende anche le condizioni di pagamento.
-- Regole: assenza di riga = saldo zero, non errore.
DECLARE
    v_saldo vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
BEGIN
    -- 🔴 GUARD, 18-08-2026.
    --   `.codex/AGENTS.md`: «per parametri numerici di tipo ID applicare guard
    --   di validazione esplicita: errore se NULL o <= 0 (non normalizzare
    --   silenziosamente)». Qui mancava, e non era innocuo: la funzione promette
    --   «assenza di riga = saldo zero», quindi un parametro NULL non trova
    --   nulla e torna **0** — uno zero PLAUSIBILE, indistinguibile da quello
    --   legittimo. Su un saldo di arrotondamento uno zero sbagliato non e' un
    --   messaggio brutto: e' un importo sbagliato, e nessuno lo vede.
    --   Lo diceva da tempo il test 6 di
    --   db/pgtap/vendite/test-fatture-arrotondamenti-scope.sql, rosso in
    --   baseline con «caught: no exception».
    --
    -- ⚠️ SOLO DUE DEI CINQUE, ed e' la parte da non sbagliare.
    --   `p_billing_account_id` e `p_emittente_soggetto_ruolo_id` sono NOT NULL
    --   su `vendite.fatture`: un NULL li' e' un errore di programmazione.
    --   `p_utility_id`, `p_tipo_doc_fiscale_id` e `p_valuta_id` invece sono
    --   **nullable** sulla stessa tabella (verificato, non dedotto), quindi
    --   l'unico chiamante — `vendite.fn_ricalcola_totali_fattura` — puo'
    --   passarli NULL in modo legittimo. Un guard su tutti e cinque avrebbe
    --   trasformato un caso valido in un errore di dominio, cioe' avrebbe rotto
    --   il ricalcolo dei totali per le fatture che quei campi non li hanno.
    --   ⚠️ Su quei tre resta aperta una questione DIVERSA, non toccata qui: il
    --   confronto e' `=`, che con NULL non matcha mai, mentre il setter una
    --   riga con quella chiave a NULL potrebbe averla scritta — get e set
    --   asimmetrici sulle chiavi nullable. E' la trappola gemella del NULL
    --   nelle chiavi, e va decisa, non corretta di sfuggita.
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.fn_get_arrotondamento_scope',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id',
                               'valore', p_billing_account_id),
            NULL::uuid,
            'p_billing_account_id obbligatorio e > 0');
    END IF;

    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'vendite.fn_get_arrotondamento_scope',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id',
                               'valore', p_emittente_soggetto_ruolo_id),
            NULL::uuid,
            'p_emittente_soggetto_ruolo_id obbligatorio e > 0');
    END IF;

    SELECT s.saldo_arrotondamento
      INTO v_saldo
      FROM vendite.fatture_arrotondamenti_scope s
     WHERE s.billing_account_id = p_billing_account_id
       AND s.utility_id = p_utility_id
       AND s.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
       AND s.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
       AND s.valuta_id = p_valuta_id
       AND s.termine_pagamento_id  IS NOT DISTINCT FROM p_termine_pagamento_id
       AND s.modalita_pagamento_id IS NOT DISTINCT FROM p_modalita_pagamento_id;

    RETURN COALESCE(v_saldo, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
IS 'Saldo arrotondamento dell''ambito di compensazione. Da D-N l''ambito comprende (termine_pagamento_id, modalita_pagamento_id), confrontati con IS NOT DISTINCT FROM perche'' sono NULL nella maggioranza dei casi. Assenza di riga = 0. Post 18-08-2026: guard esplicito su p_billing_account_id e p_emittente_soggetto_ruolo_id (NULL o <= 0 -> E_PARAMETRO_INVALIDO). Senza, un parametro nullo non trovava riga e la funzione restituiva 0 — indistinguibile dallo zero legittimo del contratto ''assenza di riga = saldo zero''. Gli altri tre parametri di ambito NON sono guardati di proposito: sono nullable su vendite.fatture, quindi l''unico chiamante (fn_ricalcola_totali_fattura) puo'' passarli NULL legittimamente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
