## 📘 Documentazione Concettuale – Tabella `pratiche.note_flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso a cui la nota appartiene
> * [pratiche.note_pratiche](/dbzero/pratiche/tabelle/note_pratiche) — la gemella, per le note della pratica
> * [config.tipi_nota](/dbzero/config/tabelle/tipi_nota) — la classificazione della nota
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si registra l'aggiunta
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_note_flussi_giornale](/dbzero/pratiche/funzioni/trgfn_note_flussi_giornale) — scrive `NOTA_AGGIUNTA` nel giornale
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modello delle pratiche

---

### 🎯 Scopo Principale

La tabella `pratiche.note_flussi` contiene le note testuali associate a un singolo flusso di una
pratica: ha la stessa forma di `pratiche.note_pratiche`, ma è legata allo step invece che alla pratica.

---

### Una nota si modifica, e la storia resta

Una nota è modificabile. Ogni modifica e ogni cancellazione passano dallo storico
(`storico.note_flussi`), e la riga porta `tx_id` per correlare la modifica alla transazione.

---

### Il tipo di nota classifica, non nasconde

`tipo_nota_id` dice di che nota si tratta, e deve essere attivo: lo controlla, a fine transazione, il
presidio sul padre attivo di `config.tipi_nota`.

⚠️ Il database non decide chi vede una nota in base al tipo: `config.tipi_nota` non ha attributi di
visibilità, e nessuna regola li legge.

---

### Chi scrive e chi legge

* Scrive il backend, quando l'operatore annota un flusso.
* All'inserimento, `pratiche.trgfn_note_flussi_giornale` registra nel giornale della pratica del flusso
  l'azione `NOTA_AGGIUNTA`. Le modifiche successive non vanno nel giornale: la loro storia sta nello
  storico.
* La visibilità segue la pratica del flusso: la regola RLS lascia vedere a un operatore solo le note
  delle pratiche del proprio perimetro di emittente.

---

{% include-markdown "signature-core.md" %}
