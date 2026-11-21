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
[anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo)   
> [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo)   
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---
### 🎯 Scopo Principale

> **Ultimo aggiornamento**: 17 novembre 2026

Verificare che un **ruolo soggetto**, quando si scrive, abbia gli indirizzi **obbligatori** che il suo tipo di
ruolo chiede, sulla **natura** del soggetto.

Il controllo non sta qui: sta in
[fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo), che
chiamano anche i trigger della cancellazione di un indirizzo e del cambio di natura del soggetto (vedi sotto). Il
trigger passa il ruolo scritto e il suo `tx_id`.

---

### Il requisito

Lo calcola [fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo), per
ogni riga obbligatoria della matrice del tipo di ruolo, attiva e valida nel giorno aziendale
(`script.fn_data_operativa()`):

| La natura del soggetto… | Il ruolo deve avere |
| --- | --- |
| ammette il tipo della riga | il tipo, oppure il suo ripiego (se il ruolo e la natura lo ammettono) |
| non ammette il tipo, ammette il ripiego | il ripiego |
| non ammette né il tipo né il ripiego | niente, per quella riga |

Un indirizzo del ruolo soddisfa il requisito anche se è legato a un'istanza. Natura assente: la natura non conta.
Tipo di ruolo assente, o senza righe obbligatorie: nessun requisito.

---

### Come Funziona

1. Ignora le `DELETE`.
2. Chiama il guard col ruolo scritto: il guard legge il tipo di ruolo e la natura del soggetto, calcola il
   requisito e cerca il primo tipo richiesto che manca, nell'ordine del tipo.
3. Il controllo è eseguito da **constraint trigger deferrable**:
   * default: a fine transazione (`COMMIT`);
   * anticipabile con `SET CONSTRAINTS ... IMMEDIATE`.

---

### 🚨 Errori Gestiti

| Codice errore | Quando si verifica |
| --- | --- |
| **E_INDIRIZZO_OBBLIGATORIO_MANCANTE** | Manca un indirizzo che il requisito del ruolo chiede |

La frase nomina il ruolo e il tipo richiesto, col suo ripiego quando vale, per descrizione:
«Il ruolo Cliente richiede l'indirizzo «Fatturazione» / «Domicilio Fiscale».». Su un privato fornitore a cui il
ruolo chiede la sede legale col ripiego del domicilio fiscale, la frase nomina il solo domicilio fiscale. I nomi
li compone [anagrafiche.fn_nomi_tipo_indirizzo_richiesto](/dbzero/anagrafiche/funzioni/fn_nomi_tipo_indirizzo_richiesto);
gli id (ruolo del soggetto, tipo di ruolo, natura, tipo richiesto, ripiego) stanno nel contesto dell'errore.

⛔ Il codice è **del layer ruolo**. Il gemello del soggetto,
[trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required),
legge la matrice della natura e solleva `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO`.

---

## Trigger Associato

Questa funzione è usata come **constraint trigger DEFERRABLE INITIALLY DEFERRED** su `anagrafiche.soggetti_ruoli`:

```sql
CREATE CONSTRAINT TRIGGER trg_soggetti_ruoli_def_guard_indirizzi_required_aft_ins_upd
  AFTER INSERT OR UPDATE
  ON anagrafiche.soggetti_ruoli
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required();
```

Lo stesso guard lo chiamano, sempre a fine transazione:

* [trgfn_indirizzi_guard_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_obbligatori_ruolo),
  quando si cancella un indirizzo del ruolo o se ne cambia il tipo o il ruolo: si giudica il ruolo da cui
  l'indirizzo è uscito;
* [trgfn_soggetti_guard_obbligatori_ruoli](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_obbligatori_ruoli),
  quando cambia la natura del soggetto: si giudicano tutti i suoi ruoli.

---

### Note Operative

* Sostituire un indirizzo obbligatorio (cancellarlo e riscriverlo) passa, se le due scritture stanno nella stessa
  transazione.
* Cancellare un ruolo coi suoi indirizzi passa: il ruolo che non c'è più non si giudica.
* Ciò che il guard pretende è ciò che la copia automatica degli obbligatori scrive
  ([fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo)) e che i picker del ruolo
  segnano obbligatorio: tutti leggono lo stesso requisito.
* Un cambio della matrice non rigiudica i ruoli già scritti.

---

> **"Gli indirizzi obbligatori dipendono dal ruolo e dalla natura del soggetto: il trigger assicura la conformità."**
