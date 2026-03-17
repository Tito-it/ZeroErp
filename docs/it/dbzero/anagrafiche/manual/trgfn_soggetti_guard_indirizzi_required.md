## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_soggetti_guard_indirizzi_required()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)   
> [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)   
>
**Approfondimento Funzioni:**   
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---

### 🎯 Scopo Principale

(latest review 15-02-26)
Verificare che un soggetto possieda tutti i **tipi di indirizzo obbligatori** definiti nella matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`.

Se per il tipo soggetto dettaglio sono presenti righe di matrice con `obbligatorio = true`, la funzione controlla l'esistenza di almeno un indirizzo (anche tramite fallback) per ciascun tipo obbligatorio.

---

### Come Funziona

1. Ignora le `DELETE`.
2. Se `NEW.tipo_soggetto_dettaglio_id` e' NULL, la funzione non applica vincoli.
3. Verifica se esiste almeno una riga di matrice per quel tipo soggetto dettaglio:
   * **Matrice assente** -> nessun vincolo.
4. Cerca un indirizzo obbligatorio mancante considerando:
   * `obbligatorio = true` e `attivo = true`
   * validita' temporale (`valido_dal`/`valido_al`)
   * presenza di un indirizzo con `tipo_indirizzo_id` oppure il relativo `fallback_tipo_indirizzo_id`.
5. Se trova un obbligatorio mancante, genera errore applicativo.
6. Il controllo e' eseguito da **constraint trigger deferrable**:
   * default: a fine transazione (`COMMIT`);
   * anticipabile con `SET CONSTRAINTS ... IMMEDIATE`.

---

### 🚨 Errori Gestiti

| Codice errore                         | Quando si verifica                                |
| ------------------------------------- | ------------------------------------------------- |
| **E_INDIRIZZO_OBBLIGATORIO_MANCANTE** | Manca un indirizzo richiesto per il tipo soggetto |

Gli errori sono prodotti tramite:
`script.fn_log_and_raise_error('<contesto>', '<funzione>', '<codice>', <meta>, NEW.tx_id, ...)`.

---

## Trigger Associato

Questa funzione e' usata come **constraint trigger DEFERRABLE INITIALLY DEFERRED** su `anagrafiche.soggetti`:

```sql
CREATE CONSTRAINT TRIGGER trg_soggetti_def_guard_indirizzi_required_aft_ins_upd
  AFTER INSERT OR UPDATE
  ON anagrafiche.soggetti
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required();
```

---

### Note Operative

* La matrice e' opzionale: se non esiste per il tipo soggetto dettaglio, il controllo non scatta.
* Il fallback consente di soddisfare l'obbligo con un tipo indirizzo alternativo configurato.
* La validita' temporale e' valutata su `current_date`.

---

> **"Gli indirizzi obbligatori dipendono dal tipo soggetto: il trigger assicura la conformita'."**
