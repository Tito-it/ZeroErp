## 📘 Documentazione Concettuale – Tabella `vendite.contratti_utilities`

> 👀 **Vedi anche**
>
> **Guide generali:**    
>
> • [Generazione di un cliente](/guide/generazione-cliente)    
> • [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility)    
>
> **Approfondimento tabelle:**    
>
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)    
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)    
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)    
> • [config.utilities](/dbzero/config/tabelle/utilities)    

---

### 🎯 Scopo Principale

(latest review 20/01/26)
`vendite.contratti_utilities` conserva lo **snapshot** dei dati pre‑contrattuali al **momento della creazione del contratto**.  
L’obiettivo e` rendere il contratto **autonomo e stabile**: i dati tecnici/commerciali che lo qualificano non vengono piu` aggiornati dopo la creazione.

Questa scelta garantisce che:

* il contratto rimanga la **fonte corretta** per il processo commerciale e di fatturazione;
* i dati precontrattuali possano **evolvere** solo tramite **nuovo contratto**;
* si mantenga **tracciabilita** puntuale del dato utilizzato.

---

### 🧭 Regola di snapshot

Lo snapshot viene eseguito **solo alla creazione del contratto**:

* se esiste un record in `anagrafiche.istanze_dati_precontrattuali`, viene copiato in `contratti_utilities`;
* se non esiste, la tabella resta vuota per quel contratto;
* **nessun aggiornamento successivo** e` previsto: eventuali correzioni richiedono un nuovo contratto.

---

### 🔗 Collegamenti principali

* **1:1 con contratto** → `contratto_id` (un contratto puo` avere al massimo uno snapshot).
* **Origine precontrattuale** → `istanza_dati_precontrattuali_id` per tracciabilita.
* **Dati di dominio** → `classe_utenza_id`, `param_1_num`, `param_2_txt`, `meta`.

---

### 🧩 Campi principali (concetto)

* `contratto_id` → aggancio al contratto.
* `istanza_dati_precontrattuali_id` → riferimento al record sorgente.
* `classe_utenza_id` → snapshot della classe utenza.
* `param_1_num`, `param_2_txt`, `meta` → parametri tecnici snapshot.

---

### ✅ Ruolo nel processo

`vendite.contratti_utilities` e` il **punto di consolidamento** tra fase pre‑contrattuale e fase contrattuale:

* i dati precontrattuali restano **storico di raccolta**;
* il contratto diventa la **base operativa** per pricing, fatturazione e controlli;
* ogni variazione sostanziale richiede **nuova generazione contratto**.

---

{% include-markdown "signature-core.md" %}

---
