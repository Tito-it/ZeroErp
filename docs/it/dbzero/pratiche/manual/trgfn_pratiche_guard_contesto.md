## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_guard_contesto`

> 👀 **Vedi anche**
>
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)

---
### 🎯 Scopo Principale

Guard: valida la coerenza del contesto anagrafico sulla pratica nel **modello a
due rami**, pendenti indipendentemente dal soggetto:

```text
soggetto ──→ soggetto_ruolo      (pratiche su ruoli: cliente attivo, fornitore, …)
        └──→ istanza_utility     (pratiche pre-contrattuali: nessun ruolo richiesto)
```

Regole:

- Un ruolo non può esistere senza soggetto
- Un'istanza non può esistere senza soggetto
- Il ruolo deve appartenere al soggetto indicato
- L'istanza deve appartenere al soggetto indicato

**Istanza senza ruolo è ammessa** (prospect puro): nel dominio utilities
l'istanza nasce *prima* del contratto, in fase pre-contrattuale il soggetto non
ha ancora il ruolo CLIENTE — che arriva a valle, con la nascita del billing
account (`ClienteService` / `fn_get_or_create_soggetto_ruolo`). Imporre il ruolo
all'aggancio dell'istanza sarebbe un ruolo CL prematuro.

Tutti i campi sono opzionali: una pratica interna ha tutti NULL.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_contesto()
RETURNS trigger LANGUAGE plpgsql
```

---

### Regole di validazione

| # | Regola | Condizione errore |
|---|--------|-------------------|
| 1 | Ruolo richiede soggetto | `soggetto_ruolo_id NOT NULL AND soggetto_id IS NULL` |
| 2 | Istanza richiede soggetto | `istanza_utility_id NOT NULL AND soggetto_id IS NULL` |
| 3 | Ruolo deve appartenere al soggetto | `soggetti_ruoli.soggetto_id <> pratiche.soggetto_id` |
| 4 | Istanza deve appartenere al soggetto | `istanze_utilities.soggetto_id <> pratiche.soggetto_id` |

> **Nota** (dalla `20260611-01`): la vecchia regola «istanza richiede ruolo» è
> stata **rimossa**. L'istanza pende direttamente dal soggetto, non dal ruolo
> (`istanze_utilities.soggetto_id` è FK NOT NULL al soggetto). La regola 2
> (istanza → soggetto) è formalmente coperta anche dalla regola 4 quando
> `soggetto_id IS NULL`, ma è esplicitata per restituire un messaggio chiaro.

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_pratiche_a10_guard_contesto_ins_upd` | BEFORE | INSERT, UPDATE OF soggetto_id, soggetto_ruolo_id, istanza_utility_id | `pratiche.pratiche` |

---

### Messaggi errore

| Codice | ID | Messaggio |
|--------|----|-----------|
| `PRATICHE_RUOLO_SENZA_SOGGETTO` | 305 | soggetto_ruolo_id richiede soggetto_id |
| `PRATICHE_ISTANZA_SENZA_SOGGETTO` | 308 | istanza_utility_id richiede soggetto_id |
| `PRATICHE_RUOLO_NON_COERENTE` | 306 | Il ruolo %s non appartiene al soggetto %s |
| `PRATICHE_ISTANZA_NON_COERENTE` | 307 | L'istanza %s non appartiene al soggetto %s |

> `PRATICHE_ISTANZA_SENZA_RUOLO` (304) è **deprecato** (non più sollevato dalla
> `20260611-01`): la riga resta in `config.messaggi_errore` come orfana.

---

### Note operative

* Il trigger scatta solo su INSERT o UPDATE delle colonne `soggetto_id`, `soggetto_ruolo_id`, `istanza_utility_id` (non su altri campi).
* La stessa validazione puo' essere replicata nel service Python per errori user-friendly, ma il trigger DB garantisce l'integrita' anche per accessi diretti.
* La catena di collegamento e': `pratiche.soggetto_id → soggetti_ruoli.soggetto_id` e `pratiche.soggetto_id → istanze_utilities.soggetto_id`.

---

{% include-markdown "signature-core.md" %}

---

### Regola 5 — il billing account della pratica e' del suo ruolo (dal 2026-10-08)

Con `billing_account_id` valorizzato, il ruolo del billing account deve essere il
`soggetto_ruolo_id` della pratica (un ruolo assente e' incoerente quanto uno diverso):
`E_PRATICHE_BA_NON_COERENTE`, campo `billing_account_id`. Il legame BA ↔ istanza lo tiene la FK
composta, la presenza dell'istanza il CHECK. Il trigger scatta anche su `billing_account_id`.

⚠️ Il commento di testa parlava di «prospect puro»: un'istanza agganciata senza ruolo perche' il
ruolo CLIENTE arrivava dopo, col BA. Non e' piu' cosi': l'istanza nasce col BA, e il ruolo con
lui. Brief: brief-db-istanza-nasce-col-ba (R-8, D-9).

### Revisione del 19-10-2026 — regole 3 e 4 dai BB

Le regole 3 (il ruolo è del soggetto) e 4 (l'istanza è del soggetto) passano da
[`fn_ruolo_di_altro_soggetto`](/dbzero/anagrafiche/manual/fn_ruolo_di_altro_soggetto) e
[`fn_istanza_di_altro_soggetto`](/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto): è la
stessa regola dei controlli di indirizzi, contatti e conti del ruolo (regola del 2). Codici e frasi
non cambiano. ⚠️ Un ruolo o un'istanza che **non esistono** non sono più «non coerenti»: li rifiuta
la chiave esterna della tabella, che dice la causa giusta. Brief:
`brief-db-processi-accensione-per-ambiente` §6.17 (D-17b).
