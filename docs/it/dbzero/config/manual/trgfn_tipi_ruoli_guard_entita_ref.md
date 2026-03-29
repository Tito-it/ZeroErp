## 📘 Documentazione Concettuale – Funzione `config.trgfn_tipi_ruoli_guard_entita_ref()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)    
>
**Approfondimento funzioni:**    
>
• [script.fn_search_soggetti_universale](/dbzero/script/funzioni/fn_search_soggetti_universale)    
> • [script.fn_get_entita_ruolo_detail](/dbzero/script/funzioni/fn_get_entita_ruolo_detail)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
La trigger function `config.trgfn_tipi_ruoli_guard_entita_ref()` valida la
configurazione dei riferimenti dinamici salvati in `config.tipi_ruoli`,
assicurando che `entita_tabella` e `entita_colonna_codice` puntino a una
tabella o vista realmente utilizzabile dalle funzioni di ricerca dettaglio.

---

### Quando si attiva

* trigger `BEFORE INSERT OR UPDATE` su `config.tipi_ruoli`;
* controlla i campi di configurazione della riga `NEW` prima del salvataggio.

---

### Regole operative

* se `entita_tabella` e` `NULL`, allora anche `entita_colonna_codice` deve essere `NULL`;
* se `entita_tabella` e` valorizzata, deve risolversi in una `regclass` valida;
* la tabella o vista referenziata deve contenere la colonna `soggetto_ruolo_id`;
* la colonna codice deve esistere:
  * usa `entita_colonna_codice` se valorizzata;
  * altrimenti assume `codice` come default.

---

### Perche` e` importante

* evita configurazioni errate che romperebbero la ricerca dinamica per codice entita`;
* protegge funzioni come `script.fn_search_soggetti_universale` e `script.fn_get_entita_ruolo_detail` da riferimenti a viste o tabelle incoerenti;
* consente di estendere i tipi ruolo via configurazione, senza introdurre SQL hardcoded per ogni nuovo ruolo.

---

### Effetto pratico

* un tipo ruolo puo` dichiarare una tabella dedicata per la ricerca del proprio codice entita`;
* se la configurazione e` incompleta o punta a colonne mancanti, l'errore emerge subito in fase di setup;
* il catalogo `config.tipi_ruoli` resta affidabile come fonte di metadata dinamici per il dominio anagrafiche.

---

{% include-markdown "signature-core.md" %}
