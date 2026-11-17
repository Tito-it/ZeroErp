## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()`

> 👀 **Vedi anche**   
>
**Approfondimento tabelle:**    
>
[anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo)   
>
**Approfondimento Funzioni:**   
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
> [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   

---
### 🎯 Scopo Principale

> **Ultimo aggiornamento**: 17 novembre 2026

Verificare che un **ruolo soggetto** abbia tutti i tipi di indirizzo **obbligatori** definiti nella matrice `config.tipi_ruolo_tipi_indirizzo`.

Se per il tipo ruolo sono presenti righe di matrice con `obbligatorio = true`, la funzione controlla l'esistenza di almeno un indirizzo (anche tramite fallback) per ciascun tipo richiesto.

---

### Come Funziona

1. Ignora le `DELETE`.
2. Se `NEW.tipo_ruolo_id` e' NULL, la funzione non applica vincoli.
3. Verifica se esiste almeno una riga di matrice per quel tipo ruolo:
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

| Codice errore                         | Quando si verifica                             |
| ------------------------------------- | ---------------------------------------------- |
| **E_INDIRIZZO_OBBLIGATORIO_MANCANTE** | Manca un indirizzo richiesto per il tipo ruolo |

La frase nomina il ruolo e il tipo richiesto, col suo ripiego se la riga ne ha uno, per descrizione:
«Il ruolo Fornitore richiede l'indirizzo «Fatturazione».». I nomi dei tipi li compone
[anagrafiche.fn_nomi_tipo_indirizzo_richiesto](/dbzero/anagrafiche/funzioni/fn_nomi_tipo_indirizzo_richiesto);
gli id (ruolo del soggetto, tipo di ruolo, tipo richiesto, ripiego) stanno nel contesto dell'errore.

⛔ Il codice è **del layer ruolo**. Il gemello del soggetto,
[trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required),
legge la matrice della natura e solleva `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO`.

⚠️ Il requisito **non guarda la natura** del soggetto del ruolo: una riga obbligatoria che la natura
non ammette resta pretesa, e nessuna scrittura può soddisfarla.

---

## Trigger Associato

Questa funzione e' usata come **constraint trigger DEFERRABLE INITIALLY DEFERRED** su `anagrafiche.soggetti_ruoli`:

```sql
CREATE CONSTRAINT TRIGGER trg_soggetti_ruoli_def_guard_indirizzi_required_aft_ins_upd
  AFTER INSERT OR UPDATE
  ON anagrafiche.soggetti_ruoli
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required();
```

---

### Note Operative

* La matrice e' opzionale: se non esiste per il tipo ruolo, il controllo non scatta.
* Il fallback consente di soddisfare l'obbligo con un tipo indirizzo alternativo configurato.
* La validita' temporale e' valutata sul giorno aziendale, `script.fn_data_operativa()`.

---

> **"Gli indirizzi obbligatori dipendono dal ruolo: il trigger assicura la conformita'."**
