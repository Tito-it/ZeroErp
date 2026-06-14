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

La pratica generata eredita emittente, soggetto, **contesto** (`soggetto_ruolo_id`, `istanza_utility_id`) e priorita' dalla pratica sorgente, con il tipo_prestazione definito dalla regola di destinazione, e porta la **genealogia completa**: `pratica_padre_id` (la pratica sorgente) + `flusso_origine_id` (il flusso che l'ha generata).

La funzione e' **idempotente** (rev 2026-06-11): per la stessa coppia (flusso, tipo destinazione) esiste al massimo una figlia; le chiamate successive ritornano l'id esistente senza crearne altre.

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
3. **Recupera pratica sorgente**: copia `emittente_fiscale_id`, `soggetto_id`, `soggetto_ruolo_id`, `istanza_utility_id`, `priorita_id` (fix-4: senza la propagazione del contesto le figlie cadrebbero fuori dalle lenti D1).
4. **Recupera regola**: legge `tipo_prestazione_dest_id` e `template_flusso_dest_id` dalla regola (deve essere attiva).
5. **Idempotenza (fix-1)**: se esiste gia' una pratica con `flusso_origine_id = p_flusso_id` e `tipo_prestazione_id` di destinazione, **ritorna l'id esistente** (copre trigger auto, API `/genera/` e doppi eventi).
6. **Stato iniziale**: cerca lo stato con `codice_interno = 'APERTA'` in `config.stati_pratiche`. La figlia auto-generata e' un lavoro gia' avviato: nasce **operativa**, coerente con il modello "la pratica nasce APERTA" (`20260614-03`). La `data_apertura` viene valorizzata automaticamente dal trigger `trg_pratiche_m50_set_data_apertura_ins` all'INSERT.
7. **Crea pratica target**: INSERT in `pratiche.pratiche` con:
   - `tipo_prestazione_id` dalla regola
   - `emittente_fiscale_id`, `soggetto_id`, `soggetto_ruolo_id`, `istanza_utility_id`, `priorita_id` dalla sorgente
   - `stato_id` = APERTA
   - `pratica_padre_id` = pratica sorgente (fix-2)
   - `flusso_origine_id` = `p_flusso_id`
8. **Flusso iniziale (fix-3)**: se la regola dichiara `template_flusso_dest_id`, crea il primo flusso della figlia in `DA_ESEGUIRE` con la `sequenza` del template. Il template destinazione deve essere **senza prerequisiti** (la figlia nasce vuota): in caso contrario il guard prerequisiti fa fallire la generazione — fail-fast voluto, e' un errore di seed della regola.
9. **Ritorna** l'ID della pratica (nuova o esistente).

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `E_PARAMETRO_INVALIDO` | `p_flusso_id` o `p_regola_id` NULL o <= 0 |
| `E_VALORE_MANCANTE` | Flusso non trovato |
| `E_CODICE` | Regola non trovata o non attiva |
| `E_CODICE` | Stato APERTA (pratiche) o DA_ESEGUIRE (flussi) non configurato |

---

### Catena di invocazione

```
UPDATE flussi SET stato_id = <COMPLETATO>   -- solo alla TRANSIZIONE di stato
  → trg_flussi_z90_generazione_upd (AFTER UPDATE OF stato_id)
    → trgfn_flussi_generazione()
      → fn_genera_pratica_da_flusso(flusso_id, regola_id)   -- dedup interno
        → INSERT INTO pratiche.pratiche (pratica_padre_id + flusso_origine_id + contesto)
        → INSERT INTO pratiche.flussi (se template_flusso_dest_id)
```

---

### Note operative

* La funzione e' invocata automaticamente dal trigger `trgfn_flussi_generazione` per le regole con `auto = true`.
* Le regole con `auto = false` richiedono invocazione esplicita dal backend — anche in quel caso il dedup garantisce un solo figlio per (flusso, tipo destinazione).
* Cintura strutturale: indice UNIQUE parziale `uq_pratiche_flusso_origine_tipo` su `pratiche.pratiche(flusso_origine_id, tipo_prestazione_id)` — il doppio figlio e' impossibile anche per scritture fuori dal motore. Resta legittimo che un flusso generi pratiche di tipi **diversi** (regole multiple).
* `pratica_padre_id` + `flusso_origine_id` consentono la **tracciabilita' bidirezionale** completa: dalla figlia risalire a pratica e flusso che l'hanno generata.
* Test: `db/pgtap/pratiche/test-generazione-cross-pratica.sql`.
