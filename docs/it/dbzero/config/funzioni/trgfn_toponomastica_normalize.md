{% include-markdown "it/dbzero/config/manual/trgfn_toponomastica_normalize.md" %}
# ⚙️ Funzione `trgfn_toponomastica_normalize`

```sql
CREATE FUNCTION trgfn_toponomastica_normalize()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: default e validazione obbligatoria di stato_id su
--   config.toponomastica. ⚠️ `stato_id` e' la NAZIONE (FK
--   config.stati), non lo stato di una macchina
--   a stati: il nome della colonna e' fuorviante ed e' la
--   ragione per cui questo errore ha condiviso per mesi il
--   codice con il cambio stato di commesse e preventivi.
--   rev 2026-08-06: solleva E_NAZIONE_NON_TROVATA. Il
--   precedente E_STATO_SCONOSCIUTO diceva due cose e non
--   poteva ricevere una policy sola: dandogli il 404 che
--   merita il cambio stato, questa form si sarebbe svuotata
--   mentre l'operatore digita. Qui la verita' e' 400 — c'e'
--   un campo da correggere. Brief terzo lato §11.2.
BEGIN
  -- Default stato_id se mancante
  IF NEW.stato_id IS NULL THEN
    NEW.stato_id := script.fn_stato_proposto_id(TG_NAME);
  END IF;

  -- Se ancora NULL, errore: ne' il chiamante ne' il default
  -- per parametro hanno risolto una nazione.
  IF NEW.stato_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_NAZIONE_NON_TROVATA',
      jsonb_build_object('campo', 'stato_id', 'table','config.toponomastica'),
      NULL::uuid,
      'stato_id'
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_toponomastica_normalize()
IS 'Trigger function per default stato_id e validazione obbligatoria su config.toponomastica. ⚠️ stato_id e'' la NAZIONE (FK config.stati), non lo stato di una macchina a stati. rev 2026-08-06: solleva E_NAZIONE_NON_TROVATA (893) invece di E_STATO_SCONOSCIUTO (9), ritirato. Il vecchio codice era condiviso con vendite.fn_cambia_stato_commessa / _preventivo, dove «stato» era davvero uno stato di workflow: due verita'' diverse sotto un nome solo, e nessun http_status poteva essere giusto per entrambe — 404 avrebbe fatto svuotare la form indirizzi mentre l''operatore digita, 400 avrebbe fatto mentire il cambio stato. Qui la verita'' e'' 400: c''e'' un campo da correggere. Brief brief-db-be-terzo-lato-presidio-codici §11.2, decisione di Tid del 2026-08-06. Rev 2026-10-18 (D-1 di Tid): il default viene da script.fn_stato_proposto_id (STATO_PROPOSTO_ISO2), che valida e non ripiega; prima state_code_iso3 con fn_get_default_by_param, ritirati. Il secondo controllo (stato_id ancora NULL) resta come rete.';
```

</div>

---
{% include-markdown "signature-core.md" %}
