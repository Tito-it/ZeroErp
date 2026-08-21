## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_utilities_guard_tipo_classe()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> • [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — pricing v5)

Governa la coppia **tipo utenza / classe di utenza** sullo snapshot pre-contrattuale, e lo fa
partendo da una domanda sola: *questa utility ha la dimensione tipo/classe?*

La risposta non è configurata da nessuna parte come flag: si **deduce** dall'esistenza di
almeno una riga in `config.tipi_utenze` per quella utility. Da lì discendono due regimi
opposti e nessuna via di mezzo:

* **utility con dimensione** (energia elettrica, gas…): tipo e classe sono **obbligatori** e
  devono essere coerenti fra loro;
* **utility senza dimensione** (base, commercio): tipo e classe devono essere **entrambi
  vuoti**.

Il secondo regime è la parte che si dimentica: valorizzare un tipo utenza su un contratto di
commercio non è un dato in più, è un dato che non significa niente e che a valle verrebbe
usato dal pricing.

---

### Aggancio

Trigger `trg_contratti_utilities_a10_guard_tipo_classe_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE OF tipo_utenza_id, classe_utenza_id, utility_id`
su `vendite.contratti_utilities`, `FOR EACH ROW`.

Il `UPDATE OF` include `utility_id`: cambiare utility può spostare la riga da un regime
all'altro, quindi va rivalutata.

---

### Regole applicate

Una sola query risolve entrambe le informazioni necessarie: se l'utility ha tipi
(`EXISTS` in `config.tipi_utenze`) e a quale tipo appartiene la classe dichiarata.

**Ramo A — utility con dimensione:**

1. `tipo_utenza_id` e `classe_utenza_id` devono essere **entrambi valorizzati**, altrimenti
   `E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI`;
2. la classe deve **appartenere** al tipo dichiarato
   (`classi_utenze.tipo_utenza_id = NEW.tipo_utenza_id`), altrimenti
   `E_CONTRATTO_CLASSE_TIPO_INCOERENTE`.

**Ramo B — utility senza dimensione:** tipo e classe devono essere entrambi `NULL`,
altrimenti `E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI`.

---

### ⚠️ La classe inesistente arriva con l'errore «incoerente»

Il tipo della classe è letto con una sotto-select: se `classe_utenza_id` punta a una classe
che non esiste, la variabile resta `NULL`, e `NULL IS DISTINCT FROM NEW.tipo_utenza_id` è
vero. Il guard solleva quindi `E_CONTRATTO_CLASSE_TIPO_INCOERENTE` con
`tipo_utenza_id_classe = null`.

È fail-closed, il verso giusto — ma il messaggio racconta un'incoerenza fra due tipi quando
la causa vera è una classe che non c'è. Nel diagnosticare, un `null` in
`tipo_utenza_id_classe` va letto come «classe non trovata», non come «classe senza tipo».

---

### ⚠️ Il regime dipende dai dati, non da una configurazione esplicita

`v_utility_has_tipi` è un `EXISTS` su `config.tipi_utenze`. Ne segue che **svuotare i tipi di
un'utility ne cambia il regime**: da quel momento i contratti di quell'utility devono avere
tipo e classe `NULL`, e ogni `UPDATE` su una riga esistente che li porta ancora valorizzati
viene rifiutato — anche se la riga era corretta quando è stata scritta.

Non è un difetto, è la conseguenza di dedurre il regime dai dati. Va però considerato prima
di ripulire `config.tipi_utenze`: le righe già scritte diventano non più aggiornabili
finché non si allineano al nuovo regime.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI` | Utility con dimensione, tipo o classe mancante |
| `E_CONTRATTO_CLASSE_TIPO_INCOERENTE` | La classe non appartiene al tipo dichiarato (o non esiste) |
| `E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI` | Utility senza dimensione, tipo o classe valorizzato |

Tutti via `script.fn_log_and_raise_error`, area `vendite`.

---

{% include-markdown "signature-core.md" %}
