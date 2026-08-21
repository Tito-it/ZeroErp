## 📘 Documentazione Concettuale – Tabella `config.categoria_accisa`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
> • [config.utilities](/dbzero/config/tabelle/utilities)
> • [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Categoria di **accisa** per utility: la classificazione fiscale che, nel mondo energia,
determina l'aliquota dell'imposta di consumo. È referenziata da `config.classi_utenze`.

L'accisa non dipende dal prodotto ma dall'**uso** che se ne fa — domestico, industriale,
agricolo — ed è per questo che vive accanto alle classi di utenza e non al catalogo articoli.

---

### ⚠️ Oggi è **vuota**

Misurato il 2026-08-21: **zero righe**, come `config.tipi_tariffe_ee`. Sono le due tabelle
della dimensione fiscale delle utilities, e il modello energia non è ancora in esercizio.

Va letta come predisposizione: la struttura c'è, la configurazione no.

---

### È **per utility**, non globale

`utility_id` è `NOT NULL`: le categorie di accisa dell'energia elettrica non sono quelle del
gas, e la tabella lo impone invece di lasciarlo alla disciplina di chi la popola.

⚠️ Conseguenza: non esiste una categoria di accisa «generica». Chi aggiunge una utility nuova
con dimensione fiscale deve aggiungere anche le sue categorie, altrimenti
`config.classi_utenze` non ha nulla a cui puntare.

---

### La struttura è minima, e lo resta

Quattro colonne: `id`, `utility_id`, `codice`, `descrizione`. Nessun `attivo`, nessun `meta`,
nessun audit. È un vocabolario di lookup puro — il che, se un giorno servisse deprecare una
categoria senza cancellarla, richiederebbe di aggiungere `obsoleto_dal` come sulle altre
tabelle di catalogo del progetto.

---

{% include-markdown "signature-core.md" %}
