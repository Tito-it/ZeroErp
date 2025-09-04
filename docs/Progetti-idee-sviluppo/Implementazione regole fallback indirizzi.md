# Regole di fallback degli indirizzi (configurabili)

> **Obiettivo**
> Rendere **configurabile** la scelta dell’**indirizzo “migliore”** per un determinato **caso d’uso** (es. CONSEGNA, FATTURAZIONE, RECAPITO\_POSTALE, PARTENZA\_DDT, …) tramite **regole a DB**, senza logica hard-coded in funzioni.

---

## 1) Contesto e motivazione

* Oggi la funzione `fn_pick_indirizzo_consegna` seleziona l’indirizzo seguendo un **ordine fisso** (es. `SPED → FATT → SEDEOP → SEDELEG → RES → DOMFISC → POSTA`) con eventuale fallback generico.
* In futuro possono servire **ordini diversi** per casi d’uso differenti (es. recapito postale, partenza DDT) e **override** per:

  * **emittente** (brand/tenant che emette documenti);
  * **soggetto/ruolo** (cliente/fornitore specifico);
  * opzionalmente **paese**, **canale** (ECOM/CRM/API), **validità temporale**.
* Una soluzione **dichiarativa** consente di **cambiare comportamento** aggiungendo/modificando **righe di configurazione**.

---

## 2) Tabella di regole proposta: `config.indirizzi_fallback_rules`

**Scopo**: definire, per un “caso d’uso”, una **sequenza ordinata** di tipi di indirizzo da tentare, con possibilità di **override per ambito (scope)**.

### 2.1 Campi principali

* `id` (PK)
* `use_case` **VARCHAR(32)**
  Esempi: `CONSEGNA`, `FATTURAZIONE`, `RECAPITO_POSTALE`, `PARTENZA_DDT`, `RITIRO_SEDE`, …
* `scope_tipo` **VARCHAR(16)**
  Valori: `SYSTEM` | `EMITTENTE` | `RUOLO`
* `scope_id` **BIGINT NULL**

  * `NULL` se `scope_tipo='SYSTEM'`
  * `emittente_soggetto_ruolo_id` se `scope_tipo='EMITTENTE'`
  * `soggetto_ruolo_id` se `scope_tipo='RUOLO'`
* `tipo_indirizzo_id` **INT** → FK `config.tipi_indirizzi(id)`
  (Esempi attuali: `SPED`, `FATT`, `RES`, `DOMFISC`, `SEDELEG`, `SEDEOP`, `POSTA`)
* `priority` **SMALLINT** (1, 2, 3, …) — ordine di tentativo

### 2.2 Filtri/attributi opzionali (estensioni)

* `country_id` **INT NULL** → se vuoi regole diverse per paese
* `channel` **VARCHAR(16) NULL** → es. `ECOM`, `CRM`, `API`
* `must_normalized` **BOOLEAN** (default `false`) → preferisci indirizzi **normalizzati** (`indirizzo_dettaglio_id` non NULL) e scarta i liberi
* `valid_from` **DATE NULL**, `valid_to` **DATE NULL** → validità della regola
* `attivo` **BOOLEAN NOT NULL DEFAULT true**
* `meta` **JSONB NOT NULL DEFAULT '{}'** → predicati/annotazioni custom (future-proof)

### 2.3 Vincoli consigliati

* **UNIQUE** su `(use_case, scope_tipo, scope_id, priority)`
  (impedisce doppioni alla stessa “posizione” di escalation)
* **CHECK**: `scope_id IS NULL` **se e solo se** `scope_tipo='SYSTEM'`
* **CHECK**: `priority BETWEEN 1 AND 32767`
* **FK**: `tipo_indirizzo_id → config.tipi_indirizzi(id)`

### 2.4 Indici consigliati

* `(use_case, scope_tipo, scope_id, priority)`  → lookup e ordinamento
* Facoltativi con filtri frequenti:
  `(use_case, scope_tipo, scope_id) WHERE attivo`
  `(use_case, country_id)`
  `(use_case, channel)`

> **Nota**: resta valido l’indice già in anagrafe `ix_indirizzi_ruolo_tipo` su `anagrafiche.indirizzi (soggetto_ruolo_id, tipo_indirizzo_id)` per velocizzare la selezione dei candidati.

---

## 3) Algoritmo di risoluzione (cascata di scope)

1. **Risolvi scope** (più specifico → meno specifico):

   * `RUOLO` (se esistono regole per quel `soggetto_ruolo_id`)
   * `EMITTENTE` (se esistono regole per quel `emittente_soggetto_ruolo_id`)
   * `SYSTEM` (default globale)
2. Per **il primo scope che ha regole attive e valide**, costruisci la **lista ordinata** di `tipo_indirizzo_id` in base a `priority` (applica i filtri opzionali, es. `country_id`, `channel`, `valid_from/to`, `attivo`).
3. Cerca indirizzi in `anagrafiche.indirizzi` per **quel `soggetto_ruolo_id`** seguendo l’ordine dei tipi; se `must_normalized=true`, scarta quelli senza `indirizzo_dettaglio_id`.
4. Se **non trovi nulla** a quello scope, passa allo scope successivo (EMITTENTE → SYSTEM) e ripeti.
5. Se **ancora nulla** e hai bisogno di resilienza, usa un **fallback\_any**: prendi “qualunque” indirizzo del ruolo (preferendo normalizzato; ultimo update più recente), oppure **ritorna NULL** (nessun indirizzo).

> Esempio **PARTENZA\_DDT**: se l’utente ha selezionato un **magazzino**, si usa sempre l’indirizzo del **magazzino** (già FK a `anagrafiche.indirizzi_dettaglio`). Le regole entrano in gioco solo se non è stato selezionato un magazzino.

---

## 4) Esempi di regole (dati di configurazione)

### 4.1 Default di sistema – Caso d’uso: CONSEGNA

1. `SPED`
2. `FATT`
3. `SEDEOP`
4. `SEDELEG`
5. `RES`
6. `DOMFISC`
7. `POSTA`

### 4.2 Default di sistema – Caso d’uso: RECAPITO\_POSTALE

1. `POSTA`
2. `SPED`
3. `RES`
4. `FATT`
5. `SEDELEG`
6. `SEDEOP`
7. `DOMFISC`

### 4.3 Override per emittente (brand X) – Caso d’uso: CONSEGNA

1. `SPED`
2. `SEDEOP`
3. `FATT`

### 4.4 Override per ruolo (cliente Y) – Caso d’uso: CONSEGNA

1. `SEDEOP`
2. `SPED`

---

## 5) Funzione di pick (specifica funzionale)

**Firma proposta**
`script.fn_pick_indirizzo_by_rules(
  p_use_case TEXT,
  p_soggetto_ruolo_id INT,
  p_emittente_soggetto_ruolo_id INT DEFAULT NULL,
  p_opts JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE (
  indirizzo_id INT,
  tipo_indirizzo_id INT,
  tipo_codice TEXT,
  indirizzo_dettaglio_id INT,
  resolved_scope TEXT,     -- SYSTEM|EMITTENTE|RUOLO
  resolved_priority SMALLINT,
  rule_id BIGINT           -- quale regola ha vinto (debug/audit)
)`

**Comportamento**

* Applica l’algoritmo di §3; valorizza `resolved_scope/priority/rule_id` con la **regola vincente** (tracciabilità e debug semplificati).
* Supporta filtri/parametri opzionali in `p_opts` (es. `{ "country_id": 380, "channel": "ECOM", "must_normalized": true, "fallback_any": true }`).
* Se nessun indirizzo è disponibile e `fallback_any=false`, **ritorna 0 righe** (chiamante decide cosa fare).

**Compatibilità retro**

* Se per uno scope non esistono regole, la function può **degradare** su una lista **di default** passata in `p_opts` o sulla vecchia `fn_pick_indirizzo_consegna`.

**Sicurezza**

* Marcata `STABLE` (solo letture).
* In genere **no** `SECURITY DEFINER`: meglio garantire i **GRANT** necessari su tabelle `config.*` e `anagrafiche.indirizzi` al ruolo applicativo.
* Se si decidesse per `SECURITY DEFINER`, fissare `search_path` e limitare al minimo i privilegi del proprietario della funzione.

---

## 6) Performance e indici

* **Lookup regole**: indice su `(use_case, scope_tipo, scope_id, priority)`; opzionale parziale `WHERE attivo`.
* **Lookup indirizzi**: già presente `ix_indirizzi_ruolo_tipo (soggetto_ruolo_id, tipo_indirizzo_id)`; utile aggiungere

  * `(soggetto_ruolo_id)` semplice (per fallback\_any veloce)
  * `(tipo_indirizzo_id)` se filtri frequenti per reportistiche.
* Le funzioni ordinano sulle poche righe candidate; costi contenuti.

---

## 7) Accorgimenti e qualità dati

* Definire **tipi indirizzo** standardizzati in `config.tipi_indirizzi` (già presenti):

  * `FATT` (Fatturazione) — id: 8
  * `SPED` (Spedizione) — id: 7
  * `RES` (Residenza) — id: 1
  * `DOMFISC` (Domicilio Fiscale) — id: 2
  * `SEDELEG` (Sede Legale) — id: 3
  * `SEDEOP` (Sede Operativa) — id: 4
  * `POSTA` (Corrispondenza postale) — id: 5
* Mantenere **coerenza** nei dati (un solo indirizzo “primario” per tipo quando possibile).
* Valutare `must_normalized=true` per casi che **richiedono** indirizzo normalizzato (es. stampa DDT/label spedizione).

---

## 8) Integrazione con DDT, Ordini, Fatture

* **DDT Vendita**:

  * `indirizzo_partenza`: se selezionato un **magazzino**, usare l’indirizzo del magazzino (FK a `anagrafiche.indirizzi_dettaglio`); altrimenti applicare `use_case='PARTENZA_DDT'` sull’**emittente**.
  * `indirizzo_consegna`: applicare `use_case='CONSEGNA'` sul **cliente** (ruolo), con override per emittente o cliente se configurati.
* **Ordini**: in conferma, puoi **freezare** gli indirizzi scelti (FK + snapshot) seguendo le stesse regole.
* **Fatture**: per l’intestazione/recapito, usare `use_case='FATTURAZIONE'` o `RECAPITO_POSTALE` se serve; snapshot sempre in testata.

---

## 9) Esempi d’uso (SQL)

**Selezione indirizzo di consegna (default system)**

```sql
SELECT *
FROM script.fn_pick_indirizzo_by_rules(
  p_use_case := 'CONSEGNA',
  p_soggetto_ruolo_id := 12345,
  p_emittente_soggetto_ruolo_id := NULL,
  p_opts := '{"fallback_any": true}'
);
```

**Selezione recapito postale con filtri**

```sql
SELECT *
FROM script.fn_pick_indirizzo_by_rules(
  'RECAPITO_POSTALE', 12345, 67890,
  '{"channel":"CRM","must_normalized":false,"fallback_any":true}'
);
```

**Partenza DDT con magazzino (bypass regole)**

```sql
-- Se l’utente ha scelto magazzino M, usa direttamente il suo indirizzo_dettaglio
SELECT i.id AS indirizzo_id, i.indirizzo_dettaglio_id
FROM magazzino.magazzini m
JOIN anagrafiche.indirizzi_dettaglio d ON d.id = m.indirizzo_dettaglio_id
JOIN anagrafiche.indirizzi i ON i.indirizzo_dettaglio_id = d.id
WHERE m.id = :magazzino_id
LIMIT 1;
```

---

## 10) Roadmap di implementazione

1. **DDL** tabella `config.indirizzi_fallback_rules` (+ indici, vincoli, commenti).
2. **Function** `script.fn_pick_indirizzo_by_rules` (STABLE):

   * risoluzione scope RUOLO→EMITTENTE→SYSTEM
   * filtri (country/channel/validità/must\_normalized)
   * ritorno del “percorso decisionale” (`rule_id`, `resolved_scope`, `resolved_priority`).
3. **Migrazione**: popolare regole **SYSTEM** per `CONSEGNA` e `RECAPITO_POSTALE` replicando i comportamenti attuali.
4. **Refactor**: far usare la nuova function dove oggi è chiamata `fn_pick_indirizzo_consegna`; mantenere la vecchia come **fallback** iniziale.
5. **Documentazione**: linea guida per amministratori su come aggiungere/override le regole.

---

## 11) Benefici

* **Configurabilità** per caso d’uso e per tenant/cliente, senza nuovi rilasci.
* **Determinismo** e **audit** (regole persistite a DB + identificazione della regola vincente).
* **Estensibilità** (nuovi filtri/condizioni via colonne o `meta`).
* **Coerenza** con DDT, ordini e fatture e con l’anagrafica magazzini.

---

### Appendice A — Glossario rapido

* **use\_case**: contesto applicativo della scelta (CONSEGNA, FATTURAZIONE, …)
* **scope**: livello di applicazione della regola (SYSTEM, EMITTENTE, RUOLO)
* **emittente**: ruolo che emette documenti (registro di numerazione, intestazione fiscale)
* **ruolo**: soggetto/ruolo destinatario (cliente/fornitore, ecc.)
* **must\_normalized**: preferenza/obbligo per indirizzi con dettaglio normalizzato

### Appendice B — Tipi indirizzo correnti (`config.tipi_indirizzi`)

* `FATT` — Fatturazione (id 8)
* `SPED` — Spedizione (id 7)
* `RES` — Residenza (id 1)
* `DOMFISC` — Domicilio Fiscale (id 2)
* `SEDELEG` — Sede Legale (id 3)
* `SEDEOP` — Sede Operativa (id 4)
* `POSTA` — Corrispondenza Postale (id 5)

---
{% include-markdown "signature-core.md" %}
