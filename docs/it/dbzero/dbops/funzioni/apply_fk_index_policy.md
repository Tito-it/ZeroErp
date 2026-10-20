{% include-markdown "it/dbzero/dbops/manual/apply_fk_index_policy.md" %}
# ⚙️ Procedura `apply_fk_index_policy`

```sql
CREATE PROCEDURE apply_fk_index_policy()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE dbops.apply_fk_index_policy()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
  rec            RECORD;
  idx_name       TEXT;
  v_scoperte     TEXT[];
  v_creati       INT := 0;
  v_saltati      INT := 0;
  v_droppati     INT := 0;
  v_rifiutati    INT := 0;
BEGIN
  -- Fotografia delle FK realmente scoperte. Una sola valutazione:
  -- la vista e' costosa e le righe di policy sono centinaia.
  SELECT array_agg(schema_name || '.' || table_name || '.' || constraint_name)
    INTO v_scoperte
    FROM dbops.vw_fk_senza_indice;

  v_scoperte := COALESCE(v_scoperte, ARRAY[]::TEXT[]);

  FOR rec IN SELECT * FROM dbops.fk_index_policy LOOP
    idx_name := split_part(rec.dll_command, ' ', 6);

    IF rec.consentito THEN

      -- GUARDIA 1: si crea solo se la FK e' ancora scoperta.
      IF (rec.schema_name || '.' || rec.table_name || '.' || rec.constraint_name)
         = ANY (v_scoperte)
      THEN
        EXECUTE rec.dll_command;
        v_creati := v_creati + 1;
      ELSE
        v_saltati := v_saltati + 1;
      END IF;

    ELSE

      -- GUARDIA 2: mai togliere un vincolo o la replica identity.
      IF EXISTS (
           SELECT 1
             FROM pg_class c
             JOIN pg_namespace n ON n.oid = c.relnamespace
             JOIN pg_index ix    ON ix.indexrelid = c.oid
            WHERE c.relkind = 'i'
              AND n.nspname = rec.schema_name
              AND c.relname = idx_name
              AND (ix.indisunique
                   OR ix.indisprimary
                   OR ix.indisreplident
                   OR EXISTS (SELECT 1 FROM pg_constraint k
                               WHERE k.conindid = c.oid)))
      THEN
        v_rifiutati := v_rifiutati + 1;
        RAISE WARNING
          'apply_fk_index_policy: DROP RIFIUTATO su %.% — l''indice sostiene un vincolo (UNIQUE/PK/constraint) o e'' la REPLICA IDENTITY. Riga di policy: %.%.%',
          rec.schema_name, idx_name,
          rec.schema_name, rec.table_name, rec.constraint_name;
      ELSE
        EXECUTE format('DROP INDEX IF EXISTS %I.%I', rec.schema_name, idx_name);
        v_droppati := v_droppati + 1;
      END IF;

    END IF;
  END LOOP;

  RAISE NOTICE
    'apply_fk_index_policy: creati=%, saltati_perche_gia_coperti=%, droppati=%, drop_rifiutati=%',
    v_creati, v_saltati, v_droppati, v_rifiutati;
END;
$procedure$

COMMENT ON PROCEDURE dbops.apply_fk_index_policy()
IS 'Applica dbops.fk_index_policy: crea o rimuove gli indici sulle foreign key secondo il flag consentito. Dal 2026-07-27 con due guardie. (1) Con consentito=true crea SOLO se la FK figura ancora in dbops.vw_fk_senza_indice: una FK gia'' servita da una UNIQUE piu'' larga o da un parziale "IS NOT NULL" non riceve un indice dedicato nemmeno se il flag e'' true, cosi'' un true rimesso per errore non puo'' rigenerare le ridondanze bonificate. (2) Con consentito=false RIFIUTA il DROP, con RAISE WARNING, se il nome estratto dal comando appartiene a un UNIQUE, a una PK, a un indice a supporto di un constraint o alla REPLICA IDENTITY: un flag non deve poter togliere un vincolo di integrita''. Si sceglie il warning e non l''eccezione perche'' la procedura gira runAlways in 90_end e nel job settimanale, e un errore bloccherebbe ogni migrate. Emette a fine ciclo un RAISE NOTICE con creati / saltati / droppati / rifiutati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
