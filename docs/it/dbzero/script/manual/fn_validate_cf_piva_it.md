# 📘 Documentazione Concettuale – Funzione `script.fn_validate_cf_piva_it`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
> [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)      
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)    
>
Approfondimento funzioni:   
> [script.fn_valida_partita_iva](/dbzero/script/funzioni/fn_valida_partita_iva)   
> [script.fn_valida_codice_fiscale](/dbzero/script/funzioni/fn_valida_codice_fiscale)   


La funzione **`script.fn_validate_cf_piva_it(p_tipo_det_id bigint, p_partita_iva text, p_piva_gruppo text, p_codice_fiscale text)`** centralizza i controlli di validità di Partita IVA e Codice Fiscale per soggetti italiani, utilizzando i formati definiti in `config.tipi_soggetto_dettaglio`.

Il suffisso **`_it`** indica che i controlli sono specifici per l'Italia: in futuro si potranno implementare varianti analoghe con suffissi come **`_FR`**, **`_DE`**, **`_UK`** per altri Stati.

---
### 🎯 Scopo Principale
* **Centralizzazione Validazioni**: Unico punto per verificare CF e P.IVA in accordo ai formati configurati.
* **Dinamicità**: I formati (alfanumerico, numerico, lunghezza) sono letti da `config.tipi_soggetto_dettaglio` e possono variare per Stato.
* **Estendibilità**: Aggiunta futura di funzioni con suffissi di Stato, es. `_FR`, `_DE`, `_UK`.

---

### Parametri di Input

| Nome               | Tipo     | Descrizione                                                                                |
| ------------------ | -------- | ------------------------------------------------------------------------------------------ |
| `p_tipo_det_id`    | `bigint` | FK su `config.tipi_soggetto_dettaglio(id)`: definisce i formati CF/PIVA per lo Stato (IT). |
| `p_partita_iva`    | `text`   | Partita IVA principale del soggetto.                                                       |
| `p_piva_gruppo`    | `text`   | Partita IVA del gruppo di acquisto (se previsto).                                          |
| `p_codice_fiscale` | `text`   | Codice Fiscale del soggetto.                                                               |

---

### Flusso Logico

1. **Recupero formato**

   ```plpgsql
   SELECT formato_cf, formato_piva
     INTO STRICT l_tipo_det
     FROM config.tipi_soggetto_dettaglio
    WHERE id = p_tipo_det_id;
   ```
2. **Validazione Partita IVA principale**

   * Se `formato_piva` non `NULL` e `p_partita_iva` valorizzata:

     * Chiama `script.fn_valida_partita_iva(p_partita_iva)`
     * In caso di `FALSE`, solleva errore `PIVA_NON_VALIDA` con contesto dettagliato.
3. **Validazione Partita IVA Gruppo di Acquisto**

   * Stesse condizioni e metodo del punto precedente su `p_piva_gruppo`.
4. **Validazione Codice Fiscale**

   * Se `formato_cf` non `NULL` e `p_codice_fiscale` valorizzato:

     * Chiama `script.fn_valida_codice_fiscale(p_codice_fiscale)`
     * In caso di `FALSE`, solleva errore `CF_NON_VALIDO` con contesto specifico.

---

### 💥 Error Handling

La funzione **non restituisce** un valore, ma utilizza **`script.fn_log_and_raise_error`** per loggare e alzare eccezione:

* **Codici messaggio**:

  * `PIVA_NON_VALIDA`
  * `CF_NON_VALIDO`
* **Contesto JSONB** con i parametri in input (es. `partita_iva`, `codice_fiscale`).

---

### Estensioni Future

* Implementare funzioni con suffissi per altri Stati: `script.fn_validate_cf_piva_fr`, `script.fn_validate_cf_piva_de`, etc.
* Eventuale aggiunta di controlli avanzati basati su data di nascita o sesso, delegabili al backend.

---
ℹ️ Considerazioni Finali

Questa funzione rappresenta il punto unico di validazione formale di Partita IVA e Codice Fiscale per soggetti italiani, garantendo coerenza con i formati configurati in tabella e centralizzando la gestione degli errori. Grazie all’uso di script.fn_log_and_raise_error, ogni errore viene registrato e sollevato in modo standard, semplificando il backend e migliorando l’affidabilità complessiva.
```
