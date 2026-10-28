{% include-markdown "it/dbzero/magazzino/manual/trgfn_trasferimenti_guard_stesso_emittente.md" %}
# ⚙️ Funzione `trgfn_trasferimenti_guard_stesso_emittente`

```sql
CREATE FUNCTION trgfn_trasferimenti_guard_stesso_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_trasferimenti_guard_stesso_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_ef_from      magazzino.magazzini.emittente_fiscale_id%TYPE;
  v_ef_to        magazzino.magazzini.emittente_fiscale_id%TYPE;
  v_codice_from  magazzino.magazzini.codice%TYPE;
  v_codice_to    magazzino.magazzini.codice%TYPE;
BEGIN
  -- Scopo: nessuna operazione di magazzino attraversa due emittenti (M-6).
  --   I due magazzini di un trasferimento devono appartenere allo stesso
  --   emittente fiscale. Lettura sotto RLS (SECURITY INVOKER): un magazzino
  --   fuori perimetro non risolve, e si rifiuta lo stesso (fail-closed).
  -- Regole:
  --   - emittenti diversi, o uno dei due non risolvibile:
  --     E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI (DATO_ERRATO, campo magazzino_id_to).
  SELECT m.emittente_fiscale_id, m.codice
    INTO v_ef_from, v_codice_from
    FROM magazzino.magazzini m
   WHERE m.id = NEW.magazzino_id_from;

  SELECT m.emittente_fiscale_id, m.codice
    INTO v_ef_to, v_codice_to
    FROM magazzino.magazzini m
   WHERE m.id = NEW.magazzino_id_to;

  IF v_ef_from IS NULL OR v_ef_to IS NULL OR v_ef_from <> v_ef_to THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'magazzino.trgfn_trasferimenti_guard_stesso_emittente',
      'E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI',
      jsonb_build_object(
        'detail',            'magazzino_id_from e magazzino_id_to non appartengono allo stesso emittente (o uno dei due non e'' visibile)',
        'campo',             'magazzino_id_to',
        'magazzino_id_from', NEW.magazzino_id_from,
        'magazzino_id_to',   NEW.magazzino_id_to,
        'emittente_from',    v_ef_from,
        'emittente_to',      v_ef_to
      ),
      NEW.tx_id,
      coalesce(v_codice_to, NEW.magazzino_id_to::text),
      coalesce(v_codice_from, NEW.magazzino_id_from::text)
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION magazzino.trgfn_trasferimenti_guard_stesso_emittente()
IS 'Guard M-6 sui trasferimenti: i due magazzini devono appartenere allo stesso emittente fiscale, altrimenti E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI (DATO_ERRATO, campo magazzino_id_to: la destinazione la sceglie una persona). Legge magazzini sotto RLS: un magazzino fuori perimetro non risolve e si rifiuta lo stesso (fail-closed). La policy RLS di trasferimenti poggia su magazzino_id_from; questo guard copre la destinazione. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
