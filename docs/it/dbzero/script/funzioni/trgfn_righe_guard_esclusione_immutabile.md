{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_esclusione_immutabile.md" %}
# ⚙️ Funzione `trgfn_righe_guard_esclusione_immutabile`

```sql
CREATE FUNCTION trgfn_righe_guard_esclusione_immutabile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_esclusione_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare l'UPDATE di una riga ESCLUSIONE di contratto o
--   di offerta. Un'esclusione si crea (Escludi) e si cancella
--   (Ripristina articolo, DELETE): non si modifica.
-- Uso:   BEFORE UPDATE FOR EACH ROW
--        WHEN (OLD.tipo_eccezione = 'ESCLUSIONE'), fascia _a05_,
--        su vendite.contratti_righe e
--        vendite.offerte_commerciali_eccezioni.
-- TG_ARGV[0]: colonna del documento padre ('contratto_id',
--   'offerta_id'), solo per il contesto dell'errore.
-- Ammesse: le sole colonne tecniche, che i trigger della stessa
--   riga riscrivono. Tutto il resto, `attivo` e le FK comprese, e'
--   contenuto: un elenco delle AMMESSE, cosi' una colonna nuova
--   nasce bloccata.
DECLARE
    c_tecniche CONSTANT text[] := ARRAY['data_update', 'user_update', 'tx_id'];
    v_col_padre text := TG_ARGV[0];
    v_cambiate  text[];
BEGIN
    SELECT array_agg(n.key ORDER BY n.key)
      INTO v_cambiate
      FROM jsonb_each(to_jsonb(NEW) - c_tecniche) AS n
      LEFT JOIN jsonb_each(to_jsonb(OLD) - c_tecniche) AS o
             ON o.key = n.key
     WHERE o.value IS DISTINCT FROM n.value;

    -- Un UPDATE che non cambia niente (o solo le tecniche) passa.
    IF v_cambiate IS NULL THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE',
        jsonb_build_object(
            'riga_id',     OLD.id,
            v_col_padre,   to_jsonb(OLD) -> v_col_padre,
            'articolo_id', OLD.articolo_id,
            'colonne',     to_jsonb(v_cambiate)),
        NEW.tx_id,
        VARIADIC ARRAY[]::text[]);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_esclusione_immutabile()
IS 'Guard: una riga ESCLUSIONE di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni non si modifica (E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE, CONFLITTO_STATO, nessun valore). Si crea (Escludi) e si cancella (Ripristina articolo). Ammesse le sole colonne tecniche data_update, user_update, tx_id: elenco delle AMMESSE, una colonna nuova nasce bloccata; attivo e le FK sono vietate. TG_ARGV[0] = colonna del padre (contratto_id | offerta_id), solo per il contesto (riga_id, padre, articolo_id, colonne cambiate). Trigger _a05_ BEFORE UPDATE WHEN (OLD.tipo_eccezione = ''ESCLUSIONE''): parla prima dei guard _a10_ e dei CHECK. Prende il posto di vendite.trgfn_contratti_righe_guard_esclusione_immutabile (solo contratto, ritirata nello stesso giro). Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R3); la regola e'' di brief-db-contratto-esclusione-non-modificabile (decisione di Tid).';
```

</div>

---
{% include-markdown "signature-core.md" %}
