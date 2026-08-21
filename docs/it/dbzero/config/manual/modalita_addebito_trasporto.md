## 📘 Documentazione Concettuale – Tabella `config.modalita_addebito_trasporto`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.fatture](/dbzero/vendite/tabelle/fatture)
>
Approfondimenti funzioni/trigger generici:
>
[script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)

---

La tabella **`config.modalita_addebito_trasporto`** definisce il **dominio delle modalità di addebito delle spese di trasporto** (tradizionalmente note come *porto*), utilizzate nei documenti di vendita e logistica (DDT, fatture, ordini, ecc.).

Esempi tipici: **FRANCO**, **ASSEGNATO**, **TERZI**, con comportamenti diversi rispetto a chi sostiene il costo e a come viene eventualmente fatturato.

---
### 🎯 Scopo Principale
* Centralizzare le **modalità di addebito del trasporto** utilizzabili nei DDT e nelle fatture.
* Permettere una gestione coerente delle regole di **chi paga il trasporto** (mittente, destinatario, terzi) e di come questo impatta:

  * la fatturazione delle spese;
  * la responsabilità sul rischio di trasporto;
  * eventuali integrazioni con vettori esterni.
* Offrire codici tecnici stabili e sigle operative leggibili in UI.

---

### Vincoli e Regole Aziendali

* **Codice tecnico interno** (`codice_interno`):

  * identificatore **stabile** e univoco (`uq_modalita_addebito_trasporto_codice_interno`);
  * usato per configurazioni di processo, mapping verso altre tabelle e integrazioni (es. `FRANCO`, `ASSEGNATO`, `TERZI`).

* **Codice operativo** (`codice`):

  * sigla operativa visibile agli utenti (spesso coincide con il codice interno);
  * anch’esso univoco (`uq_modalita_addebito_trasporto_codice`).

* **Descrizione** (`descrizione`):

  * testo descrittivo mostrato in combo, stampe documenti, UI;
  * può essere opzionale nella struttura, ma in pratica è **fortemente consigliato** valorizzarla per leggibilità operativa.

* **Stato di attivazione** (`attivo`):

  * indica se la modalità è utilizzabile nei processi correnti;
  * le modalità non più in uso dovrebbero essere disattivate anziché cancellate, per non compromettere la storicità dei documenti.

* **Ordinamento** (`ordine`):

  * intero che consente di definire un **ordine personalizzato di presentazione** nelle interfacce (es. mostrare `FRANCO`, poi `ASSEGNATO`, poi `TERZI`).

* **Estensioni tramite `meta`** (`jsonb`):

  * campo obbligatorio con default `{}` pensato per gestire parametri opzionali, ad esempio:

    * chi è il **soggetto economicamente responsabile** del trasporto (mittente/destinatario/terzo);
    * se la spesa di trasporto è **fatturata** nello stesso documento o gestita separatamente;
    * regole per calcolo automatico delle spese (es. tariffari, soglie, esenzioni);
    * eventuali vincoli su causali di trasporto o vettori associabili.
  * La struttura del JSON deve seguire linee guida comuni per evitare usi non coerenti.

---

### Relazioni

`config.modalita_addebito_trasporto` è una tabella di **configurazione sorgente** referenziata da:

* **Documenti di trasporto e vendita**:

  * campi tipo `modalita_addebito_trasporto_id` in `vendite.ddt` o `vendite.fatture`;
  * influenza le logiche di calcolo e addebito delle spese di trasporto.

* **Anagrafiche clienti/fornitori** (in prospettiva):

  * una modalità può essere impostata come **default** per un cliente/fornitore specifico, attraverso collegamenti in tabelle anagrafiche o configurazioni per gestore.

> In combinazione con causali di trasporto, aspetti beni e condizioni di vendita, la modalità di addebito trasporto contribuisce a definire il comportamento complessivo del documento.

---

### Trigger Associati

Attualmente la definizione non include campi di audit (`data_insert`, `user_insert`, ecc.). Se in futuro verranno aggiunti, si potrà:

1. Introdurre un trigger di audit generico (es. `trg_upd_modalita_addebito_trasporto_audit_data_user`).
2. Collegarlo alla funzione `script.trgfn_audit_data_user_generic()` per allineare la gestione agli altri domini `config.*`.

> L’adozione di un audit standard è consigliata qualora la tabella venga utilizzata in contesti multi-gestore o dove è importante tracciare modifiche alle regole di porto.

---

### Vantaggi Operativi

* **Coerenza di processo**: tutte le applicazioni utilizzano lo stesso catalogo di modalità di addebito, evitando codifiche duplicate o incoerenti.
* **Chiarezza contrattuale**: la combinazione di codice tecnico, sigla e descrizione rende esplicite le regole su chi paga il trasporto.
* **Flessibilità**: tramite `meta` è possibile arricchire progressivamente il modello (es. regole tariffarie, logiche per tipo documento) senza modificare la struttura fisica.
* **Governance**: i flag di attivazione e l’ordinamento consentono di gestire il ciclo di vita delle modalità (introduzione, dismissione, riorganizzazione della lista visibile agli utenti).

---

> **“Gestire in modo esplicito e centralizzato le modalità di addebito del trasporto riduce ambiguità operative e semplifica la configurazione delle regole di fatturazione e logistica.”**
