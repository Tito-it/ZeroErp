{% include-markdown "it/dbzero/vendite/manual/fn_get_commessa_stato.md" %}
# ⚙️ Funzione `fn_get_commessa_stato`

```sql
CREATE FUNCTION fn_get_commessa_stato(p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_commessa_stato(p_commessa_id bigint)
 RETURNS TABLE(commessa_id bigint, stato_commessa_id bigint, stato_commessa character varying, chiude_commessa boolean, emittibile boolean, modificabile boolean, policy_fatturazione character varying, fatturazione_immediata boolean, priorita_operativa character varying, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, total_attivita bigint, total_approvate bigint, total_non_approvate bigint, total_emesse bigint, total_non_emesse bigint, total_prezzo_da_riallineare bigint, last_update timestamp with time zone, commessa_codice character varying, cliente_display text)
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Guard: parametro obbligatorio
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_commessa_stato', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id),
            NULL::uuid, 'p_commessa_id obbligatorio e > 0'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM vendite.commesse c WHERE c.id = p_commessa_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_commessa_stato', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id),
            NULL::uuid, concat('commessa_id ', p_commessa_id)
        );
    END IF;

    RETURN QUERY
    SELECT
        c.id AS commessa_id,
        c.stato_commessa_id,
        sc.codice AS stato_commessa,
        sc.chiude_commessa,
        sc.emittibile,
        sc.modificabile,
        c.policy_fatturazione,
        c.fatturazione_immediata,
        c.priorita_operativa,
        c.billing_account_id,
        c.utility_id,
        c.emittente_soggetto_ruolo_id,
        -- rev 2026-07-28 (brief-annullamento-righe-manuali-commessa §3-ter):
        -- il FUNNEL e' cieco alle righe ANNULLATA, il TOTALE no.
        -- total_attivita resta il conteggio FISICO: una riga
        -- annullata esiste, e questo e' l'unico numero da cui si
        -- vede che qualcosa e' stato annullato (totale >
        -- approvate + non approvate). Nota: stato_approvazione di
        -- una riga annullata resta 'APPROVATA' (assi distinti),
        -- quindi senza il filtro esplicito continuerebbe a
        -- pesare sul funnel.
        COALESCE(count(ca.id), 0)::BIGINT AS total_attivita,
        COALESCE(count(*) FILTER (WHERE ca.stato_approvazione = 'APPROVATA'
                                    AND ca.stato_emissione <> 'ANNULLATA'), 0)::BIGINT,
        COALESCE(count(*) FILTER (WHERE ca.stato_approvazione <> 'APPROVATA'
                                    AND ca.stato_emissione <> 'ANNULLATA'), 0)::BIGINT,
        COALESCE(count(*) FILTER (WHERE ca.stato_emissione = 'EMESSA'), 0)::BIGINT,
        COALESCE(count(*) FILTER (WHERE ca.stato_emissione NOT IN ('EMESSA', 'ANNULLATA')), 0)::BIGINT,
        COALESCE(count(*) FILTER (WHERE ca.prezzo_da_riallineare IS TRUE
                                    AND ca.stato_emissione <> 'ANNULLATA'), 0)::BIGINT,
        GREATEST(c.data_update, COALESCE(max(ca.data_update), c.data_update)),
        -- rev 2026-07-24: identificazione della testata.
        -- ATTENZIONE: 'stato_commessa' qui sopra e' sc.codice (codice
        -- dello STATO); questo e' c.codice, il codice della COMMESSA.
        -- Nomi distinti di proposito.
        c.codice AS commessa_codice,
        -- Stessa espressione di vw_dash_competenza_attivita: una sola
        -- definizione di "nome del cliente" in tutto il dominio.
        s.ragione_sociale_completa AS cliente_display
    FROM vendite.commesse c
    JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
    LEFT JOIN vendite.commesse_attivita ca ON ca.commessa_id = c.id
    -- LEFT: un BA senza soggetto risolto non deve far sparire la riga
    -- di stato (cliente_display esce NULL, la testata resta leggibile).
    LEFT JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
    LEFT JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = ba.soggetto_ruolo_id
    LEFT JOIN anagrafiche.soggetti s         ON s.id  = sr.soggetto_id
    WHERE c.id = p_commessa_id
    GROUP BY c.id, c.stato_commessa_id, sc.codice, sc.chiude_commessa,
             sc.emittibile, sc.modificabile, c.policy_fatturazione,
             c.fatturazione_immediata, c.priorita_operativa,
             c.billing_account_id, c.utility_id,
             c.emittente_soggetto_ruolo_id, c.data_update,
             c.codice, s.ragione_sociale_completa;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_commessa_stato(p_commessa_id bigint)
IS 'Stato testata commessa con flag operativi e contatori attivita in singolo round-trip. rev 2026-07-24 (brief-db-guard-uscita-commessa-e-capabilities D6): + commessa_codice (c.codice — da non confondere con stato_commessa, che e'' il codice dello STATO) e + cliente_display (anagrafiche.soggetti.ragione_sociale_completa via billing_account->soggetti_ruoli->soggetti, STESSA espressione di vw_dash_competenza_attivita). LEFT JOIN sulla catena cliente: un BA senza soggetto non fa sparire la riga. rev 2026-07-28 (brief-annullamento-righe-manuali-commessa §3-ter): i contatori del FUNNEL (total_approvate, total_non_approvate, total_non_emesse, total_prezzo_da_riallineare) escludono le righe con stato_emissione=ANNULLATA, coerentemente con tutte le altre porte del dominio; total_attivita resta invece il conteggio FISICO delle righe -- una riga annullata esiste, e il totale e'' l''unico numero da cui si vede che qualcosa e'' stato annullato. Serve il filtro esplicito perche'' stato_approvazione di una riga annullata resta APPROVATA (assi distinti). total_emesse invariato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
