{% include-markdown "it/dbzero/script/manual/trgfn_prevent_modification_generic.md" %}
# ⚙️ Funzione `trgfn_prevent_modification_generic`

```sql
CREATE FUNCTION trgfn_prevent_modification_generic()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_prevent_modification_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Building block «rifiuta sempre». Montato su una tabella, vieta a
--   chiunque, owner compreso, le operazioni del suo evento: la sola
--   presenza del trigger e' la regola. Non ha porte: dove una scrittura
--   legittima deve passare (una GUC di manutenzione, una riga scaduta)
--   serve un guard proprio.
--
-- Argomenti del trigger, tutti facoltativi:
--   TG_ARGV[0]     il codice d'errore. Senza argomenti:
--                  E_TABELLA_OP_NON_CONSENTITA, con tabella e operazione
--                  nella frase;
--   TG_ARGV[1..n]  le colonne della riga i cui valori entrano nella
--                  frase, nell'ordine dei segnaposto del messaggio. Una
--                  colonna `date` si scrive GG/MM/AAAA. Una colonna che
--                  la tabella non ha e' un montaggio sbagliato.
--
-- La riga e' OLD su UPDATE e DELETE, NEW su INSERT; un trigger di
-- istruzione non ha riga, e le sue colonne valgono NULL.
--
-- Errori:
--   il codice del montaggio (o E_TABELLA_OP_NON_CONSENTITA);
--   E_TRIGGER_ARGOMENTI_INVALIDI se una colonna non esiste.
DECLARE
  v_codice  config.codici_errore.codice%TYPE;
  -- tipo esplicito: la riga intera, di una tabella qualunque
  v_riga    jsonb;
  -- tipo esplicito: i valori della frase, gli argomenti VARIADIC
  v_valori  text[] := ARRAY[]::text[];
  v_colonna pg_catalog.pg_attribute.attname%TYPE;
  v_tipo    pg_catalog.pg_attribute.atttypid%TYPE;
  -- tipo esplicito: il valore di una colonna qualunque, come testo
  v_valore  text;
  v_tx_id   dbops.transaction_ids.id%TYPE;
  -- tipo esplicito: un indice di TG_ARGV, non il riflesso di una colonna
  i         integer;
BEGIN
  IF TG_NARGS = 0 THEN
    v_codice := 'E_TABELLA_OP_NON_CONSENTITA';
    v_valori := ARRAY[TG_TABLE_NAME::text, TG_OP::text];
  ELSE
    v_codice := TG_ARGV[0];
  END IF;

  IF TG_LEVEL = 'ROW' THEN
    IF TG_OP = 'INSERT' THEN
      v_riga := to_jsonb(NEW);
    ELSE
      v_riga := to_jsonb(OLD);
    END IF;
  END IF;

  FOR i IN 1 .. TG_NARGS - 1 LOOP
    v_colonna := TG_ARGV[i];

    SELECT a.atttypid
      INTO v_tipo
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = TG_RELID
       AND a.attname  = v_colonna
       AND a.attnum   > 0
       AND NOT a.attisdropped;

    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        TG_TABLE_SCHEMA::text, TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
        jsonb_build_object(
          'tabella',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
          'argomento', i,
          'colonna',   v_colonna
        ),
        NULL::uuid,
            format('la colonna %s del trigger %s non esiste', v_colonna::text, TG_NAME)
      );
    END IF;

    v_valore := v_riga ->> v_colonna::text;
    IF v_tipo = 'date'::regtype AND v_valore IS NOT NULL THEN
      v_valore := to_char(v_valore::date, 'DD/MM/YYYY');
    END IF;
    v_valori := array_append(v_valori, v_valore);
  END LOOP;

  v_tx_id := (v_riga ->> 'tx_id')::uuid;

  PERFORM script.fn_log_and_raise_error(
    TG_TABLE_SCHEMA::text, TG_NAME::text, v_codice,
    jsonb_build_object(
      'tabella',    TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
      'operazione', TG_OP,
      'id',         v_riga -> 'id'
    ),
    v_tx_id,
    VARIADIC v_valori
  );

  -- Irraggiungibile: fn_log_and_raise_error solleva sempre. Una trigger
  -- function che arrivasse oltre l'END solleverebbe 2F005 al posto
  -- dell'errore di dominio; e in un BEFORE ROW NULL annulla l'operazione.
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.trgfn_prevent_modification_generic()
IS 'Building block «rifiuta sempre»: montato su una tabella, vieta a chiunque, owner compreso, le operazioni del suo evento, senza porte. Argomenti facoltativi: TG_ARGV[0] il codice d''errore (senza argomenti E_TABELLA_OP_NON_CONSENTITA, con tabella e operazione nella frase); TG_ARGV[1..n] le colonne della riga i cui valori entrano nella frase, nell''ordine dei segnaposto, con le date in GG/MM/AAAA. Una colonna che la tabella non ha solleva E_TRIGGER_ARGOMENTI_INVALIDI. Il contesto porta tabella, operazione e id della riga; il tx_id viene dalla riga. Dove una scrittura legittima deve passare serve un guard proprio, come script.trgfn_delete_block_by_guc.';
```

</div>

---
{% include-markdown "signature-core.md" %}
