## 📘 Documentazione Funzione – `pratiche.fn_coda_lavoro_operatore`

> 👀 **Vedi anche**
>
> [pratiche.competenze_flussi](/dbzero/pratiche/manual/competenze_flussi)
> [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/manual/fn_prendi_in_carico_flusso)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---
### 🎯 Scopo Principale

Restituisce la coda di lavoro di un operatore in tre livelli di priorita', mutuamente esclusivi. Ogni flusso appare in un solo livello (quello piu' alto applicabile).

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_coda_lavoro_operatore(
    p_risorsa_umana_id     anagrafiche.risorse_umane.id%TYPE,
    p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE
)
RETURNS TABLE(
    livello, flusso_id, pratica_id, pratica_codice, pratica_descrizione,
    priorita_codice, tipo_prestazione_codice, template_flusso_codice,
    template_flusso_desc, stato_flusso_codice, sequenza,
    data_scadenza, risorsa_assegnata
)
LANGUAGE sql STABLE
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_risorsa_umana_id` | bigint | SI | ID dell'operatore per cui costruire la coda |
| `p_emittente_fiscale_id` | bigint | SI | Filtro emittente fiscale (segregazione multi-company) |

---

### Livelli della coda (mutuamente esclusivi)

| Livello | Criterio | Descrizione |
|---------|----------|-------------|
| **ASSEGNATO** | `flussi.risorsa_umana_id = p_risorsa_umana_id` | Flussi DA_ESEGUIRE o IN_CORSO assegnati direttamente all'operatore |
| **COMPETENZA** | `flussi.risorsa_umana_id IS NULL` + stato DA_ESEGUIRE + competenza attiva | Flussi non assegnati che l'operatore puo' prendere in carico |
| **REPARTO** | `flussi.unita_organizzativa_id` nei reparti dell'operatore | Flussi del reparto per visibilita' (esclusi quelli gia' nei livelli precedenti) |

La priorita' tra livelli e' gestita da un `CASE WHEN`: un flusso assegnato all'operatore appare sempre come ASSEGNATO, mai come COMPETENZA o REPARTO.

---

### Ordinamento

1. Livello (ASSEGNATO → COMPETENZA → REPARTO)
2. Priorita' pratica (DESC)
3. Data scadenza (NULLS LAST)
4. Sequenza flusso

---

### Logica di funzionamento

1. **CTE `flussi_base`**: singola scansione di tutti i flussi pendenti (DA_ESEGUIRE o IN_CORSO) dell'emittente, **escluse le pratiche terminali**. Una pratica e' terminale quando non ha alcuna transizione di stato in uscita attiva in `config.transizioni_stati_pratiche` (oggi `CHIUSA`/`ANNULLATA`): i suoi flussi sono congelati dal guard `trgfn_flussi_guard_pratica_terminale` e non sono lavoro da fare, quindi non compaiono in coda (stessa definizione di "terminale" del guard, nessun id/codice hardcodato).
2. **CTE `classificati`**: ogni flusso viene classificato nel livello piu' alto applicabile via `CASE WHEN`.
3. **SELECT finale**: JOIN display fields (pratica, priorita', tipo prestazione, template, soggetto operatore) una sola volta sul risultato classificato. Filtra `WHERE livello IS NOT NULL` (esclude flussi non rilevanti per l'operatore).

---

### Esempi di utilizzo

```sql
-- Coda completa dell'operatore 42 per emittente 1
SELECT * FROM pratiche.fn_coda_lavoro_operatore(42, 1);

-- Solo flussi da prendere in carico
SELECT * FROM pratiche.fn_coda_lavoro_operatore(42, 1)
WHERE livello = 'COMPETENZA';

-- Conteggio per livello
SELECT livello, count(*)
FROM pratiche.fn_coda_lavoro_operatore(42, 1)
GROUP BY livello;
```

---

### Note operative

* Funzione `STABLE`: non modifica dati.
* Per volumi elevati (migliaia di flussi pendenti), valutare un indice parziale su `pratiche.flussi (stato_id)` per gli stati DA_ESEGUIRE/IN_CORSO.
* Il campo `risorsa_assegnata` e' popolato solo per il livello REPARTO (mostra chi ha il flusso); per ASSEGNATO e COMPETENZA e' NULL.

---

{% include-markdown "signature-core.md" %}
