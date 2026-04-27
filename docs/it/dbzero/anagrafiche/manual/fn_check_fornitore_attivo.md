## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_fornitore_attivo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)  
> • [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore)  
>
> **Approfondimento funzioni:**
>
> • [anagrafiche.fn_guard_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_guard_fornitore_attivo)  
>
---

### 🎯 Scopo Principale

(latest review 22-04-2026)
La funzione **`anagrafiche.fn_check_fornitore_attivo()`** verifica in modo
puramente booleano se un fornitore puo' essere usato nei flussi operativi del
ciclo passivo, in particolare per ordini e DDT.

Ritorna `true` solo quando il fornitore esiste, e' attivo e il suo stato
operativo non blocca gli ordini.

---

### Contesto

`fn_check_fornitore_attivo` e' la variante **check** della coppia
guard/check dedicata allo stato operativo dei fornitori:

* `fn_check_fornitore_attivo` restituisce un boolean e non solleva eccezioni.
* `fn_guard_fornitore_attivo` applica le stesse regole in modalita'
  fail-fast, usando `script.fn_log_and_raise_error`.

Questa separazione permette di usare il check in query, viste, filtri,
validazioni preventive o flussi backend dove serve conoscere l'esito senza
interrompere immediatamente la transazione.

---

### Input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_fornitore_id` | `anagrafiche.fornitori.id%TYPE` | ID del fornitore da verificare. |

---

### Output

| Tipo | Descrizione |
|------|-------------|
| `boolean` | `true` se il fornitore e' utilizzabile per ordini/DDT; `false` in tutti gli altri casi. |

La funzione e' **fail-closed**: se il parametro e' `NULL`, se il fornitore non
esiste, se e' inattivo o se lo stato blocca ordini, il risultato e' `false`.

---

### Regole

La funzione ritorna `true` solo se tutte le condizioni sono soddisfatte:

* esiste una riga in `anagrafiche.fornitori` con `id = p_fornitore_id`;
* `anagrafiche.fornitori.attivo = true`;
* il fornitore ha uno stato collegato in `config.stati_fornitore`;
* `config.stati_fornitore.blocca_ordini = false`.

Non normalizza dati, non aggiorna record e non registra errori applicativi.

---

### Semantica dei casi principali

| Caso | Risultato |
|------|-----------|
| Fornitore attivo con stato che non blocca ordini | `true` |
| `p_fornitore_id` nullo | `false` |
| Fornitore inesistente | `false` |
| Fornitore con `attivo = false` | `false` |
| Stato fornitore mancante/non collegato | `false` |
| Stato fornitore con `blocca_ordini = true` | `false` |

---

### Dipendenze DB

| Oggetto | Ruolo |
|---------|-------|
| `anagrafiche.fornitori` | Sorgente del flag `attivo` e dello `stato_fornitore_id`. |
| `config.stati_fornitore` | Sorgente del flag operativo `blocca_ordini`. |

---

### Esempi d'uso

```sql
-- Verifica puntuale
SELECT anagrafiche.fn_check_fornitore_attivo(123);

-- Uso in filtro applicativo/query
SELECT f.id, f.codice
FROM anagrafiche.fornitori f
WHERE anagrafiche.fn_check_fornitore_attivo(f.id);
```

---

### Note operative

* La funzione e' `STABLE`: legge dati ma non li modifica.
* E' adatta a controlli preventivi e filtri, non a blocchi transazionali con
  messaggio di errore dettagliato.
* Per imporre la regola in una procedura o in un trigger, usare la guard
  fail-fast `anagrafiche.fn_guard_fornitore_attivo`.

---

{% include-markdown "signature-core.md" %}
