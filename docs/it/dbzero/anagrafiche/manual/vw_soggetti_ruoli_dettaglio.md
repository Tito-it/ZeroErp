## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_soggetti_ruoli_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo, una riga della vista ciascuno
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — l'identità del soggetto del ruolo
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il tipo di ruolo, decodificato
> * [config.titoli_cortesia](/dbzero/config/tabelle/titoli_cortesia) — il titolo di cortesia, se c'è
>
> Approfondimento funzioni:
>
> * [script.fn_get_soggetto_dati_by_ruolo](/dbzero/script/funzioni/fn_get_soggetto_dati_by_ruolo) — legge i dati del soggetto dal ruolo
> * [vendite.fn_snapshot_intestazione_fattura](/dbzero/vendite/funzioni/fn_snapshot_intestazione_fattura) — la fotografia dell'intestazione di una fattura

---

### 🎯 Scopo Principale

`anagrafiche.vw_soggetti_ruoli_dettaglio` mette in una riga un ruolo e il soggetto che lo riveste: l'identità
anagrafica e fiscale del soggetto, il tipo di ruolo decodificato e il titolo di cortesia. Si parte dal ruolo
e si arriva a «chi è», senza ricomporre i join.

---

### Una riga per ruolo

Un soggetto con tre ruoli ha tre righe, ciascuna col suo tipo di ruolo e con l'identità del soggetto
ripetuta. Ogni ruolo ha la sua riga: il soggetto e il tipo di ruolo ci sono sempre, il titolo di cortesia
solo quando il soggetto ne ha uno.

Le colonne del ruolo e quelle del soggetto hanno nomi distinti (le prime col prefisso del ruolo, le audit del
soggetto col prefisso del soggetto): nella stessa riga stanno due autori e due date di modifica, quelli del
ruolo e quelli del soggetto.

---

### Chi la legge

La leggono, nel database, la funzione che restituisce i dati del soggetto a partire da un ruolo e la
fotografia dell'intestazione della fattura, che dalla vista prende l'identità dell'emittente e del cliente,
ciascuno dal suo ruolo. La vista non aggiunge regole: espone le tabelle così come sono.

---

### ⚠️ Che cosa oggi non copre

* **I permessi di scrittura dell'applicazione.** L'applicazione ha INSERT, UPDATE e DELETE sulla vista, che
  unisce più tabelle e non è aggiornabile: i permessi non servono, e una scrittura fallirebbe comunque.
* **La vista non gira coi permessi di chi la interroga.** Oggi è innocuo, perché le sue tabelle non hanno
  visibilità per riga; se la avessero, la vista la scavalcherebbe.

---

{% include-markdown "signature-core.md" %}
