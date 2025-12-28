## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_dati_societari_guard_forma_giuridica()`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle:**
> 
> • [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)  
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> • [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche)   
>
> **Approfondimento Funzioni:**   
> 
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
> • [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---

### 🎯 Scopo Principale

(latest review 28-12-25)
Garantire la **coerenza paese** tra il soggetto e la forma giuridica associata nei dati societari.

La funzione blocca l'operazione se `anagrafiche.soggetti.stato_id` e `config.forme_giuridiche.stato_id` non coincidono.

---

### 🧩 Come Funziona

1. Recupera lo `stato_id` del soggetto collegato a `NEW.soggetto_id`.
2. Recupera lo `stato_id` della forma giuridica collegata a `NEW.forma_giuridica_id`.
3. Confronta i due valori e, in caso di differenza, genera un errore applicativo tramite `script.fn_log_and_raise_error`.

---

### 🚨 Errori Gestiti

| Codice errore               | Quando si verifica                                         |
| --------------------------- | ---------------------------------------------------------- |
| **E_FORMA_GIURIDICA_PAESE** | Paese del soggetto diverso dal paese della forma giuridica |

Gli errori sono prodotti tramite:
`script.fn_log_and_raise_error('<contesto>', '<funzione>', '<codice>', <meta>, NEW.tx_id, ...)`.

---

### 🔗 Relazioni con altri trigger

Questa funzione e' usata come guard su `anagrafiche.dati_societari`, tipicamente in un trigger `BEFORE INSERT OR UPDATE`, ad esempio:

```sql
CREATE TRIGGER trg_dati_societari_guard_forma_giuridica
  BEFORE INSERT OR UPDATE ON anagrafiche.dati_societari
  FOR EACH ROW EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica();
```

---

### 💡 Note Implementative

* Il controllo e' volutamente **fail-fast**: se la coerenza paese non e' rispettata, l'operazione viene bloccata.
* I dettagli utili per il debug (soggetto, forma giuridica, stati) sono inseriti nel payload di errore.

---

> 🧠 **"La forma giuridica deve appartenere allo stesso paese del soggetto: questo trigger evita associazioni incoerenti."**

