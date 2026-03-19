## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo()`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle:**
> 
• [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)  
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> • [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)  
> • [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)  
>
**Approfondimento Funzioni:**   
> 
• [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
> • [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---
### 🎯 Scopo Principale
(latest review 28-12-25)
Garantire che il **tipo indirizzo** associato a un soggetto sia coerente con la **matrice di abilitazione** definita per il suo tipo soggetto dettaglio.

Se e' presente una matrice attiva in `config.tipi_soggetto_dettaglio_tipi_indirizzo`, la funzione consente solo i tipi indirizzo previsti, attivi e validi per data.

---

### Come Funziona

1. Ignora le `DELETE` (non applica controlli).
2. Se mancano `soggetto_id` o `tipo_indirizzo_id`, non applica controlli.
3. Recupera `tipo_soggetto_dettaglio_id` dal soggetto.
4. Se non esiste un tipo soggetto dettaglio, la funzione e' permissiva (non blocca).
5. Verifica se esiste almeno una riga di matrice per quel tipo:
   * **Matrice assente** → indirizzi liberi (nessun vincolo).
   * **Matrice presente** → accetta solo righe con `attivo = true` e validita' temporale coerente.
6. In caso di violazione, genera errore applicativo con `script.fn_log_and_raise_error`.

---

### 🚨 Errori Gestiti

| Codice errore                     | Quando si verifica                                         |
| --------------------------------- | ---------------------------------------------------------- |
| **E_TIPO_INDIRIZZO_NON_PERMESSO** | Il tipo indirizzo non e' previsto/attivo/valido in matrice |

Gli errori sono prodotti tramite:
`script.fn_log_and_raise_error('<contesto>', '<funzione>', '<codice>', <meta>, NEW.tx_id, ...)`.

---

### Relazioni con altri trigger

Questa funzione e' usata come guard su `anagrafiche.indirizzi_soggetti`, tipicamente in un trigger `BEFORE INSERT OR UPDATE`, ad esempio:

```sql
CREATE TRIGGER trg_indirizzi_soggetti_guard_tipo_indirizzo
  BEFORE INSERT OR UPDATE ON anagrafiche.indirizzi_soggetti
  FOR EACH ROW EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo();
```

---

### Note Implementative

* La matrice e' **opzionale**: se non definita per il tipo soggetto dettaglio, la funzione non blocca.
* La validita' temporale usa `current_date` e rispetta `valido_dal`/`valido_al`.
* I dettagli di errore includono `tipo_indirizzo_id`, `tipo_soggetto_dettaglio_id` e `soggetto_id`.

---

> **"La matrice tipi indirizzo decide cosa e' permesso: il trigger impedisce associazioni non configurate."**

