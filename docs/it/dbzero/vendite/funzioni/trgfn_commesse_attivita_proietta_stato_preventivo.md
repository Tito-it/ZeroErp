{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_attivita_proietta_stato_preventivo.md" %}
# ⚙️ Funzione `trgfn_commesse_attivita_proietta_stato_preventivo`

```sql
CREATE FUNCTION trgfn_commesse_attivita_proietta_stato_preventivo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_attivita_proietta_stato_preventivo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: una riga di commessa di un preventivo e' nata, ha
--   cambiato stato_emissione o e' sparita: il preventivo si
--   riproietta (ACCETTATO <-> EVASO) dal BB
--   vendite.fn_preventivo_proietta_stato_smistamento.
-- Montaggio: AFTER INSERT OR DELETE, e AFTER UPDATE con WHEN sul
--   cambio di stato_emissione, FOR EACH ROW. Vedi l'intestazione
--   del changeSet.
-- =========================================================
DECLARE
    v_sorgente_tipo_id vendite.commesse_attivita.sorgente_tipo_id%TYPE;
    v_sorgente_id      vendite.commesse_attivita.sorgente_id%TYPE;
    v_sorgente_uid     vendite.commesse_attivita.sorgente_uid%TYPE;
    v_preventivo_id    vendite.preventivi.id%TYPE;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_sorgente_tipo_id := OLD.sorgente_tipo_id;
        v_sorgente_id      := OLD.sorgente_id;
        v_sorgente_uid     := OLD.sorgente_uid;
    ELSE
        v_sorgente_tipo_id := NEW.sorgente_tipo_id;
        v_sorgente_id      := NEW.sorgente_id;
        v_sorgente_uid     := NEW.sorgente_uid;
    END IF;

    -- Sourceless (oneri, rettifiche) o di un'altra sorgente: niente.
    IF v_sorgente_tipo_id IS NULL
       OR NOT EXISTS (SELECT 1
                        FROM config.sorgenti s
                       WHERE s.id = v_sorgente_tipo_id
                         AND s.codice_interno = 'PREVENTIVO') THEN
        RETURN NULL;
    END IF;

    -- La chiave del modello, con la regola d'incontro (il preventivo e'
    -- a chiave uid: la riga porta sorgente_uid).
    SELECT p.id
      INTO v_preventivo_id
      FROM vendite.preventivi p
     WHERE (p.id = v_sorgente_id OR p.uid = v_sorgente_uid);

    IF v_preventivo_id IS NOT NULL THEN
        PERFORM vendite.fn_preventivo_proietta_stato_smistamento(v_preventivo_id);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_attivita_proietta_stato_preventivo()
IS 'Funzione trigger (2026-10-12, brief-db-annullo-a-valle-riapre-a-monte D-1/D-10 di Tid): una riga di vendite.commesse_attivita con sorgente PREVENTIVO che nasce, cambia stato_emissione o sparisce riproietta lo stato del suo preventivo (ACCETTATO <-> EVASO) dal BB vendite.fn_preventivo_proietta_stato_smistamento. Trigger e non chiamata da una madre perche'' l''invio in commessa nel DB non ha una madre (lo orchestra il backend riga per riga): la riga di commessa e'' il solo punto che vede ogni strada (invio singolo e batch, ritiro all''annullo di un documento, annullo della commessa, cancellazione). Prende il posto del gate EVASO del backend dopo l''invio in commessa. Il preventivo si trova dal suo uid (sorgente_uid = uid::text); le righe sourceless e delle altre sorgenti escono subito. SECURITY INVOKER: la RLS di chi scrive la riga; un preventivo invisibile non si tocca. Montaggio: trg_commesse_attivita_z90_proietta_stato_preventivo_ins_dlt e _upd (20261012-15).';
```

</div>

---
{% include-markdown "signature-core.md" %}
