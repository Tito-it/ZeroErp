# Brief DB — il lavoro che non torna indietro: eliminazione fattura, residui, ritiro a monte

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono** i prerequisiti
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** Tid, 2026-08-26, con una domanda che non era su un difetto:
> *«non ricordo più l'utilizzo di emesse non fatturate e Fatturate e la loro
> logica»*. Cercando la risposta nella dashboard di competenza è emerso che
> quella casella conteneva **5 attività** — e da lì il difetto qui sotto.
>
> **Correlati:**
> [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md) ·
> [brief-be-fe-rendi-definitive-sui-lotti.md](brief-be-fe-rendi-definitive-sui-lotti.md)
> (l'altro esito della stessa conversazione)
>
> ⛔ **Stato: difetto PROVATO, causa isolata, correzione proposta. Nessun file
> scritto** ([[feedback_db_actions_passaggio_team]]).

---

## 1. Il difetto: «Elimina dal lotto» non libera niente

`vendite.fn_elimina_fattura_da_lotto` → `fn_cleanup_fatture_by_ids(ARRAY[id], NULL)`.

Dentro `fn_cleanup_fatture_by_ids` l'ordine delle operazioni è questo:

```
1.  SELECT array_agg(r.id) INTO v_righe_ids  FROM fatture_righe WHERE fattura_id = ANY(...)
...
2.  DELETE FROM vendite.fatture_righe WHERE fattura_id = ANY(p_fatture_ids);
...
3.  SELECT array_agg(DISTINCT af.commessa_attivita_id) INTO v_ca_ids
      FROM attivita_fatturabili af
     WHERE (p_lock_batch_id IS NOT NULL AND af.lock_batch_id = p_lock_batch_id)
        OR af.fattura_riga_id = ANY(v_righe_ids);      -- ⛔
4.  UPDATE attivita_fatturabili SET fatturato = false, lock_in_fatturazione = false, ...
     WHERE (p_lock_batch_id IS NOT NULL AND lock_batch_id = p_lock_batch_id)
        OR fattura_riga_id = ANY(v_righe_ids);         -- ⛔
5.  UPDATE commesse_attivita SET stato_emissione = 'NON_EMESSA' WHERE id = ANY(v_ca_ids);
```

Il passo **2** cancella le righe. La FK
`fk_attivita_fatturabili_fattura_riga` è
`ON DELETE SET NULL`, **NOT DEFERRABLE** (`condeferrable = f`, verificato su
`pg_constraint`): l'azione referenziale scatta **a fine statement**, cioè prima
che i passi 3 e 4 vengano eseguiti.

Quando i passi 3 e 4 girano, `af.fattura_riga_id` **è già NULL**. Il predicato
`fattura_riga_id = ANY(v_righe_ids)` non può più corrispondere a nessuna riga.

⭐ **Perché il ramo `lock_batch_id` non salva la situazione**: sul percorso
per-fattura vale la regola C-22 e si passa deliberatamente `p_lock_batch_id =
NULL` (passare quello del lotto libererebbe anche le attività delle *altre*
fatture). Restano quindi **solo** i due predicati barrati sopra — e non
corrispondono a nulla.

### 1.1 La prova, isolata dal dominio

Riproduzione con tabelle temporanee, stessa semantica, nessun dato reale
toccato:

```sql
CREATE TEMP TABLE t_righe (id bigint PRIMARY KEY);
CREATE TEMP TABLE t_af (id bigint PRIMARY KEY,
                        riga_id bigint REFERENCES t_righe(id) ON DELETE SET NULL,
                        fatturato bool);
INSERT INTO t_righe VALUES (1),(2);
INSERT INTO t_af    VALUES (10,1,true),(11,2,true);

DELETE FROM t_righe WHERE id IN (1,2);
UPDATE t_af SET fatturato = false WHERE riga_id = ANY(ARRAY[1,2]::bigint[]);
```

Esito: **`UPDATE 0`**, e `fatturato` resta `t` su entrambe le righe.

### 1.2 Il danno è DOPPIO, ed è la parte peggiore

Non si perde solo lo sblocco: salta anche il passo 5, perché `v_ca_ids` esce
vuoto dallo stesso predicato.

| Livello | Resta | Conseguenza |
| --- | --- | --- |
| `attivita_fatturabili` | `fatturato = t`, `lock_in_fatturazione = t` | `fn_select_attivita_fatturabili` non la seleziona mai più |
| `commesse_attivita` | `stato_emissione = 'EMESSA'` | `fn_emit_attivita_fatturabili_da_commessa` non la ri-emette mai più |

**Due porte chiuse invece di una.** Il commento RD-4 nella funzione descrive
esattamente questo scenario come il livello «che mancava» — e sul percorso
per-fattura è tornato a mancare.

⚠️ **Silenzioso per costruzione**: la funzione ritorna `updated_attivita = 0` e
`riemesse_attivita = 0`, ma nessuno li legge come anomalia. L'operazione
riesce, la fattura sparisce, e il lavoro esce dal giro senza un errore.

---

## 2. La misura sul dato vero (2026-08-26)

Contesto operatore impostato (`app.ruolo_applicativo = 'OPERATORE'`,
`app.current_user_id`) — [[feedback_rls_conteggio_zero_non_e_un_dato]].

```sql
SELECT count(*), count(DISTINCT commessa_id), sum(quantita*prezzo_unitario)
  FROM vendite.attivita_fatturabili
 WHERE fattura_riga_id IS NULL AND fatturato IS TRUE;
```

| | |
| --- | ---: |
| attività orfane | **5** |
| commesse coinvolte | 2 |
| valore | **5.019,00 €** |
| competenza | luglio 2026 (tutte) |
| righe di commessa bloccate su `EMESSA` | **5** |

### 2.1 La ricostruzione del caso, con le prove

| Fatto | Prova |
| --- | --- |
| il lotto è `603` / `LTF-0000679` | `lock_batch_id` delle 5 AF = quello del lotto |
| conteneva **due** fatture, `834` e `835` | `fatturazione_lotti_task_runs` nomina entrambe |
| la `834` ha fallito la numerazione il 24/08 | `task_code = numera_fatture`, `E_FATTURA_NON_NUMERABILE_INCOERENTE` |
| la `834` oggi **non esiste** | assente da `vendite.fatture` |
| le 5 orfane erano della `834`, non della `835` | orfane = billing account **173**; la `835` è del **169** |
| il passo 5 non è avvenuto | le loro `commesse_attivita` sono ancora `EMESSA` |

⭐ Le 10 AF della fattura `835`, sopravvissuta, sono **regolarmente agganciate**:
il difetto colpisce solo ciò che passa dall'eliminazione.

---

## 3. Correzione proposta (D-1)

**Catturare gli identificativi prima di distruggere il legame** — esattamente
come la funzione già fa due passi sopra per `v_righe_ids`.

Prima del `DELETE FROM vendite.fatture_righe`:

```sql
SELECT array_agg(af.id), array_agg(DISTINCT af.commessa_attivita_id)
  INTO v_af_ids, v_ca_ids
  FROM vendite.attivita_fatturabili af
 WHERE (p_lock_batch_id IS NOT NULL AND af.lock_batch_id = p_lock_batch_id)
    OR af.fattura_riga_id = ANY(v_righe_ids);
```

e poi far lavorare i passi 4 e 5 **per id**, non più per legame:

```sql
UPDATE vendite.attivita_fatturabili SET ... WHERE id = ANY(v_af_ids);
UPDATE vendite.commesse_attivita    SET ... WHERE id = ANY(v_ca_ids) AND stato_emissione = 'EMESSA';
```

⭐ **La proprietà che il commento RD-4 chiedeva si rafforza**: oggi i passi 3 e 4
ripetono lo stesso predicato «di proposito, perché se divergessero si
sbloccherebbe un insieme e se ne rimetterebbe in coda un altro». Con la cattura
unica quel rischio **sparisce per costruzione** — l'insieme è uno solo, calcolato
una volta.

⚠️ **Non correggere rendendo la FK `DEFERRABLE`**: sposterebbe il problema
(l'azione scatterebbe a fine transazione, e i passi 3-4 vedrebbero i legami
ancora vivi — funzionerebbe, ma per effetto collaterale di una proprietà
dichiarata altrove, che chiunque potrebbe togliere senza sapere cosa rompe).
La cattura anticipata è locale e leggibile dove serve.

### 3.1 Bonifica delle 5 righe esistenti (D-2)

Vanno riportate a mano in coda, una volta corretta la funzione: `fatturato =
false`, `lock_in_fatturazione = false`, `lock_batch_id = NULL`,
`stato_esecuzione = NULL` sulle 5 AF, e `stato_emissione = 'NON_EMESSA'` sulle 5
`commesse_attivita`.

⚠️ **Da fare DOPO la correzione**, non prima: se qualcuno rieliminasse una
fattura nel frattempo si ricreerebbe il caso.

### 3.2 Presidio (D-3)

pgTAP: eliminare una fattura da un lotto con 2 fatture, e verificare **tre**
cose — che le AF di quella fattura tornino libere, che le loro
`commesse_attivita` tornino `NON_EMESSA`, e che le AF **dell'altra fattura**
restino agganciate (è il motivo per cui esiste la regola C-22, e una correzione
sbagliata lo romperebbe in silenzio).

---

## 4. Il verbo che manca: «Riporta da emettere» (D-4)

Anche corretto il difetto, la casella dei residui resta **senza uscita**: ogni
altra causa che scolleghi un'AF dalla sua riga produrrebbe lo stesso stato, e
oggi il rimedio è una scrittura a mano sul database.

**Nome deciso da Tid**: **«Riporta da emettere»** — nomina la destinazione, come
già fa «Riporta in lavorazione» sui lotti.

**Cosa fa**, e niente di più:

| Tocca | Da | A |
| --- | --- | --- |
| `attivita_fatturabili` | `fatturato = t`, bloccata su un lotto | libera |
| `commesse_attivita` | `stato_emissione = 'EMESSA'` | `'NON_EMESSA'` |

Il lavoro ricompare in **«Da emettere»** e da lì segue il giro normale: nessun
lotto viene rigenerato, nessuna fattura viene ricreata.

⭐ **Sono le stesse due scritture dei passi 4 e 5** di
`fn_cleanup_fatture_by_ids`: il verbo non inventa logica, riusa quella che c'è.
Da valutare se estrarre la coppia in una primitiva condivisa
([[feedback_regola_del_2_estrai_bb]]) — sarebbe la seconda occorrenza.

**Domande al team DB:**

- **Q-1.** Perimetro della funzione: una AF alla volta, oppure la lista delle AF
  orfane di una commessa? Il FE le mostra per commessa.
- **Q-2.** Motivo obbligatorio? `fn_annulla_commessa_attivita` lo pretende, e il
  precedente è forte. Qui però non si distrugge nulla: si **rimette in coda**.
  La mia proposta è **no motivo** — l'azione è recuperativa e reversibile
  (rifatturi, e sei al punto di prima).
- **Q-3.** Permesso: nuovo, o si riusa quello della generazione fatture/lotti?
- **Q-4.** Guard: rifiutare se l'AF **non** è orfana (cioè ha una
  `fattura_riga_id`), con codice parlante — altrimenti il verbo diventa un modo
  per scollegare una fattura viva.

---

## 5. La domanda sul ritiro a monte (Q-5) — modello

Tid: *«lato sorgente, se ad esempio un ordine o un preventivo non deve essere
fatturato, credo si possa chiudere/annullare? Piuttosto che aprire una porta
preferisco, se possibile, un tornare indietro.»*

Il modello **gli dà ragione per iscritto**. In `fn_annulla_commessa_attivita`,
guard 4:

> *«per una riga da push il rimedio è **SEMPRE a monte, sul documento**, sia
> essa emessa o no»*

Una riga nata da un documento non si annulla dalla commessa: è vietato, con
codice dedicato (`E_RIGA_COMMESSA_NON_MANUALE`).

⛔ **Ma il rimedio a monte, oggi, non ritira niente.** Misurato:

```sql
SELECT proname FROM pg_proc
 WHERE prokind='f' AND prosrc ~* 'stato_emissione[[:space:]]*=[[:space:]]*''ANNULLATA''';
```

→ **due sole funzioni**: `fn_annulla_commessa_attivita` (righe manuali,
sourceless) e `fn_annulla_accredito_riga_reso`. Nessuna delle due è raggiunta
annullando un ordine: la transizione `→ ANNULLATO` è generica e data-driven, e
`fn_reconcile_sorgente` usa lo stato del documento **solo per filtrare i push
futuri** (`codice_interno NOT IN ('COMPLETATO','ANNULLATO')`).

**Quindi**: annullare l'ordine impedisce i passaggi successivi, ma ciò che è già
passato in commessa **resta fatturabile**.

> **Q-5 — la domanda.** È voluto, o manca il pezzo? Il guard 4 promette un
> rimedio a monte che, per una riga già passata, non esiste. Se è voluto, va
> scritto dove qualcuno lo legge; se non lo è, è un secondo buco dello stesso
> tipo del §1 — silenzioso, e visibile solo come «lavoro che nessuno fattura
> mai».

⭐ **Nota che toglie urgenza alla Q-5 senza chiuderla.** Per i residui non
serve aspettare la risposta: «Riporta da emettere» li porta a `NON_EMESSA`,
che è lo stato in cui il rimedio a monte è **ammesso** dal guard 5. La sequenza
per Tid diventa *recupera → poi chiudi l'ordine*, e non serve nessuno «Scarta»
sulla dashboard — porta che Tid ha **esplicitamente rifiutato di aprire**:
*«se apriamo questa porta significa che tutto quello che è arrivato qui da tutte
le sorgenti è come se fosse annullato, credo che era una cosa che volevo
evitare»*.

---

## 6. Cosa aspetta BE/FE

| # | Prerequisito | Blocca |
| --- | --- | --- |
| D-1 | correzione `fn_cleanup_fatture_by_ids` | niente lato codice: è una correzione pura |
| D-2 | bonifica delle 5 righe | la verifica in-app della casella a zero |
| D-4 | funzione «Riporta da emettere» + codici errore | il verbo FE sulla card dei residui |
| Q-5 | risposta sul ritiro a monte | niente adesso; cambia la guida operativa |

Lato mio, già fatto e **non** in attesa di nulla: la guida operativa
[cruscotti-fatturazione.md](/guide/cruscotti-fatturazione) ora **avverte** del
difetto in §7.6 e indica la strada sicura (usare *Riporta in lavorazione*
sull'intero lotto, che passa dal ramo `lock_batch_id` e funziona), e la §3.1
spiega che la casella dei residui è una **spia di perdita**, non una tappa.

---

## 7. Trappole

1. ⚠️ **Il ramo che funziona nasconde quello rotto.** *Riporta in lavorazione* e
   *Annulla lotto* passano `lock_batch_id` e liberano correttamente: chi prova
   il difetto da lì **non lo vede**. Va provato da *Elimina dal lotto*, e solo
   da lì.
2. ⚠️ **Un conteggio a zero su queste tabelle non è un dato senza contesto
   operatore**: `commesse_attivita` ha RLS che si accende solo con
   `app.ruolo_applicativo = 'OPERATORE'`, e senza la GUC la tabella appare
   **vuota** ([[feedback_rls_query_contesto_sistema]]). Le misure del §2 sono
   state prese con la GUC impostata.
3. ⚠️ **La vista della dashboard è fail-closed a parte**: senza
   `app.current_user_id` restituisce 0 righe anche a superuser
   (`security_invoker` + `fn_get_emittenti_scope_sr_ids`). Due meccanismi
   diversi, entrambi capaci di far sembrare «pulito» un database sporco.
4. ⚠️ **Il difetto ha colpito una volta sola** (5 righe) perché *Elimina dal
   lotto* è raro. La rarità non è una difesa: è il motivo per cui è rimasto
   invisibile per settimane.
