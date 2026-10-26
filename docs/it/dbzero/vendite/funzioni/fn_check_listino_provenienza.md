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
    v_riga_articolo      vendite.listini_righe.articolo_id%TYPE;
    v_riga_uom           vendite.listini_righe.uom_id%TYPE;
    v_riga_versione      vendite.listini_righe.listino_versione_id%TYPE;
    v_versione           vendite.listini_versioni.id%TYPE := p_listino_versione_id;
    v_stato              vendite.listini_versioni.stato%TYPE;
    v_emittente_listino  vendite.listini.emittente_soggetto_ruolo_id%TYPE;
    v_emittente_commessa vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   il codice del primo motivo per cui la provenienza del
    --   prezzo (versione e riga di listino) di una riga della
    --   commessa data non e' ammessa; NULL = ammessa.
    --   1. riga di listino incoerente con articolo, UoM, versione
    --   2. listino di un altro emittente
    --   3. versione in BOZZA
    -- =========================================================

    -- 1. La riga di listino: articolo, unita' di misura, versione.
    IF p_listino_riga_id IS NOT NULL THEN
        SELECT lr.articolo_id, lr.uom_id, lr.listino_versione_id
          INTO v_riga_articolo, v_riga_uom, v_riga_versione
          FROM vendite.listini_righe lr
         WHERE lr.id = p_listino_riga_id;

        IF NOT FOUND
           OR v_riga_articolo IS DISTINCT FROM p_articolo_id
           OR v_riga_uom      IS DISTINCT FROM p_uom_id
           OR (v_versione IS NOT NULL AND v_riga_versione <> v_versione) THEN
            RETURN 'E_ATTIVITA_LISTINO_RIGA_INCOERENTE';
        END IF;

        v_versione := v_riga_versione;
    END IF;

    -- Ne' riga ne' versione: niente da giudicare.
    IF v_versione IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT lv.stato, l.emittente_soggetto_ruolo_id
      INTO v_stato, v_emittente_listino
      FROM vendite.listini_versioni lv
      JOIN vendite.listini l ON l.id = lv.listino_id
     WHERE lv.id = v_versione;

    SELECT c.emittente_soggetto_ruolo_id
      INTO v_emittente_commessa
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    -- 2. Il listino e' dell'emittente della commessa.
    IF v_emittente_listino IS DISTINCT FROM v_emittente_commessa THEN
        RETURN 'E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO';
    END IF;

    -- 3. Mai un prezzo da una versione in bozza.
    IF v_stato = 'BOZZA' THEN
        RETURN 'E_ATTIVITA_LISTINO_VERSIONE_BOZZA';
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_listino_provenienza(p_commessa_id bigint, p_articolo_id uuid, p_uom_id bigint, p_listino_versione_id bigint, p_listino_riga_id bigint)
IS 'Check (brief-db-coerenza-listino-della-riga-di-commessa, D-1 2026-10-15 e §6 2026-10-16): il codice del primo motivo per cui la provenienza del prezzo di una riga della commessa data (versione e riga di listino) non e'' ammessa; NULL = ammessa. Motivi in ordine: 1) E_ATTIVITA_LISTINO_RIGA_INCOERENTE: la riga di listino non c''e'', o non e'' dell''articolo e dell''unita'' di misura dati, o (se la versione e'' data) non e'' di quella versione; 2) E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO: il listino della versione (data, o quella della riga) e'' di un altro emittente rispetto alla commessa; 3) E_ATTIVITA_LISTINO_VERSIONE_BOZZA: quella versione e'' in BOZZA (mai un prezzo da una bozza). Ne'' riga ne'' versione: NULL. SECURITY DEFINER: listini e commesse hanno la RLS per emittente, e letto con la RLS di chi scrive un listino di un''altra azienda tornerebbe a vuoto. Ritorna solo un codice. Non solleva: lo fa vendite.trgfn_attivita_guard_listino_riga. Sostituisce vendite.fn_listino_riga_coerente (20261015-20, ritirata).';
```

</div>

---
{% include-markdown "signature-core.md" %}
