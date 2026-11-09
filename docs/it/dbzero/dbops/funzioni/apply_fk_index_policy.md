{% include-markdown "it/dbzero/dbops/manual/apply_fk_index_policy.md" %}
# ⚙️ Procedura `apply_fk_index_policy`

```sql
CREATE PROCEDURE apply_fk_index_policy()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE dbops.apply_fk_index_policy()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
  rec            dbops.fk_index_policy%ROWTYPE;
  v_scoperte     text[];
  v_creati       int := 0;
  v_saltati      int := 0;
  v_droppati     int := 0;
  v_rifiutati    int := 0;
  v_da_decidere  int := 0;
  v_fuori_ambito int := 0;
BEGIN
  -- Fotografia delle FK scoperte, una sola valutazione: la vista e' costosa.
  SELECT array_agg(v.schema_name || '.' || v.table_name || '.' || v.constraint_name)
    INTO v_scoperte
    FROM dbops.vw_fk_senza_indice v;

  v_scoperte := COALESCE(v_scoperte, ARRAY[]::text[]);

  FOR rec IN
    SELECT *
      FROM dbops.fk_index_policy
     ORDER BY schema_name, table_name, constraint_name
  LOOP
    IF NOT dbops.fn_indici_schema_nell_ambito(rec.schema_name) THEN
      v_fuori_ambito := v_fuori_ambito + 1;

    ELSIF rec.decisione = 'DA_DECIDERE' THEN
      v_da_decidere := v_da_decidere + 1;

    ELSIF rec.decisione = 'CON_INDICE' THEN
      -- GUARDIA 1: si crea solo se la FK e' ancora scoperta.
      IF (rec.schema_name || '.' || rec.table_name || '.' || rec.constraint_name) = ANY (v_scoperte) THEN
        EXECUTE rec.dll_command;
        v_creati := v_creati + 1;
      ELSE
        v_saltati := v_saltati + 1;
      END IF;

    ELSIF rec.decisione = 'SENZA_INDICE' THEN
      -- GUARDIA 2: mai togliere un vincolo o la replica identity.
      IF EXISTS (
           SELECT 1
             FROM pg_class c
             JOIN pg_namespace n ON n.oid = c.relnamespace
             JOIN pg_index ix    ON ix.indexrelid = c.oid
            WHERE c.relkind = 'i'
              AND n.nspname = rec.schema_name
              AND c.relname = rec.indice_nome
              AND (ix.indisunique
                   OR ix.indisprimary
                   OR ix.indisreplident
                   OR EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conindid = c.oid)))
      THEN
        v_rifiutati := v_rifiutati + 1;
        RAISE WARNING
          'apply_fk_index_policy: DROP RIFIUTATO su %.% — l''indice sostiene un vincolo (UNIQUE/PK/constraint) o e'' la REPLICA IDENTITY. Riga di policy: %.%.%',
          rec.schema_name, rec.indice_nome,
          rec.schema_name, rec.table_name, rec.constraint_name;
      ELSE
        EXECUTE format('DROP INDEX IF EXISTS %I.%I', rec.schema_name, rec.indice_nome);
        v_droppati := v_droppati + 1;
      END IF;
    END IF;
  END LOOP;

  RAISE NOTICE
    'apply_fk_index_policy: creati=%, saltati_perche_gia_coperti=%, droppati=%, drop_rifiutati=%, da_decidere=%, fuori_ambito=%',
    v_creati, v_saltati, v_droppati, v_rifiutati, v_da_decidere, v_fuori_ambito;
END;
$procedure$

COMMENT ON PROCEDURE dbops.apply_fk_index_policy()
IS 'Applica dbops.fk_index_policy alle righe decise, negli schemi governati (dbops.fn_indici_schema_nell_ambito). CON_INDICE: esegue dll_command solo se la FK figura ancora in dbops.vw_fk_senza_indice, cosi'' una FK gia'' servita da una UNIQUE piu'' larga o da un parziale "IS NOT NULL" non riceve un indice dedicato. SENZA_INDICE: DROP INDEX IF EXISTS di indice_nome, RIFIUTATO con RAISE WARNING se l''indice regge un UNIQUE, una PK, un constraint o la REPLICA IDENTITY: una decisione non deve poter togliere un vincolo di integrita''. DA_DECIDERE e righe fuori ambito: nessuna azione, le mostra dbops.vw_fk_da_decidere. Warning e non eccezione perche'' la procedura gira runAlways in 90_end e nel job settimanale, e un errore bloccherebbe ogni migrate. A fine ciclo un RAISE NOTICE con creati / saltati / droppati / rifiutati / da decidere / fuori ambito.';
```

</div>

---
{% include-markdown "signature-core.md" %}
