## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_registro_id`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_anno_registro](/dbzero/vendite/funzioni/fn_get_anno_registro)  
> • [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)  
>
### 🎯 Scopo Principale
(latest review 27-01-2026)
La funzione **`vendite.fn_get_registro_id`** risolve il registro di fatturazione
in base al mapping **tipo documento → registro**, considerando utility/emittente se presenti.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_tipo_doc_fiscale_id` | `config.tipi_doc_fiscale.id%TYPE` | Tipo documento fiscale. |
| `p_utility_id` | `config.utilities.id%TYPE` | Utility di riferimento (opzionale). |
| `p_emittente_soggetto_ruolo_id` | `anagrafiche.soggetti_ruoli.id%TYPE` | Emittente fiscale (opzionale). |

---

### Regola applicata

1. tipo_doc + utility + emittente
2. tipo_doc + utility
3. tipo_doc + emittente
4. tipo_doc (generico)
5. Se assente → errore bloccante.

---

### Note operative

* Funzione pensata per la numerazione e per i processi che richiedono il registro contabile.
* Le varianti sono gestite tramite registri con utility/emittente valorizzati.

---


---

### 🔄 rev 2026-08-18 — la natura entra, la SERIE esce

Brief: `brief-design-note-credito-resi` (slice **N2**).

La firma e il **tipo di ritorno** sono cambiati (`DROP` + `CREATE`: un
`CREATE OR REPLACE` non cambia un tipo di ritorno):

```text
prima    fn_get_registro_id(tipo_doc, utility, emittente)          → bigint
ora      fn_get_registro_id(tipo_doc, NATURA, utility, emittente)  → TABLE(registro_id, serie)
```

La natura entra in **seconda posizione**, accanto al tipo documento, perché i due
sono la coppia che identifica la riga di mapping; utility ed emittente restano il
raffinamento.

#### ⚠️ La natura è un filtro ESATTO, non un livello di fallback

Il fallback a quattro livelli (utility+emittente → utility → emittente → nessuno
dei due) è la gerarchia di specificità del **registro** e resta identico. La
natura no: se il mapping per `(tipo_doc, NOTA_CREDITO)` non esiste, la risposta è
`E_CONFIG_MANCANTE`. Ripiegare sulla fattura emetterebbe **una nota di credito
nel registro delle fatture**, in silenzio.

#### Perché restituisce anche la serie

Perché è il mapping a saperlo, e perché `vendite.fatture.serie` **non era mai
stata scritta dalla pipeline**: restava `NULL` e la numerazione cadeva sul
`serie_default` del registro. Va benissimo finché esiste una serie sola per
registro; smette di funzionare nel momento in cui due nature devono numerare
separate **dentro** lo stesso registro.

⚠️ La serie esce **grezza** (l'override del mapping), non `COALESCE`-ata sul
default del registro: scrivere il default dentro `fatture.serie`, dove oggi c'è
`NULL`, cambierebbe il valore di una colonna **su documenti già emessi**.

#### ⭐ E così «registro proprio o serie dedicata?» diventa una riga di seed

| Se il seed dice… | Effetto |
|---|---|
| stesso `registro_id`, `serie = 'NC'` | le note di credito numerano in una serie a parte **dentro** il registro vendite |
| `registro_id` diverso | **sezionale proprio**, progressivo e `reset_policy` indipendenti |

Entrambe funzionano **senza una riga di codice diversa**. È la forma che il
progetto usa per le scelte che appartengono all'azienda e non allo sviluppatore.
⭐ La scelta è stata il **sezionale proprio** (D-NC-3b), e lo dice il seed, non
questa funzione.

---

{% include-markdown "signature-core.md" %}
