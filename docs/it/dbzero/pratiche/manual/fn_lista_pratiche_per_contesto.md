## 📘 Documentazione Funzione – `pratiche.fn_lista_pratiche_per_contesto`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>
Funzioni collegate:
>
[pratiche.trgfn_pratiche_guard_contesto](trgfn_pratiche_guard_contesto.md)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_lista_pratiche_per_contesto`** e' la **lente canonica del contesto anagrafico** (decisione D1, analisi-pratiche-workflow-v2): il punto unico di verita' per ogni vista "pratiche di X" dell'applicazione.

Tre lenti **mutuamente alternative** sulla stessa lista:

1. **Pratiche del ruolo** (`p_soggetto_ruolo_id`) — es. tutte le pratiche del ruolo CLIENTE di un soggetto (drawer cliente, tab pratiche);
2. **Pratiche dell'istanza** (`p_istanza_utility_id`) — es. tutte le pratiche di un contatore (viste utenze);
3. **Pratiche interne** (`p_solo_interne = true`) — nessun contesto cliente (`soggetto_id IS NULL`).

Nessuna lente valorizzata = tutte le pratiche dell'emittente. Ogni vista applicativa deve passare da qui — **mai ricostruzioni ad hoc del filtro**.

---

### Firma della funzione

```sql
CREATE FUNCTION pratiche.fn_lista_pratiche_per_contesto(
  p_emittente_fiscale_id pratiche.pratiche.emittente_fiscale_id%TYPE,
  p_soggetto_ruolo_id    pratiche.pratiche.soggetto_ruolo_id%TYPE DEFAULT NULL,
  p_istanza_utility_id   pratiche.pratiche.istanza_utility_id%TYPE DEFAULT NULL,
  p_solo_interne         boolean DEFAULT false
)
RETURNS TABLE(...)
LANGUAGE plpgsql
STABLE
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_emittente_fiscale_id` | bigint | SI | Emittente fiscale (segregazione multi-company) |
| `p_soggetto_ruolo_id` | bigint | NO | Lente 1: pratiche del ruolo soggetto |
| `p_istanza_utility_id` | bigint | NO | Lente 2: pratiche dell'istanza utility |
| `p_solo_interne` | boolean | NO | Lente 3: solo pratiche senza contesto cliente |

---

### Colonne ritornate

| Colonna | Descrizione |
|---------|-------------|
| `pratica_id`, `codice`, `descrizione` | Identificazione pratica |
| `contesto` | **Bucket canonico calcolato**: `RUOLO` / `ISTANZA` / `SOGGETTO` (solo soggetto, senza ruolo ne' istanza) / `INTERNA` |
| `tipo_prestazione_codice`, `stato_codice`, `priorita_codice` | Decodifiche |
| `soggetto_id`, `soggetto_ragione_sociale`, `soggetto_ruolo_id`, `istanza_utility_id` | Contesto anagrafico |
| `risorsa_umana_id`, `unita_organizzativa_id` | Assegnazione |
| `data_apertura`, `data_scadenza` | Date di lavoro |

Ordinamento: priorita' (`sequenza` DESC) → scadenza (NULLS LAST) → id.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `E_PARAMETRO_INVALIDO` | `p_emittente_fiscale_id` NULL o <= 0 |
| `PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI` (484) | Piu' di una lente valorizzata nella stessa chiamata |

---

### Esempi di utilizzo

```sql
-- Pratiche del ruolo cliente 42 (drawer soggetto)
SELECT * FROM pratiche.fn_lista_pratiche_per_contesto(1, p_soggetto_ruolo_id := 42);

-- Pratiche dell'istanza utility 7 (vista utenze)
SELECT * FROM pratiche.fn_lista_pratiche_per_contesto(1, p_istanza_utility_id := 7);

-- Pratiche interne (inventario, attivita' senza cliente)
SELECT * FROM pratiche.fn_lista_pratiche_per_contesto(1, p_solo_interne := true);

-- Dashboard: tutte, raggruppabili per bucket "contesto"
SELECT contesto, count(*) FROM pratiche.fn_lista_pratiche_per_contesto(1) GROUP BY contesto;
```

---

### Note operative

* Indici di supporto (via `dbops.fk_index_policy`, parziali su NOT NULL): `ix_pratiche_soggetto_ruolo_id`, `ix_pratiche_istanza_utility_id`.
* La coda lavoro (`fn_coda_lavoro_operatore`) **non** e' contesto-aware per scelta di modello: la coda e' per-operatore, il contesto e' per-cliente.
* La generazione cross-pratica propaga `soggetto_ruolo_id`/`istanza_utility_id` alla figlia (fix-4, `fn_genera_pratica_da_flusso`): le pratiche generate ricadono nelle lenti corrette.
* Test: `db/pgtap/pratiche/test-lista-pratiche-contesto.sql`.
