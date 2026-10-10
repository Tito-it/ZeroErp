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
> • [script.fn_predicato_soggetto_ruolo_visibile](/dbzero/script/funzioni/fn_predicato_soggetto_ruolo_visibile)    
>
### 🎯 Scopo Principale
(latest review 10-10-2026)
La trigger function `config.trgfn_tipi_ruoli_guard_entita_ref()` valida la
configurazione dei riferimenti dinamici salvati in `config.tipi_ruoli`:
`entita_tabella` e `entita_colonna_codice` (dove la ricerca cerca il codice
dell'entità) ed `entita_esistenza` (quale tabella fa esistere il soggetto-ruolo
per chi guarda, dal 2026-10-10).

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
  * altrimenti assume `codice` come default;
* se `entita_esistenza` è valorizzata (dal 2026-10-10), deve essere una **tabella**
  che esiste, con la colonna `soggetto_ruolo_id`. **Le viste non sono ammesse**: chi
  si vede lo decide la RLS della tabella, e una vista senza `security_invoker` la
  spegnerebbe senza nessun errore.

Errore: `E_TIPI_RUOLI_ENTITA_INVALIDA` per ogni regola strutturale, con la parte
sbagliata nel messaggio; `E_PARAMETRO_INVALIDO` per la colonna codice senza tabella.

⚠️ Il guard vale **in scrittura**. Una tabella cancellata o rinominata dopo non passa
di qui: la vede il pgTAP `script/test-search-regola-unica-visibile-v1` (test 1).

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
