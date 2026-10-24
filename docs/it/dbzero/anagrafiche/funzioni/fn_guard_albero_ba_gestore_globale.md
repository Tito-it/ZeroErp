{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_albero_ba_gestore_globale.md" %}
# ⚙️ Funzione `fn_guard_albero_ba_gestore_globale`

```sql
CREATE FUNCTION fn_guard_albero_ba_gestore_globale()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_albero_ba_gestore_globale()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    r record;
BEGIN
    -- ⚠️ E' l'unica operazione del cantiere con RAGGIO N: cambiare
    --   il gestore globale sposta in blocco l'emittente di TUTTI i
    --   BA che non hanno un mapping specifico. Una riga sola puo'
    --   spaccare un numero arbitrario di alberi. (brief §11.3, Q3)
    --
    -- ⚠️ La condizione che conta e' la COPPIA MISTA (padre e figlio,
    --   almeno uno senza mapping) — non «esiste un albero».
    --   (decisione Q3)
    -- ⭐ rev 2026-10-10 (D-5): l'azienda di ogni BA si chiede per
    --   l'INSTALLAZIONE (script.fn_get_ba_emittente_sr_id_installazione),
    --   non per chi agisce: con il risolutore di sessione un utente
    --   con un'azienda vedeva il BA scollegato restare alla SUA
    --   azienda, e lo spostamento passava.
    SELECT c.figlio_id,
           c.padre_id,
           c.verso,
           script.fn_get_ba_emittente_sr_id_installazione(c.figlio_id) AS ef_figlio,
           script.fn_get_ba_emittente_sr_id_installazione(c.padre_id)  AS ef_padre
      INTO r
      FROM (
            -- lo scollegato e' il FIGLIO: si guarda verso il padre
            SELECT ba.id                AS figlio_id,
                   ba.parent_account_id AS padre_id,
                   'padre'::text        AS verso,
                   ba.id                AS scollegato_id
              FROM anagrafiche.billing_account ba
             WHERE ba.parent_account_id IS NOT NULL
               AND NOT EXISTS (
                       SELECT 1
                         FROM anagrafiche.emittenti_fiscali_billing_account e
                        WHERE e.billing_account_id = ba.id)
            UNION ALL
            -- lo scollegato e' il PADRE: si guarda verso il figlio
            SELECT f.id                 AS figlio_id,
                   f.parent_account_id  AS padre_id,
                   'figlio'::text       AS verso,
                   f.parent_account_id  AS scollegato_id
              FROM anagrafiche.billing_account f
             WHERE f.parent_account_id IS NOT NULL
               AND NOT EXISTS (
                       SELECT 1
                         FROM anagrafiche.emittenti_fiscali_billing_account e
                        WHERE e.billing_account_id = f.parent_account_id)
           ) c
     WHERE script.fn_get_ba_emittente_sr_id_installazione(c.figlio_id)
           IS DISTINCT FROM script.fn_get_ba_emittente_sr_id_installazione(c.padre_id)
     ORDER BY c.scollegato_id, c.figlio_id
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Stesso rifiuto di fn_guard_albero_ba_emittente: codice,
    -- valori della frase e chiavi di contesto.
    PERFORM script.fn_log_and_raise_error(
        'anagrafiche', 'fn_guard_albero_ba_gestore_globale',
        'E_ALBERO_EMITTENTE_MISTO',
        jsonb_build_object(
            'verso',               r.verso,
            'billing_account_id',  r.figlio_id,
            'parent_account_id',   r.padre_id,
            'campo',               'parent_account_id',
            'emittente_sr_figlio', r.ef_figlio,
            'emittente_sr_padre',  r.ef_padre
        ),
        NULL::uuid,
        r.figlio_id::text,
        r.padre_id::text,
        r.ef_figlio::text,
        r.ef_padre::text
    );
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_albero_ba_gestore_globale()
IS 'Guard fail-fast per lo spostamento del gestore globale (is_default), l''unica operazione del cantiere con raggio N: cambia in blocco l''emittente di tutti i BA senza mapping specifico. Cerca la prima coppia (figlio, padre), con almeno uno dei due senza mapping, le cui aziende PER L''INSTALLAZIONE (script.fn_get_ba_emittente_sr_id_installazione: mapping, altrimenti la predefinita) sono diverse, e solleva E_ALBERO_EMITTENTE_MISTO con gli stessi valori di fn_guard_albero_ba_emittente — se entrambi i lati sono non mappati si spostano insieme e l''albero resta omogeneo (decisione Q3: la condizione e'' la COPPIA MISTA). SECURITY DEFINER: legge billing_account, che ha la RLS. Brief P-1 §11.3. ⚠️ rev 2026-08-26: dal 20260826-48 quello stesso movimento ha un SECONDO cancello, anagrafiche.fn_guard_ba_gestore_globale_storia, che lo vieta se anche UN SOLO billing account non mappato ha gia'' fatture o commesse — cioe'', su un''installazione che ha gia'' fatturato, quasi sempre. Spostare il gestore globale li'' non e'' una configurazione da rivedere: e'' una riscrittura retroattiva della storia. ⭐ I due guard restano entrambi: questo chiede «l''albero puo'' diventare misto?», l''altro «c''e'' storia da proteggere?». Brief: brief-db-billing-account-cambio-emittente. rev 2026-10-10 (20261010-59, D-5): fino a quel giorno delegava al guard per BA, che risolve PER CHI AGISCE; spostata da un utente con un''azienda, la predefinita passava sopra un albero misto. search_path con pg_temp (D6-bis). Brief: brief-db-istanza-nasce-col-ba-residui (D-5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
