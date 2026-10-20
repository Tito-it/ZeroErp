# ⚙️ Funzione `trgfn_fatture_log_a10_orario_reale`

```sql
CREATE FUNCTION trgfn_fatture_log_a10_orario_reale()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_log_a10_orario_reale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: mettere su `data_ora` l'istante della SCRITTURA e non
--   quello di inizio transazione — ma solo quando il chiamante
--   non ha scelto un orario suo.
--
-- ⭐ PERCHE' UN TRIGGER E NON CINQUE RISCRITTURE. Gli scrittori di
--   questo registro sono cinque funzioni per 957 righe di corpo
--   vivo — piu' il backend — e in nessuna di esse il log e' il
--   soggetto: e' una riga di servizio dentro un ramo di errore.
--   Riprodurre quei corpi per spostare cinque token vorrebbe dire
--   cinque occasioni di regredire qualcosa che non c'entra, e
--   lascerebbe comunque fuori l'INSERT del backend.
--
-- ⭐ LA REGOLA, e la sua correzione del 24-08-2026. La prima
--   versione scriveva SEMPRE, senza guardare NEW.data_ora, e
--   cancellava le linee del tempo che le fixture pgTAP
--   fabbricano a mano (`now() - interval '40 min'`) — l'unico
--   modo di collaudare una finestra temporale dentro una
--   transazione, dove `now()` e' costante.
--
--     Se il chiamante ha passato l'istante di INIZIO TRANSAZIONE
--     non ha scelto un orario: ha usato l'unico che aveva, e
--     quello si sostituisce. Qualunque ALTRO valore e' una
--     scelta, e si rispetta.
--
--   ⚠️ Non e' «fidarsi del chiamante»: `now()` dentro una
--   transazione e' una costante, quindi il confronto riconosce
--   esattamente il caso «non ha deciso niente» — che e' quello
--   dei sei scrittori veri, tutti con `now()` letterale.
--   `CURRENT_TIMESTAMP` e `transaction_timestamp()` sono lo
--   stesso valore e sono coperti senza nominarli.
--
-- ⚠️ Il ramo IS NULL ha una ragione sua: la colonna e' NOT NULL,
--   quindi un NULL esplicito verrebbe respinto DOPO i BEFORE
--   trigger. Riempirlo qui trasforma un errore di vincolo in un
--   comportamento sensato, e non nasconde niente.
--
-- ⚠️ Idioma gia' in casa: trgfn_audit_data_user_generic fa
--   qualcosa di simile sulle colonne di audit, su questa stessa
--   tabella. Qui la colonna e' di OSSERVABILITA', e per questo
--   l'orologio e' un altro.
BEGIN
    IF NEW.data_ora IS NULL OR NEW.data_ora = now() THEN
        NEW.data_ora := clock_timestamp();
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_log_a10_orario_reale()
IS 'BEFORE INSERT su vendite.fatture_log: mette data_ora = clock_timestamp(), cioe'' l''istante della SCRITTURA, quando il chiamante ha passato l''istante di INIZIO TRANSAZIONE (now(), CURRENT_TIMESTAMP, transaction_timestamp() — lo stesso valore) o non ha passato niente. ⭐ Nasce da R-1 (brief-db-event-log-scope-e-riga-parlante §13): con now() tutte le righe scritte nella stessa transazione escono con lo stesso timestamp al microsecondo, e la storia di un lotto — che legge tre registri — non e'' ordinabile. ⭐ E'' un trigger e non cinque riscritture perche'' gli scrittori di questo registro sono cinque funzioni per 957 righe di corpo vivo (fn_genera_scadenze_fattura, fn_genera_scadenze_lotto, fn_reset_fondi_fattura, fn_snapshot_fattura_lotto, fn_sync_contabili_fondo_fattura) piu'' l''INSERT del backend, e in nessuna di esse il log e'' il soggetto. ⚠️ rev 2026-08-24 (20260824-18): la prima versione scriveva SEMPRE, e cancellava le linee del tempo che le fixture pgTAP fabbricano a mano — l''unico modo di collaudare una finestra temporale dentro una transazione, dove now() e'' costante. Tre asserzioni di test-fn-list-lotto-segnalazioni-job sono diventate rosse. La regola corretta e'': chi passa l''istante di inizio transazione non ha SCELTO un orario, ha usato l''unico che aveva; qualunque altro valore e'' una scelta e si rispetta. Sui sei scrittori veri, tutti con now() letterale, il comportamento e'' identico. ⚠️ Il ramo IS NULL c''e'' perche'' la colonna e'' NOT NULL: un NULL esplicito verrebbe respinto dopo i BEFORE trigger, e riempirlo qui trasforma un errore di vincolo in un comportamento sensato. Fase a10: i BEFORE ROW scattano in ordine alfabetico e questo viene prima di trg_fatture_log_audit_data_user_upd e trg_fatture_log_gen_tx_id_ins_upd, nessuno dei quali legge data_ora.';
```

</div>

---
{% include-markdown "signature-core.md" %}
