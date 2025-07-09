{% include-markdown "it/dbzero/script/manual/fn_get_contatti.md" %}
# ⚙️ Funzione `fn_get_contatti`

### 🎯 Scopo Principale
* **Selezione univoca per tipo**
  Ottenere il contatto più rilevante per ciascun `tipo_contatto_id` rispetto ai parametri forniti.
* **Gerarchia di contesti**
  Filtra e ordina i contatti in base alla priorità:

  1. **soggetto + ruolo + utility**
  2. **soggetto + ruolo**
  3. **soggetto + utility**
  4. **solo soggetto** (fallback **soggetto** garantisce che, se non esistono contatti per proprietà o utility, si recuperino comunque i contatti generici del soggetto.)
* **Validazione e logging**
  Verifica che `p_soggetto_id` sia valorizzato; in caso contrario utilizza `script.fn_log_and_raise_error` per loggare e sollevare un’eccezione con codice `ERRORE_PARAMETRI`.
* **Centralizzazione della logica**
  La tabella risultante è pensata come unico punto di accesso per il reperimento contatti: consente di applicare filtri successivi (es. solo default, ordini personalizzati, ecc.) senza replicare la logica di fallback in ogni query.

---

```sql
CREATE FUNCTION fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id integer, p_utility_id integer, p_tipo_contatto_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id integer DEFAULT NULL::integer, p_utility_id integer DEFAULT NULL::integer, p_tipo_contatto_id integer DEFAULT NULL::integer)
 RETURNS TABLE(id integer, tipo_contatto_id integer, soggetto_id uuid, soggetto_ruolo_id integer, utility_id integer, nominativo character varying, email character varying, telefono character varying, cellulare character varying, pec character varying, note text, is_default boolean, default_context character varying)
 LANGUAGE sql
AS $function$
/*
  1) Validate mandatory p_soggetto_id: if NULL, raises via fn_log_and_raise_error.
  2) Build `candidates` filtered by parameters and assign a `priority`:
    - 1: soggetto+ruolo+utility
    - 2: soggetto+ruolo
    - 3: soggetto+utility
    - 4: soggetto (fallback)
  3) For each tipo_contatto_id pick the row with lowest priority.
*/
WITH validate AS (
  SELECT script.fn_log_and_raise_error(
    'database',
    'fn_get_contatti',
    'ERRORE_PARAMETRI',
    jsonb_build_object(
      'soggetto_id',      p_soggetto_id,
      'soggetto_ruolo_id',p_soggetto_ruolo_id,
      'utility_id',       p_utility_id,
      'tipo_contatto_id', p_tipo_contatto_id
    ),
    COALESCE(p_soggetto_id::text, 'NULL')
  )
  WHERE p_soggetto_id IS NULL
),
candidates AS (
  SELECT
    c.id,
    c.tipo_contatto_id,
    c.soggetto_id,
    c.soggetto_ruolo_id,
    c.utility_id,
    c.nominativo,
    c.email,
    c.telefono,
    c.cellulare,
    c.pec,
    c.note,
    c.is_default,
    c.default_context,

CASE
  WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
  AND c.utility_id        IS NOT DISTINCT FROM p_utility_id THEN 1
  WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id THEN 2
  WHEN c.utility_id        IS NOT DISTINCT FROM p_utility_id THEN 3
  ELSE 4
  END AS priority
  FROM anagrafiche.contatti AS c
  WHERE c.soggetto_id = p_soggetto_id
  AND (c.soggetto_ruolo_id IS NULL OR c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id)
  AND (c.utility_id        IS NULL OR c.utility_id        IS NOT DISTINCT FROM p_utility_id)
  AND (p_tipo_contatto_id IS NULL OR c.tipo_contatto_id = p_tipo_contatto_id)
  )

SELECT
  sub.id,
  sub.tipo_contatto_id,
  sub.soggetto_id,
  sub.soggetto_ruolo_id,
  sub.utility_id,
  sub.nominativo,
  sub.email,
  sub.telefono,
  sub.cellulare,
  sub.pec,
  sub.note,
  sub.is_default,
  sub.default_context
FROM (
  SELECT
    candidates.*,
    ROW_NUMBER() OVER (
      PARTITION BY candidates.tipo_contatto_id
      ORDER BY candidates.priority
    ) AS rn
  FROM candidates
) AS sub
WHERE sub.rn = 1;
$function$
```