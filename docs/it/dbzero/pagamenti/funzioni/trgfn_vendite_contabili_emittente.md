# ⚙️ Funzione `trgfn_vendite_contabili_emittente`

```sql
CREATE FUNCTION trgfn_vendite_contabili_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Applicare a ogni scrittura la SEDE UNICA che dice di chi
    --   e' una distinta (pagamenti.fn_get_emittente_distinta,
    --   D4). Qui NON c'e' il predicato: c'e' l'applicazione.
    --
    -- Uso: BEFORE INSERT OR UPDATE OF ente_incasso_id,
    --      emittente_soggetto_ruolo_id FOR EACH ROW
    -- ⚠️ Il nome del trigger deve precedere alfabeticamente
    --   a10_gen_codice (numera) e a10_guard_emittente_scope
    --   (giudica): l'emittente va risolto PRIMA di entrambi.
    -- =========================================================

    IF TG_OP = 'INSERT' THEN
        -- I quattro livelli: dato (coerente col canale), dal
        -- canale, dalla sessione, altrimenti rifiuto parlante.
        NEW.emittente_soggetto_ruolo_id :=
            pagamenti.fn_get_emittente_distinta(
                NEW.emittente_soggetto_ruolo_id, NEW.ente_incasso_id);
        RETURN NEW;
    END IF;

    -- UPDATE. ⭐ Un emittente messo a NULL NON si ri-riempie:
    --   parla il NOT NULL (23502, con column_name per il client).
    --   Ri-risolverlo dalla sessione sarebbe un cambio di
    --   emittente che nessuno ha chiesto (scelta confermata da
    --   Tid il 2026-09-15).
    IF NEW.emittente_soggetto_ruolo_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Entrambi valorizzati: solo i livelli 0-1, cioe' la COERENZA
    -- fra il canale (nuovo) e l'emittente della riga. Spostare
    -- una distinta sul canale di un altro emittente e' un rifiuto.
    PERFORM pagamenti.fn_get_emittente_distinta(
                NEW.emittente_soggetto_ruolo_id, NEW.ente_incasso_id);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_emittente()
IS 'Applica a ogni scrittura su pagamenti.vendite_contabili la sede unica che dice di chi e'' la distinta (pagamenti.fn_get_emittente_distinta, D4 del brief distinta-numerata-sul-registro). In INSERT scrive NEW.emittente_soggetto_ruolo_id con i quattro livelli (dato e coerente col canale / dal canale / dall''operatore in sessione / rifiuto parlante); in UPDATE con l''emittente a NULL NON risolve — parla il NOT NULL, perche'' ri-riempirlo dalla sessione sarebbe un cambio di emittente che nessuno ha chiesto (scelta di Tid, 2026-09-15); in UPDATE con entrambi verifica solo la coerenza fra il canale nuovo e l''emittente della riga. ⚠️ Qui non c''e'' il predicato: c''e'' la sua applicazione. Il predicato sta nella funzione, che la madre fn_get_or_create_vendite_contabile chiama anche per la chiave di riuso. ⚠️ L''ORDINE DEI BEFORE ROW REGGE SUL NOME: trg_…_a10_emittente_ins_upd precede a10_gen_codice_ins (che numera sul registro dell''emittente) e a10_guard_emittente_scope_ins_upd (che giudica lo scope su questa colonna). Rinominare uno dei tre sposta la risoluzione dopo chi la usa. Rev 2026-09-15.';
```

</div>

---
{% include-markdown "signature-core.md" %}
