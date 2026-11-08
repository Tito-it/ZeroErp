## 📘 Documentazione Concettuale – Funzione `pratiche.fn_pratica_flussi_aperti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le istanze di flusso della pratica
> * [config.transizioni_stati_flussi_pratiche](/dbzero/config/tabelle/transizioni_stati_flussi_pratiche) — da qui si capisce se uno stato è terminale
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_pratica_chiudibile](/dbzero/pratiche/funzioni/fn_check_pratica_chiudibile) — l'autochiusura e il guard pre-completamento
> * [pratiche.trgfn_pratiche_guard_chiusura_flussi](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_chiusura_flussi) — la chiusura manuale
> * [pratiche.fn_check_chiusura_pratica](/dbzero/pratiche/funzioni/fn_check_chiusura_pratica) — il controllo complementare, sui template obbligatori

---

### 🎯 Scopo Principale

`pratiche.fn_pratica_flussi_aperti` elenca i flussi istanziati di una pratica che sono in uno stato
non terminale, cioè il lavoro ancora pendente. È un predicato puro: non solleva mai.

---

### Terminale si legge dal grafo degli stati

Uno stato è terminale quando non ha nessuna transizione in uscita attiva in
`config.transizioni_stati_flussi_pratiche`: è la stessa definizione del guard sulla pratica terminale,
e nessuno stato è scritto per nome. Se il grafo cambia, la nozione di terminale si adegua da sola.

Nel catalogo di oggi i terminali sono `COMPLETATO` e `ANNULLATO`. `ERRORE` ha uscite, quindi non è
terminale: un flusso in errore è lavoro pendente e blocca la chiusura della pratica.

---

### Il flusso da escludere

Il secondo parametro, facoltativo, ignora un'istanza. Serve al guard che scatta prima del completamento
di un flusso: in quel momento il flusso è ancora in corso, quindi non terminale, e conterebbe sé stesso.
Escludendolo, il controllo non blocca il suo stesso completamento.

---

### ⭐ Una sola definizione di «lavoro pendente»

La funzione è la sede unica del predicato «flusso aperto», e la condividono l'autochiusura
(`pratiche.fn_check_pratica_chiudibile`) e la chiusura manuale
(`pratiche.trgfn_pratiche_guard_chiusura_flussi`): le due strade non possono dissentire.

È complementare a `pratiche.fn_check_chiusura_pratica`, che ragiona sui template obbligatori: questa
ragiona sulle istanze aperte, anche quelle opzionali.

---

### Test

* `pratiche/test-chiusura-nessun-lavoro-pendente` — la chiusura bloccata da un flusso aperto, manuale e
  automatica.

---

### Note di migrazione

* 2026-07-01 — nasce con la regola «una pratica non si chiude con lavoro pendente»
  (brief-db-chiusura-pratica-nessun-lavoro-pendente).

---

{% include-markdown "signature-core.md" %}
