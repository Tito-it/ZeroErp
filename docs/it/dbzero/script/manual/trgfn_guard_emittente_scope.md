## Documentazione Concettuale – Trigger Function `script.trgfn_guard_emittente_scope`

> **Vedi anche**
>
**Tabelle protette:**
>
[vendite.fatture](/dbzero/vendite/tabelle/fatture)
> [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)
>
**Funzioni correlate:**
>
[script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope)

---
### 🎯 Scopo Principale
(rev 2026-08-22 — la **risoluzione** esce dal guard e passa a una `SECURITY
DEFINER`, chiudendo un fail-open; aggiunte le modalità `ente_incasso` e
`contabile`. Prima: rev 2026-06-01, modalità `fiscale` PK e delega alla canonica
`fn_check_user_emittente_scope`)
La trigger function **`script.trgfn_guard_emittente_scope`** implementa il
defense-in-depth: blocca INSERT/UPDATE se l'utente corrente non ha visibilità
sull'emittente fiscale della riga.

---

### Parametri trigger (TG_ARGV)

| Indice | Valore | Descrizione |
| ------ | ------ | ----------- |
| `TG_ARGV[0]` | `'soggetto_ruolo'` \| `'fattura'` \| `'fiscale'` \| `'ente_incasso'` \| `'contabile'` | Modalita di risoluzione emittente. |
| `TG_ARGV[1]` | nome colonna | Colonna della riga che contiene l'ID da risolvere. |

---

### Modalita di risoluzione

* **`soggetto_ruolo`**: la colonna contiene un `soggetto_ruolo_id`;
  l'emittente si risolve via `anagrafiche.emittenti_fiscali.soggetto_ruolo_id`.
  Usato su `vendite.fatture` (colonna `emittente_soggetto_ruolo_id`).

* **`fattura`**: la colonna contiene un `fattura_id`;
  l'emittente si risolve via `vendite.fatture → emittenti_fiscali`.
  Usato su `pagamenti.vendite_movimenti` e `vendite.fatture_scadenze`
  (colonna `fattura_id`).

* **`fiscale`** *(dal 2026-06-01)*: la colonna contiene **già**
  `emittente_fiscale_id` (convenzione PK); **nessuna risoluzione**.
  Usato sulle tabelle documentali PK: `vendite.preventivi`, `contratti`,
  `offerte_commerciali`, `documenti.documenti_generati`, `pratiche.pratiche`,
  `vendite.ordini` (colonna `emittente_fiscale_id`).

* **`ente_incasso`** *(dal 2026-08-22)*: la colonna contiene un
  `ente_incasso_id`; l'emittente si risolve via il **conto di incasso** del
  canale (`enti_incasso → soggetti_ruoli_conti_bancari → emittenti_fiscali`).
  Usato su `pagamenti.vendite_contabili` (colonna `ente_incasso_id`).

* **`contabile`** *(dal 2026-08-22)*: la colonna contiene un `contabile_id`; si
  passa dalla testata e poi dal suo canale. Usato su
  `pagamenti.vendite_contabili_righe` (colonna `contabile_id`).

  ⭐ Gli ultimi due sono **D5**: quando il denaro arriva in banca non ha ancora
  una fattura, e il suo padrone lo dice il **conto** su cui il cliente ha scelto
  di pagare. Sono due e non uno perché i due presidi partono da due colonne
  diverse — la testata conosce il proprio canale, la riga conosce solo la testata.

---

### 🔴 Il fail-open chiuso il 2026-08-22

La risoluzione dell'emittente **stava qui dentro**, e questo guard è
`SECURITY INVOKER`: nel modo `fattura` leggeva `vendite.fatture`, che **ha la row
security accesa**. Per un utente fuori perimetro quella lettura restituisce **zero
righe**, l'emittente resta `NULL`, e il passo 4 qui sotto **lascia passare**.

> 🔴 Il guard che deve impedire di scrivere sui documenti di un altro emittente
> **si spegneva esattamente quando il documento era di un altro emittente**.

⚠️ E la chiave esterna non si opponeva: i controlli di integrità referenziale
girano **già** fuori dalla row security, quindi la riga entrava — e la vedeva poi
il proprietario del documento, come sua.

⭐ **Il rimedio**: la risoluzione è passata a
[fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id),
che è `SECURITY DEFINER` e legge tutto. Qui resta solo l'**applicazione** della
decisione. Il ramo «non risolvibile» **rimane e serve** — una distinta interna
(fondo fattura, compensazione) non è il canale di nessuno — ma adesso raccoglie
solo ciò che davvero non ha padrone, non i documenti altrui.

---

### Logica di controllo

1. Legge `app.current_user_id` dalla sessione PostgreSQL (`current_setting`).
   Se `NULL` (job batch) → **skip** (RETURN NEW).
2. Legge il valore della colonna da `NEW` (via `to_jsonb`).
   Se `NULL` → **skip**.
3. Su `UPDATE`, se il valore colonna non e cambiato → **skip**.
4. Risolve `emittente_fiscale_id` chiamando
   `script.fn_resolve_emittente_fiscale_id(modo, valore)` — **fuori** dalla row
   security. Se non risolvibile → **skip** (nessun padrone: dati non ancora
   collegati, oppure una distinta interna).
5. Chiama `script.fn_check_user_emittente_scope()`.
   Se `false` → errore via `script.fn_log_and_raise_error` con codice `E_SCOPE_EMITTENTE`.

---

### Trigger associati

```sql
-- Su vendite.fatture
CREATE TRIGGER trg_fatture_a10_guard_emittente_scope_ins_upd
  BEFORE INSERT OR UPDATE ON vendite.fatture
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id');

-- Su pagamenti.vendite_movimenti
CREATE TRIGGER trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd
  BEFORE INSERT OR UPDATE ON pagamenti.vendite_movimenti
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_id');

-- Su pagamenti.vendite_contabili — il canale su cui la distinta si apre
CREATE TRIGGER trg_vendite_contabili_a10_guard_emittente_scope_ins_upd
  BEFORE INSERT OR UPDATE ON pagamenti.vendite_contabili
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_guard_emittente_scope('ente_incasso', 'ente_incasso_id');

-- Su pagamenti.vendite_contabili_righe — DUE trigger, perche' nessuno dei due
-- copre l'altro: col solo primo si proteggerebbero le sole righe gia' abbinate
-- (cioe' non la coda da abbinare), col solo secondo si potrebbe abbinare denaro
-- proprio alla fattura di un altro.
CREATE TRIGGER trg_vendite_contabili_righe_a10_guard_emittente_scope_ins_upd
  BEFORE INSERT OR UPDATE ON pagamenti.vendite_contabili_righe
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_id');

CREATE TRIGGER trg_vendite_contabili_righe_a10_guard_scope_conto_ins_upd
  BEFORE INSERT OR UPDATE ON pagamenti.vendite_contabili_righe
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_guard_emittente_scope('contabile', 'contabile_id');
```

---

### Regole principali

* Trigger **BEFORE INSERT OR UPDATE**, fase `_a10_` (guard).
* Generica e riusabile: basta un nuovo trigger con i parametri `TG_ARGV` appropriati.
* Errori segnalati con `script.fn_log_and_raise_error` per logging + RAISE coerente.
* ⭐ **Rifiuta e spiega**, ed è per questo che non è un doppione delle policy RLS
  che presidiano le stesse tabelle: *la policy nasconde, il trigger rifiuta*. Un
  `WITH CHECK` da solo direbbe «new row violates row-level security policy», che
  è vero e inservibile.
* ⚠️ **Presidia dodici tabelle**: rendendolo più restrittivo si tocca tutto quel
  perimetro in una volta. La revisione del 2026-08-22 è stata misurata con la
  baseline pgTAP completa — `vendite`, `pratiche`, `documenti`, `anagrafiche`,
  `script`, `rls`: nessuna regressione.

---

{% include-markdown "signature-core.md" %}
