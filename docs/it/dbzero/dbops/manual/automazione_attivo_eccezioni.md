## 📘 Documentazione Concettuale – Tabella `dbops.automazione_attivo_eccezioni`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `ATTIVO` che queste righe restringono
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore che legge il registro e salta le FK dichiarate
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — toglie i trigger già generati per queste FK
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il block sul padre che qui non nasce
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il require sul figlio che qui non nasce
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §1.3 e §4.2, le eccezioni della regola ATTIVO

---

### 🎯 Scopo Principale

Il registro delle FK che l'automazione ATTIVO **non lega**: per una riga — schema e tabella della
figlia, colonna FK — il motore non genera né il block sul padre («il padre non si spegne con figli
attivi») né il require sul figlio («un figlio attivo solo sotto un padre attivo»), e toglie quelli
che c'erano già.

Serve quando `attivo` sul padre e `attivo` sul figlio rispondono a **due domande diverse**, e
legarli renderebbe impossibile uno stato legittimo.

---

### Una FK per riga, non una tabella

La chiave naturale è la terna figlia–colonna FK (`uq_automazione_attivo_eccezioni_fk`). Le altre
FK della stessa figlia restano legate: l'eccezione toglie un legame, non una tabella dal framework.

---

### ⛔ Il motivo è obbligatorio

Il CHECK `chk_automazione_attivo_eccezioni_motivo` pretende un motivo. Un'eccezione senza un
perché è un buco nel framework, non una decisione: chi la legge deve poter capire quale stato
legittimo il legame avrebbe impedito.

---

### Le righe di oggi

| Figlia · FK | Perché |
| --- | --- |
| `config.profili_accesso_bindings.identita_digitale_id` | **Porta e profili** sono due domande: la veste attiva dice se la porta è aperta, il binding che cosa si può fare dentro. La veste OPERATORE nasce spenta e deve poter avere i suoi profili, SUPER_ADMIN compreso, prima dell'invito accettato; spegnere una veste non deve togliere i profili. I lettori dei permessi chiedono già entrambe le cose |
| `vendite.fatture_stampa_coda.tipo_documento_output_id` | La coda di stampa è un **outbox**: il worker aggiorna la riga a ogni passaggio, e il require scatterebbe su ogni aggiornamento. Con un tipo di documento spento si fermerebbe il lotto intero, e il block impedirebbe di spegnere un tipo finché una riga storica lo nomina. Se un tipo può stampare lo decide la risoluzione del modello al drenaggio |
| `catalogo.articoli_uom_operativa.articolo_id` e `.uom_id` | La mappatura di un'unità operativa è **storia**, come una nota: si chiude con `valido_al`, e dal primo giorno in vigore non si spegne più (`catalogo.trgfn_uom_guard_storia`). Col block, un articolo o un'unità che hanno avuto una mappatura non si spegnerebbero mai; col require, una mappatura di un articolo spento non si scriverebbe. L'articolo si spegne e si riaccende con le sue mappature intatte; una riga di documento su un articolo spento la fermano già i require del documento verso l'articolo |
| `catalogo.unita_misura_conversioni.uom_from_id` e `.uom_to_id` | La conversione generale è storia allo stesso modo: un'unità che ha avuto una conversione non si spegnerebbe mai. L'unità si spegne e si riaccende con le sue conversioni intatte |

---

### Il seed e il ritiro di una riga

Le righe arrivano da `80_data`, dal CSV `dbops/automazione_attivo_eccezioni.csv`, con un mirror
sulla chiave naturale. Il mirror non cancella: per ritirare un'eccezione serve una cancellazione
esplicita in un changeSet nuovo. Al giro successivo il motore rigenera i trigger per quella FK.

Una riga nuova ha effetto al giro successivo del motore: è lì che i trigger esistenti si tolgono.

---

### Test

* `db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql` — la prima riga c'è col suo motivo;
  per quella FK non ci sono né require né block, mentre le altre FK della stessa figlia sono
  ancora legate; un SUPER_ADMIN nasce con la veste spenta e il binding attivo, e spegnere la veste
  lascia il binding.

---

### Note di migrazione

* 2026-09-25 — nasce con la prima riga, porta e profili (`brief-db-blocco-login-per-credenziale`
  §12.3). Non è la vecchia `automation_fk_exclusions`, ritirata con le funzioni trigger legacy:
  quella era un elenco senza motivo e senza ritiro.
* 2026-10-20 — seconda riga, la coda di stampa (`brief-db-modelli-documento-standard` §9).
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-10 — quattro righe: la mappatura delle unità operative (`articolo_id`, `uom_id`) e
  la conversione generale (`uom_from_id`, `uom_to_id`) (`brief-db-revisione-catalogo` §15, Q31).

---

{% include-markdown "signature-core.md" %}
