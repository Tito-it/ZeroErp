## 📘 Documentazione Concettuale – Tabella `pratiche.allegati_pratiche`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica a cui l'allegato appartiene
> * [pratiche.allegati_flussi](/dbzero/pratiche/tabelle/allegati_flussi) — la gemella, per gli allegati di un singolo flusso
> * [config.tipi_allegato](/dbzero/config/tabelle/tipi_allegato) — la classificazione dell'allegato
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si registra l'aggiunta
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_allegati_pratiche_giornale](/dbzero/pratiche/funzioni/trgfn_allegati_pratiche_giornale) — scrive `ALLEGATO_AGGIUNTO` nel giornale
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modello delle pratiche

---

### 🎯 Scopo Principale

La tabella `pratiche.allegati_pratiche` registra i file allegati a una pratica: una riga per file, con
il tipo di allegato e il riferimento al file nello storage.

Il database non contiene il file: `percorso` è la chiave di storage (un percorso o una chiave di
oggetto), `nome_file` il nome originale, `mime_type` e `dimensione` le sue proprietà.

---

### Un allegato non si modifica: si versiona

Una nuova versione di un file è una riga nuova, che punta alla precedente con `allegato_padre_id`. Se
la versione precedente viene cancellata, il riferimento si svuota e la nuova resta.

⚠️ L'immutabilità è una **convenzione**, non un vincolo: la tabella ha le colonne di audit
dell'aggiornamento (`data_update`, `user_update`, mantenute dal trigger di audit) e il ruolo
applicativo può aggiornare e cancellare. Nessun guard rifiuta un `UPDATE`. Per questo la tabella non è
storicizzata e non porta `tx_id`.

---

### Chi scrive e chi legge

* Scrive il backend, quando l'operatore carica un file sulla pratica.
* All'inserimento, `pratiche.trgfn_allegati_pratiche_giornale` registra nel giornale della pratica
  l'azione `ALLEGATO_AGGIUNTO`.
* Il tipo di allegato deve essere attivo: lo controlla, a fine transazione, il presidio sul padre
  attivo di `config.tipi_allegato`.
* La visibilità segue la pratica: la regola RLS lascia vedere a un operatore solo gli allegati delle
  pratiche del proprio perimetro di emittente.

---

### Test

* `pratiche/test-audit-update-appendonly-pratiche` — la tabella ha le colonne di audit
  dell'aggiornamento, valorizzate con l'utente reale.

---

{% include-markdown "signature-core.md" %}
