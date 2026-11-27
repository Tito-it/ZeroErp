## 📘 Documentazione Concettuale – Tabella `config.utilities_tipi_ruolo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[`config.utilities`](/dbzero/config/tabelle/utilities)
> [`config.tipi_ruoli`](/dbzero/config/tabelle/tipi_ruoli)
>
**Approfondimento funzioni:**
>
[`script.fn_guard_utility_tipo_ruolo`](/dbzero/script/manual/fn_guard_utility_tipo_ruolo)

---
### 🎯 Scopo Principale
(latest review 27-11-2026)
La tabella `config.utilities_tipi_ruolo` dice quali `tipo_ruolo` possono trattare ciascuna `utility`.

Regola di dominio:

1. un tipo di ruolo tratta l'utility solo se ha la sua riga, accesa e valida oggi;
2. un'utility **senza righe** non è ammessa per **nessuno** (la matrice è chiusa).

La riga dell'**emittente fiscale** (`EF`) ha due regole in più, di
`config.trgfn_utilities_tipi_ruolo_guard_uscita_ef`:

* non ha **data di fine** (`E_UTILITY_EF_SENZA_SCADENZA`): l'uscita di un'utility dall'emittente fiscale
  è un gesto, non una data che passa;
* finché un'azienda **gestisce** l'utility (ha la sua riga in `anagrafiche.emittenti_fiscali_utilities`),
  la riga `EF` non si spegne, non prende una data d'inizio futura, non si cancella e non si sposta
  (`E_UTILITY_EF_GESTITA`).

### Il seed

La matrice ha un seed di **primo impianto, per riga**: ogni utility del catalogo è ammessa per l'emittente
fiscale e per il cliente, e energia, gas e acqua per il fornitore. Il CSV crea le righe e le aggiorna finché
l'installazione non le modifica; una riga toccata dal SUPER_ADMIN resta com'è. Utility e tipo di ruolo sono la
chiave della riga, ferma col lucchetto di colonna: una riga sbagliata si spegne e se ne scrive un'altra.

---

### Struttura logica

Campi principali:

* `utility_id` -> FK `config.utilities(id)`
* `tipo_ruolo_id` -> FK `config.tipi_ruoli(id)`
* `attivo` -> abilita/disabilita logicamente la regola
* `valido_dal` / `valido_al` -> finestra temporale della regola
* `meta` -> metadati estensibili

Vincoli principali:

* `UNIQUE (utility_id, tipo_ruolo_id)`
* check di validita temporale (`valido_al >= valido_dal` quando entrambi valorizzati)

---

### Semantica operativa

La tabella **non** impone da sola i blocchi: la leggono il guard `script.fn_guard_utility_tipo_ruolo`
(sulle tabelle del registro `dbops.automazione_guard_utility_tipo_ruolo`) e la tendina
`anagrafiche.fn_lookup_utilities_per_ba`, con la stessa regola: senza la riga della coppia, il ruolo non
tratta l'utility.

---

### Esempio concettuale

Utility `GAS`:

* righe configurate: `CLIENTE`, `GESTORE`
* tentativo con `FORNITORE` -> bloccato
* tentativo con `CLIENTE` -> consentito

Utility `MANIFATTURIERO` senza righe:

* qualsiasi ruolo -> bloccato

---

### Nota architetturale

Per scelta progettuale corrente:

* si introduce policy `utility -> tipo_ruolo`;
* **non** si introduce una matrice `utility -> tipo_soggetto` (tutti i tipi soggetto potenzialmente ammessi).

---

{% include-markdown "signature-core.md" %}
