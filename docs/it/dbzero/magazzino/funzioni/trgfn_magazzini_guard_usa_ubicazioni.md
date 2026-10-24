{% include-markdown "it/dbzero/magazzino/manual/trgfn_magazzini_guard_usa_ubicazioni.md" %}
# ⚙️ Funzione `trgfn_magazzini_guard_usa_ubicazioni`

```sql
CREATE FUNCTION trgfn_magazzini_guard_usa_ubicazioni()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_magazzini_guard_usa_ubicazioni()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_codice magazzino.magazzini.codice%TYPE;
BEGIN
  -- Scopo: la grana del registro (con o senza ubicazioni) si decide alla
  --   nascita del magazzino, prima del primo movimento (D-L2-m). Con merce
  --   a registro il flag non si cambia: la strada e' un magazzino nuovo e
  --   un trasferimento.
  -- Regole:
  --   - stesso valore riscritto: non e' un cambio (RETURN NEW);
  --   - esiste un movimento del magazzino: E_MAG_MAGAZZINO_CON_GIACENZA
  --     (CONFLITTO_STATO, campo = usa_ubicazioni); contano i movimenti,
  --     non il saldo, e non gli attesi (una promessa non e' merce).
  IF NEW.usa_ubicazioni IS NOT DISTINCT FROM OLD.usa_ubicazioni THEN
    RETURN NEW;
  END IF;

  IF EXISTS (SELECT 1
               FROM magazzino.movimenti m
              WHERE m.magazzino_id = NEW.id) THEN
    v_codice := NEW.codice;
    PERFORM script.fn_log_and_raise_error(
      'magazzino',
      'magazzino.trgfn_magazzini_guard_usa_ubicazioni',
      'E_MAG_MAGAZZINO_CON_GIACENZA',
      jsonb_build_object(
        'campo',          'usa_ubicazioni',
        'magazzino_id',   NEW.id,
        'usa_ubicazioni', NEW.usa_ubicazioni,
        'detail',         'cambio di usa_ubicazioni su un magazzino con movimenti a registro'
      ),
      NEW.tx_id,
      v_codice
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION magazzino.trgfn_magazzini_guard_usa_ubicazioni()
IS 'Guard di D-L2-m: magazzini.usa_ubicazioni si cambia SOLO a registro vuoto. Se esiste un movimento del magazzino rifiuta con E_MAG_MAGAZZINO_CON_GIACENZA (CONFLITTO_STATO, campo usa_ubicazioni, il codice del magazzino nella frase): la grana del registro — ogni movimento con un''ubicazione, o nessuno — si decide prima del primo carico; con merce dentro la strada e'' un magazzino nuovo e un trasferimento. Contano i movimenti (anche a saldo zero le righe hanno la grana vecchia), non gli attesi. Riscrivere lo stesso valore non e'' un cambio. INVOKER: legge movimenti sotto la RLS del magazzino, che e'' lo stesso perimetro della riga scritta. Montata BEFORE UPDATE OF usa_ubicazioni. Brief: brief-db-magazzino-lotto-2-motore, sezione 3 (D-L2-m).';
```

</div>

---
{% include-markdown "signature-core.md" %}
