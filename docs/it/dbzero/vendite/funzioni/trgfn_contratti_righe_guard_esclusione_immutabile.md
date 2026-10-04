{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_righe_guard_esclusione_immutabile.md" %}
# ⚙️ Funzione `trgfn_contratti_righe_guard_esclusione_immutabile`

```sql
CREATE FUNCTION trgfn_contratti_righe_guard_esclusione_immutabile()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_guard_esclusione_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare l'UPDATE di una riga di contratto ESCLUSIONE.
--   Un'esclusione si crea (Escludi) e si cancella (Ripristina
--   articolo, DELETE): non si modifica.
-- Uso:   BEFORE UPDATE FOR EACH ROW
--        WHEN (OLD.tipo_eccezione = 'ESCLUSIONE'), fascia _a05_.
-- Ammesse: le sole colonne tecniche, che i trigger della stessa
--   riga riscrivono. Tutto il resto, `attivo` e le FK comprese, e'
--   contenuto: un elenco delle AMMESSE, cosi' una colonna nuova
--   nasce bloccata.
DECLARE
    c_tecniche CONSTANT text[] := ARRAY['data_update', 'user_update', 'tx_id'];
    v_cambiate text[];
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
            'riga_id',      OLD.id,
            'contratto_id', OLD.contratto_id,
            'articolo_id',  OLD.articolo_id,
            'colonne',      to_jsonb(v_cambiate)),
        NEW.tx_id,
        VARIADIC ARRAY[]::text[]);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_guard_esclusione_immutabile()
IS 'Guard: una riga ESCLUSIONE di vendite.contratti_righe non si modifica (E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE, CONFLITTO_STATO). Un''esclusione dice solo «questo articolo del listino non e'' disponibile per il contratto»: si crea (Escludi) e si cancella (Ripristina articolo, DELETE fisico), e basta. Confronta la riga intera tolte le sole colonne tecniche (data_update, user_update, tx_id): un elenco delle AMMESSE, cosi'' una colonna nuova nasce bloccata. Non ammesse anche attivo (la riga spenta terrebbe occupato lo slot di uq_contrighe_one_eccezione_per_articolo: niente piu'' esclusione ne'' OVERRIDE sull''articolo) e le FK (spostare un''esclusione e'' crearne un''altra; le tre FK sono ON UPDATE CASCADE, e la rinumerazione della chiave di un padre verrebbe rifiutata come dai lock di colonna su FK). Un UPDATE senza cambi passa. Nessuna fn_check_*: non c''e'' un pulsante da spegnere col motivo, l''origine ESCLUSIONE semplicemente non ha il verbo MODIFICA in vendite.fn_contratto_righe_preview. Trigger trg_contratti_righe_a05_guard_esclusione_immutabile_upd, BEFORE UPDATE, WHEN OLD.tipo_eccezione = ESCLUSIONE: parla prima dei guard _a10_ e del CHECK sul prezzo. Contesto: riga_id, contratto_id, articolo_id, colonne (quelle cambiate). Nasce il 2026-10-04, brief-db-contratto-esclusione-non-modificabile R2 (decisione di Tid).';
```

---
{% include-markdown "signature-core.md" %}
