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

> **Ultimo aggiornamento**: 12 novembre 2026

### 🎯 Scopo Principale
(rev 2026-09-04 — chiuso il ramo «nessun utente in sessione → passa»: il
criterio è `row_security_active()`. Prima: rev 2026-08-22, la **risoluzione**
esce dal guard e passa a una `SECURITY DEFINER`, chiudendo un fail-open, e
arrivano le modalità `ente_incasso` e `contabile`; rev 2026-06-01, modalità
`fiscale` PK e delega alla canonica `fn_check_user_emittente_scope`)
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
  Usato su `pagamenti.vendite_contabili` (colonna `ente_incasso_id`) **fino al
  2026-09-15**: da quel giorno la distinta porta il suo emittente in colonna e
  il guard è montato in modo `soggetto_ruolo` su `emittente_soggetto_ruolo_id`
  (`20260915-31`) — la coerenza canale↔emittente la garantisce prima
  `pagamenti.fn_get_emittente_distinta`, quindi il canale è in perimetro per
  costruzione, e due guard sulla stessa domanda sarebbero due frasi per lo
  stesso rifiuto. Oggi il modo non ha montaggi.

* **`contabile`** *(dal 2026-08-22)*: la colonna contiene un `contabile_id`; si
  passa dalla testata — *dal 2026-09-15 dalla sua colonna emittente, prima dal
  suo canale*. Usato su `pagamenti.vendite_contabili_righe` (colonna
  `contabile_id`).

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
decisione. Il ramo «non risolvibile» **rimane e serve** per i dati non ancora
collegati (una riga senza fattura né canale) — ma adesso raccoglie solo ciò che
davvero non ha padrone, non i documenti altrui. ⚠️ *Fino al 2026-09-15 vi
cadeva anche la distinta interna («non è il canale di nessuno»): oggi la
distinta sa di chi è, e non ci passa più.*

---

### ⛔ La porta chiusa il 2026-09-04

Fino a questa data il primo passo diceva: *«nessun utente in sessione? è un job
batch, passa»*. Era l'**ultima via** per cui un processo automatico scriveva su
un documento senza dire per conto di chi: bastava **non impostare una GUC**.

> ⛔ Un cartello, non un cancello. Chiunque poteva non impostarla.

⭐ **Il criterio nuovo è uno solo, e non è nostro**: `row_security_active()`
sulla tabella in gioco.

| Chi | Esito |
| --- | --- |
| il **proprietario** delle tabelle (le migrazioni Liquibase) | ✅ passa — la row level security non lo filtra |
| un **superuser** (lo scheduler pgAgent) | ✅ passa |
| un ruolo con **BYPASSRLS** (oggi il batch fatturazione) | ✅ passa |
| una **sessione applicativa senza utente** | ⛔ **si ferma** |

⇒ Chi passa dalle policy passa anche di qui; chi le subisce deve dichiarare chi
agisce. ⛔ Non si riscrive la regola elencando a mano *«proprietario o superuser
o bypassrls»*: sarebbe una **seconda scrittura** dello stesso fatto, e due
scritture prima o poi dissentono. Si chiede a PostgreSQL quella che sta già
applicando alla stessa riga, nello stesso istante.

⚠️ **Deroga dichiarata** alle linee guida §10.4 (le funzioni di scope non
guardano il ruolo DB): qui non si identifica l'utente dal ruolo, si
**rispecchia** una decisione che il motore ha già preso. L'alternativa — una GUC
che una migrazione imposta per dire «sono io» — sarebbe di nuovo un cartello.

⚠️ **E non ferma il batch fatturazione**, che è il contrario di come lo si
racconta di solito: quel ruolo ha `BYPASSRLS`, quindi è proprio ciò che continua
a passare. Sarà il **ritiro del ruolo** (nel provisioning) a rendere questo
cancello efficace anche su di lui.

### ⛔ Dentro una `SECURITY DEFINER` il criterio risponde per la persona sbagliata (rev 2026-09-18)

`row_security_active()` risponde per il `current_user`, e dentro una funzione `SECURITY
DEFINER` il `current_user` è il **proprietario** della funzione — che qui possiede anche le
tabelle, con la row level security abilitata ma non forzata: la risposta è **false**, sempre,
chiunque abbia chiamato. Provato il 18-09 su dbdev, stessa sessione applicativa senza GUC, in
una transazione annullata: la stessa riga era rifiutata scritta direttamente e **passava** via
`config.fn_accoda_email_sistema` (DEFINER del proprietario). Per la primitiva di magazzino
(`fn_scrivi_movimento`, DEFINER per costruzione della porta) sarebbe stata la porta aperta a
ogni processo senza identità.

⭐ **La rev**: se non c'è utente in sessione, la RLS «non è attiva» **ma** si sta dentro una
DEFINER, il guard risolve comunque l'emittente della riga e, se la riga **ha
un padrone**, si ferma con `E_SCOPE_SENZA_UTENTE`; una riga **senza padrone** passa come prima —
è il caso delle email di sistema (emittente `NULL`), da cui dipende il reset password senza
sessione. Non è una seconda scrittura della regola di esenzione: il criterio resta
`row_security_active`, si aggiunge il solo caso in cui quella funzione guarda l'altro.
Consumatori DEFINER censiti al 18-09: `fn_accoda_email_sistema`, `fn_chiudi_email_sistema`
(entrambe a emittente `NULL`, invariate). Presidi: `test-guard-emittente-senza-utente.sql`
(7-8) e `magazzino/test-porta-ledger-v1.sql` (13-14: la primitiva senza identità si ferma).

⭐ **Come si riconosce «dentro una DEFINER» (rev 2026-10-15).** Il guard confronta il
`current_user` con il **ruolo di sessione**, cioè il parametro `role`, e solo se `role` non è
impostato con il `session_user`. Il confronto col solo `session_user` sbagliava per chi lavora
come proprietario con `SET role`: un utente personale che fa `SET role zeroerp_owner` ha
`current_user <> session_user` anche fuori da una DEFINER, e il guard lo trattava come una
DEFINER. Una DEFINER cambia il `current_user` ma non il parametro `role`, quindi la differenza
fra i due resta il segnale giusto.

⭐ **Gli altri sette trigger che leggono `app.current_user_id` non sono stati
toccati**, ed è una scelta: i cinque `*_default_emittente` non *concedono*
niente — riempiono un valore di comodo, e poi è questo guard a decidere se la
riga entra.

---

### Logica di controllo

1. Legge `app.current_user_id` dalla sessione PostgreSQL (`current_setting`).
   Se `NULL`, **non passa più in automatico** (vedi la sezione qui sotto):
   passa solo chi bypasserebbe comunque la row level security, altrimenti
   errore `E_SCOPE_SENZA_UTENTE`.
2. Legge il valore della colonna da `NEW` (via `to_jsonb`).
   Se `NULL` → **skip**.
3. Su `UPDATE`, se il valore colonna non e cambiato → **skip**.
4. Risolve `emittente_fiscale_id` chiamando
   `script.fn_resolve_emittente_fiscale_id(modo, valore)` — **fuori** dalla row
   security. Se non risolvibile → **skip** (nessun padrone: dati non ancora
   collegati; *dal 2026-09-15 non più la distinta interna, che sa di chi è*).
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
* ⚠️ **Presidia quindici tabelle**: rendendolo più restrittivo si tocca tutto
  quel perimetro in una volta. Le due revisioni sono state misurate con la
  baseline pgTAP completa (`vendite`, `pratiche`, `documenti`, `anagrafiche`,
  `pagamenti`, `dbops`, `maintenance`, `script`): nessuna regressione — 491 file
  il 2026-09-04.

---

{% include-markdown "signature-core.md" %}
