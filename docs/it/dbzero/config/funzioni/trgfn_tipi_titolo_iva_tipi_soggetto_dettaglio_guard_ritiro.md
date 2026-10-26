# ⚙️ Funzione `trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro`

```sql
CREATE FUNCTION trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: una riga che smette di ammettere un tipo di titolo per una
--   natura e' rifiutata finche' esistono titoli VIGENTI che la usano.
--   Smette di ammettere: era attiva e ora e' spenta, cancellata o
--   spostata su un'altra coppia. Dopo il cambio la coppia vecchia
--   non deve essere ammessa da nessun'altra riga (la PK ne lascia una
--   sola, ma la domanda si fa alla sede unica, fn_titolo_iva_ammesso).
-- Aggancio: AFTER UPDATE OR DELETE — la matrice e' gia' aggiornata.
-- ⛔ I titoli si leggono da anagrafiche.fn_titolo_iva_vigente_su_natura_esiste,
--   SECURITY DEFINER (RLS per emittente su soggetti_titoli_iva).
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (D-6).
-- =========================================================
DECLARE
    v_titolo config.tipi_titolo_iva.descrizione%TYPE;
    v_natura config.tipi_soggetto_dettaglio.descrizione%TYPE;
BEGIN
    -- Una riga gia' spenta non ammetteva niente.
    IF NOT OLD.attivo THEN
        RETURN NULL;
    END IF;

    -- Riscrittura della stessa coppia ancora attiva (il mirror del CSV).
    IF TG_OP = 'UPDATE'
       AND NEW.attivo
       AND NEW.tipo_titolo_iva_id         = OLD.tipo_titolo_iva_id
       AND NEW.tipo_soggetto_dettaglio_id = OLD.tipo_soggetto_dettaglio_id THEN
        RETURN NULL;
    END IF;

    IF anagrafiche.fn_titolo_iva_ammesso(OLD.tipo_titolo_iva_id,
                                        OLD.tipo_soggetto_dettaglio_id) THEN
        RETURN NULL;
    END IF;

    IF NOT anagrafiche.fn_titolo_iva_vigente_su_natura_esiste(
               OLD.tipo_titolo_iva_id, OLD.tipo_soggetto_dettaglio_id) THEN
        RETURN NULL;
    END IF;

    SELECT tt.descrizione INTO v_titolo
      FROM config.tipi_titolo_iva tt WHERE tt.id = OLD.tipo_titolo_iva_id;
    SELECT COALESCE(tsd.descrizione, tsd.codice_interno) INTO v_natura
      FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = OLD.tipo_soggetto_dettaglio_id;

    PERFORM script.fn_log_and_raise_error(
        'database', 'config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro',
        'E_TITOLO_IVA_AMMISSIONE_IN_USO',
        jsonb_build_object('tipo_titolo_iva_id',         OLD.tipo_titolo_iva_id,
                           'tipo_soggetto_dettaglio_id', OLD.tipo_soggetto_dettaglio_id,
                           'operazione',                 TG_OP),
        CASE WHEN TG_OP = 'UPDATE' THEN NEW.tx_id ELSE OLD.tx_id END,
        COALESCE(v_titolo, OLD.tipo_titolo_iva_id::text),
        COALESCE(v_natura, OLD.tipo_soggetto_dettaglio_id::text));

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro()
IS 'Guard AFTER UPDATE OR DELETE su config.tipi_titolo_iva_tipi_soggetto_dettaglio: una riga che smette di ammettere un tipo di titolo IVA per una natura (attivo true -> false, DELETE, coppia cambiata) e'' rifiutata con E_TITOLO_IVA_AMMISSIONE_IN_USO finche'' esistono titoli VIGENTI di quel tipo su soggetti di quella natura (anagrafiche.fn_titolo_iva_vigente_su_natura_esiste, SECURITY DEFINER). AFTER perche'' la domanda «la coppia e'' ancora ammessa?» (anagrafiche.fn_titolo_iva_ammesso) va fatta alla matrice gia'' aggiornata. La riscrittura della stessa riga attiva (il mirror del CSV) tace. Ritiro: attivo = f nel CSV, dopo aver chiuso i titoli (D-6). Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
