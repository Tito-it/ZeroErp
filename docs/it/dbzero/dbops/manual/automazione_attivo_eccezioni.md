## 📘 Documentazione Concettuale – Tabella `dbops.automazione_attivo_eccezioni`

> **Ultimo aggiornamento**: 19 novembre 2026
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
| `ui.lista_preferenza_utente.lista_id` e `.preset_base_id`, `ui.dashboard_preferenza_utente.dashboard_id` e `.preset_base_id` | La preferenza è uno **stato dell'utente**, non un'entità col suo ciclo di vita: non ha `attivo`, quindi per il block conta ogni riga, e una lista o un preset che un utente ha scelto non si spegnerebbero più. Se il preset di base è spento o sparito, `ui.fn_resolve_lista_config` e `ui.fn_resolve_dashboard_config` ripiegano già sul livello successivo |
| `ui.lista_preset_colonna.preset_id` e `.colonna_id`, `ui.lista_colonna_permesso.colonna_id`, `ui.dashboard_widget.dashboard_id` e `.widget_id`, `ui.dashboard_preset_widget.preset_id` e `.widget_id` | Righe di **composizione** senza `attivo` (le colonne di un preset, i widget di una dashboard o di un preset, i permessi di una colonna): sono parti del padre, non entità che ne dipendono. Senza `attivo` per il block conta ogni riga, e il padre non si spegnerebbe mai. Spegnere il padre spegne le parti; quale parte mostrare lo decidono i risolutori |
| `ui.lista_preset.emittente_fiscale_id` e `.profilo_accesso_id`, `ui.dashboard_preset.emittente_fiscale_id` e `.profilo_accesso_id`, `ui.lista_colonna_permesso.profilo_accesso_id` | Configurazione dell'interfaccia legata a un'entità di **un altro dominio**: spegnere un emittente o un profilo è un gesto del dominio, e non deve fermarsi su un preset o su un permesso di lista. Il preset di un emittente o di un profilo spento già non si applica: la cascata dei risolutori parte dalla veste corrente |
| `catalogo.articoli_uom_operativa.articolo_id` e `.uom_id` | La mappatura di un'unità operativa è **storia**, come una nota: si chiude con `valido_al`, e dal primo giorno in vigore non si spegne più (`catalogo.trgfn_uom_guard_storia`). Col block, un articolo o un'unità che hanno avuto una mappatura non si spegnerebbero mai; col require, una mappatura di un articolo spento non si scriverebbe. L'articolo si spegne e si riaccende con le sue mappature intatte; una riga di documento su un articolo spento la fermano già i require del documento verso l'articolo |
| `catalogo.unita_misura_conversioni.uom_from_id` e `.uom_to_id` | La conversione generale è storia allo stesso modo: un'unità che ha avuto una conversione non si spegnerebbe mai. L'unità si spegne e si riaccende con le sue conversioni intatte |
| `catalogo.note_articoli.target_id`, `catalogo.note_articoli_componenti.target_id` | La nota di un'anagrafica **annota** l'oggetto, non lo tiene in vita. La partizione non ha `attivo`: col block ogni nota conterebbe come figlia attiva e l'articolo non si spegnerebbe; col require una nota su un articolo spento non si scriverebbe. L'articolo si spegne e si riaccende con le sue note intatte. Il legame di distinta non si spegne (si chiude con `valido_al` e resta attivo), e un legame chiuso si annota ancora. Le note vanno via col padre solo se lo si cancella (`ON DELETE CASCADE`) |
| `documenti.documenti_generati.template_documento_id`, `.template_versione_id`, `.sorgente_tipo_id`, `.emittente_fiscale_id` | La stampa è **storia**: la fotografia del modello, della versione, della sorgente e dell'azienda del momento dell'emissione, e non si cancella. Col block, un modello, una versione o un'azienda che hanno stampato non si spegnerebbero più; col require, ogni modifica di una stampa chiederebbe padri ancora accesi. Che cosa può stampare oggi lo decide la risoluzione del modello prima del render |
| `config.email_log.email_account_id` e `.email_template_id` | La mail spedita è **storia**: la fotografia dell'account e del template con cui è partita, e resta. Col block, un account o un template che hanno spedito non si spegnerebbero più, e siccome non si cancellano non ci sarebbe nessun gesto per toglierli dall'uso. Con quale account e template si spedisce lo decidono i risolutori, che leggono solo le righe accese |
| `config.email_outbox.email_account_id` e `.email_template_id` | La bozza cita l'account e il template con cui è stata composta: è la **provenienza** del testo, non un legame vivo. Col block conterebbe anche la bozza annullata o spedita. L'account di invio si risolve di nuovo alla conferma |
| `documenti.template_documenti_versioni.derivata_da_versione_id` | L'origine di una copia è la sua **provenienza**, non un padre vivo: una versione dello standard da cui deriva una copia si ritira lo stesso. Che cosa fare di una copia il cui standard non stampa lo dice la vista dello scarto |

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
* 2026-11-08 — sedici righe di `ui`: le preferenze degli utenti, le righe di composizione, la
  configurazione legata a un emittente o a un profilo (`brief-db-revisione-dbops`, giro 7-bis
  blocco c, §23.12).
* 2026-11-11 — due righe, le note di catalogo: `note_articoli` e `note_articoli_componenti`
  (`brief-db-revisione-catalogo`, Q12, giro 4).
* 2026-11-10 — quattro righe: la mappatura delle unità operative (`articolo_id`, `uom_id`) e
  la conversione generale (`uom_from_id`, `uom_to_id`) (`brief-db-revisione-catalogo` §15, Q31).
* 2026-11-12 — il motivo di `note_articoli_componenti` dice che il legame di distinta non si
  spegne (`brief-db-revisione-catalogo`, Q35 (c)).
* 2026-11-15 — sette righe: le cinque chiavi della stampa, il tipo del suo file, l'origine di una
  copia di modello.
* 2026-11-16 — escono le tre righe verso i tipi di documento e di file (la coda di stampa delle
  fatture, la stampa, il suo file): quei vocabolari non hanno più `attivo`, e la coppia ATTIVO non
  nasce.
* 2026-11-19 — quattro righe, lo storico della posta: `email_log` ed `email_outbox` verso
  account e template. Account e template non si cancellano più: si spengono, anche dopo aver
  spedito (`brief-db-seed-primo-impianto-non-si-riscrive` §16.14, Q24).

---

{% include-markdown "signature-core.md" %}
