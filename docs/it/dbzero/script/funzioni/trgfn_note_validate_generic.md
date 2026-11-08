{% include-markdown "it/dbzero/script/manual/trgfn_note_validate_generic.md" %}
# ⚙️ Funzione `trgfn_note_validate_generic`

```sql
CREATE FUNCTION trgfn_note_validate_generic()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_note_validate_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_child_table text := TG_ARGV[0];
  v_child_fk    text := TG_ARGV[1];

  -- La parola che l'operatore legge nella frase d'errore: l'etichetta della
  --   sorgente del tipo della nota (si legge solo nel ramo d'errore).
  v_etichetta   config.sorgenti.etichetta%TYPE;

  -- ⚠️ `bigint` esplicito: e' l'id della testata letto dalla tabella delle righe
  --   che arriva in TG_ARGV, diversa per ogni montaggio.
  v_found_parent_id bigint;
  v_reg regclass;
  v_area text := TG_TABLE_SCHEMA;
BEGIN

  IF NEW.anchor_tipo <> 'RIGA' THEN
    RETURN NEW;
  END IF;


  IF NEW.target_riga_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_TARGET_ID',
      jsonb_build_object('anchor_tipo', NEW.anchor_tipo,
                        'target_id', NEW.target_id,
                        'target_riga_id', NEW.target_riga_id,
                        'detail','target_riga_id mancante'),
      NULL::uuid,
      NEW.anchor_tipo, NEW.target_id::text
    );
  END IF;


  v_reg := to_regclass(v_child_table);
  IF v_reg IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_CONFIG',
      jsonb_build_object('child_table', v_child_table,
                        'child_fk', v_child_fk,
                        'detail','tabella righe non trovata'),
      NULL::uuid,
      v_child_table
    );
  END IF;


  EXECUTE format('SELECT %I FROM %s WHERE id = $1', v_child_fk, v_reg)
    INTO v_found_parent_id
    USING NEW.target_riga_id;


  IF v_found_parent_id IS NULL OR v_found_parent_id IS DISTINCT FROM NEW.target_id THEN
    -- rev 2026-10-25 (grammatica unica, lotto 3, L3-4): il dominio e' il tipo della
    --   riga, non piu' il terzo argomento del trigger (che lo ripeteva a mano).
    SELECT s.etichetta INTO v_etichetta
      FROM config.sorgenti s
     WHERE s.codice_interno = NEW.target_tipo;

    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_RIGA_MISMATCH',
      jsonb_build_object('dominio', NEW.target_tipo,
                        'target_id', NEW.target_id,
                        'target_riga_id', NEW.target_riga_id,
                        'child_table', v_child_table,
                        'child_fk', v_child_fk,
                        'fk_value', v_found_parent_id),
      NULL::uuid,
      -- rev 2026-08-04 (bonifica F3): NEW.target_riga_id e' bigint e il
      --   parametro e' VARIADIC text[]: senza ::text la chiamata non si
      --   risolve.
      NEW.target_riga_id::text,
      COALESCE(v_etichetta, NEW.target_tipo)::text,
      NEW.target_id::text
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_note_validate_generic()
IS 'Validazione delle note ancorate a una RIGA, BEFORE INSERT OR UPDATE sulle partizioni di note: la riga target_riga_id appartiene alla testata target_id. Una nota con anchor_tipo diverso da RIGA passa senza controlli. TG_ARGV[0] = la tabella delle righe, qualificata con lo schema; TG_ARGV[1] = la colonna della riga che punta alla testata. target_riga_id mancante -> E_NOTE_TARGET_ID; tabella delle righe inesistente -> E_NOTE_CONFIG (un errore del montaggio, non dei dati); riga inesistente o di un''altra testata -> E_NOTE_RIGA_MISMATCH, con NEW.target_tipo come dominio nel payload e, nella frase per l''operatore, l''etichetta della sorgente (config.sorgenti.etichetta, o il codice se il tipo non e'' una sorgente). Gli errori si sollevano nell''area dello schema della tabella su cui scatta. Montata sulle note di preventivi, offerte commerciali (le righe di un''offerta sono le sue eccezioni), contratti, ordini, DDT e fatture di vendita, e sulle note di ordini e DDT d''acquisto. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
