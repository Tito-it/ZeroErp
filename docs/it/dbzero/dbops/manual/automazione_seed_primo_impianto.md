## 📘 Documentazione Concettuale – Tabella `dbops.automazione_seed_primo_impianto`

> **Ultimo aggiornamento**: 18 novembre 2026
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

Oggi le tabelle sono due: `config.email_account` (solo inserimento) e `config.email_template` (per
colonna).

---

### Una riga per tabella, in tre forme

| Forma | Colonne | Che cosa fa il CSV su una riga di seed |
| --- | --- | --- |
| **per riga** (il default) | `colonne_software` e `colonne_installazione` `NULL` | finché la riga è intatta la aggiorna tutta; personalizzata, non le riscrive più niente |
| **per colonna** | i due elenchi, non vuoti e disgiunti | le colonne del software le aggiorna sempre, e l'installazione non le può cambiare; quelle dell'installazione come nella forma per riga |
| **solo inserimento** | `solo_inserimento` vero, i due elenchi `NULL` | crea la riga se manca, e poi non la aggiorna più, toccata o no |

* La forma **per colonna** serve alle righe miste, in cui una parte è del software e una parte
  dell'installazione. In `email_template` il `codice`, il reparto, il tipo di prestazione, la lingua
  e le variabili sono del software; oggetto, corpi e `attivo` dell'installazione.
* Il **solo inserimento** serve quando il CSV porta segnaposto che ogni installazione sostituisce:
  l'host SMTP di esempio, la password da configurare.
* ⛔ In forma per colonna ogni colonna della tabella sta in uno dei due elenchi, tranne quelle libere
  (`id`, `meta`, le colonne d'audit, `tx_id`). Una colonna nuova non classificata ferma il giro su
  quella tabella: il trigger di prima resta finché qualcuno non la classifica.
* `enabled` spento toglie il trigger al giro dopo; il registro delle righe di seed resta.
* `trigger_name` — il nome del trigger, se non si vuole quello del template
  (`trg_<tabella>_a00_seed_primo_impianto_ins_upd_dlt`).
* `motivo` — perché la tabella è di primo impianto, in parole.

I `CHECK` della tabella tengono la forma coerente: i due elenchi sono tutti e due `NULL` o tutti e due
pieni e disgiunti, e il solo inserimento vale solo per la forma per riga.

---

### Chi la scrive

Solo la migrazione, dal CSV `80_data/sql/dbops/automazione_seed_primo_impianto.csv`. L'applicazione
la legge soltanto: un'app che la scrivesse spegnerebbe la protezione.

⚠️ **Una tabella si iscrive in un rilascio precedente al primo ritocco del suo CSV.** Il trigger
nasce dopo `80_data`, quindi il CSV ritoccato nello stesso rilascio passa prima che il trigger ci sia.

---

### Test

* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql` — il trigger montato su tutte e due
  le tabelle, primo fra i `BEFORE`, e nessuna divergenza.
* `db/pgtap/dbops/test-seed-primo-impianto-postura-v1.sql` — all'applicazione solo `SELECT`.

---

### Note di migrazione

* 2026-11-17 — nasce, con `config.email_account` e `config.email_template`
  (`brief-db-seed-primo-impianto-non-si-riscrive`).

---

{% include-markdown "signature-core.md" %}
