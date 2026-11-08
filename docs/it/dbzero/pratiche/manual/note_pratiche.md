## 📘 Documentazione Concettuale – Tabella `pratiche.note_pratiche`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica a cui la nota appartiene
> * [pratiche.note_flussi](/dbzero/pratiche/tabelle/note_flussi) — la gemella, per le note di un singolo flusso
> * [config.tipi_nota](/dbzero/config/tabelle/tipi_nota) — la classificazione della nota
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si registra l'aggiunta
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_note_pratiche_giornale](/dbzero/pratiche/funzioni/trgfn_note_pratiche_giornale) — scrive `NOTA_AGGIUNTA` nel giornale
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modello delle pratiche

---

### 🎯 Scopo Principale

La tabella `pratiche.note_pratiche` contiene le note testuali associate a una pratica: annotazioni
libere aggiunte durante il suo ciclo di vita, ciascuna classificata per tipo di nota.

---

### Una nota si modifica, e la storia resta

A differenza degli allegati, una nota è modificabile. Ogni modifica e ogni cancellazione passano dallo
storico (`storico.note_pratiche`, scritto dal trigger di storicizzazione), e la riga porta `tx_id` per
correlare la modifica alla transazione che l'ha fatta.

---

### Il tipo di nota classifica, non nasconde

`tipo_nota_id` dice di che nota si tratta (generale, interna, per il cliente, tecnica, legale). Il
tipo deve essere attivo: lo controlla, a fine transazione, il presidio sul padre attivo di
`config.tipi_nota`.

⚠️ Il database non decide chi vede una nota in base al tipo: `config.tipi_nota` non ha attributi di
visibilità, e nessuna regola li legge. Se un tipo va nascosto a qualcuno, la regola sta in chi
presenta la nota.

---

### Chi scrive e chi legge

* Scrive il backend, quando l'operatore annota la pratica.
* All'inserimento, `pratiche.trgfn_note_pratiche_giornale` registra nel giornale l'azione
  `NOTA_AGGIUNTA`. Le modifiche successive non vanno nel giornale: la loro storia sta nello storico.
* La visibilità segue la pratica: la regola RLS lascia vedere a un operatore solo le note delle pratiche
  del proprio perimetro di emittente.

---

{% include-markdown "signature-core.md" %}
