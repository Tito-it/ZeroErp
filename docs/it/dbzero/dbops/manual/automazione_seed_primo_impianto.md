## 📘 Documentazione Concettuale – Tabella `dbops.automazione_seed_primo_impianto`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.seed_righe](/dbzero/dbops/tabelle/seed_righe) — il registro delle righe nate dal seed
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — il giro che porta i trigger allo stato di questa tabella
> * [dbops.fn_seed_primo_impianto_divergenze](/dbzero/dbops/funzioni/fn_seed_primo_impianto_divergenze) — il confronto fra il trigger atteso e quello vivo
> * [dbops.fn_seed_primo_impianto_argomenti](/dbzero/dbops/funzioni/fn_seed_primo_impianto_argomenti) — la grammatica degli argomenti del trigger
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — la funzione del trigger
>
> Guide:
>
> * [Linee guida SQL — 11.7 Le tre specie di seed](/linee-guida-sql#117-in-80_data-convivono-tre-specie-di-seed-catalogo-primo-impianto-e-macchina) — quando una tabella è di primo impianto
> * [Framework di automazione DB — 4.9 SEED_PRIMO_IMPIANTO](/guide/automazione-db#49-seed_primo_impianto-la-riga-modificata-dallinstallazione-non-si-riscrive) — la regola

---

### 🎯 Scopo Principale

L'elenco delle tabelle del **seed di primo impianto**: quelle in cui il CSV crea la riga, e dopo che
l'installazione l'ha modificata la riga è sua. Su ognuna il giro delle automazioni monta il trigger
[trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto).

Oggi le tabelle sono sei: `config.email_account` (solo inserimento), `config.email_template`,
`ui.lista_definizione`, `ui.lista_colonna` e `ui.lista_preset` (per colonna), e `ui.lista_preset_colonna`
(figlia di `ui.lista_preset`).

---

### Una riga per tabella, in quattro forme

| Forma | Colonne | Che cosa fa il CSV su una riga di seed |
| --- | --- | --- |
| **per riga** (il default) | `colonne_software`, `colonne_installazione`, `tabella_padre` e `colonna_padre` `NULL` | finché la riga è intatta la aggiorna tutta; personalizzata, non le riscrive più niente |
| **per colonna** | i due elenchi, non vuoti e disgiunti | le colonne del software le aggiorna sempre, e l'installazione non le può cambiare; quelle dell'installazione come nella forma per riga |
| **solo inserimento** | `solo_inserimento` vero, i due elenchi `NULL` | crea la riga se manca, e poi non la aggiorna più, toccata o no |
| **figlia** | `tabella_padre` (`schema.tabella`) e `colonna_padre`, i due elenchi `NULL` | scrive la riga solo se il padre è una riga di seed intatta; sotto un padre personalizzato non la tocca |

* La forma **per colonna** serve alle righe miste, in cui una parte è del software e una parte
  dell'installazione. In `email_template` il `codice`, il reparto, il tipo di prestazione, la lingua
  e le variabili sono del software; oggetto, corpi e `attivo` dell'installazione.
* Il **solo inserimento** serve quando il CSV porta segnaposto che ogni installazione sostituisce:
  l'host SMTP di esempio, la password da configurare.
* La forma **figlia** serve a una tabella di composizione senza colonna `id`, che non ha una vita sua
  e segue il padre: la composizione di un preset (`ui.lista_preset_colonna`, colonna `preset_id`).
  Le sue righe non entrano nel registro delle righe di seed; l'installazione le scrive e le cancella
  sempre. Il padre è a sua volta iscritto, acceso, non figlia e con la colonna `id`, altrimenti il
  confronto dà `PADRE_NON_ISCRITTO` e il trigger non si monta.
* ⭐ Una scrittura dell'installazione che cambia la composizione personalizza il preset: a fine
  transazione cambia `composizione_impronta`, che in `ui.lista_preset` è una colonna
  dell'installazione insieme a `contenuto_aggiornato_il`. Una composizione riscritta uguale (un
  DELETE seguito dall'INSERT delle stesse righe) non cambia l'impronta, e non personalizza.
* ⛔ In forma per colonna ogni colonna della tabella sta in uno dei due elenchi, tranne quelle libere
  (`id`, `meta`, le colonne d'audit, `tx_id`). Una colonna nuova non classificata ferma il giro su
  quella tabella: il trigger di prima resta finché qualcuno non la classifica.
* `enabled` spento toglie il trigger al giro dopo; il registro delle righe di seed resta.
* `trigger_name` — il nome del trigger, se non si vuole quello del template
  (`trg_<tabella>_a00_seed_primo_impianto_ins_upd_dlt`).
* `motivo` — perché la tabella è di primo impianto, in parole.

I `CHECK` della tabella tengono la forma coerente: i due elenchi sono tutti e due `NULL` o tutti e due
pieni e disgiunti, il solo inserimento vale solo per la forma per riga, e la forma figlia ha padre e
colonna insieme, senza elenchi e senza solo inserimento.

---

### Chi la scrive

Solo la migrazione, dal CSV `80_data/sql/dbops/automazione_seed_primo_impianto.csv`. L'applicazione
la legge soltanto: un'app che la scrivesse spegnerebbe la protezione.

⚠️ **Una tabella si iscrive in un rilascio precedente al primo ritocco del suo CSV.** Il trigger
nasce dopo `80_data`, quindi il CSV ritoccato nello stesso rilascio passa prima che il trigger ci sia.

---

### Test

* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql` — il trigger montato su tutte e due
  le tabelle di `config`, primo fra i `BEFORE`, e nessuna divergenza.
* `db/pgtap/ui/test-seed-primo-impianto-ui-installazione-v1.sql` — le quattro tabelle di `ui` montate,
  la composizione nella forma figlia del preset, nessuna divergenza.
* `db/pgtap/ui/test-seed-primo-impianto-ui-software-v1.sql`, asserzione 12 — una riga figlia con gli
  elenchi è rifiutata dal `CHECK`.
* `db/pgtap/dbops/test-seed-primo-impianto-postura-v1.sql` — all'applicazione solo `SELECT`.

---

### Note di migrazione

* 2026-11-17 — nasce, con `config.email_account` e `config.email_template`
  (`brief-db-seed-primo-impianto-non-si-riscrive`).
* 2026-11-20 — la forma figlia (`tabella_padre`, `colonna_padre`) e le quattro tabelle di `ui`.

---

{% include-markdown "signature-core.md" %}
