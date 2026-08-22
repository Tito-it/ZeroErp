## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_ruoli_conti_bancari`

> 👀 **Vedi anche**
>
**Appronfondimento Tabelle correlate**   
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)    
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> • [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari)    
> • [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari)    
> • [pagamenti.sepa_mandati](/dbzero/pagamenti/tabelle/sepa_mandati)    
>
**Artefatti di selezione**   
> • [anagrafiche.vw_conti_bancari_per_ruolo](/dbzero/anagrafiche/views/vw_conti_bancari_per_ruolo)    
> • [script.fn_get_conto_bancario_predefinito](/dbzero/script/funzioni/fn_get_conto_bancario_predefinito)   
>
**Approfondimento Trigger/Funzioni generiche**   
> • [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)    
> • [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)    
> • [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)   
 
---
### 🎯 Scopo Principale
(latest review 25-03-26)
`anagrafiche.soggetti_ruoli_conti_bancari` gestisce l’**associazione tra un Ruolo** di un soggetto (CLIENTE, FORNITORE, GESTORE, …) e uno o più **conti bancari (IBAN)**, distinguendo l’**uso** del conto: `INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO`.

Supporta la **differenziazione per istanza di servizio** tramite `istanza_utility_id` (opzionale, `bigint`, FK → `anagrafiche.istanze_utilities`): due istanze GAS dello stesso soggetto possono avere conti INCASSO diversi.

La cascata di selezione è a **3 livelli** (istanza → ruolo generico → soggetto), implementata dalla vista `vw_conti_bancari_per_ruolo` (flat) e dalla funzione `fn_get_conto_bancario_predefinito` (cascata 7 livelli con fallback uso GENERICO).

---

### Relazioni

| Tipo       | Tabella ↔ Campo                                        | Descrizione                                          |
| ---------- | ------------------------------------------------------ | ---------------------------------------------------- |
| FK →       | `anagrafiche.soggetti_ruoli(id)` ← `soggetto_ruolo_id` | Ruolo del soggetto (es. Cliente, Fornitore)          |
| FK →       | `anagrafiche.conti_bancari(id)` ← `conto_bancario_id`  | Conto bancario registrato nell’anagrafe unica        |
| (usata da) | `anagrafiche.vw_conti_bancari_per_ruolo`               | Selezione con priorità RUOLO → fallback SOGGETTO     |
| (usata da) | `pagamenti.sepa_mandati`                               | Collega il mandato al **conto di ruolo** selezionato |

> **Nota:** cancellazioni **NO ACTION** per evitare orfani; disattiva un legame impostando `valido_al` o `bloccato=true`.

---

### Struttura logica (campi chiave)

* `soggetto_ruolo_id` (**FK** obbligatoria)
* `conto_bancario_id` (**FK** obbligatoria)
* `istanza_utility_id` (**FK** opzionale, `bigint` → `anagrafiche.istanze_utilities`) — se valorizzato, il legame è specifico per quell’istanza di servizio; se NULL, è generico del ruolo
* `uso VARCHAR(16)` → `INCASSO | PAGAMENTO | RIMBORSO | GENERICO` (default `GENERICO`)
* `predefinito BOOLEAN` → predefinito per l’uso **in questo ruolo/istanza**
* `valido_dal DATE`, `valido_al DATE` → finestra di validità del legame
* `intestazione_dichiarata VARCHAR(140)` → opzionale (se diversa da intestatario del conto)
* Flag operativi: `verificato BOOLEAN`, `bloccato BOOLEAN`
* Estensioni: `meta JSONB`
* Audit: `tx_id UUID`, `storicizza BOOLEAN`, `data_*`, `user_*`

---

### 🚦 Vincoli & Regole

* **Unicità combinazione** (4 partial unique index per gestire NULL su `istanza_utility_id`):
  - `uq_src_bancari_ruolo_istanza_conto_uso (soggetto_ruolo_id, istanza_utility_id, conto_bancario_id, uso) WHERE istanza_utility_id IS NOT NULL`
  - `uq_src_bancari_ruolo_conto_uso_no_istanza (soggetto_ruolo_id, conto_bancario_id, uso) WHERE istanza_utility_id IS NULL`
* **Predefinito per uso/ruolo/istanza** (2 partial unique index):
  - `uq_src_bancari_predefinito_istanza (soggetto_ruolo_id, istanza_utility_id, uso) WHERE predefinito=true AND istanza_utility_id IS NOT NULL`
  - `uq_src_bancari_predefinito_no_istanza (soggetto_ruolo_id, uso) WHERE predefinito=true AND istanza_utility_id IS NULL`
* 🔴 **Un conto di INCASSO appartiene a UN SOLO soggetto** — vincolo di
  esclusione `ex_src_bancari_conto_incasso_un_solo_soggetto`
  `EXCLUDE USING gist (conto_bancario_id WITH =, soggetto_ruolo_id WITH <>) WHERE (uso = 'INCASSO')`
  *(dal 2026-08-22)*. ⭐ **E' il pezzo che regge il perimetro degli incassi**: la
  catena *azienda → conto* era già garantita, ma serviva **al contrario** — «questi
  soldi su questo conto, di chi sono?» — e in quel verso non c'era niente. La
  regola di dominio è vera nel mondo (due partite IVA, due conti correnti) ma il
  database non la sapeva: finché quel legame serviva a stampare un IBAN in fattura
  l'ambiguità era un fastidio, appoggiandoci la sicurezza diventa un **varco
  silenzioso** — due aziende sullo stesso conto, ciascuna vede i soldi dell'altra,
  e nessun errore da nessuna parte.
  > ⚠️ **Esclusione e non indice unico** su `(conto_bancario_id) WHERE uso = 'INCASSO'`:
  > quello vieterebbe anche lo stesso conto sullo **stesso** soggetto una volta a
  > livello di ruolo e una per istanza utility — cioè proprio la configurazione che
  > i due indici `uq_src_bancari_ruolo_*_conto_uso` dichiarano legittima. La regola
  > nomina **due** colonne: stesso conto **e** soggetto diverso.
  >
  > ⛔ Il periodo di validità **non** entra nel vincolo di proposito: in Italia un
  > IBAN non passa di mano, e ammettere la sovrapposizione nel tempo costringerebbe
  > il perimetro a risolvere il conto **alla data** — cioè a rispondere in modo
  > diverso ieri e oggi alla domanda «di chi sono questi soldi?».
  >
  > ⭐ **Regola generale, oltre questo caso:** una verità di dominio su cui si
  > appoggia un perimetro di sicurezza deve diventare un **vincolo**, non restare
  > un'assunzione. Il costo di scriverla è un indice; il costo di non scriverla non
  > si vede finché non è successo.
* **Chi ci si appoggia**: `pagamenti.enti_incasso.soggetto_ruolo_conto_bancario_id`
  punta a una riga di questa tabella, e un guard pretende che il suo `uso` sia
  `INCASSO` — è lì che l'unicità qui sopra diventa il perimetro degli incassi.
* **Validità temporale**: `CHECK (valido_al IS NULL OR valido_dal IS NULL OR valido_al >= valido_dal)`.
* **Valori ammessi `uso`**: `CHECK (uso IN ('INCASSO','PAGAMENTO','RIMBORSO','GENERICO'))`.
* **Guard‑rail conto attivo**: trigger impedisce associazioni a `conti_bancari.attivo=false`.


---

### Query tipiche

**1) Predefinito d’incasso per un ruolo (oggi valido)**

```sql
SELECT srcb.*
FROM anagrafiche.soggetti_ruoli_conti_bancari srcb
JOIN anagrafiche.conti_bancari cb ON cb.id = srcb.conto_bancario_id
WHERE srcb.soggetto_ruolo_id = :soggetto_ruolo_id
  AND srcb.uso = 'INCASSO'
  AND srcb.predefinito = true
  AND (srcb.valido_dal IS NULL OR srcb.valido_dal <= CURRENT_DATE)
  AND (srcb.valido_al  IS NULL OR srcb.valido_al  >= CURRENT_DATE)
  AND srcb.bloccato = false
  AND cb.attivo = true
LIMIT 1;
```

**2) Tutti i conti attivi del ruolo (per auditing)**

```sql
SELECT srcb.uso, srcb.predefinito, cb.iban, cb.verificato
FROM anagrafiche.soggetti_ruoli_conti_bancari srcb
JOIN anagrafiche.conti_bancari cb ON cb.id = srcb.conto_bancario_id
WHERE srcb.soggetto_ruolo_id = :soggetto_ruolo_id
  AND (srcb.valido_al IS NULL OR srcb.valido_al >= CURRENT_DATE)
ORDER BY srcb.uso, srcb.predefinito DESC, srcb.data_update DESC;
```

---

### Cascata di selezione (3 livelli + fallback uso)

La funzione `fn_get_conto_bancario_predefinito(ruolo, uso, istanza_utility_id)` implementa una cascata a **7 livelli**:

1. Ruolo + istanza specifica + uso richiesto
2. Ruolo + istanza NULL (generico) + uso richiesto
3. Soggetto + uso richiesto
4. Ruolo + istanza specifica + uso GENERICO
5. Ruolo + istanza NULL + uso GENERICO
6. Soggetto + uso GENERICO
7. NULL (nessun conto trovato)

La vista `vw_conti_bancari_per_ruolo` e **flat** (espone tutte le candidate senza DISTINCT ON). La selezione singola e nella funzione.

---

### Best practice

* Definisci **un solo predefinito per uso** per ciascuna combinazione ruolo/istanza (vincolo unico parziale).
* Usa `valido_dal/valido_al` per cambi programmati; **non cancellare**, storicizza.
* Per **ruoli sensibili** (es. Gestore con CI SEPA), documenta nel `meta` eventuali vincoli di utilizzo.
* Limita la visibilità degli IBAN via servizi/vista: qui lavora per **ID conto**.
* Per conti generici del ruolo (validi per tutte le istanze), lascia `istanza_utility_id = NULL`.

---

### Diagramma ER relazioni (focus ruolo)

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    soggetti_ruoli ||--o{ soggetti_ruoli_conti_bancari : possiede
    conti_bancari ||--o{ soggetti_ruoli_conti_bancari : collega
    istanze_utilities ||--o{ soggetti_ruoli_conti_bancari : scoped_by
    soggetti_ruoli_conti_bancari ||--o{ sepa_mandati : usa
    soggetti_ruoli ||..o{ vw_conti_bancari_per_ruolo : selezione
```

---

{% include-markdown "signature-core.md" %}

---
