## 📘 Documentazione Concettuale – Tabella `pratiche.allegati_flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso a cui l'allegato appartiene
> * [pratiche.allegati_pratiche](/dbzero/pratiche/tabelle/allegati_pratiche) — la gemella, per gli allegati della pratica
> * [config.tipi_allegato](/dbzero/config/tabelle/tipi_allegato) — la classificazione dell'allegato
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si registra l'aggiunta
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_allegati_flussi_giornale](/dbzero/pratiche/funzioni/trgfn_allegati_flussi_giornale) — scrive `ALLEGATO_AGGIUNTO` nel giornale
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modello delle pratiche

---

### 🎯 Scopo Principale

La tabella `pratiche.allegati_flussi` registra i file allegati a un singolo flusso di una pratica (la
foto di un sopralluogo, il verbale di un intervento): ha la stessa forma di
`pratiche.allegati_pratiche`, ma è legata allo step invece che alla pratica.

Il database non contiene il file: `percorso` è la chiave di storage, `nome_file` il nome originale,
`mime_type` e `dimensione` le sue proprietà.

---

### Un allegato non si modifica: si versiona

Una nuova versione è una riga nuova, che punta alla precedente con `allegato_padre_id`; se la
precedente viene cancellata, il riferimento si svuota.

⚠️ L'immutabilità è una **convenzione**, non un vincolo: la tabella ha le colonne di audit
dell'aggiornamento, mantenute dal trigger di audit, e il ruolo applicativo può aggiornare e
cancellare. Nessun guard rifiuta un `UPDATE`. La tabella non è storicizzata e non porta `tx_id`.

---

### Chi scrive e chi legge

* Scrive il backend, quando l'operatore carica un file su un flusso.
* All'inserimento, `pratiche.trgfn_allegati_flussi_giornale` registra nel giornale della pratica del
  flusso l'azione `ALLEGATO_AGGIUNTO`.
* Il tipo di allegato deve essere attivo: lo controlla, a fine transazione, il presidio sul padre
  attivo di `config.tipi_allegato`.
* La visibilità segue la pratica del flusso: la regola RLS lascia vedere a un operatore solo gli
  allegati delle pratiche del proprio perimetro di emittente.

---

### Test

* `pratiche/test-audit-update-appendonly-pratiche` — la tabella ha le colonne di audit
  dell'aggiornamento.

---

{% include-markdown "signature-core.md" %}
