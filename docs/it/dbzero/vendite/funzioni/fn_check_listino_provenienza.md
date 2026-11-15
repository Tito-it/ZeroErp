{% include-markdown "it/dbzero/vendite/manual/fn_check_listino_provenienza.md" %}
# ⚙️ Funzione `fn_check_listino_provenienza`

```sql
CREATE FUNCTION fn_check_listino_provenienza(p_commessa_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_listino_provenienza(p_commessa_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_emittente_commessa vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   la regola sulla riga e sulla versione di listino citate
    --   per il prezzo di una riga della commessa data: ricava
    --   l'emittente della commessa e chiede al BB
    --   vendite.fn_check_listino_provenienza_emittente.
    -- =========================================================
    -- Ne' riga ne' versione: niente da giudicare, nessuna lettura.
    IF p_listino_riga_id IS NULL AND p_listino_versione_id IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT c.emittente_soggetto_ruolo_id
      INTO v_emittente_commessa
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    RETURN vendite.fn_check_listino_provenienza_emittente(
        v_emittente_commessa, p_articolo_id, p_uom_id,
        p_listino_versione_id, p_listino_riga_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_listino_provenienza(p_commessa_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
IS 'Check per la commessa: il codice del primo motivo per cui la riga e la versione di listino citate per il prezzo di una riga della commessa data non sono ammesse; NULL = ammesse. Ricava l''emittente della commessa e applica le regole di vendite.fn_check_listino_provenienza_emittente (riga coerente con articolo, unita'' di misura e versione; listino dell''emittente; versione non in bozza), con gli stessi codici. Ne'' riga ne'' versione: NULL. SECURITY DEFINER: le commesse hanno la RLS per emittente. Non solleva: lo fa vendite.trgfn_attivita_guard_listino_riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
