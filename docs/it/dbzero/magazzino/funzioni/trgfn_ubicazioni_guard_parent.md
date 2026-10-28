{% include-markdown "it/dbzero/magazzino/manual/trgfn_ubicazioni_guard_parent.md" %}
# ⚙️ Funzione `trgfn_ubicazioni_guard_parent`

```sql
CREATE FUNCTION trgfn_ubicazioni_guard_parent()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_ubicazioni_guard_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_padre_magazzino_id  magazzino.ubicazioni.magazzino_id%TYPE;
  v_padre_codice        magazzino.ubicazioni.codice%TYPE;
  v_mag_codice          magazzino.magazzini.codice%TYPE;
  v_mag_padre_codice    magazzino.magazzini.codice%TYPE;
  v_ciclo               boolean := false;
BEGIN
  -- Scopo: il padre di un'ubicazione (parent_id) sta nello stesso magazzino
  --   della figlia, e la catena dei padri non torna mai su se stessa.
  --   Lettura sotto RLS (SECURITY INVOKER): un padre fuori perimetro non
  --   risolve, e si rifiuta lo stesso (fail-closed).
  -- Regole:
  --   - parent_id = id, o NEW.id fra gli antenati del padre nuovo (solo in
  --     UPDATE: in INSERT la riga non e' ancora in nessuna catena):
  --     E_MAG_UBICAZIONE_PADRE_CICLICO (DATO_ERRATO, campo parent_id);
  --   - padre di un altro magazzino, o non visibile:
  --     E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO (DATO_ERRATO, campo parent_id).
  --   Il cambio di magazzino_id NON passa di qui: e' una colonna immutabile
  --   (automation_lock_columns, E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE).
  IF NEW.parent_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- 1) Ciclo di lunghezza uno: un'ubicazione dentro se stessa.
  IF NEW.parent_id = NEW.id THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'magazzino.trgfn_ubicazioni_guard_parent',
      'E_MAG_UBICAZIONE_PADRE_CICLICO',
      jsonb_build_object(
        'detail',        'parent_id = id',
        'campo',         'parent_id',
        'ubicazione_id', NEW.id,
        'parent_id',     NEW.parent_id
      ),
      NULL::uuid,
      NEW.codice,
      NEW.codice
    );
  END IF;

  -- 2) Il padre, sotto RLS: magazzino e codici per la frase.
  SELECT u.magazzino_id, u.codice, m.codice
    INTO v_padre_magazzino_id, v_padre_codice, v_mag_padre_codice
    FROM magazzino.ubicazioni u
    LEFT JOIN magazzino.magazzini m ON m.id = u.magazzino_id
   WHERE u.id = NEW.parent_id;

  IF v_padre_magazzino_id IS NULL OR v_padre_magazzino_id <> NEW.magazzino_id THEN
    SELECT m.codice INTO v_mag_codice
      FROM magazzino.magazzini m
     WHERE m.id = NEW.magazzino_id;

    PERFORM script.fn_log_and_raise_error(
      'database',
      'magazzino.trgfn_ubicazioni_guard_parent',
      'E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO',
      jsonb_build_object(
        'detail',             'il padre non e'' del magazzino della figlia (o non e'' visibile)',
        'campo',              'parent_id',
        'ubicazione_id',      NEW.id,
        'parent_id',          NEW.parent_id,
        'magazzino_id',       NEW.magazzino_id,
        'magazzino_id_padre', v_padre_magazzino_id
      ),
      NULL::uuid,
      coalesce(v_padre_codice, NEW.parent_id::text),
      coalesce(v_mag_codice, NEW.magazzino_id::text),
      coalesce('appartiene al magazzino ' || v_mag_padre_codice,
               'non è visibile con i permessi di chi sta operando')
    );
  END IF;

  -- 3) Cicli piu' lunghi: NEW.id fra gli antenati del padre nuovo. Solo in
  --    UPDATE. L'array dei visitati ferma la risalita anche su una catena
  --    gia' ciclica nel pregresso.
  IF TG_OP = 'UPDATE' THEN
    SELECT EXISTS (
      WITH RECURSIVE antenati AS (
        SELECT u.id, u.parent_id, ARRAY[u.id] AS percorso
          FROM magazzino.ubicazioni u
         WHERE u.id = NEW.parent_id
        UNION ALL
        SELECT u.id, u.parent_id, a.percorso || u.id
          FROM antenati a
          JOIN magazzino.ubicazioni u ON u.id = a.parent_id
         WHERE NOT (u.id = ANY (a.percorso))
      )
      SELECT 1 FROM antenati a WHERE a.id = NEW.id
    ) INTO v_ciclo;

    IF v_ciclo THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'magazzino.trgfn_ubicazioni_guard_parent',
        'E_MAG_UBICAZIONE_PADRE_CICLICO',
        jsonb_build_object(
          'detail',        'NEW.id e'' fra gli antenati di parent_id',
          'campo',         'parent_id',
          'ubicazione_id', NEW.id,
          'parent_id',     NEW.parent_id
        ),
        NULL::uuid,
        NEW.codice,
        v_padre_codice
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION magazzino.trgfn_ubicazioni_guard_parent()
IS 'Guard R-1 sulle ubicazioni: il padre (parent_id) sta nello stesso magazzino della figlia — altrimenti E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO (DATO_ERRATO, campo parent_id; fail-closed: un padre fuori perimetro RLS non risolve e si rifiuta lo stesso) — e la gerarchia non ha cicli di nessuna lunghezza: E_MAG_UBICAZIONE_PADRE_CICLICO (stessa classe, stesso campo). Il cambio di magazzino_id non passa di qui: colonna immutabile via automation_lock_columns. Brief: brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici, R-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
