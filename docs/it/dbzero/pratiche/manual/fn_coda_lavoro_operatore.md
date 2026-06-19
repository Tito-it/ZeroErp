## 📘 Documentazione Funzione – `pratiche.fn_coda_lavoro_operatore`

> 👀 **Vedi anche**
>
> [pratiche.competenze_flussi](/dbzero/pratiche/manual/competenze_flussi)
> [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/manual/fn_prendi_in_carico_flusso)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---
### 🎯 Scopo Principale

Restituisce la coda di lavoro di un operatore in **quattro** livelli di priorita', mutuamente esclusivi. Ogni flusso appare in un solo livello (quello piu' alto applicabile).

> **Rev 2026-06-18** (brief-db-assegnazione-flusso): allineata alla policy reparto-first di `fn_prendi_in_carico_flusso`. Il livello REPARTO usa ora il reparto **anagrafico** (`risorse_umane.unita_organizzativa_id`), non piu' i reparti-da-competenza, ed e' limitato ai flussi senza skill-lock (caso B). Aggiunto il livello **LIBERO** (caso C) per non lasciare invisibili i flussi liberi.

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

Tutti i livelli "prendibili" (COMPETENZA/REPARTO/LIBERO) richiedono il flusso **non assegnato** e in stato **DA_ESEGUIRE**. La mappatura ai casi della policy (vedi `fn_prendi_in_carico_flusso`) e' diretta.

| Livello | Criterio | Caso policy |
|---------|----------|-------------|
| **ASSEGNATO** | `flussi.risorsa_umana_id = p_risorsa_umana_id` | — (assegnato direttamente; DA_ESEGUIRE o IN_CORSO) |
| **COMPETENZA** | non assegnato + DA_ESEGUIRE + operatore **competente** per il template | A / D |
| **REPARTO** | non assegnato + DA_ESEGUIRE + `flussi.unita_organizzativa_id` = reparto **anagrafico** dell'operatore + **nessuno skill-lock** attivo sul template | B |
| **LIBERO** | non assegnato + DA_ESEGUIRE + niente reparto + niente skill-lock + **la pratica e' assegnata all'operatore** (`pratiche.risorsa_umana_id`) | C |

La priorita' tra livelli e' gestita da un `CASE WHEN`: un flusso assegnato appare sempre come ASSEGNATO; uno skill-locked appare come COMPETENZA solo ai competenti (mai come REPARTO/LIBERO); un flusso senza skill-lock cade in REPARTO (se ha reparto) o LIBERO.

> **Caso C → LIBERO all'operatore della pratica** (decisione 2026-06-18): un flusso libero non viene mostrato a tutti (rumore), ma a chi e' assegnata la pratica padre, cosi' resta scopribile senza invadere le code altrui.

<!-- -->

> **`competenze_flussi.unita_organizzativa_id` non e' piu' usata** da questa funzione: il reparto e' quello anagrafico dell'operatore, la competenza e' su `(template, operatore)`.

---

### Ordinamento

1. Livello (ASSEGNATO → COMPETENZA → REPARTO → LIBERO)
2. Priorita' pratica (DESC)
3. Data scadenza (NULLS LAST)
4. Sequenza flusso

---

### Logica di funzionamento

1. **CTE `flussi_base`**: singola scansione di tutti i flussi pendenti (DA_ESEGUIRE o IN_CORSO) dell'emittente, **escluse le pratiche terminali**. Una pratica e' terminale quando non ha alcuna transizione di stato in uscita attiva in `config.transizioni_stati_pratiche` (oggi `CHIUSA`/`ANNULLATA`): i suoi flussi sono congelati dal guard `trgfn_flussi_guard_pratica_terminale` e non sono lavoro da fare, quindi non compaiono in coda (stessa definizione di "terminale" del guard, nessun id/codice hardcodato). Porta anche `pratiche.risorsa_umana_id` (per il livello LIBERO).
2. **CTE `operatore`**: risolve il reparto **anagrafico** dell'operatore (`risorse_umane.unita_organizzativa_id`), usato dal livello REPARTO.
3. **CTE `competenze_op`**: i template per cui l'operatore ha competenza attiva (livello COMPETENZA).
4. **CTE `classificati`**: ogni flusso viene classificato nel livello piu' alto applicabile via `CASE WHEN` (ASSEGNATO → COMPETENZA → REPARTO → LIBERO); lo skill-lock per-template e' valutato con `EXISTS(competenze_flussi attiva per il template)`.
5. **SELECT finale**: JOIN display fields (pratica, priorita', tipo prestazione, template) una sola volta sul risultato classificato. Filtra `WHERE livello IS NOT NULL` (esclude flussi non rilevanti per l'operatore).

---

### Esempi di utilizzo

```sql
-- Coda completa dell'operatore 42 per emittente 1
SELECT * FROM pratiche.fn_coda_lavoro_operatore(42, 1);

-- Solo flussi da prendere in carico (per skill)
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
* Il campo `risorsa_assegnata` e' ora sempre `NULL`: i livelli mostrati sono auto-assegnato (ASSEGNATO) o non assegnati (COMPETENZA/REPARTO/LIBERO), quindi non c'e' un "altro" assegnatario da mostrare.
* Allineata a `fn_prendi_in_carico_flusso`: cio' che appare come COMPETENZA/REPARTO/LIBERO e' effettivamente prendibile dall'operatore secondo la stessa policy.

---

{% include-markdown "signature-core.md" %}
