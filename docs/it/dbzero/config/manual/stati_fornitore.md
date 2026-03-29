## 📘 Documentazione Concettuale – Tabella `config.stati_fornitore`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)    
>
**Approfondimento funzioni:**    
>
• [anagrafiche.fn_guard_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_guard_fornitore_attivo)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_fornitore` definisce gli **stati operativi** dei fornitori. Il
catalogo non serve solo a classificare il fornitore, ma anche a governare se il
soggetto puo` essere usato normalmente nei processi di acquisto.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Descrizione operativa**: `descrizione`, `descrizione_breve`.
* **Disponibilita` d'uso**: `attivo`.
* **Blocco processo**: `blocca_ordini` per impedire l'uso del fornitore in ordini/DDT quando lo stato lo richiede.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* Lo stato e` referenziato da `anagrafiche.fornitori.stato_fornitore_id`.
* `codice` e `codice_interno` devono restare **stabili** per API, lookup e integrazioni.
* La disattivazione di uno stato gia` usato da fornitori esistenti e` bloccata da trigger DB.
* `blocca_ordini = true` rende il fornitore non utilizzabile nei flussi operativi che richiedono fornitore attivo.

---

### Uso tipico nel processo

* **Qualifica iniziale**: stati come verifica o onboarding del fornitore.
* **Operativita`**: stati che consentono emissione ordini e gestione acquisti.
* **Sospensione/blocco**: stati che mantengono lo storico ma impediscono nuovi utilizzi operativi.
* **Cessazione**: stati finali per fornitori non piu` utilizzabili.

---

{% include-markdown "signature-core.md" %}
