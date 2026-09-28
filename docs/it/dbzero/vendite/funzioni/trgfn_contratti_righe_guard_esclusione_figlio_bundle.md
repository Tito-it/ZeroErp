{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_righe_guard_esclusione_figlio_bundle.md" %}
# ⚙️ Funzione `trgfn_contratti_righe_guard_esclusione_figlio_bundle`

```sql
CREATE FUNCTION trgfn_contratti_righe_guard_esclusione_figlio_bundle()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga di contratto ESCLUSIONE su un articolo che
--   e' componente di un bundle del listino del contratto: il bundle si
--   vende come unita', si esclude il padre, mai il figlio.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW
--        WHEN (new.tipo_eccezione = 'ESCLUSIONE').
-- ⭐ rev 2026-09-28 (brief-db-liste-righe-documento): il predicato
--   vive in script.fn_check_esclusione_articolo_contratto, la stessa
--   funzione con cui l'anteprima delle righe spegne «Escludi». Qui si
--   solleva il suo PRIMO motivo, e basta: tooltip ed errore non possono
--   dire cose diverse. Su un array vuoto l'helper tace (= passa).
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite',
        TG_NAME::text,
        script.fn_check_esclusione_articolo_contratto(NEW.contratto_id, NEW.articolo_id),
        'articolo_id',
        NEW.tx_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle()
IS 'Guard ESCLUSIONE figlio bundle: rifiuta contratti_righe.tipo_eccezione = ESCLUSIONE se l''articolo e'' un componente di un bundle nel listino del contratto (E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA). ⭐ Dal 2026-09-28 (brief-db-liste-righe-documento) il predicato NON e'' qui: e'' in script.fn_check_esclusione_articolo_contratto, di cui il guard solleva il primo motivo con script.fn_raise_primo_motivo_se_presente. La stessa check la legge vendite.fn_contratto_righe_preview per spegnere «Escludi» sulla riga col motivo: un predicato, due consumatori, nessuna divergenza possibile. Rami (nella check): nessun listino -> passa; bozza -> versioni ATTIVA/CHIUSA valide oggi; attivo -> versione fissata. Trigger: BEFORE INSERT OR UPDATE, WHEN tipo_eccezione = ESCLUSIONE. §6.1 2026-05-16, rev 2026-09-28.';
```

---
{% include-markdown "signature-core.md" %}
