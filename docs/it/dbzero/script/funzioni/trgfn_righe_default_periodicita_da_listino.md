# ⚙️ Funzione `trgfn_righe_default_periodicita_da_listino`

```sql
CREATE FUNCTION trgfn_righe_default_periodicita_da_listino()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_default_periodicita_da_listino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la riga a canone su un articolo del listino (ADESIONE, OVERRIDE)
--   senza periodicita' la prende dalla riga di listino dell'articolo, nella
--   versione operativa del documento. Riempie solo il vuoto.
-- Generica sulle due tabelle gemelle: TG_ARGV[0] = documento (codice della
--   sorgente), TG_ARGV[1] = colonna del padre. Regola completa nell'intestazione
--   del changeSet 20261029-44.
DECLARE
    v_documento    config.sorgenti.codice_interno%TYPE := TG_ARGV[0];
    -- Nudo DICHIARATO: l'id del padre, polimorfo (contratto o offerta).
    v_documento_id bigint := (to_jsonb(NEW) ->> TG_ARGV[1])::bigint;
    v_versione_id  vendite.listini_righe.listino_versione_id%TYPE;
    v_periodicita  vendite.listini_righe.periodicita%TYPE;
BEGIN
    IF NEW.tipo_eccezione NOT IN ('ADESIONE'::vendite.tipo_eccezione_contratto,
                                  'OVERRIDE'::vendite.tipo_eccezione_contratto) THEN
        RETURN NEW;
    END IF;

    SELECT lo.listino_versione_id INTO v_versione_id
      FROM vendite.fn_documento_listino_operativo(v_documento, v_documento_id) lo;
    IF v_versione_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT lr.periodicita INTO v_periodicita
      FROM vendite.listini_righe lr
     WHERE lr.listino_versione_id = v_versione_id
       AND lr.articolo_id = NEW.articolo_id
       AND lr.attivo IS TRUE
       AND lr.periodicita IS NOT NULL
     ORDER BY lr.id
     LIMIT 1;

    IF v_periodicita IS NOT NULL THEN
        NEW.periodicita := v_periodicita;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_default_periodicita_da_listino()
IS 'Trigger generico (vendite.contratti_righe, vendite.offerte_commerciali_eccezioni), BEFORE INSERT OR UPDATE OF tipo_erogazione WHEN la riga è a canone e senza periodicità: su una riga ADESIONE o OVERRIDE la periodicità viene dalla riga di listino dell''articolo nella versione operativa del documento (vendite.fn_documento_listino_operativo), se la dice. Riempie solo il vuoto. L''AGGIUNTA (fuori listino) non eredita: la periodicità la scrive l''operatore (F-9). L''obbligo non è qui: entra col passaggio BE/FE (decisione (b) di Tid). TG_ARGV[0] = documento (CONTRATTO | OFFERTA_COMMERCIALE), TG_ARGV[1] = colonna del padre. Nasce il 2026-10-29 (20261029-44), brief-db-contratto-righe-periodiche-in-commessa G-0-bis.';
```

</div>

---
{% include-markdown "signature-core.md" %}
