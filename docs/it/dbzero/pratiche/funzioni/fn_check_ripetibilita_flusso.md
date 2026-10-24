{% include-markdown "it/dbzero/pratiche/manual/fn_check_ripetibilita_flusso.md" %}
# ⚙️ Funzione `fn_check_ripetibilita_flusso`

```sql
CREATE FUNCTION fn_check_ripetibilita_flusso(p_pratica_id bigint, p_template_flusso_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_ripetibilita_flusso(p_pratica_id bigint, p_template_flusso_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ripetibilita   pratiche.template_flussi.ripetibilita%TYPE;
    v_ultimo_stato   config.stati_flussi_pratiche.codice_interno%TYPE;
    v_ultimo_esito   pratiche.flussi.esito%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Verifica se una NUOVA istanza del template flusso e'
  --   ammessa nella pratica, secondo la regola di
  --   ripetibilita' del template.
  --   Funzione fn_check_*: puro boolean, no raise.
  --
  -- Regole (D3, ratifica 2026-06-11):
  --   - ultima istanza = MAX(id) per (pratica, template),
  --     escluse le istanze ANNULLATO
  --   - MAI: ammessa solo se non esiste alcuna istanza
  --   - SE_NON_POSITIVO: ammessa se non esiste istanza,
  --     oppure se l'ultima e' COMPLETATO con esito diverso
  --     da POSITIVO (un'istanza ancora aperta blocca)
  --   - SEMPRE: sempre ammessa
  -- =========================================================

  -- Regola dichiarata sul template; template inesistente:
  -- nessun blocco qui (ci pensa la FK su pratiche.flussi).
  SELECT tf.ripetibilita
    INTO v_ripetibilita
    FROM pratiche.template_flussi tf
   WHERE tf.id = p_template_flusso_id;

  IF NOT FOUND OR v_ripetibilita = 'SEMPRE' THEN
    RETURN true;
  END IF;

  -- Ultima istanza non annullata (recency = MAX(id), non sequenza).
  SELECT sfp.codice_interno, f.esito
    INTO v_ultimo_stato, v_ultimo_esito
    FROM pratiche.flussi f
    JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
   WHERE f.pratica_id         = p_pratica_id
     AND f.template_flusso_id = p_template_flusso_id
     AND sfp.codice_interno  <> 'ANNULLATO'
   ORDER BY f.id DESC
   LIMIT 1;

  -- Nessuna istanza precedente: la prima e' sempre ammessa.
  IF NOT FOUND THEN
    RETURN true;
  END IF;

  -- MAI: esiste gia' un'istanza valida -> mai ripetibile.
  IF v_ripetibilita = 'MAI' THEN
    RETURN false;
  END IF;

  -- SE_NON_POSITIVO: ripetibile solo se l'ultima istanza e'
  -- chiusa (COMPLETATO) con esito non positivo. Un'istanza
  -- ancora aperta o chiusa POSITIVO blocca la ripetizione.
  RETURN v_ultimo_stato = 'COMPLETATO'
         AND v_ultimo_esito IS DISTINCT FROM 'POSITIVO';
END;
$function$

COMMENT ON FUNCTION pratiche.fn_check_ripetibilita_flusso(p_pratica_id bigint, p_template_flusso_id integer)
IS 'Pure check: true se una nuova istanza del template e'' ammessa nella pratica secondo template_flussi.ripetibilita (MAI/SE_NON_POSITIVO/SEMPRE). Ultima istanza = MAX(id), escluse ANNULLATO; SE_NON_POSITIVO blocca anche istanza ancora aperta.';
```

</div>

---
{% include-markdown "signature-core.md" %}
