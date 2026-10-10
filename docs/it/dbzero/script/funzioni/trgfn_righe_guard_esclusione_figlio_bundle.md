{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_esclusione_figlio_bundle.md" %}
# ⚙️ Funzione `trgfn_righe_guard_esclusione_figlio_bundle`

```sql
CREATE FUNCTION trgfn_righe_guard_esclusione_figlio_bundle()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_esclusione_figlio_bundle()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga ESCLUSIONE (contratto o offerta) su un
--   articolo che e' componente di un bundle del listino del
--   documento: il bundle si vende come unita', si esclude il padre,
--   mai il figlio.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW
--        WHEN (NEW.tipo_eccezione = 'ESCLUSIONE'), fascia _a10_.
-- TG_ARGV[0]: documento ('CONTRATTO' | 'OFFERTA'), il selettore di
--   script.fn_check_esclusione_articolo_documento.
-- TG_ARGV[1]: colonna del documento padre ('contratto_id',
--   'offerta_id').
-- Il predicato vive nella check, la stessa con cui la lista delle
--   righe spegne «Escludi»: qui si solleva il suo PRIMO motivo, e
--   basta. Su un array vuoto l'helper tace (= passa).
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite',
        TG_NAME::text,
        script.fn_check_esclusione_articolo_documento(
            TG_ARGV[0],
            (to_jsonb(NEW) ->> TG_ARGV[1])::bigint,
            NEW.articolo_id),
        'articolo_id',
        NEW.tx_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_esclusione_figlio_bundle()
IS 'Guard: una riga ESCLUSIONE di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni non puo'' escludere un componente di un bundle della versione operativa del listino: si esclude il bundle padre (E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA, campo articolo_id). Solleva il primo motivo di script.fn_check_esclusione_articolo_documento, lo stesso predicato con cui la lista delle righe spegne «Escludi». TG_ARGV[0] = documento (CONTRATTO | OFFERTA), TG_ARGV[1] = colonna del padre (contratto_id | offerta_id). Trigger _a10_ BEFORE INSERT OR UPDATE WHEN (NEW.tipo_eccezione = ''ESCLUSIONE''). Prende il posto di vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle (solo contratto, ritirata nello stesso giro): fn_push_offerta_a_contratto copia le righe 1:1 e la regola deve valere ai due capi. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R5c).';
```

---
{% include-markdown "signature-core.md" %}
