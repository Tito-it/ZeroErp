## 📘 Documentazione Concettuale – Tabella `config.titoli_cortesia`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)   
> [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti)    


La tabella **`config.titoli_cortesia`** raccoglie i titoli di cortesia (es. “Signore”, “Dottore”, “Ingegnere”) utilizzabili nei contatti e nelle anagrafiche, separando la forma estesa dalla sua abbreviazione.

---
### 🎯 Scopo Principale
* **Uniformare i titoli**  
  Gestire centralmente i titoli di cortesia per tutti i soggetti/contatti, evitando discrepanze tra form, report e stampe.

* **Forma estesa vs. abbreviazione**  
  - **`descrizione`**: titolo completo (es. “Dottoressa”)  
  - **`descrizione_breve`**: forma abbreviata (es. “Dott.ssa”)  

---

### Esempi di valori

| descrizione    | descrizione_breve |
| -------------- | ----------------- |
| Signore        | Sig.              |
| Signora        | Sig.ra            |
| Dottore        | Dott.             |
| Dottoressa     | Dott.ssa          |
| Ingegnere      | Ing.              |
| Avvocato       | Avv.              |
| Presidente     | Pres.             |

---

### Vincoli e trigger

- **`PK (id)`**: identificatore univoco del titolo.  
- **`UNIQUE(descrizione)`**: garantisce che non esistano duplicati di titolo esteso.  
- **Trigger di audit**  
  - **`trg_upd_titoli_cortesia_audit_data_user`**  
    Aggiorna automaticamente `data_update` e `user_update` ad ogni modifica.

---

### Vantaggi Operativi

* **Coerenza terminologica**  
  Un unico elenco di titoli di cortesia evita errori di battitura e differenze tra le varie parti dell’applicazione.  
* **Manutenzione semplificata**  
  Nuovi titoli o modifiche si gestiscono in un solo punto.  
* **Flessibilità di presentazione**  
  La doppia descrizione consente di scegliere la forma più adatta in base al contesto (spazi ridotti vs. documentazione dettagliata).

> **“Centralizzare i titoli di cortesia migliora uniformità, leggibilità e facilità di gestione dei dati anagrafici.”**  
