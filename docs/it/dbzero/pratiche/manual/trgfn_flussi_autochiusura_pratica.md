## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_autochiusura_pratica`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso che si completa
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica che si chiude
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — `chiude_pratica` e `obbligatorio`
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_pratica_chiudibile](/dbzero/pratiche/funzioni/fn_check_pratica_chiudibile) — il predicato del modello senza flusso di chiusura
> * [pratiche.trgfn_flussi_guard_chiusura_prematura](/dbzero/pratiche/funzioni/trgfn_flussi_guard_chiusura_prematura) — il flusso di chiusura si completa solo a percorso concluso
> * [pratiche.trgfn_pratiche_guard_chiusura_flussi](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_chiusura_flussi) — il guard di chiusura della pratica, che la chiusura automatica attraversa
> * [pratiche.trgfn_flussi_guard_pratica_terminale](/dbzero/pratiche/funzioni/trgfn_flussi_guard_pratica_terminale) — niente flussi nuovi su una pratica chiusa

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_autochiusura_pratica` chiude la pratica guidata dal
workflow: quando un flusso passa a `COMPLETATO`, porta la pratica da `APERTA` a `CHIUSA` se
l'edizione di workflow della pratica dice che il percorso è concluso.

---

### Le regole

1. Scatta solo quando lo stato del flusso cambia davvero verso `COMPLETATO`.
2. Solo da pratica `APERTA`: una pratica in bozza, sospesa o terminale non si chiude da sé.
3. **Edizione con flusso di chiusura** (`chiude_pratica`, attivo): la pratica si chiude se e solo se il
   flusso completato è quello. Nessun altro flusso la chiude.
4. **Edizione senza flusso di chiusura ma con almeno un obbligatorio attivo**: la pratica si chiude se
   `pratiche.fn_check_pratica_chiudibile` risponde sì, cioè non resta nessun obbligatorio bloccante e
   nessun flusso istanziato aperto, escluso quello appena completato.
5. **Edizione senza obbligatori e senza flusso di chiusura**: niente, la pratica resta aperta. Non ha un
   percorso di chiusura automatico.

La chiusura è un aggiornamento della pratica che passa dai guard di transizione e di chiusura e dal
giornale come una chiusura manuale; tocca la pratica solo se è ancora `APERTA`, e non riscrive i flussi,
quindi non ricorre.

---

### ⭐ Si legge dall'edizione della pratica, non dal tipo

Il flusso di chiusura e gli obbligatori si cercano nell'edizione di workflow fissata sulla pratica
(`definizione_id`), non nel tipo di prestazione: un tipo può avere più edizioni, ciascuna col suo
flusso di chiusura.

---

### ⭐ Subito, non a fine transazione

Il trigger è `AFTER UPDATE OF stato_id` su `pratiche.flussi`, nella fase finale, e chiude subito. I rami
condizionali si modellano come bivi per esito (obbligatori sul ramo, tramite prerequisiti che guardano
l'esito): il predicato blocca prima che servano istanze a valle. Se un flusso a valle venisse creato su
una pratica già chiusa, `pratiche.trgfn_flussi_guard_pratica_terminale` lo rifiuta a voce alta: è la
rete che rende inutile rimandare il controllo.

---

### Test

* `pratiche/test-autochiusura-pratica` — i due modelli, con e senza flusso di chiusura.
* `pratiche/test-chiusura-nessun-lavoro-pendente` — il bivio e il lavoro rimasto.
* `pratiche/test-fork-chiusura-per-definizione` — due edizioni dello stesso tipo non si mescolano.
* `pratiche/test-bivi-condizionali` — la chiusura su un ramo.

---

### Note di migrazione

* 2026-07-03 — flusso di chiusura e obbligatori si cercano nell'edizione della pratica e non più nel
  tipo: con le copie degli emittenti un tipo ha più edizioni.

---

{% include-markdown "signature-core.md" %}
