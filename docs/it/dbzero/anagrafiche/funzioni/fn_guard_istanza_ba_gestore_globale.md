{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_istanza_ba_gestore_globale.md" %}
# ⚙️ Funzione `fn_guard_istanza_ba_gestore_globale`

```sql
CREATE FUNCTION fn_guard_istanza_ba_gestore_globale()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_istanza_ba_gestore_globale()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    r record;
BEGIN
    -- ⚠️ RAGGIO N: cambiare il gestore globale sposta in blocco
    --   l'emittente di TUTTI i BA senza collegamento specifico.
    --   La condizione che conta e' la coppia MISTA (uno collegato,
    --   uno no) nella stessa istanza.
    -- ⭐ rev 2026-10-10 (D-5): l'azienda di ogni BA si chiede per
    --   l'INSTALLAZIONE (script.fn_get_ba_emittente_sr_id_installazione),
    --   non per chi agisce. Con il risolutore di sessione un utente
    --   con un'azienda vedeva il BA scollegato restare alla SUA
    --   azienda, e lo spostamento passava.
    SELECT u.id                 AS ba_id,
           u.codice             AS ba_codice,
           f.id                 AS altro_id,
           f.codice             AS altro_codice,
           u.istanza_utility_id AS istanza_id,
           iu.codice            AS istanza_codice,
           script.fn_get_ba_emittente_sr_id_installazione(u.id) AS ef_ba,
           script.fn_get_ba_emittente_sr_id_installazione(f.id) AS ef_altro
      INTO r
      FROM anagrafiche.billing_account u
      JOIN anagrafiche.billing_account f
        ON f.istanza_utility_id = u.istanza_utility_id
       AND f.id <> u.id
      JOIN anagrafiche.istanze_utilities iu
        ON iu.id = u.istanza_utility_id
     WHERE NOT EXISTS (
               SELECT 1
                 FROM anagrafiche.emittenti_fiscali_billing_account e
                WHERE e.billing_account_id = u.id)
       AND script.fn_get_ba_emittente_sr_id_installazione(u.id)
           IS DISTINCT FROM script.fn_get_ba_emittente_sr_id_installazione(f.id)
     ORDER BY u.id, f.id
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Stesso rifiuto di fn_guard_istanza_ba_emittente: codice,
    -- valori della frase e chiavi di contesto.
    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', 'fn_guard_istanza_ba_gestore_globale',
        'E_ISTANZA_EMITTENTI_DIVERSI',
        jsonb_build_object(
            'billing_account_id',       r.ba_id,
            'altro_billing_account_id', r.altro_id,
            'istanza_utility_id',       r.istanza_id,
            'emittente_sr',             r.ef_ba,
            'emittente_sr_altro',       r.ef_altro
        ),
        NULL::uuid,
        r.ba_codice::text,
        r.altro_codice::text,
        r.istanza_codice::text
    );
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_istanza_ba_gestore_globale()
IS 'Guard fail-fast per lo spostamento del gestore globale (is_default), che cambia in blocco l''emittente di tutti i BA senza collegamento specifico: verifica che nessuna istanza finisca su due emittenti. Cerca la prima coppia (BA non collegato, fratello di istanza) le cui aziende PER L''INSTALLAZIONE (script.fn_get_ba_emittente_sr_id_installazione: collegamento, altrimenti la predefinita) sono diverse, e solleva E_ISTANZA_EMITTENTI_DIVERSI con gli stessi valori di fn_guard_istanza_ba_emittente. Due collegati non si spostano, due non collegati si spostano insieme: conta la coppia MISTA. rev 2026-10-10 (20261010-58, D-5): fino a quel giorno delegava al guard per BA, che risolve PER CHI AGISCE; spostata da un utente con un''azienda, la predefinita passava sopra una coppia mista. Gemello di fn_guard_albero_ba_gestore_globale; lo stesso movimento ha anche il cancello fn_guard_ba_gestore_globale_storia, e i due si sommano. SECURITY DEFINER: legge billing_account, che ha la RLS. Brief: brief-db-istanza-nasce-col-ba (R-7), brief-db-istanza-nasce-col-ba-residui (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
