## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [anagrafiche.trgfn_billing_account_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

(latest review 02-05-2026)

La trigger function **`anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()`**
chiude una **lacuna del modello dati** sul vincolo "1 soggetto per istanza".

Il manuale di [`istanze_utilities`](/dbzero/anagrafiche/tabelle/istanze_utilities) §7.3
dichiara che "il cliente vive *dentro* l'istanza" e che ogni istanza ha al
massimo un cliente (`UNIQUE (istanza_utility_id)` su `clienti`). Per
costruzione del flusso applicativo, il **soggetto del billing_account**
ancorato a un'istanza coincide con il **soggetto dell'istanza** stessa.

Fino al 2026-05-02 questa coerenza era una **regola operativa** non
applicata da vincoli DB stretti. Un INSERT diretto su `billing_account`
con `soggetto_ruolo_id` riferito a un soggetto diverso da quello
dell'istanza target sarebbe passato silenziosamente — drift potenziale
in caso di import / batch / errore di codice.

Questo guard chiude la lacuna: **BEFORE INSERT OR UPDATE OF
`(istanza_utility_id, soggetto_ruolo_id)`** verifica che
`soggetti_ruoli.soggetto_id == istanze_utilities.soggetto_id`. Se
differiscono, raise `E_BA_SOGGETTO_INCOERENTE_ISTANZA`.

E' applicata dal trigger
`trg_billing_account_a10_guard_soggetto_coerenza_istanza_ins_upd`
(fase `_a10_`, guard fail-fast).

---

### Logica

1. Lookup `v_soggetto_ruolo` da `anagrafiche.soggetti_ruoli` via `NEW.soggetto_ruolo_id`.
2. Lookup `v_soggetto_istanza` da `anagrafiche.istanze_utilities` via `NEW.istanza_utility_id`.
3. Se entrambi sono valorizzati e **differiscono**: raise `E_BA_SOGGETTO_INCOERENTE_ISTANZA`.
4. Se uno dei due lookup non risolve (caso difensivo, FK esistenti dovrebbero gia' aver gestito): pass-through. Le FK strutturali bloccheranno l'errore.

---

### Errori sollevati

| Codice | Contesto | Quando |
| --- | --- | --- |
| `E_BA_SOGGETTO_INCOERENTE_ISTANZA` (id 424) | `billing_account_id`, `codice`, `istanza_utility_id`, `soggetto_ruolo_id`, `ba_soggetto_id`, `istanza_soggetto_id` | INSERT/UPDATE su `billing_account` con `soggetto_ruolo_id` che punta a un soggetto diverso da quello dell'istanza target. SQLSTATE `P0001`. Tre `%s` nel template (`codice`, `ba_soggetto_id`, `istanza_soggetto_id`). |

---

### Esempi

**1) INSERT BA coerente (passa):**

```sql
-- Istanza con soggetto S1, BA con soggetto_ruolo che punta a S1
INSERT INTO anagrafiche.billing_account
    (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, codice)
VALUES (42, 7, 1, 3, 'BA-2026-0001');
-- ok
```

**2) INSERT BA incoerente (raise):**

```sql
-- Istanza con soggetto S1, BA con soggetto_ruolo che punta a S2 != S1
INSERT INTO anagrafiche.billing_account
    (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, codice)
VALUES (42, 99, 1, 3, 'BA-2026-0002');
-- ERROR: P0001 — Billing account BA-2026-0002: soggetto del BA (S2-uuid)
-- diverso da soggetto dell'istanza_utility (S1-uuid).
```

**3) UPDATE soggetto_ruolo verso un altro soggetto (raise):**

```sql
-- Tentativo di reassign a un soggetto_ruolo di un altro soggetto
UPDATE anagrafiche.billing_account
   SET soggetto_ruolo_id = 99
 WHERE id = 1;
-- ERROR: P0001 — analogo al caso 2
```

**4) UPDATE solo `valido_dal` (no scatto via clausola OF):**

```sql
UPDATE anagrafiche.billing_account
   SET valido_dal = '2026-06-01'
 WHERE id = 1;
-- ok: la clausola OF (istanza_utility_id, soggetto_ruolo_id) salta il guard
```

---

### Diagnostica righe esistenti

Per identificare BA che violerebbero il guard (utile prima del deploy
o in audit periodico):

```sql
SELECT ba.id, ba.codice,
       sr.soggetto_id  AS ba_soggetto,
       iu.soggetto_id  AS istanza_soggetto
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
  JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
 WHERE sr.soggetto_id <> iu.soggetto_id;
```

**Su DB pulito**: 0 righe attese. Se >0 il deploy del guard halta tramite
preCondition `sqlCheck` del changeSet `20260502-16-01`.

---

### Note operative

* **Modello "chi paga != chi intesta"**: NON supportato oggi. Se in futuro servira'
  modellare un terzo pagante (es. delegato di pagamento, intestazione fattura
  diversa), va aggiunta una struttura dedicata sul preventivo / fattura, non
  riusando la coppia BA/istanza.
* **No clausola WHEN**: il guard scatta su ogni INSERT/UPDATE delle 2 colonne
  rilevanti. Costo trascurabile (2 SELECT su PK indicizzata per riga).
* **Pattern coerente con `trgfn_billing_account_guard_normalize`**: l'altro guard
  fa coerenza fiscale parent↔child (sezione 2.2). Questo si concentra sul
  vincolo soggetto↔istanza (sezione 2.x ortogonale, tenuta separata per
  leggibilita' e manutenibilita').
* **Pre-deploy**: il changeSet `20260502-16-01` (pre-check) verifica zero
  violazioni esistenti. Se violazioni >0, vanno corrette manualmente (UPDATE
  `soggetto_ruolo_id` o DELETE+ricreazione del BA) prima di applicare il guard.

---

### Revisione del 19-10-2026 — il confronto dal BB

Il confronto fra il soggetto del ruolo e quello dell'istanza passa da
[`fn_istanza_di_altro_soggetto`](/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto), la
stessa domanda che usano i controlli di indirizzi, contatti, conti del ruolo e pratiche (regola
del 2). Codice, campo e frase non cambiano. Il soggetto di un ruolo ora è bloccato
(`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`): la regola non si aggira più cambiando il ruolo invece del
billing account. Brief: `brief-db-processi-accensione-per-ambiente` §6.17 (D-17b, D-17d).

---

{% include-markdown "signature-core.md" %}

---
