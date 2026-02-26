# Brief Team DB — Funzioni rettifiche listino e lookup componenti utility

**Data:** 27-02-2026
**Riferimento:** gestione-commesse-v2.md §25.5 (FASE 4.5) e §25.2.2 (#9)
**Priorità:** alta (rettifiche = gap funzionale aperto, componenti = fan-out consumi)

---

## Funzionalità 1 — Rettifiche listino (§25.5)

### Problema

Quando un documento (es. preventivo `LIBERO`) cambia prezzo **dopo** il push su
`commesse_attivita`, il sistema imposta:

```
commesse_attivita.prezzo_da_riallineare = TRUE
```

Oggi questi flag si accumulano senza auto-correzione. Serve un ciclo di
riallineamento che consumi il flag e applichi la rettifica (§7.4, §23).

### Regole business

1. **Override manuale**: `prezzo_bloccato = TRUE` → la riga non viene mai
   riallineata automaticamente
2. **Documento `LIBERO`**: prezzo cambiato dopo push → `prezzo_da_riallineare = TRUE`
3. **Documento non più `LIBERO`** (confermato/convertito): modifica prezzo non
   altera la commessa consolidata
4. **Delta = 0**: skip senza errore (il prezzo è già corretto)

### Funzioni DB richieste

#### A) `vendite.fn_apply_rettifica`

**Scopo:** Applica una rettifica prezzo su una singola riga `commesse_attivita`.

**Parametri suggeriti:**

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_commessa_attivita_id` | BIGINT | Riga da rettificare |
| `p_nuovo_prezzo` | NUMERIC | Nuovo `prezzo_snapshot` (o in alternativa `p_delta_prezzo`) |
| `p_motivo` | VARCHAR | Causale (es. `RIALLINEAMENTO_LISTINO`, `RETTIFICA_MANUALE`) |
| `p_tipo` | VARCHAR | Canale: `AUTOMATICO` / `MANUALE` |

**Comportamento atteso:**

1. Verifica che la riga esista e non sia `prezzo_bloccato = TRUE`
   (se bloccata → raise errore o skip con flag)
2. Aggiorna `prezzo_snapshot` con il nuovo valore
3. Imposta `prezzo_da_riallineare = FALSE`
4. Logga l'evento su `commesse_attivita_log` con dettaglio:
   `{"tipo": "RETTIFICA", "prezzo_precedente": X, "prezzo_nuovo": Y, "motivo": "...", "canale": "AUTOMATICO"}`
5. Restituisce un record di conferma (id, prezzo_precedente, prezzo_nuovo, applicata: bool)

**Nota:** se il team preferisce un approccio con `p_delta_prezzo` anziche`
`p_nuovo_prezzo`, il backend si adatta. Importante e` che il prezzo finale sia
determinato nel DB.

#### B) `vendite.fn_list_righe_da_riallineare`

**Scopo:** Elenca le righe `commesse_attivita` con `prezzo_da_riallineare = TRUE`,
arricchite con il prezzo corretto attuale da listino.

**Parametri suggeriti:**

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_lotto_id` | BIGINT | Filtro opzionale su lotto_attivita |
| `p_utility_id` | BIGINT | Filtro opzionale |
| `p_billing_account_id` | BIGINT | Filtro opzionale |
| `p_competenza_mese` | DATE | Filtro opzionale |
| `p_limit` | INT | Paginazione (default 1000) |
| `p_offset` | INT | Paginazione (default 0) |

**Colonne output suggerite:**

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | BIGINT | commesse_attivita.id |
| `commessa_id` | BIGINT | |
| `segment_key` | VARCHAR | |
| `articolo_id` | UUID | |
| `competenza_mese` | DATE | |
| `prezzo_snapshot` | NUMERIC | Prezzo attuale sulla riga (da rettificare) |
| `prezzo_corretto` | NUMERIC | Prezzo corretto da listino alla data |
| `delta` | NUMERIC | `prezzo_corretto - prezzo_snapshot` |
| `prezzo_bloccato` | BOOLEAN | Per escludere dal riallineamento automatico |
| `sorgente_tipo_id` | BIGINT | Per capire la sorgente business originale |

**Note:**
- La risoluzione `prezzo_corretto` da listino e` la parte critica. Il backend
  non conosce la logica listino — deve arrivare dal DB
- Righe con `prezzo_bloccato = TRUE` dovrebbero essere incluse nell'output
  ma marcate, in modo che il backend possa segnalarle senza applicare rettifica

### Tabelle coinvolte

- `vendite.commesse_attivita` — riga da rettificare (`prezzo_snapshot`, `prezzo_da_riallineare`, `prezzo_bloccato`)
- `vendite.commesse_attivita_log` — audit trail rettifiche
- Tabelle listino (per risolvere `prezzo_corretto`) — gestione interna DB

### Come verrà usata dal backend

```
1. Service chiama fn_list_righe_da_riallineare(lotto_id=X)
2. Per ogni riga con delta != 0 e prezzo_bloccato = FALSE:
   → chiama fn_apply_rettifica(id, prezzo_corretto, 'RIALLINEAMENTO_LISTINO', 'AUTOMATICO')
3. Per righe con prezzo_bloccato = TRUE:
   → segnalazione via LottoSegnalazioniService (skip con log)
4. Per delta = 0:
   → skip (prezzo gia` corretto, reset solo il flag)
```

---

## Funzionalità 2 — Lookup componenti utility (§25.2.2 #9)

### Problema

`HandlerConsumi` riceve dal DB righe consumo aggregate (es. "100 kWh per utility X
nel mese Y"). Ogni riga deve essere espansa in N componenti fatturabili
(es. energia, rete, oneri di sistema), ognuno con il proprio articolo, quantita`
scalata e prezzo da listino.

Oggi `_fetch_componenti()` e` uno stub che ritorna lista vuota → la riga consumo
passa intera senza espansione.

### Struttura dati attesa dal backend

```python
@dataclass(frozen=True)
class ComponenteConsumabile:
    codice: str           # codice componente (es. "ENERGIA", "RETE")
    articolo_id: Any      # UUID articolo catalogo del componente
    quantita: Any         # quantita` scalata (coeff_qta * consumo_totale)
    prezzo: Any           # prezzo unitario da listino per il componente
    uom_id: int | None    # UOM del componente
```

### Funzione DB richiesta

#### `vendite.fn_list_componenti_consumo` (o nome equivalente)

**Scopo:** Data una istanza utility e un periodo, restituisce l'elenco dei
componenti fatturabili con quantita` scalata e prezzo da listino.

**Parametri suggeriti:**

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_istanza_utility_id` | BIGINT | Istanza utility del consumo |
| `p_consumo_totale` | NUMERIC | Quantita` totale da espandere |
| `p_competenza_mese` | DATE | Mese di competenza (per listino) |

**Colonne output suggerite:**

| Colonna | Tipo | Note |
|---------|------|------|
| `codice` | VARCHAR | Codice componente (es. "ENERGIA") |
| `articolo_id` | UUID | FK verso `catalogo.articoli` |
| `quantita` | NUMERIC | `p_consumo_totale * coeff_qta` |
| `prezzo` | NUMERIC | Prezzo unitario da listino alla data |
| `uom_id` | BIGINT | UOM del componente |

### Tabelle coinvolte

- `catalogo.articoli_componenti` — mapping prodotto → componenti (con `coeff_qta`, `valido_dal/al`)
- `catalogo.articoli` — per risolvere `articolo_id` del componente
- Tabelle listino — per risolvere prezzo alla data
- `config.istanze_utility` (o equivalente) — per risolvere l'articolo prodotto
  radice dell'utility

### Come verrà usata dal backend

```
1. HandlerConsumi._expand_rows(row) chiamato per ogni riga consumo
2. _fetch_componenti(row) chiama fn_list_componenti_consumo(
       row.istanza_utility_id, row.quantita, row.competenza_mese
   )
3. Per ogni componente restituito:
   → genera una riga PushableRow con segment_key = "CONS:<uid>:COMP:<codice>"
4. Se la funzione restituisce lista vuota:
   → la riga consumo passa intera (fallback attuale)
```

### Note

- La logica di risoluzione prezzo e di filtering componenti validi alla data
  resta nel DB (coerente con architettura DB-first)
- Il backend riceve dati gia` pronti e li mappa 1:1 su `ComponenteConsumabile`
- La tabella `catalogo.articoli_componenti` esiste gia` con `coeff_qta`,
  `valido_dal/al`, `obbligatorio`, `attivo`

---

## Riepilogo richieste

| # | Funzione | Schema | Dipendenze |
|---|----------|--------|------------|
| 1 | `fn_apply_rettifica` | vendite | commesse_attivita, commesse_attivita_log, listino |
| 2 | `fn_list_righe_da_riallineare` | vendite | commesse_attivita, listino (per prezzo_corretto) |
| 3 | `fn_list_componenti_consumo` | vendite | catalogo.articoli_componenti, listino, istanze_utility |

## Riferimenti

| File | Contenuto |
|------|-----------|
| `gestione-commesse-v2.md` §7.4 | Regole business riallineamento prezzo |
| `gestione-commesse-v2.md` §25.5 | Spec FASE 4.5 rettifiche (repository + service) |
| `gestione-commesse-v2.md` §25.2.2 #9 | Spec fan-out consumi 1→N |
| `commesse_source_handlers.py` L215-257 | Stub `_fetch_componenti`, dataclass `ComponenteConsumabile` |
| `docs/it/dbzero/vendite/tabelle/commesse_attivita.md` | Colonne `prezzo_da_riallineare`, `prezzo_bloccato` |
| `docs/it/dbzero/catalogo/tabelle/articoli_componenti.md` | Mapping prodotto → componenti |
| `docs/it/dbzero/vendite/funzioni/fn_list_consumi_da_pushare.md` | Note su espansione componenti |
