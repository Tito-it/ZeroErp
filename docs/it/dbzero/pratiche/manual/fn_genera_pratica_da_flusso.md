## 📘 Documentazione Funzione – `pratiche.fn_genera_pratica_da_flusso`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.regole_generazione](regole_generazione.md)
> [pratiche.pratiche](pratiche.md)
> [pratiche.flussi](flussi.md)
> [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)
>
Trigger:
>
`trg_flussi_z90_generazione_upd` (AFTER UPDATE OF stato_id su flussi)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_genera_pratica_da_flusso`** e' il motore della **generazione cross-pratica**: crea una nuova pratica a partire da un flusso completato, secondo una regola configurata in `pratiche.regole_generazione`.

La pratica generata eredita emittente, soggetto e priorita' dalla pratica sorgente, ma con il tipo_prestazione definito dalla regola di destinazione.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_genera_pratica_da_flusso(
  p_flusso_id  pratiche.flussi.id%TYPE,
  p_regola_id  pratiche.regole_generazione.id%TYPE
)
RETURNS pratiche.pratiche.id%TYPE
LANGUAGE plpgsql
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_flusso_id` | bigint | SI | ID del flusso che ha generato l'evento (il flusso completato) |
| `p_regola_id` | bigint | SI | ID della regola di generazione da applicare |

**Ritorna**: `bigint` — ID della nuova pratica creata.

---

### Logica di funzionamento

1. **Validazione parametri**: verifica che `p_flusso_id` e `p_regola_id` siano NOT NULL e > 0.
2. **Recupera dati flusso**: legge `pratica_id` dal flusso indicato.
3. **Recupera pratica sorgente**: copia `emittente_fiscale_id`, `soggetto_id`, `priorita_id`.
4. **Recupera regola**: legge `tipo_prestazione_dest_id` dalla regola (deve essere attiva).
5. **Stato iniziale**: cerca lo stato con `codice_interno = 'BOZZA'` in `config.stati_pratiche`.
6. **Crea pratica target**: INSERT in `pratiche.pratiche` con:
   - `tipo_prestazione_id` dalla regola
   - `emittente_fiscale_id`, `soggetto_id`, `priorita_id` dalla pratica sorgente
   - `stato_id` = BOZZA
   - `flusso_origine_id` = `p_flusso_id` (tracciabilita' cross-pratica)
7. **Ritorna** l'ID della nuova pratica.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `E_GENERICO` | `p_flusso_id` NULL o <= 0 |
| `E_GENERICO` | `p_regola_id` NULL o <= 0 |
| `E_GENERICO` | Flusso non trovato |
| `E_GENERICO` | Regola non trovata o non attiva |
| `E_GENERICO` | Stato BOZZA non configurato |

---

### Catena di invocazione

```
UPDATE flussi SET stato_id = <COMPLETATO>
  → trg_flussi_z90_generazione_upd (AFTER UPDATE OF stato_id)
    → trgfn_flussi_generazione()
      → fn_genera_pratica_da_flusso(flusso_id, regola_id)
        → INSERT INTO pratiche.pratiche (con flusso_origine_id)
```

---

### Note operative

* La funzione e' invocata automaticamente dal trigger `trgfn_flussi_generazione` per le regole con `auto = true`.
* Le regole con `auto = false` richiedono invocazione esplicita dal backend.
* Il filtro `esito_richiesto` nella regola permette di generare pratiche solo per esiti specifici del flusso.
* `flusso_origine_id` sulla pratica target consente la **tracciabilita' bidirezionale**: dalla pratica risalire al flusso che l'ha generata.
