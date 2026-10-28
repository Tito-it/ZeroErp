{% include-markdown "it/dbzero/script/manual/fn_get_sistemazione_di_contabile.md" %}
# ⚙️ Funzione `fn_get_sistemazione_di_contabile`

```sql
CREATE FUNCTION fn_get_sistemazione_di_contabile(p_contabile_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_sistemazione_di_contabile(p_contabile_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_sistemazione_id pagamenti.sistemazioni.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire se una distinta contabile e' nata da un atto di
    --   sistemazione, e quale. Un id, e nient'altro.
    --
    -- 🔴 Perche' SECURITY DEFINER: pagamenti.sistemazioni ha la
    --   row security. Il guard che chiama e' SECURITY INVOKER, e
    --   per un utente fuori perimetro l'atto NON C'E' — quindi
    --   lascerebbe passare. ⚠️ E il caso e' raggiungibile: la
    --   contabile di una compensazione e' una distinta INTERNA
    --   (centro dedicato, nessun canale), e le distinte interne
    --   sono visibili a TUTTI gli operatori.
    --
    -- ⚠️ Non allarga niente: un id su una distinta che il
    --   chiamante ha gia' nominato. Chi chiede scopre solo che
    --   quella distinta e' impegnata — cioe' esattamente cio' che
    --   gli serve per non impegnarla due volte.
    --
    -- ⚠️ Dipende dalla RLS abilitata e NON forzata. Con un FORCE
    --   va rivista, come le sorelle.
    --
    -- ⭐ uq_sistemazioni_contabile garantisce che la riga sia una
    --   sola: niente ORDER BY da scegliere, niente scommesse.
    -- =========================================================

    IF p_contabile_id IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT s.id
      INTO v_sistemazione_id
      FROM pagamenti.sistemazioni s
     WHERE s.contabile_id = p_contabile_id;

    RETURN v_sistemazione_id;
END
$function$

COMMENT ON FUNCTION script.fn_get_sistemazione_di_contabile(p_contabile_id bigint)
IS 'Dice se una distinta contabile e'' nata da un atto di sistemazione, e quale: un id, fuori dalla row security. ⭐ Esiste perche'' girando il verso del legame (D15-e) la domanda e'' passata da «guarda una colonna della riga» a «leggi un''altra tabella» — e pagamenti.sistemazioni ha la RLS. 🔴 Il varco che chiude e'' raggiungibile: la contabile di una compensazione e'' una distinta INTERNA, e quelle sono visibili a tutti gli operatori — quindi un operatore di un''altra azienda potrebbe agganciarla a un proprio lotto di fatturazione, e un guard che leggesse l''atto sotto RLS non vedrebbe niente e tacerebbe. ⚠️ Non allarga niente: chi chiede scopre solo che quella distinta e'' impegnata. ⚠️ Dipende dalla RLS abilitata e NON forzata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
