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
(latest review 16-02-2026)
La tabella `config.utilities_tipi_ruolo` definisce una **whitelist opzionale** dei `tipo_ruolo` ammessi per ciascuna `utility`.

Regola di dominio:

1. se per una utility **non esistono righe attive/valide**, il comportamento e` **fail-open** (nessun vincolo);
2. se per una utility **esistono righe attive/valide**, sono ammessi **solo** i `tipo_ruolo` presenti.

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

La tabella **non** impone da sola i blocchi: e` la funzione guard a leggerla.

Comportamento previsto:

1. nessuna riga attiva/valida per utility -> nessun blocco;
2. righe attive/valide presenti -> blocco dei ruoli non configurati.

Questo consente rollout graduale senza rompere utilities non ancora configurate.

---

### Esempio concettuale

Utility `GAS`:

* righe configurate: `CLIENTE`, `GESTORE`
* tentativo con `FORNITORE` -> bloccato
* tentativo con `CLIENTE` -> consentito

Utility `MANIFATTURIERO` senza righe:

* qualsiasi ruolo -> consentito (fail-open)

---

### Nota architetturale

Per scelta progettuale corrente:

* si introduce policy `utility -> tipo_ruolo`;
* **non** si introduce una matrice `utility -> tipo_soggetto` (tutti i tipi soggetto potenzialmente ammessi).

---

{% include-markdown "signature-core.md" %}
