## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_snapshot_precontrattuali()`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)    
> • [vendite.contratti_utilities](/dbzero/vendite/manual/contratti_utilities)    
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)    
>
> **Approfondimento funzioni:**    
>
> • [vendite.trgfn_contratti_normalize](/dbzero/vendite/funzioni/trgfn_contratti_normalize)    
> • [vendite.trgfn_contratti_gen_codice](/dbzero/vendite/funzioni/trgfn_contratti_gen_codice)    
>

---

### 🎯 Scopo Principale

(latest review 20/01/26)
La funzione `vendite.trgfn_contratti_snapshot_precontrattuali()` crea lo **snapshot** dei dati
precontrattuali **solo alla creazione del contratto**.  
La scelta progettuale e` deliberata: il contratto diventa la **fonte stabile** per i dati tecnici/commerciali
e le eventuali correzioni richiedono **un nuovo contratto**.

La funzione e` eseguita da un trigger **AFTER INSERT** su `vendite.contratti`.

---

### 🔗 Regola di snapshot

1. Alla creazione del contratto, la funzione cerca il record piu` recente in
   `anagrafiche.istanze_dati_precontrattuali` per `(istanza_utility_id, utility_id)`.
2. Se esiste, inserisce uno snapshot in `vendite.contratti_utilities`:
   * `classe_utenza_id`, `param_1_num`, `param_2_txt`, `meta`
   * riferimento al record sorgente con `istanza_dati_precontrattuali_id`
3. Se non esiste alcun precontrattuale, non inserisce nulla.

Non sono previsti aggiornamenti successivi dello snapshot.

---

### 🧱 Contesto operativo

**Tabella di origine:** `anagrafiche.istanze_dati_precontrattuali`  
**Tabella di destinazione:** `vendite.contratti_utilities`  
**Trigger:** `AFTER INSERT` su `vendite.contratti`

---

### ✅ Ruolo nel processo

Questa funzione consolida la transizione **pre‑contrattuale → contrattuale**:

* evita che il contratto dipenda da dati esterni mutevoli;
* rende i parametri tecnici **riproducibili** per fatturazione e audit;
* stabilisce che ogni variazione sostanziale debba passare da **nuova generazione contratto**.

---

{% include-markdown "signature-core.md" %}

---
