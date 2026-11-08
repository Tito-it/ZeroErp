## 📘 Documentazione Concettuale – Funzione `pratiche.fn_coda_lavoro_operatore`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — i flussi che entrano in coda
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica padre, il suo emittente e il suo assegnatario
> * [pratiche.competenze_flussi](/dbzero/pratiche/tabelle/competenze_flussi) — chi è competente per un template, e quali template sono riservati ai competenti
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il reparto anagrafico dell'operatore
> * [config.transizioni_stati_pratiche](/dbzero/config/tabelle/transizioni_stati_pratiche) — da qui si capisce se una pratica è terminale
>
> Approfondimento funzioni:
>
> * [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/funzioni/fn_prendi_in_carico_flusso) — la presa in carico, con la stessa policy

---

### 🎯 Scopo Principale

`pratiche.fn_coda_lavoro_operatore` restituisce la coda di lavoro di un operatore, per un emittente,
divisa in quattro livelli mutuamente esclusivi: ogni flusso compare una volta sola, nel livello più alto
che gli si applica.

La coda è allineata alla presa in carico: ciò che compare come prendibile è davvero prendibile
dall'operatore secondo la stessa policy di `pratiche.fn_prendi_in_carico_flusso`.

---

### I quattro livelli

| Livello | Che cosa ci entra | Caso della policy |
| --- | --- | --- |
| `ASSEGNATO` | I flussi assegnati all'operatore, da eseguire o in corso | — |
| `COMPETENZA` | Flussi non assegnati, da eseguire, per un template su cui l'operatore ha una competenza attiva | A / D |
| `REPARTO` | Flussi non assegnati, da eseguire, del reparto anagrafico dell'operatore, per un template senza competenze attive (nessuno skill-lock) | B |
| `LIBERO` | Flussi non assegnati, da eseguire, senza reparto e senza skill-lock, di una pratica assegnata all'operatore | C |

* I tre livelli prendibili chiedono il flusso non assegnato e nello stato `DA_ESEGUIRE`.
* Un flusso riservato ai competenti compare solo ai competenti, mai come `REPARTO` o `LIBERO`.
* ⭐ Un flusso libero non si mostra a tutti, che sarebbe rumore: lo vede chi ha in carico la pratica
  padre, così resta scopribile senza invadere le code altrui.
* Il reparto è quello anagrafico dell'operatore; il reparto scritto su una competenza non conta qui.

---

### Che cosa resta fuori

* I flussi di un altro emittente: l'emittente è un parametro obbligatorio.
* I flussi che non sono da eseguire né in corso.
* ⭐ I flussi delle pratiche **terminali**: una pratica è terminale quando il suo stato non ha nessuna
  transizione in uscita attiva in `config.transizioni_stati_pratiche`. È la stessa definizione del guard
  `trgfn_flussi_guard_pratica_terminale`, che ne congela i flussi: non sono lavoro da fare. Nessuno
  stato è scritto per nome.

---

### Le colonne che non si capiscono dal nome

* `priorita_codice` — il codice interno della priorità della pratica.
* Lo stato del flusso esce in tre forme: `stato_flusso_codice_interno` per la logica,
  `stato_flusso_codice` e `stato_flusso_descrizione` per il display.
* `data_scadenza` — la scadenza del flusso, o quella della pratica quando il flusso non ne ha una.
* `risorsa_assegnata` — sempre vuota: i livelli sono assegnati all'operatore stesso o non assegnati, e
  non c'è un altro assegnatario da mostrare.

L'ordine è: livello (dall'assegnato al libero), priorità della pratica decrescente per codice interno,
scadenza (le vuote in fondo), sequenza del flusso.

---

### Note di migrazione

* 2026-06-18 — allineata alla policy reparto-first della presa in carico: il livello `REPARTO` usa il
  reparto anagrafico e si limita ai flussi senza skill-lock; nasce il livello `LIBERO`
  (brief-db-assegnazione-flusso).
* 2026-07-01 — lo stato del flusso esce anche con codice e descrizione di display.

---

{% include-markdown "signature-core.md" %}
