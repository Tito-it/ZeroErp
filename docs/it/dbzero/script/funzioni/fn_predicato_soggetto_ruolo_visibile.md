{% include-markdown "it/dbzero/script/manual/fn_predicato_soggetto_ruolo_visibile.md" %}
# ⚙️ Funzione `fn_predicato_soggetto_ruolo_visibile`

```sql
CREATE FUNCTION fn_predicato_soggetto_ruolo_visibile(p_tipo_ruolo_id integer, p_alias_soggetto_ruolo text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_predicato_soggetto_ruolo_visibile(p_tipo_ruolo_id integer, p_alias_soggetto_ruolo text DEFAULT 'sr'::text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_descrizione       config.tipi_ruoli.descrizione%TYPE;
    v_ricerca_visibile  config.tipi_ruoli.ricerca_visibile%TYPE;
    v_entita_esistenza  config.tipi_ruoli.entita_esistenza%TYPE;
BEGIN
    IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_predicato_soggetto_ruolo_visibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_ruolo_id', 'valore', p_tipo_ruolo_id),
            NULL::uuid, 'p_tipo_ruolo_id obbligatorio e > 0'
        );
    END IF;

    -- L'alias entra nell'SQL del chiamante: solo un identificatore
    -- semplice, e comunque quotato con %I sotto.
    IF p_alias_soggetto_ruolo IS NULL
       OR p_alias_soggetto_ruolo !~ '^[a-z_][a-z0-9_]*$' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_predicato_soggetto_ruolo_visibile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_alias_soggetto_ruolo', 'valore', p_alias_soggetto_ruolo),
            NULL::uuid, 'p_alias_soggetto_ruolo deve essere un identificatore SQL semplice'
        );
    END IF;

    SELECT tr.descrizione, tr.ricerca_visibile, tr.entita_esistenza
      INTO v_descrizione, v_ricerca_visibile, v_entita_esistenza
      FROM config.tipi_ruoli tr
     WHERE tr.id = p_tipo_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_predicato_soggetto_ruolo_visibile', 'E_TIPO_RUOLO_NON_TROVATO',
            jsonb_build_object('detail', 'tipo_ruolo_id non trovato in config.tipi_ruoli', 'p_tipo_ruolo_id', p_tipo_ruolo_id),
            NULL::uuid, p_tipo_ruolo_id::text
        );
    END IF;

    -- Q-2: il ruolo si cerca solo se il catalogo lo dice. Prima lo
    --   controllava solo il backend; ora e' la regola del DB, per
    --   lista e dettaglio.
    IF NOT v_ricerca_visibile THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_predicato_soggetto_ruolo_visibile', 'E_TIPO_RUOLO_NON_RICERCABILE',
            jsonb_build_object('p_tipo_ruolo_id', p_tipo_ruolo_id),
            NULL::uuid, v_descrizione
        );
    END IF;

    -- Ruolo senza entita' propria: il soggetto-ruolo si mostra se esiste.
    IF v_entita_esistenza IS NULL THEN
        RETURN 'true';
    END IF;

    -- ⚠️ Il perimetro NON e' scritto qui: lo applica la RLS della
    --   tabella dell'entita', con l'identita' di chi esegue la query.
    --   Lo stato dell'entita' non conta (Q-3).
    RETURN format(
        'EXISTS (SELECT 1 FROM %I.%I e_vis WHERE e_vis.soggetto_ruolo_id = %I.id)',
        split_part(v_entita_esistenza, '.', 1),
        split_part(v_entita_esistenza, '.', 2),
        p_alias_soggetto_ruolo);
END;
$function$

COMMENT ON FUNCTION script.fn_predicato_soggetto_ruolo_visibile(p_tipo_ruolo_id integer, p_alias_soggetto_ruolo text)
IS 'Regola unica della ricerca universale: chi si vede. Valida il tipo ruolo (NULL o <= 0: E_PARAMETRO_INVALIDO; inesistente: E_TIPO_RUOLO_NON_TROVATO; ricerca_visibile = false: E_TIPO_RUOLO_NON_RICERCABILE) e rende il PREDICATO SQL su anagrafiche.soggetti_ruoli (alias p_alias_soggetto_ruolo, default sr) che dice se un soggetto-ruolo si mostra: almeno una riga della sua config.tipi_ruoli.entita_esistenza che chi guarda vede (il perimetro lo fa la RLS di quella tabella, per CL anagrafiche.clienti), oppure ''true'' se il ruolo non ha entita_esistenza. Lo stato dell''entita'' non conta: cliente chiuso e fornitore disattivato si ritrovano (Q-3). Nemmeno soggetti.attivo: il modello non ammette un soggetto-ruolo col soggetto spento (Q-5). Predicato e non check per riga: il ruolo e'' uno per chiamata, la regola si risolve una volta e lista e dettaglio la compongono nel proprio SQL dinamico. Lettori: script.fn_search_soggetti_universale (filtro di riga) e script.fn_get_search_detail (verifica d''esistenza): non possono dissentire su chi si vede. SECURITY INVOKER: il predicato gira con l''identita'' del chiamante. Nasce il 2026-10-10 al posto di script.fn_check_soggetto_ruolo_visibile (letterale CL), brief-db-codici-non-trovato-email-e-permessi R-6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
