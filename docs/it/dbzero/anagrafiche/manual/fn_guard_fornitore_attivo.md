## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_fornitore_attivo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)  
> • [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore)  
>
> **Approfondimento funzioni:**
>
> • [anagrafiche.fn_check_fornitore_attivo](/dbzero/anagrafiche/manual/fn_check_fornitore_attivo)  
> • [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)  
>
---

### 🎯 Scopo Principale

(latest review 22-04-2026)
La funzione **`anagrafiche.fn_guard_fornitore_attivo()`** applica una verifica
fail-fast sul fornitore prima di consentirne l'uso nei flussi operativi del
ciclo passivo, in particolare ordini e DDT.

La guard interrompe l'operazione quando il fornitore non esiste, non e' attivo
oppure si trova in uno stato operativo che blocca gli ordini.

---

### Contesto

La funzione fa parte della coppia guard/check dedicata alla disponibilita'
operativa dei fornitori:

* `fn_guard_fornitore_attivo` e' la variante **imperativa**: solleva errore e
  registra il dettaglio applicativo tramite `script.fn_log_and_raise_error`.
* `fn_check_fornitore_attivo` e' la variante **boolean**: ritorna `true` o
  `false` senza sollevare eccezioni.

Usare la guard quando la regola deve bloccare una scrittura o un passaggio di
stato. Usare il check quando serve un filtro o una validazione preventiva non
bloccante.

---

### Input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_fornitore_id` | `anagrafiche.fornitori.id%TYPE` | ID del fornitore da validare. |

---

### Output

La funzione ritorna `void`.

Se tutte le verifiche passano, termina senza effetti collaterali sui dati. In
caso contrario solleva un errore applicativo tramite `script.fn_log_and_raise_error`.

---

### Regole

La funzione applica le seguenti regole:

* `p_fornitore_id` deve essere valorizzato e maggiore di zero.
* Il fornitore deve esistere in `anagrafiche.fornitori`.
* Il campo `anagrafiche.fornitori.attivo` deve essere `true`.
* Lo stato collegato in `config.stati_fornitore` non deve avere
  `blocca_ordini = true`.

La funzione non modifica il fornitore e non normalizza dati: e' solo una
barriera di validazione.

---

### Errori applicativi

| Codice | Quando viene sollevato |
|--------|------------------------|
| `E_FORNITORE_ID_INVALIDO` | `p_fornitore_id` e' `NULL` oppure `<= 0`. |
| `E_FORNITORE_NON_TROVATO` | Nessun fornitore esiste con l'ID indicato. |
| `E_FORNITORE_NON_ATTIVO` | Il fornitore esiste ma `attivo` non e' `true`. |
| `E_FORNITORE_BLOCCATO` | Lo stato del fornitore ha `blocca_ordini = true`. |

---

### Dipendenze DB

| Oggetto | Ruolo |
|---------|-------|
| `anagrafiche.fornitori` | Sorgente del fornitore, del flag `attivo` e dello `stato_fornitore_id`. |
| `config.stati_fornitore` | Sorgente del flag operativo `blocca_ordini` e della descrizione stato. |
| `script.fn_log_and_raise_error` | Gestione standard di log ed errore applicativo. |

---

### Esempio d'uso

```sql
-- Blocca la transazione se il fornitore non puo' essere usato
SELECT anagrafiche.fn_guard_fornitore_attivo(123);
```

Uso tipico in una procedura o trigger del ciclo passivo:

```sql
PERFORM anagrafiche.fn_guard_fornitore_attivo(NEW.fornitore_id);
```

---

### Note operative

* La funzione e' `STABLE`: legge dati ma non li modifica.
* E' adatta a trigger, procedure e comandi transazionali che devono fallire in
  modo esplicito.
* Per liste, filtri o preview UI usare invece
  `anagrafiche.fn_check_fornitore_attivo`.

---

{% include-markdown "signature-core.md" %}
