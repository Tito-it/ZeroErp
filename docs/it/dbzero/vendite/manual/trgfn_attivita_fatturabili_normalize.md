## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_normalize()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)    
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)    
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_tipo_doc_fiscale_id](/dbzero/vendite/funzioni/fn_get_tipo_doc_fiscale_id)   
> • [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id)   
>
### 🎯 Scopo Principale
(latest review 21/01/2026)
La funzione `vendite.trgfn_attivita_fatturabili_normalize()` applica una **normalizzazione minima**
su `vendite.attivita_fatturabili` per garantire coerenza **temporale** e **tecnica** dei dati
prima della scrittura.

La funzione e` eseguita da un trigger **BEFORE INSERT** e **BEFORE UPDATE OF**
`competenza_mese`, `sorgente_tipo_id`, `sorgente_riga`, `billing_account_id`, `tipo_doc_fiscale_id`, `valuta_id`
su `vendite.attivita_fatturabili`.
Le operazioni **DELETE** non attivano la normalizzazione.

---

### Regole applicate

1. **Competenza mensile**  
   Se `competenza_mese` e` valorizzato, viene normalizzato al **primo giorno del mese** (YYYY-MM-01).

2. **Sorgente tecnica**  
   `sorgente_tipo_id` e` una **FK** verso `config.sorgenti`, quindi non si applica alcuna
   normalizzazione stringa.  
   Se `sorgente_tipo_id` e` valorizzato e `sorgente_riga` e` NULL, viene impostato `sorgente_riga = 0`
   per garantire coerenza con l’idempotenza import.

3. **Tipo documento fiscale**  
   Se `tipo_doc_fiscale_id` e` NULL, viene risolto tramite `vendite.fn_get_tipo_doc_fiscale_id`
   (solo sorgente, senza fallback).

4. **Valuta**  
   Se `valuta_id` e` NULL, viene risolto tramite `vendite.fn_get_valuta_id`
   (priorita`: BA → utility → gestore).

La funzione non esegue validazioni di dominio (delegate ai trigger guard dedicati).

---

### Ruolo nel processo

Questa funzione:

* assicura che le competenze mensili siano **allineate** al calendario;
* standardizza la gestione della riga sorgente quando l’attivita` proviene da sistemi esterni;
* mantiene le trasformazioni **minime** per evitare effetti collaterali sulle logiche di business.

---

{% include-markdown "signature-core.md" %}
