## 📘 Documentazione Concettuale – Funzione `script.fn_check_attivita_riportabile_da_emettere`

> 👀 **Vedi anche**
>
> [vendite.fn_riporta_attivita_da_emettere](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere) — la mutazione che la consuma
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [script.fn_check_fattura_eliminabile_da_lotto](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto) — il gemello per forma

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

Elenca i **motivi che impediscono di riportare «da emettere»** un insieme di
`vendite.attivita_fatturabili`. Funzione **pura** (`fn_check_*`): non scrive e
non solleva errori di dominio. Ritorna `[]` quando si può fare su tutte.

**Sede unica della regola.** La legge la mutazione, che solleva il codice del
**primo** motivo; e la legge il **read-side**, per spegnere il pulsante e dire
perché invece di far scoprire il vincolo sbagliando.

---

### ⛔ Il perimetro NON usa `fatturato`, ed è la trappola evitata

La prima stesura del piano proponeva `fatturato IS TRUE AND fattura_riga_id IS
NULL`. ⚠️ Quel predicato è diventato **impossibile per costruzione** il giorno in
cui `fatturato` è passata a colonna **generata** (`20260826-33`): sarebbe sempre
falso, e il verbo avrebbe smesso di funzionare **in silenzio** — la stessa
famiglia di difetto che il cantiere stava chiudendo.

Il perimetro effettivo sono **tre condizioni che si leggono come una frase**:

```sql
fattura_riga_id IS NULL                              -- non è in nessuna fattura
AND COALESCE(lock_in_fatturazione, false) IS TRUE    -- è ancora lucchettata
AND stato_esecuzione = 'COMPLETED'                   -- e il giro che la lucchettava ha finito
```

⭐ **La terza separa l'orfana dal giro VIVO**: `PENDING`/`RUNNING` vuol dire
lotto in corso, e quello non si tocca. ⭐ E il predicato **sopravvive** a
qualunque cosa succeda a `fatturato`, perché `stato_esecuzione` non è generata.

---

### ⛔ Lo scope sta sulla commessa, non sull'attività

| Tabella | RLS |
| --- | --- |
| `vendite.attivita_fatturabili` | **no** |
| `vendite.commesse_attivita` | **sì** (`rls_commesse_attivita_ef_whitelist`, per `commessa_id`) |

Una `fn_check_*` che leggesse la sola `attivita_fatturabili` sarebbe **fail-open
sullo scope**. E il danno non sarebbe un permesso concesso a vuoto: la mutazione
libererebbe l'attività (tabella senza RLS) e **non** riporterebbe la riga di
commessa a `NON_EMESSA` (tabella con RLS, zero righe toccate) — cioè **lo stato
spezzato** per impedire il quale esiste
[`fn_libera_attivita_fatturabili`](/dbzero/vendite/funzioni/fn_libera_attivita_fatturabili).

⭐ Per questo l'attività si risolve **passando per** `commesse_attivita`: quel
`JOIN` *è* il perimetro. Chi non la vede riceve «non trovata», che dal suo punto
di vista è la verità.

---

### I cinque motivi, nell'ordine

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `ATTIVITA_NON_TROVATA` | `E_ATTIVITA_FATTURABILE_NON_TROVATA` | non si risolve, o è fuori perimetro |
| 2 | `ATTIVITA_IN_FATTURA` | `E_ATTIVITA_ANCORA_IN_FATTURA` | è ancora agganciata a una riga di fattura |
| 3 | `ATTIVITA_GIA_DISPONIBILE` | `E_ATTIVITA_GIA_DA_EMETTERE` | non è lucchettata **e la riga di commessa è già `NON_EMESSA`**: è davvero in coda |
| 5 | `ATTIVITA_EMESSA_IN_GIRO_VIVO` | `E_ATTIVITA_IN_LAVORAZIONE` | non è lucchettata, la riga è `EMESSA` e il **marchio** (`emit_batch_id`) è di un lotto **in gioco**: è in transito fra il pull e la `select` |
| 4 | `ATTIVITA_IN_GIRO_VIVO` | `E_ATTIVITA_IN_LAVORAZIONE` | lucchettata, ma il giro non ha finito |

⚠️ **L'ordine è il contratto**, perché la mutazione solleva il primo (il 5 sta
fra il 3 e il 4: viene dal livello della riga, come il 3).

### 🔴 rev 12-09-2026 — la DIVERGENZA è riportabile, il transito no

Il motivo 3 diceva: *«senza lucchetto l'attività è già disponibile, il giro
successivo la prende da sé»*. **Falso** quando la riga di commessa è ancora
`EMESSA`: il pull la vede `EMESSA`, la `select` di un lotto nuovo non trova il suo
marchio — nessun giro la riprende. Quello stato (attività libera, riga `EMESSA`,
marchio di un lotto **morto**) era **irraggiungibile da ogni verbo**: il reset non
la prendeva (`fn_cleanup_fatture_by_ids`, corretto dal `20260912-34`) e questo
check la rifiutava come «già disponibile». Verificato il 12-09 sul lotto 13338,
riparato a mano con `fn_libera_attivita_fatturabili`.

La `vis` legge ora **i due livelli**: `stato_emissione` della riga e, dal marchio,
se il lotto è in gioco (`vendite.fn_lotto_da_emit_batch` + `vw_lotti_fase.pre_fiscale`
— le due sedi già esistenti):

* libera + riga `NON_EMESSA` → motivo 3, com'era (davvero disponibile);
* libera + riga `EMESSA` + lotto **in gioco** → motivo 5: è la finestra fra pull e
  `select` di un giro vivo, liberarla da qui la farebbe prendere da due giri
  (stessa ragione del 4, letta dal marchio). Stesso codice e classe del 4;
* libera + riga `EMESSA` + lotto **morto** o senza marchio → **nessun motivo**: il
  verbo chiama `fn_libera_attivita_fatturabili`, che riallinea i due livelli.

⚠️ Un lotto fuori dal perimetro RLS di chi chiede risolve a `NULL` → «morto»:
chi vede la commessa vede il suo lotto, è lo stesso emittente.

Presidio: `db/pgtap/vendite/test-af-emessa-non-lockata-reset-e-riporto-v1.sql`
(2, 5, 6, 7), con la finestra costruita dal **pull vero**. Brief:
`brief-db-rilancio-step-non-rivede-le-proprie-commesse` §10.4.

⛔ **Il motivo 2 è il guard che impedisce al verbo di diventare un modo per
scollegare una fattura viva.** Il trigger di riga
`trgfn_attivita_fatturabili_guard_fatturato` dice già la stessa cosa da un altro
livello, con `E_RIGA_GIA_FATTURATA`: i due **non si fondono**, perché quello è
generico e non dice all'operatore *cosa* stava tentando. Se il guard di dominio
si rompesse, il trigger tiene comunque.

---

### ⚠️ Il primo motivo è AGGREGATO, gli altri sono per attività

Non è incoerenza. Di una riga che non si vede non si può dire niente che
l'operatore riconosca — **nemmeno la commessa** — quindi l'unica informazione
onesta è **quante** sono, e il rimedio (aggiorna l'elenco) è lo stesso per tutte.

Delle altre si nomina **«commessa `<codice>`, competenza `<MM/AAAA>`»**, che è
come le vede sulla card. ⛔ Mai un id tecnico.

Per la stessa ragione il motivo 1 **non porta un bersaglio**: un pulsante verso
una riga invisibile è un vicolo cieco.

---

### La forma del motivo

```json
{ "codice":                  "E_ATTIVITA_ANCORA_IN_FATTURA",
  "reason":                  "ATTIVITA_IN_FATTURA",
  "reason_key":              "vendite.attivita.azione_reason.ancora_in_fattura",
  "dettaglio":               "commessa C-2026-041, competenza 07/2026",
  "attivita_fatturabile_id": 1123,
  "commessa_id":             318,
  "fattura_id":              835 }
```

Gli ultimi tre campi **non servono all'interfaccia**: servono alla **mutazione**
per comporre il `bersaglio` dell'errore (`linee-guida-sql` §5) senza doversi
rileggere le stesse righe. Il bersaglio ha in testa la **commessa** — l'unico
posto dove quella riga si vede — e poi la **fattura**, la cosa da sistemare.

---

### Esempio d'uso

```sql
-- Si può riportare?
SELECT jsonb_array_length(
         script.fn_check_attivita_riportabile_da_emettere(ARRAY[1123, 1130])) = 0 AS ammesso;

-- Perché no?
SELECT script.fn_check_attivita_riportabile_da_emettere(ARRAY[1123]) -> 0 ->> 'reason';
-- → ATTIVITA_IN_FATTURA
```

---

### Note operative

* **`STABLE`**: è una lettura. Il **solo** raise è sul parametro — un elenco
  assente o vuoto è un errore di *chiamante*, non una condizione di dominio.
  ⛔ Se uscisse come «nessun motivo» diventerebbe poi «zero righe riportate»,
  indistinguibile da un'operazione riuscita che non ha trovato niente da fare.
* **Array esplicito** `bigint[]`: `colonna%TYPE[]` non esiste in PostgreSQL.
* 🔴 Le quattro `reason_key` (`vendite.attivita.azione_reason.*`) vanno presenti
  nei locales: `check_i18n_keys.py` fallisce se ne manca una, e un tooltip vuoto
  è peggio del pulsante acceso.
* Test: `db/pgtap/vendite/test-riporta-attivita-da-emettere-v1.sql`. ⭐ Il **13**
  è il presidio che conta: verifica che il codice nominato qui sia **lo stesso**
  che la mutazione solleva, su ogni rifiuto.
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L5 / D-4.

---

{% include-markdown "signature-core.md" %}
