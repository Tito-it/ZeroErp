# Brief DB — Lo spegnimento di un padre e le figlie scadute: il BLOCK dell'automazione ATTIVO e la validità

## ⏭️ Chi riparte — aggiornato al 2026-11-27

**Riparte: Tid**, con le decisioni di §3. Il brief è **aperto, non iniziato**: nessuno sviluppo, nessun range di
changeSet. Nasce da D-T8a-12 di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) (§25.10), che
Tid ha tolto da T8a il 2026-11-27.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | sessione DB | L'analisi: la decisione esistente sull'automazione ATTIVO, le coppie, le guide | §2 | il via di Tid |
| 2 | Tid | Le decisioni D-BV-1 … D-BV-3 | §3 | 1 |
| 3 | sessione DB | Il giro: pgTAP rosso, changeSet, prova sullo scratch, guida `automazione-db` | — | 2, via e range |
| 4 | Tid | Apply e pgTAP, commit | — | 3 |
| 5 | team BE/FE | La richiesta al BE (i codici `E_ATTIVO_BLOCK_*` che cambiano risposta) | — | 4 |
| 6 | sessione DB | Archiviazione in `work-done/` | — | 4, 5 |

**Decisioni aperte di Tid:** D-BV-1 … D-BV-3.
**Da committare:** questo brief, nato il 2026-11-27.

> **Brief vicini verificati:** [brief-db-reseller](brief-db-reseller.md) D-R-4 (la stessa domanda per il legame
> reseller–BA: si decide qui, e il reseller ne prende l'esito); [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md)
> §25.7 D-T8c-9 (il vettore del DDT, risolto con un'eccezione: «la bolla è storia») e §25.10 D-T8a-12.
> **Guide verificate:** da fare al primo giro (`scripts/guide_coinvolte.py` su `dbops.trgfn_prevent_deactivate_if_children`,
> `dbops.fn_trigger_figlie_presenti` e le figlie); la prima è [automazione-db](../../guide/automazione-db.md) §4.2.

## 1. Il difetto

`dbops.trgfn_prevent_deactivate_if_children`, il BLOCK che l'automazione ATTIVO monta su ogni padre di una FK, rifiuta
lo spegnimento se il padre ha figlie (le figlie attive, se la figlia ha `attivo`). Non guarda la validità: una figlia
con `valido_al` passato, cioè storia, ferma lo spegnimento come una viva. Casi letti sul catalogo (2026-11-27):

* `conti_bancari` ← i due legami (che non hanno `attivo`): **un conto con un legame chiuso non si spegne**;
* `soggetti` ← `soggetti_conti_bancari`: **un soggetto con un conto storico non si spegne**;
* `resellers` ← il legame reseller–BA (S57e, D-R-4).

Le coppie BLOCK con una figlia che ha `valido_al` sono una trentina; in molte la figlia ha anche `attivo`, e la
domanda è se la validità conti accanto all'attivo o solo quando l'attivo manca. Il trigger è dell'automazione: non
si riscrive con un DDL (linee-guida-sql §11.5), si cambia il BB o si dichiara un'eccezione.

## 2. Da analizzare prima di proporre

* la decisione esistente sull'automazione ATTIVO (brief in `work-done/`, guida `automazione-db`, `git log -S`): se la
  validità fu esclusa per scelta;
* l'elenco delle coppie, una per una: la figlia ha `attivo`, `valido_al`, tutte e due; che cosa garantisce oggi il
  BLOCK ai lettori del padre spento («nessuna figlia lo nomina») — è una **garanzia che si ritira**, da censire;
* il verso opposto: una figlia scaduta su un padre spento si può riaprire allungando `valido_al`, e il REQUIRE
  (`trgfn_child_requires_active_parent`) scatta solo su `INSERT` o sul cambio della FK, non sulle date;
* la data con cui si misura: il giorno operativo (`script.fn_data_operativa`), come la vista dei conti.

## 3. Le decisioni attese

* **D-BV-1** — il BB conta solo le figlie valide nel giorno operativo o dopo, quando la figlia ha `valido_al`: per
  tutte le coppie, o per quelle dichiarate in un registro;
* **D-BV-2** — il REQUIRE guarda anche il cambio delle date della figlia (il verso opposto);
* **D-BV-3** — il codice: una figlia solo storica non è più un rifiuto, una viva resta `E_ATTIVO_BLOCK_*`.
