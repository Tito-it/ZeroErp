## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle:**
> 
> • [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)  
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> • [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)   
>
> **Approfondimento Funzioni:**   
> 
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
> • [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---

### 🎯 Scopo Principale

Garantire che *solo* i soggetti autorizzati secondo le **policy dati societari** possano inserire o aggiornare una riga in `anagrafiche.dati_societari`.

La funzione applica la logica definita nella colonna:

```
config.tipi_soggetto_dettaglio.dati_societari_policy
```

che può assumere i valori:

| Policy       | Significato                                   | Effetto su dati_societari                                         |
| ------------ | --------------------------------------------- | ----------------------------------------------------------------- |
| **NONE**     | Il tipo soggetto NON può avere dati societari | ❌ Inserimento vietato                                             |
| **OPTIONAL** | I dati societari sono facoltativi             | ✔️ Inserimento ammesso                                             |
| **REQUIRED** | I dati societari sono obbligatori             | ✔️ Inserimento ammesso (obbligo verificato da trigger su soggetti) |

> 🔎 **Nota:** questa funzione controlla il *permesso di inserimento*.
> L’obbligo di presenza di dati societari per policy *REQUIRED* viene verificato dal constraint trigger dedicato:
> `anagrafiche.trgfn_soggetti_guard_dati_societari_required()`.

---

### 🧩 Come Funziona

1. Recupera il `tipo_soggetto_dettaglio` associato al soggetto indicato in `NEW.soggetto_id`.
2. Legge la policy `dati_societari_policy`.
3. Applica la regola:

   * **NONE → Errore** (bloccato tramite `script.fn_log_and_raise_error`)
   * **OPTIONAL → OK**
   * **REQUIRED → OK** (la presenza obbligatoria sarà controllata altrove)

Se il soggetto appartiene a un tipo non configurato oppure mancano informazioni, la funzione produce un errore applicativo dedicato.

---

### 🚨 Errori Gestiti

| Codice errore                                       | Quando si verifica                                                |
| --------------------------------------------------- | ----------------------------------------------------------------- |
| **E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO**      | Il tipo soggetto ha policy `NONE`, quindi l’inserimento è vietato |
| **E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO** | Il tipo soggetto non ha una policy definita                       |

Gli errori sono prodotti tramite:
`script.fn_log_and_raise_error('<contesto>', '<funzione>', '<codice>', <meta>, NEW.tx_id, ...)`.

---

### 🔗 Relazioni con altri trigger

Questa funzione è utilizzata da:

```sql
CREATE TRIGGER trg_dati_societari_guard_tipo_soggetto
  BEFORE INSERT OR UPDATE ON anagrafiche.dati_societari
  FOR EACH ROW EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto();
```

È complementare a:

* **`trgfn_soggetti_guard_dati_societari_required()`** (constraint trigger):
  verifica che soggetti con policy *REQUIRED* abbiano almeno un record in `dati_societari`.

Insieme realizzano un modello completo:

* Controllo dei **permessi di inserimento** (questa funzione)
* Controllo dell’**obbligo di presenza** (constraint trigger su soggetti)

---

### 💡 Note Implementative

* La funzione è pensata per essere **estensibile**: se vuoi aggiungere nuove policy o nuovi comportamenti basta modificare la tabella di configurazione.
* Evita duplicazioni logiche: tutta la definizione dei tipi ammessi è centralizzata in `config.tipi_soggetto_dettaglio`.
* In caso di refactoring basato su servizi futuri (es. estero), la policy può essere differenziata per paese senza toccare la funzione.

---

> 🧠 **"Il controllo dei dati societari diventa configurabile: la logica di business è nel dato, non nel codice."**
