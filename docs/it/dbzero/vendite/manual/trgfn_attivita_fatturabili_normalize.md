## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_normalize()`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)    
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)    
>

---

### 🎯 Scopo Principale

(latest review 21/01/2026)
La funzione `vendite.trgfn_attivita_fatturabili_normalize()` applica una **normalizzazione minima**
su `vendite.attivita_fatturabili` per garantire coerenza **temporale** e **tecnica** dei dati
prima della scrittura.

La funzione e` eseguita da un trigger **BEFORE INSERT/UPDATE** su `vendite.attivita_fatturabili`.

---

### 🔧 Regole applicate

1. **Competenza mensile**  
   Se `competenza_mese` e` valorizzato, viene normalizzato al **primo giorno del mese** (YYYY-MM-01).

2. **Sorgente tecnica**  
   `sorgente_tipo_id` e` una **FK** verso `config.sorgenti`, quindi non si applica alcuna
   normalizzazione stringa.  
   Se `sorgente_tipo_id` e` valorizzato e `sorgente_riga` e` NULL, viene impostato `sorgente_riga = 0`
   per garantire coerenza con l’idempotenza import.

La funzione non esegue validazioni di dominio (delegate ai trigger guard dedicati).

---

### ✅ Ruolo nel processo

Questa funzione:

* assicura che le competenze mensili siano **allineate** al calendario;
* standardizza la gestione della riga sorgente quando l’attivita` proviene da sistemi esterni;
* mantiene le trasformazioni **minime** per evitare effetti collaterali sulle logiche di business.

---

{% include-markdown "signature-core.md" %}
