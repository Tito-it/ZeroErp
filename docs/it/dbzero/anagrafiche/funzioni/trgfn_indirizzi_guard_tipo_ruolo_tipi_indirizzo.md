{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo.md" %}
# ⚙️ Funzione `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

```sql
CREATE FUNCTION trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_ruolo_id anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
  v_natura_id     anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
  v_ruolo_nome    config.tipi_ruoli.descrizione%TYPE;
  v_natura_nome   config.tipi_soggetto_dettaglio.descrizione%TYPE;
  v_tipo_nome     config.tipi_indirizzi.descrizione%TYPE;
BEGIN
  -- Gestione DELETE: nessun controllo
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  -- Se mancano i riferimenti chiave, non faccio nulla
  IF NEW.soggetto_ruolo_id IS NULL OR NEW.tipo_indirizzo_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Il tipo di ruolo e la natura del soggetto, dal ruolo
  SELECT sr.tipo_ruolo_id, s.tipo_soggetto_dettaglio_id
    INTO v_tipo_ruolo_id, v_natura_id
    FROM anagrafiche.soggetti_ruoli sr
    JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
   WHERE sr.id = NEW.soggetto_ruolo_id;

  -- I predicati sono quelli che legge anche la check del tipo
  -- sul ruolo (fn_check_tipo_indirizzo_ruolo_su_contesto), nello
  -- stesso ordine dei suoi motivi: prima il tipo di ruolo, poi la
  -- natura. Tipo di ruolo o natura NULL, o senza matrice:
  -- indirizzi liberi per quella regola; altrimenti la coppia deve
  -- essere in matrice, attiva e valida oggi.
  IF NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
             v_tipo_ruolo_id, NEW.tipo_indirizzo_id,
             script.fn_data_operativa()) THEN
    -- La frase vuole cio' che l'operatore riconosce: le
    -- descrizioni. Gli id restano nel contesto.
    SELECT tr.descrizione INTO v_ruolo_nome
      FROM config.tipi_ruoli tr
     WHERE tr.id = v_tipo_ruolo_id;
    SELECT ti.descrizione INTO v_tipo_nome
      FROM config.tipi_indirizzi ti
     WHERE ti.id = NEW.tipo_indirizzo_id;

    -- Codice PROPRIO di questo layer, distinto da quello del
    -- guard sugli indirizzi di SOGGETTO, che legge un'altra
    -- matrice.
    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo',
      'E_TIPO_INDIRIZZO_NON_PERMESSO',
      jsonb_build_object(
        'campo',             'tipo_indirizzo_id',
        'tipo_indirizzo_id', NEW.tipo_indirizzo_id,
        'tipo_ruolo_id',     v_tipo_ruolo_id,
        'soggetto_ruolo_id', NEW.soggetto_ruolo_id),
      NEW.tx_id,
      COALESCE(v_ruolo_nome, v_tipo_ruolo_id::text),
      COALESCE(v_tipo_nome, NEW.tipo_indirizzo_id::text));
  END IF;

  -- La natura del soggetto del ruolo: la stessa regola del guard
  -- sugli indirizzi di SOGGETTO, e lo stesso codice, perche' la
  -- matrice letta e' la sua.
  IF NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(
             v_natura_id, NEW.tipo_indirizzo_id,
             script.fn_data_operativa()) THEN
    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura_nome
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = v_natura_id;
    SELECT ti.descrizione INTO v_tipo_nome
      FROM config.tipi_indirizzi ti
     WHERE ti.id = NEW.tipo_indirizzo_id;

    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo',
      'E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO',
      jsonb_build_object(
        'campo',                      'tipo_indirizzo_id',
        'tipo_indirizzo_id',          NEW.tipo_indirizzo_id,
        'tipo_soggetto_dettaglio_id', v_natura_id,
        'soggetto_ruolo_id',          NEW.soggetto_ruolo_id),
      NEW.tx_id,
      COALESCE(v_natura_nome, v_natura_id::text),
      COALESCE(v_tipo_nome, NEW.tipo_indirizzo_id::text));
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
IS 'Guard sugli indirizzi di RUOLO (anagrafiche.indirizzi), quando si scrive un indirizzo, con due regole nell''ordine dei motivi di anagrafiche.fn_check_tipo_indirizzo_ruolo (giorno: script.fn_data_operativa()). Il tipo di indirizzo deve essere ammesso dal tipo di ruolo del soggetto_ruolo, col predicato di anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo; altrimenti E_TIPO_INDIRIZZO_NON_PERMESSO, coi valori della frase nell''ordine tipo di ruolo e tipo di indirizzo. Poi deve essere ammesso dalla natura del soggetto del ruolo, col predicato di anagrafiche.fn_tipo_indirizzo_ammesso_per_natura, la regola del guard del layer SOGGETTO; altrimenti E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO, coi valori natura e tipo di indirizzo. Valori per descrizione, gli id nel contesto, campo tipo_indirizzo_id. Fallback permissivo per ciascuna regola quando il tipo di ruolo o la natura non hanno nessuna riga di matrice, o sono NULL. Le madri singolari lo anticipano con anagrafiche.fn_check_tipo_indirizzo_ruolo, sugli stessi predicati e con gli stessi valori: questo guard resta il presidio di ogni altra strada. ⛔ Da NON confondere con anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo, il guard del layer SOGGETTO, che legge solo la matrice della natura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
