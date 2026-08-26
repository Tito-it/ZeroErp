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
> ⛔ **Stato: difetto PROVATO, causa isolata e DATATA, piano di sviluppo scritto
> (§9). Nessun file scritto, nessuna migrazione applicata**
> ([[feedback_db_actions_passaggio_team]], [[feedback_mai_applicare_migrazioni_db]]).
>
> 📌 **Seconda passata, 2026-08-26** — analisi critica nel **§8**, piano in **§9**,
> domande nel **§10**, collegamenti con l'altro brief nel **§11**, **stato e
> ordine di esecuzione nel §13**.
> ✅ **Tutte le domande aperte sono state chiuse da Tid il 2026-08-26** (elenco
> nel §13.1). ⛔ **L'esecuzione non è iniziata**: si parte su «procedi», lotto
> per lotto.
> Due paragrafi sono marcati come superati: il **§3** (c'è una correzione più
> piccola) e la nota finale del **§5** (era sbagliata). Non cancellati:
> ⚠️ leggere il §8 **prima** del §3 e del §5.

---

## 1. Il difetto: «Elimina dal lotto» non libera niente

`vendite.fn_elimina_fattura_da_lotto` → `fn_cleanup_fatture_by_ids(ARRAY[id], NULL)`.

Dentro `fn_cleanup_fatture_by_ids` l'ordine delle operazioni è questo:

```text
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

> ⚠️ **SUPERATA dal §8.8 (2026-08-26, seconda passata).** La conclusione di
> questo paragrafo è giusta, ma esiste una modifica **più piccola** — spostare le
> due `UPDATE` prima del `DELETE` invece di catturare un array in più — che
> ottiene lo stesso risultato **e** rende possibile il `CHECK` del §8.7. Il
> paragrafo resta perché l'argomento contro la FK `DEFERRABLE` (§3, in fondo) è
> valido e va tenuto. Piano operativo: §9.1, lotto **L1**.

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

⛔ **NOTA RITIRATA dal §8.5 (2026-08-26, seconda passata): era SBAGLIATA.**
In `fn_annulla_commessa_attivita` il guard **4** (origine) precede il **5**
(stato): una riga nata da un documento viene rifiutata con
`E_RIGA_COMMESSA_NON_MANUALE` *qualunque* sia il suo `stato_emissione`. Portarla
a `NON_EMESSA` non apre nessuna porta — la apre solo per le righe sourceless,
che sono proprio quelle che la Q-5 non riguarda. **La Q-5 non perde urgenza: la
acquista.** Riformulata come Q-5′ nel §10, con le tre strade nel §10.1.
Il testo originale resta qui sotto perché è ciò che è stato creduto:

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

> ⚠️ **Tabella INCOMPLETA dopo la seconda passata**: mancano D-5 (il `CHECK`) e i
> lotti. Versione aggiornata nel **§12**. Questa resta come stato al primo giro.

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
5. ⛔ **Il presidio esiste già ed è verde.**
   `test-fatturazione-reset-lotto-draft.sql` costruisce esattamente questo caso
   e asserisce su `deleted_fatture`, che è una colonna a sinistra di
   `updated_attivita`. Chi corregge D-1 e rilancia la suite vede verde **prima e
   dopo**: il verde non è la prova. Dettaglio nel §8.4, rimedio in L4.
6. ⛔ **La stessa cosa falsa è scritta in quattro posti** — un `COMMENT ON
   COLUMN`, due commenti dentro la funzione e la motivazione di un inventario
   pgTAP. Correggere solo il codice lascia in piedi quattro dichiarazioni che il
   prossimo lettore prenderà per buone. Elenco nel §8.3.

---

## 8. Analisi critica del brief (revisione 2026-08-26, seconda passata)

> **Metodo.** Ogni affermazione del brief è stata riletta contro il **contratto
> vivo** — `pg_constraint`, `pg_proc`, indici, CSV di `80_data`, doc auto-gen —
> non contro la popolazione. Le misure del §2 restano dov'erano: **fatti datati**,
> non motivi ([[feedback_dati_test_non_misurano_la_gravita]]).

### 8.1 Cosa regge, e si dice in una riga

| Affermazione del brief | Esito | Prova |
| --- | --- | --- |
| ordine dei passi in `fn_cleanup_fatture_by_ids` | ✅ esatto | doc auto-gen `fn_cleanup_fatture_by_ids.md` |
| FK `SET NULL`, **non** deferrable | ✅ esatto | `pg_constraint`: `confdeltype='n'`, `condeferrable='f'`, `confupdtype='c'` |
| il ramo `lock_batch_id` non copre il percorso per-fattura (C-22) | ✅ esatto | corpo di `fn_elimina_fattura_da_lotto`: passa `NULL::uuid` |
| il danno è doppio (AF **e** `commesse_attivita`) | ✅ esatto | `v_ca_ids` nasce dallo stesso predicato morto |
| «non correggere rendendo la FK `DEFERRABLE`» | ✅ e va tenuta | è l'argomento giusto: sposta la garanzia in una reloption che nessuno collega alla funzione |
| «solo `fn_annulla_commessa_attivita` e `fn_annulla_accredito_riga_reso` scrivono `ANNULLATA`» | ✅ e **peggio**: nessuna funzione fa `DELETE` su `commesse_attivita` | scansione `pg_proc` su `UPDATE vendite.commesse_attivita` → 5 funzioni; su `DELETE FROM` → **zero** |

⭐ Il §3 del brief («cattura prima di distruggere») **arriva alla conclusione
giusta**. Il §8.8 qui sotto dice che la stessa conclusione si ottiene con una
modifica più piccola e con una proprietà in più.

### 8.2 La regressione ha una data e un changeSet — e non è il 2026-08-03

Il brief presenta il difetto come una proprietà stabile della funzione. Non lo è:
è una **regressione**, e si può datare leggendo solo il contratto.

| Data | changeSet | Cosa cambia |
| --- | --- | --- |
| 2026-02-11 | `20260211-07-update-fn-cleanup-fatture-by-ids` | il `DELETE FROM fatture_righe` c'è già, e la `UPDATE ... OR fattura_riga_id = ANY(v_righe_ids)` c'è già **dopo**. `fattura_riga_id` è un **bigint nudo**: nessuna FK, nessuna azione referenziale → **il predicato tiene** |
| 2026-07-28 | `20260728-11-fk-attivita-fatturabili-fattura-riga` | nasce la FK `ON UPDATE CASCADE ON DELETE SET NULL`. Da questo minuto il predicato è morto |
| 2026-08-03 | `20260803-10-cleanup-unico-reset-commesse-attivita` | RD-4 aggiunge `v_ca_ids` **con lo stesso predicato**. Nasce già morto sul percorso per-fattura |

⛔ **E la scelta di `SET NULL` è motivata per iscritto proprio con l'ordine dei
passi.** Il `COMMENT ON COLUMN` scritto nello stesso changeSet dice:

> *«ON DELETE SET NULL perché `fn_cleanup_fatture_by_ids` cancella le righe
> **prima** di riallineare le attività; l'UPDATE implicito passa il guard
> `guard_fatturato` solo grazie alla GUC `zeroerp.maintenance_reset_lotto_draft`
> che quella funzione imposta.»*

L'ordine dei passi era **visto**. `SET NULL` è stato scelto per far *passare* il
`DELETE`, e nel farlo ha tolto alla `UPDATE` successiva la cosa su cui si
appoggiava. ⭐ È la forma classica: **una FK aggiunta per far riuscire uno
statement, che disarma quello dopo.** Il pezzo mancante non è una svista di
scrittura, è che nessuno ha riletto la funzione *dopo* aver cambiato il vincolo.

### 8.3 La stessa cosa falsa, scritta in quattro posti, verificata in nessuno

Questo è il vero motivo per cui il difetto è sopravvissuto — e cambia D-3.

| # | Dove | Cosa dice | Realtà |
| --- | --- | --- | --- |
| 1 | `COMMENT ON COLUMN attivita_fatturabili.fattura_riga_id` | «la pulizia cancella le righe prima di riallineare le attività» | vero, ed è **la descrizione del difetto scambiata per progetto** |
| 2 | commento RD-4 dentro la funzione | «si raccoglie PRIMA della `UPDATE` qui sotto, **che azzera** `fattura_riga_id`» | accusa la `UPDATE`. Ad azzerare è il `DELETE`, due passi prima |
| 3 | `COMMENT ON FUNCTION fn_cleanup_fatture_by_ids` | «la popolazione delle `commesse_attivita` usa il predicato IDENTICO alla `UPDATE` e si raccoglie PRIMA di essa» | i due predicati sono identici e **identicamente vuoti** |
| 4 | inventario in `test-cleanup-fattura-copertura-figlie-v1.sql` | `fk_attivita_fatturabili_fattura_riga` → `GESTITA`: *«la pulizia lo azzera comunque a mano insieme al lock … e l'attività torna in coda»* | non lo azzera «comunque»: sul percorso per-fattura non lo azzera mai, e l'attività **non** torna in coda |

⚠️ **La riga 4 è la più costosa.** Quel file esiste esattamente per impedire che
una figlia di `fatture_righe` sia trattata male, ed è scritto benissimo: ma
verifica la **classificazione** (ogni FK è inventariata, i `BLOCCO_VOLUTO` non
sono degradati a `CASCADE`), **mai l'effetto**. Una categoria sbagliata con una
motivazione convincente passa tutti i suoi test.

### 8.4 ⛔ Il presidio esisteva, la fixture era giusta, l'asserzione guardava la colonna sbagliata

`db/pgtap/vendite/test-fatturazione-reset-lotto-draft.sql`, ultimo test,
**costruisce esattamente il caso**: lotto DRAFT, `commesse_attivita`, AF portata
a mano a `fatturato = true` + `lock_batch_id` + `fattura_riga_id`, poi chiama
`fn_elimina_fattura_da_lotto`. E asserisce:

```sql
SELECT ok((SELECT deleted_fatture = 1 FROM vendite.fn_elimina_fattura_da_lotto(...)),
          'Reset singola fattura DRAFT');
```

La funzione restituisce **quattro** contatori. Il test ne legge **uno**, e non è
quello che si è rotto: `updated_attivita` vale `0` e nessuno lo guarda.

⭐ Il difetto non è «mancava un test». È: **il test c'era, la fixture era
corretta, e l'asserzione è una colonna a sinistra di quella che conta.**

⚠️ E l'altro file, `test-elimina-fattura-da-lotto-v1.sql` (12 test, il più curato
dei due), **non chiama mai la mutazione su un caso lecito**: l'unica invocazione
sta dentro un `throws_ok`, cioè su un caso che *deve* fallire. Il test 11, che il
file stesso marca 🔴 come «il bug che questo lavoro chiude», asserisce solo su
`fn_check_...`. Il percorso felice della funzione non è eseguito da nessuna parte.

→ **Conseguenza su D-3**: il presidio non è «scrivere un pgTAP». È
**correggere quattro dichiarazioni e aggiungere le asserzioni a una fixture che
esiste già**. Dettaglio in §9, lotto **L4**.

### 8.5 ⛔ La nota che «toglie urgenza alla Q-5» è falsa proprio sulle righe della Q-5

Il §5 chiude con una nota rassicurante:

> *«Per i residui non serve aspettare la risposta: «Riporta da emettere» li porta
> a `NON_EMESSA`, che è lo stato in cui il rimedio a monte è **ammesso** dal
> guard 5. La sequenza diventa recupera → poi chiudi l'ordine.»*

**Non regge, e non per un dettaglio.** In `fn_annulla_commessa_attivita`
l'ordine dei guard è: già-annullata → **origine (4)** → natura (4-bis) →
già-emessa (5). Il guard 4 rifiuta ogni riga con `sorgente_tipo_id IS NOT NULL`
— cioè **ogni riga nata da un documento**, `stato_emissione` irrilevante.

Quindi, per una riga da push:

| Passo | Esito |
| --- | --- |
| «Riporta da emettere» | ✅ la riga torna `NON_EMESSA` |
| `fn_annulla_commessa_attivita` | ⛔ `E_RIGA_COMMESSA_NON_MANUALE` — il guard 4 scatta **prima** del 5 |
| chiudere/annullare l'ordine a monte | ⚠️ blocca i push **futuri**; la riga già passata resta `NON_EMESSA` e **fatturabile** |

⭐ La sequenza «recupera → poi chiudi l'ordine» funziona **solo** sulle righe
sourceless (`ONERE`), che sono proprio quelle che la Q-5 non riguarda. Per le
righe da push il verbo D-4 non è una via d'uscita: è un **ritorno in coda senza
uscita**, e la coda non ne ha una.

⛔ E non c'è una porta di servizio: nessuna funzione fa `DELETE` da
`commesse_attivita`, e le sole due che scrivono `ANNULLATA` sono chiuse a una
riga da push. **Per una riga da push, oggi, l'unico modo di uscire dal giro è
essere fatturata.**

→ **La Q-5 non perde urgenza: la acquista.** Non blocca L1–L4, ma è il
**complemento** di D-4, non un tema parallelo. Riformulata come Q-5′ in §10.

### 8.6 ⚠️ «Emesse non fatturate» non è solo perdita — e questo cambia il perimetro di D-4

`vw_dash_competenza_attivita` assegna la fase così:

```sql
WHEN ca.stato_emissione <> 'EMESSA' AND ca.stato_approvazione <> 'APPROVATA' THEN 'DA_APPROVARE'
WHEN ca.stato_emissione <> 'EMESSA'                                          THEN 'DA_EMETTERE'
WHEN af.fattura_riga_id IS NULL                                              THEN 'EMESSA_NON_FATTURATA'
```

Il terzo ramo chiede **solo** `fattura_riga_id IS NULL`. Non guarda `fatturato`.
Ci finiscono quindi **due popolazioni strutturalmente diverse**:

| Caso | `fatturato` | Cosa è | Va toccato da D-4? |
| --- | --- | --- | --- |
| AF emessa, non ancora presa da un lotto | `false` | **transito legittimo**: `fn_emit_...` crea l'AF e porta la CA a `EMESSA`; la fattura arriva dopo | ⛔ **no** |
| AF orfana dopo l'eliminazione | `true` | il difetto del §1 | ✅ sì |

⚠️ La guida §3.1 dice *«se in quella casella c'è un numero, qualcosa si è
rotto»*. È vero **solo perché** «Fattura adesso» fa emissione e fatturazione in
un passo unico: è una proprietà del *verbo di massa*, non della casella. Il primo
caso non è raro né teorico — è ciò che si vede fra un'emissione mirata e il suo
lotto.

⛔ **Quindi il perimetro di D-4 non può essere «ciò che la card mostra».** Se lo
fosse, il verbo disferebbe emissioni corrette. Serve un predicato che
discrimina, ed è il §8.7.

### 8.7 L'invariante che nessuno ha mai scritto — ed è il vero presidio

La coppia `(fatturato, fattura_riga_id)` è scritta **in un solo statement**, dai
due soli punti che la scrivono, entrambi nel BE:

```python
# backend/apps/vendite/db/pipeline_repository.py — mark_attivita_fatturata
UPDATE vendite.attivita_fatturabili
   SET fattura_riga_id = %s, fatturato = TRUE, ...
```

```python
# stesso file, ramo aggregato
UPDATE vendite.attivita_fatturabili a
   SET fattura_riga_id = c.fattura_riga_id, fatturato = TRUE, stato_esecuzione = 'COMPLETED', ...
```

Lato DB: `fn_select_attivita_fatturabili` scrive `lock_in_fatturazione`/
`lock_batch_id`/`stato_esecuzione`, **mai** `fatturato`; `fn_cleanup_fatture_by_ids`
lo scrive solo a `false`. Nessun percorso produce `fatturato = true` con
`fattura_riga_id` nullo.

⭐ **Cioè: `fatturato IS TRUE AND fattura_riga_id IS NULL` è uno stato che il
modello non ammette e che nessuno scrive di proposito.** È un'invariante — e
**non è dichiarata da nessuna parte**. La tabella ha già un CHECK della stessa
forma (`chk_attivita_fatturabili_rettificata_e_rettifica`: se c'è il puntatore,
il movimento è `RETTIFICA`), quindi non è un idioma nuovo.

Da qui discendono tre cose, tutte nel piano:

1. è il **predicato di perimetro** di D-4 e la **condizione del guard** di Q-4 —
   uno solo, non due (§8.9);
2. ⚠️ **riformulata nel §9.3 dopo la domanda di Tid**: la strada migliore non è
   dichiarare l'invariante con un `CHECK`, è **togliere il doppione** — la
   colonna `fatturato` diventa generata e il disaccordo smette di essere
   possibile. ⛔ **E il predicato qui sotto smette di essere usabile come
   perimetro**: con la colonna generata è sempre falso. Quello vero è nel
   §9.5.0. Il testo qui sotto resta come primo ragionamento.
   Dichiararla come `CHECK` rende il difetto del §1 **impossibile**, non
   «corretto in un punto»: qualunque quarta porta futura che cancelli una riga
   lasciando l'AF fatturata sbatte su un errore, invece di sganciare in silenzio
   ([[reference_check_tabella_e_guard_funzione_dissentono]] — qui il CHECK e la
   funzione **concordano**, perché la funzione viene riordinata prima);
3. la sua **validazione** è la prova che la bonifica D-2 è stata completa — una
   prova migliore di un `count(*)` che torna zero.

⚠️ Il `CHECK` è compatibile con `ON DELETE SET NULL` **solo** se la pulizia
azzera `fatturato` *prima* di cancellare le righe. Cioè: il CHECK **impone per
costruzione** l'ordine corretto, e lo impone a chiunque, per sempre. È il §8.8.

### 8.8 D-1 si fa meglio **spostando**, non aggiungendo

Il §3 propone di catturare `v_af_ids` e `v_ca_ids` prima del `DELETE` e poi
lavorare per id. Funziona. Ma esiste una modifica **più piccola** e con una
proprietà in più: **spostare le due `UPDATE` prima del blocco di `DELETE`**.

| | §3 (cattura per id) | **D-1′ (riordino)** |
| --- | --- | --- |
| cosa si aggiunge | una `SELECT` e un array (`v_af_ids`) | **niente** |
| predicato | duplicato in cattura + due `UPDATE` per id | **uno solo, dov'è sempre stato** |
| `ON DELETE SET NULL` | resta l'attore che sgancia (e sgancia righe già sistemate) | diventa **inerte**: quando il `DELETE` arriva, il puntatore è già `NULL` |
| `CHECK` del §8.7 | ⛔ **impossibile**: il `SET NULL` scatterebbe con `fatturato` ancora `true` e violerebbe il vincolo | ✅ possibile, e diventa il presidio dell'ordine |
| la proprietà che RD-4 chiedeva | ottenuta calcolando una volta | ottenuta **non spezzando mai il legame prima di averlo usato** |

Ordine risultante dentro la funzione (invariato tutto il resto):

```text
guard rettifiche → storno arrotondamento → fn_reset_fondi_fattura
→ raccolta v_righe_ids
→ raccolta v_ca_ids                    (predicato vivo)
→ UPDATE attivita_fatturabili          (predicato vivo)   ← spostata qui
→ UPDATE commesse_attivita             (per v_ca_ids)     ← spostata qui
→ DELETE note / riepiloghi / righe / log / ponte / fatture
```

⚠️ **Verificato che lo spostamento non rompe nulla**: la GUC di manutenzione è
già impostata due passi sopra (quindi `guard_fatturato` e
`guard_quantita_immutabile` restano bypassati); il guard sulle righe rettificate
gira comunque per primo; `commesse_attivita` non ha guard che leggano
l'esistenza della fattura; tutto vive in una transazione sola, quindi nessun
concorrente può vedere lo stato intermedio.

⭐ E si porta dietro il lavoro vero: **riscrivere i tre commenti del §8.3** (il
il #2 e il #3 dentro la funzione, e il #1 sul `COMMENT ON COLUMN`, che va corretto perché oggi
motiva la `SET NULL` con l'ordine sbagliato).

### 8.9 Il guard di D-4 (Q-4) esiste già — e la sua condizione è **esattamente** il perimetro

`trgfn_attivita_fatturabili_guard_fatturato` blocca `UPDATE`/`DELETE` quando
`OLD.fattura_riga_id IS NOT NULL`, salvo GUC di manutenzione.

Su un'AF **orfana** `fattura_riga_id` è `NULL`: il guard **lascia passare**, e
`fn_riporta_...` non deve impostare alcuna GUC. Su un'AF **agganciata** il guard
**blocca**, con `E_RIGA_GIA_FATTURATA`.

⭐ Cioè il guard di riga e il guard di dominio chiesto dalla Q-4 dicono la stessa
cosa da due livelli diversi, senza essersi messi d'accordo. Il verbo nuovo:

- **non imposta la GUC** — impostarla sarebbe l'unico modo di trasformare
  «Riporta da emettere» in un modo per scollegare una fattura viva;
- **solleva il proprio errore parlante** prima (perché un `E_RIGA_GIA_FATTURATA`
  generico non dice all'operatore *cosa* stava facendo);
- e se un giorno quel guard di dominio si rompesse, il trigger tiene comunque.

⚠️ È anche il motivo per cui **la bonifica D-2 non ha bisogno della GUC**: agisce
su righe con `fattura_riga_id` già nullo.

### 8.10 Gemelli cercati, e non ce ne sono

[[reference_presidi_glob_un_livello_ramo_cieco]] dice che quando si trova un
difetto di questa forma si cercano i fratelli. Cercati sul catalogo:

```sql
-- FK non-deferrable in SET NULL il cui padre viene cancellato da una funzione
-- che nomina anche la colonna figlia
```

→ **una sola coppia**: `attivita_fatturabili.fattura_riga_id` ↔
`fn_cleanup_fatture_by_ids`. Delle sei FK che puntano a `vendite.fatture_righe`,
questa è **l'unica** in `SET NULL` (quattro sono `NO ACTION`, una `CASCADE`); ed
è anche l'unica funzione al mondo che fa `DELETE FROM vendite.fatture_righe`
(il BE non ne fa nessuno).

⭐ Il perimetro del difetto è chiuso. Ciò che **non** è chiuso è la classe: senza
il `CHECK` del §8.7, la quinta porta la riapre.

---

## 9. Piano di sviluppo

> ⛔ **Nessun file scritto, nessuna migrazione applicata**
> ([[feedback_mai_applicare_migrazioni_db]]). Questo è il piano; l'esecuzione
> parte su «procedi», lotto per lotto.
> Numerazione `NN` globale per data ([[feedback_liquibase_numerazione_globale_per_data]]),
> `runOnChange: false` ovunque tranne dove indicato, corpo delle funzioni dalla
> **doc auto-gen** e firma dall'ultimo YAML ([[feedback_autogen_firma_perde_type]]).

### 9.0 Il quadro in una tabella

| Lotto | Cosa | Fase | Dipende da | Sblocca |
| --- | --- | --- | --- | --- |
| **L1** | riordino di `fn_cleanup_fatture_by_ids` (**D-1′**) + primitiva condivisa | `20_code` | — | tutto |
| **L2** | ⛔ **cade come codice**: le 5 righe restano come banco di prova di L5 | — | L1 | il collaudo di L5 |
| **L3a** | FK `SET NULL` → **`NO ACTION`** (il muro) | `00_schema` | L1 | chiude la classe |
| **L3b** | `fatturato` → colonna **generata** (il doppione) | `00_schema` | L5 collaudato + consegna BE | toglie l'ambiguità |
| **L4** | presidi: 3 asserzioni + 4 dichiarazioni da correggere (**D-3**) | `db/pgtap` | L1 | — |
| **L5** | verbo «Riporta da emettere» (**D-4**) + codici + permesso | `20_code`+`80_data` | L1 (primitiva) | BE/FE |
| **L6** | documentazione: guida, manual, `COMMENT` | `docs/` | L1, L5 | — |
| **L7** | ritiro a monte (**Q-5′ = strada A**, decisa da Tid 2026-08-26) | `20_code`+`80_data` | L5 | chiude il giro delle righe da push |

⚠️ **L1 → L2 → L3 è una catena rigida.** Invertire L2 e L3 fa fallire la
validazione del `CHECK` sulle righe già sporche; anticipare L2 a L1 ricrea il
caso alla prima eliminazione ([[feedback_bonifica_runonchange_false_fotografa_un_minuto]]:
qui la fotografia è lecita **perché L1 chiude il rubinetto**, ed è la condizione
che quella regola pretende).

### 9.1 L1 — Riordino della primitiva, e la primitiva condivisa

**File**: `db/changelog/migrations_v2/20_code/vendite/20260827-NN-update-fn-cleanup-fatture-by-ids-ordine-ripristino-mctit.yaml`

1. `CREATE OR REPLACE vendite.fn_cleanup_fatture_by_ids(bigint[], uuid)` — corpo
   dalla doc auto-gen, con le due `UPDATE` **spostate** prima del blocco `DELETE`
   (§8.8). Firma e `RETURNS TABLE` **identici**: nessun `DROP`, nessun overload
   (verificare con `pg_get_function_identity_arguments` che non ne nasca uno —
   [[feedback_type_anche_in_firma_e_returns_table]]).
2. Riscrivere i commenti #2 e #3 del §8.3: il colpevole è il `DELETE`, non la
   `UPDATE`, e va detto **perché** l'ordine è quello (altrimenti il prossimo
   passo aggiunto in mezzo lo rompe di nuovo).
3. `COMMENT ON COLUMN vendite.attivita_fatturabili.fattura_riga_id` — correggere
   la motivazione della `SET NULL` (#1 del §8.3): non più «la pulizia cancella
   prima di riallineare», ma «la pulizia riallinea **prima** di cancellare; la
   `SET NULL` è la rete, non il meccanismo».

⭐ **DECISA (Q-6, Tid 2026-08-26): si fa in L1.** Estrarre la coppia di scritture in
`vendite.fn_libera_attivita_fatturabili(p_af_ids bigint[])`
→ `(updated_attivita int, riemesse_attivita int)`, consumata **sia** da L1 sia
da L5. È la **seconda occorrenza** ([[feedback_regola_del_2_estrai_bb]]) e
farla ora significa che la duplicazione **non esiste mai**; farla dopo significa
scriverla due volte e rifattorizzare una funzione appena toccata.

- ✅ Il ramo `lock_batch_id` risolve prima gli id, poi chiama la primitiva — il
  predicato resta uno, e la duplicazione **non esiste mai**.
- ⚠️ *costo*: L1 diventa due oggetti invece di uno, e la primitiva va numerata
  **prima** del `CREATE OR REPLACE` che la usa
  ([[reference_liquibase_autogen_ordina_per_numero]]).

**Verifica L1** (prima di dire che è fatto):

- estrarre l'SQL **dallo YAML**, non riscriverlo
  ([[feedback_verificare_sql_estratto_non_riscritto]]), ed eseguirlo in
  `BEGIN; … ROLLBACK;` con il wrapper **nel file eseguito**
  ([[feedback_verifica_sql_wrapper_transazione]]);
- `liquibase updateSQL` (non applica) + `status`;
- i tre pgTAP che toccano la pulizia devono restare verdi:
  `test-riporta-lotto-a-draft-v1`, `test-annulla-lotto-vuoto-v1`,
  `test-cleanup-fattura-copertura-figlie-v1`.

### 9.2 L2 — Le righe orfane: **niente changeSet** (D-2, riformulata 2026-08-26)

> **Decisione di Tid (2026-08-26)**: *«i dati di test non sono un problema, non è
> obbligatorio ricostruirli; lo facciamo solo se possono essere utili per
> qualcosa, esempio test»*. È anche la regola già scritta in `AGENTS.md`:
> *«prima di sviluppare fix software per correggere dati errati, chiedere se è
> più veloce correggere a mano — i fix software per problemi di dati creano
> strati di codice inutili che poi vanno rimossi»*.

#### 9.2.1 Perché il changeSet cade

Una bonifica in `80_data` sarebbe **la fotografia di un minuto su una macchina
sola** ([[feedback_bonifica_runonchange_false_fotografa_un_minuto]]): su un DB
ricostruito da zero — cioè in CI — quelle righe non esistono e il changeSet
sarebbe un `UPDATE 0` per sempre. Resterebbe in timeline a raccontare un
problema che non c'è.

⛔ **Quindi L2 non è più un lotto di codice.** Diventa un passo operativo, e il
piano ci guadagna un file in meno.

#### 9.2.2 ⭐ E le 5 righe servono: sono il banco di prova di L5

Sono l'**unico caso reale** di attività orfana che il database possiede. Se le
si bonifica a mano adesso, L5 nasce senza niente su cui essere collaudato — e
un verbo di recupero provato solo su fixture costruite non ha mai incontrato il
caso vero.

**Sequenza proposta**, che le usa invece di buttarle:

| Passo | Cosa | Chi lo fa |
| --- | --- | --- |
| 1 | L1 applicato: il rubinetto è chiuso, non se ne creano altre | migrate |
| 2 | le 5 righe **restano dove sono** | nessuno |
| 3 | L5 consegnato | migrate |
| 4 | ⭐ **primo collaudo di «Riporta da emettere»: sulle 5 righe vere** | operatore, dall'interfaccia |
| 5 | la casella «Emesse non fatturate» va a zero, e lo si vede in app | verifica |

⚠️ Se al passo 4 il verbo non le prende, non è la bonifica ad aver fallito: è
**il perimetro di L5 ad essere sbagliato**, ed è meglio scoprirlo lì che su una
fixture compiacente ([[feedback_verifica_dal_percorso_reale]]).

#### 9.2.3 ⚠️ Il vincolo d'ordine che ne discende, ed è nuovo

Il **pezzo 2 di L3** (la colonna generata) ricalcolerebbe `fatturato` su tutte le
righe, portandolo a `false` sulle 5 orfane. Se il perimetro di L5 fosse fondato
su `fatturato`, **il banco di prova sparirebbe** e con lui il verbo.

→ È il motivo per cui il perimetro di L5 **non usa `fatturato`** (§9.5) e per cui
il pezzo 2 di L3 viene **dopo** il collaudo di L5.

### 9.3 L3 — Togliere il doppione, e mettere il muro (Q-7, **riaperta da Tid il 2026-08-26**)

> **La domanda di Tid**: *«non sarebbe logico togliere il timbro?»*
> ⭐ **Sì, ed è la domanda giusta.** La proposta iniziale (un `CHECK` che vieta
> il disaccordo) dava per scontato che i due dati dovessero esistere entrambi.
> Non devono.

#### 9.3.1 `fatturato` è un doppione di `fattura_riga_id IS NOT NULL`

Sono **due colonne per un fatto solo**, e si può leggere dalla loro storia:

| | |
| --- | --- |
| `fatturato` | il **vecchio** marcatore: un booleano, quando il legame con la riga non c'era |
| `fattura_riga_id` | il **nuovo**: fino al 2026-07-28 un `bigint` nudo, poi una FK vera. Il suo `COMMENT` dice *«dal 20260728-12 è l'UNICO»* legame |

La colonna nuova, più precisa, è arrivata; quella vecchia è rimasta. **E il
difetto del §1 è esattamente il minuto in cui le due hanno smesso di dire la
stessa cosa.**

⚠️ E c'è un secondo difetto latente nella stessa colonna: `fatturato` è
**nullable** (default `false`). `fn_select_attivita_fatturabili` filtra
`a.fatturato IS FALSE` — una riga con `fatturato` a `NULL` **non verrebbe mai
selezionata**, e nessuno se ne accorgerebbe.

#### 9.3.2 Quanto costa togliere il doppione: misurato sul catalogo

| Chi tocca `fatturato` | Quanti | Effetto |
| --- | --- | --- |
| **scrive** — `fn_emit_attivita_fatturabili_da_commessa` (lista colonne dell'`INSERT`), `fn_cleanup_fatture_by_ids` (a `false`) | 2 punti DB | da correggere |
| **scrive** — `pipeline_repository.mark_attivita_fatturata` e il ramo aggregato | 2 punti BE | da correggere (⚠️ perimetro BE: richiesta nel brief) |
| **legge** — `fn_select_attivita_fatturabili`, `fn_emit_...`, ~13 file BE, 17 punti FE, 30 file pgTAP, l'indice `ix_attivita_articolo_flags` | ~60 punti | ⭐ **nessuno da toccare**, se la colonna resta col suo nome |

⭐ **Le scritture sono quattro in tutto.** È il motivo per cui la strada B qui
sotto è praticabile.

#### 9.3.3 Le tre strade

| | Cosa | Costo | Cosa garantisce |
| --- | --- | --- | --- |
| **A** — `CHECK` *(proposta iniziale, superata)* | `CHECK (fatturato IS NOT TRUE OR fattura_riga_id IS NOT NULL)` | zero consumatori toccati | vieta il disaccordo, ma **lascia due colonne da tenere allineate a mano** |
| ⭐ **B** — colonna **generata** | `fatturato boolean GENERATED ALWAYS AS (fattura_riga_id IS NOT NULL) STORED NOT NULL` | 4 punti di scrittura; ⚠️ una colonna esistente **non si converte in place**: serve `DROP COLUMN` + `ADD COLUMN` e ricreare `ix_attivita_articolo_flags` (riscrittura di tabella, e va verificato il `RETURNING a.*` di `fn_select_attivita_fatturabili`) | **il disaccordo non è più possibile**: la colonna non si può scrivere, quindi non si può disallineare. E sparisce anche il caso `NULL` |
| **C** — togliere del tutto la colonna | ogni lettura diventa `fattura_riga_id IS NOT NULL` | ~60 punti fra DB, BE, FE e pgTAP | la stessa cosa della B, pagando 15 volte tanto |

⛔ **La C non si fa**: dà quello che dà la B, con un costo che non serve a niente.
⭐ **Se si fa la B, la A sparisce**: un `CHECK` su una colonna che nessuno può
scrivere è sempre vero.

#### 9.3.4 ⛔ Ma togliere il timbro NON basta — e questa è la parte da non saltare

Ciò che tiene il lavoro fuori dal giro **non è solo il timbro**.
`fn_select_attivita_fatturabili` scarta una riga se:

```sql
a.approvato IS TRUE AND a.fatturato IS FALSE AND a.sospesa IS FALSE
AND COALESCE(a.lock_in_fatturazione, false) IS FALSE
```

Con la colonna generata, cancellare una riga di fattura toglierebbe il timbro **da
solo** — ma lascerebbe `lock_in_fatturazione = true`, `lock_batch_id` di un lotto
che non c'è più e la `commessa_attivita` su `EMESSA`. **Il lavoro resterebbe
fuori dal giro lo stesso, solo per un'altra colonna.**

⚠️ Il lucchetto **non** è un doppione e non si può generare: è vero
legittimamente *durante* il giro, quando la riga di fattura non esiste ancora.
Quindi **L1 resta necessario**, e nessuna delle tre strade lo sostituisce.

#### 9.3.5 ⭐ Il muro vero è la chiave esterna

La domanda «cosa impedisce che succeda di nuovo?» ha una risposta più diretta
del `CHECK`: **`fk_attivita_fatturabili_fattura_riga` da `SET NULL` a `NO ACTION`**.

- oggi `SET NULL` dice: *«se cancelli la riga, io sgancio l'attività e vado
  avanti»* — cioè **sgancia in silenzio**, che è la categoria che
  `test-cleanup-fattura-copertura-figlie-v1.sql` chiama *«cancellata IN
  SILENZIO … nessuno se ne accorge mai»*;
- `NO ACTION` dice: *«non puoi cancellare una riga a cui un'attività è ancora
  attaccata»* — l'operazione **esplode**, e chi ha scritto quel codice lo scopre
  subito.

⛔ **Con `NO ACTION`, il difetto di luglio sarebbe esploso il primo giorno.**
Il changeSet `20260728-11` non sarebbe passato, e l'ordine dei passi sarebbe
stato corretto allora invece che a fine agosto.

⚠️ **Perché è sicuro solo DOPO L1**: dopo il riordino, la pulizia sgancia
*tutte* le attività che puntano a una riga in via di cancellazione — sia per
`lock_batch_id`, sia per `fattura_riga_id = ANY(v_righe_ids)`. Quando il `DELETE`
arriva, non c'è più nessun puntatore vivo: la `NO ACTION` non scatta mai sul
percorso buono, e scatta **solo** su una quinta porta che si fosse dimenticata.

#### 9.3.6 Proposta finale per L3

| Pezzo | Fase | Perché |
| --- | --- | --- |
| **1.** FK → `NO ACTION` (resta `ON UPDATE CASCADE`) | `00_schema` | è il muro: rende il difetto rumoroso invece che silenzioso |
| **2.** `fatturato` → colonna **generata** `STORED NOT NULL` | `00_schema` | toglie il doppione: il timbro smette di essere un fatto autonomo |
| **3.** correzione dei 4 punti di scrittura | `20_code` + ⚠️ **richiesta al BE** (2 statement in `pipeline_repository.py`) | senza, il migrate passa e la prima fatturazione fallisce |
| ~~4.~~ ~~`CHECK`~~ | — | ⛔ **cade**: superfluo se il pezzo 2 si fa |

⚠️ **Ordine obbligato**, e il pezzo 2 si stacca dagli altri:

```text
L1 (riordino)  →  L3a (FK NO ACTION)  →  L5 (verbo) + collaudo sulle 5 righe vere
                                                    →  L3b (colonna generata)
```

Il pezzo 2 (**L3b**) va **per ultimo**, per due motivi indipendenti:

1. il `DROP`/`ADD COLUMN` ricalcola `fatturato` su tutte le righe e lo porta a
   `false` sulle 5 orfane: **è il banco di prova di L5 che sparisce** (§9.2.2);
2. dipende da una consegna BE, e L3a no.

⭐ **Buona notizia sul pezzo 3, misurata**: `mark_attivita_fatturata` in
`pipeline_repository.py` **non è chiamata da nessuno** — l'unico riferimento
fuori dal file è un doppione in un test. Lo scrittore vivo di `fatturato` è
**uno solo**, il ramo aggregato. La richiesta al BE si riduce a: togliere quello
statement la colonna, e cancellare il metodo morto.

⚠️ Il pezzo 3 tocca `backend/` ed è **fuori perimetro DB**
([[feedback_perimetro_db_no_modifiche_be]]): va scritto qui come richiesta, non
fatto. Finché non è consegnato, il pezzo 2 **non si applica**.

### 9.4 L4 — I presidi (D-3), che sono quattro correzioni e tre asserzioni

| # | File | Intervento |
| --- | --- | --- |
| a | `test-fatturazione-reset-lotto-draft.sql` | l'ultimo test ha **già la fixture giusta**: aggiungere le asserzioni su `updated_attivita = 1`, su `attivita_fatturabili.fatturato = false`, su `lock_batch_id IS NULL`. ⚠️ Portare la `commesse_attivita` dello slot `RL2` a `EMESSA` **prima** della chiamata (oggi nasce `NON_EMESSA`, e senza quel passo l'asserzione su `riemesse_attivita` sarebbe verde per sottrazione). Alzare il `plan()` |
| b | **nuovo** `test-elimina-fattura-da-lotto-effetti-v1.sql` | il caso a **due fatture** che il §3.2 chiede: le AF della fattura tolta tornano libere, le loro CA tornano `NON_EMESSA`, e le AF **dell'altra fattura restano agganciate** (è la regola C-22, e una correzione sbagliata la romperebbe in silenzio). ⚠️ Fixture **costruite**, non scelte: il file esistente sceglie e salta, e su un DB ricostruito da zero salterebbe tutto |
| c | `test-cleanup-fattura-copertura-figlie-v1.sql` | correggere la motivazione di `fk_attivita_fatturabili_fattura_riga` (§8.3 #4): oggi dichiara un comportamento che non c'è. ⭐ E valutare un test **9-bis**: la categoria `GESTITA` non dice solo «la pulizia la nomina», ma «la pulizia la nomina **prima** di cancellare il padre» |
| d | **nuovo** presidio sul `CHECK` | un `is(pg_get_constraintdef(...), ...)` su `chk_attivita_fatturabili_fatturato_ha_riga`: un vincolo tolto da un `ALTER` futuro sparisce senza che nulla diventi rosso ([[reference_check_tabella_e_guard_funzione_dissentono]]) |

⚠️ Prima di scrivere, `grep` sui pgTAP che già toccano queste tabelle: un guard
nuovo rende rossi test esistenti ([[feedback_guard_breaks_existing_tests]]), e il
`CHECK` di L3 è un guard.
⚠️ Misurare la suite con `ON_ERROR_STOP=1`, altrimenti gli ok sono gonfiati
([[feedback_pgtap_misura_serve_on_error_stop]]).

### 9.5 L5 — «Riporta da emettere» (D-4)

#### 9.5.0 ⛔ Il perimetro NON usa `fatturato` — e questa è la trappola evitata

Il §8.7 proponeva `fatturato IS TRUE AND fattura_riga_id IS NULL`. ⚠️ **Quel
predicato diventa impossibile per costruzione il giorno in cui si applica L3b**:
con la colonna generata, `fatturato` *è* `fattura_riga_id IS NOT NULL`, quindi
la congiunzione è sempre falsa. Un verbo fondato lì **smetterebbe di funzionare
in silenzio**, e il difetto sarebbe della stessa famiglia di quello del §1.

**Perimetro effettivo**, tre condizioni che si leggono come una frase:

```sql
fattura_riga_id IS NULL                              -- non è in nessuna fattura
AND COALESCE(lock_in_fatturazione, false) IS TRUE    -- è ancora lucchettata: nessun giro la riprenderà
AND stato_esecuzione = 'COMPLETED'                   -- e il giro che la lucchettava ha dichiarato di aver finito
```

⭐ **Regge sul modello**: le tre colonne (`fattura_riga_id`, `fatturato`,
`stato_esecuzione = 'COMPLETED'`) sono scritte da **un solo statement vivo**, il
ramo aggregato di `pipeline_repository`. La terza condizione è ciò che separa
l'orfana dal **giro vivo**: `PENDING`/`RUNNING` = lotto in corso, e quello non si
tocca. È anche la risposta al §8.6 (la card contiene due popolazioni diverse).

⭐ E il predicato **sopravvive a L3b**: `stato_esecuzione` non è generata, quindi
il verbo continua a funzionare identico prima e dopo.

**Oggetti**:

| Oggetto | Fase | Nota |
| --- | --- | --- |
| `script.fn_check_attivita_riportabile_da_emettere(bigint[]) → jsonb` | `20_code` | ⭐ è l'idioma del dominio: `fn_check_*` compone i motivi, la mutazione solleva il **primo**, e un pgTAP verifica che le due metà non si separino (è «il test che vale» di `test-elimina-fattura-da-lotto-v1`) |
| `vendite.fn_riporta_attivita_da_emettere(p_attivita_fatturabili_ids bigint[])` → `(riportate int, riemesse_attivita int)` | `20_code` | `SECURITY INVOKER` (RLS e scope emittente restano applicati, come `fn_annulla_commessa_attivita`); consuma la primitiva di L1 |
| append a `80_data/sql/config/messaggi_errore.csv` | `80_data` | id **992+**; ⛔ solo append, nessun loader nuovo ([[feedback_messaggi_errore_no_new_loader]]). Le colonne `causa` e `soluzione` sono prosa vera, non etichette |
| append a `80_data/sql/config/azioni_processo.csv` | `80_data` | id **33**, `area_id = 2`, `permission_codename = riporta_da_emettere`, `pericolosa = f`. ⚠️ CSV, mai `INSERT` a parte ([[feedback_seed_80_data_csv]]) |

**Guard, nell'ordine** (l'ordine è dominio, non stile):

1. parametro: array `NULL`/vuoto → errore parlante, mai «zero righe» silenziose;
2. l'AF non esiste / fuori perimetro RLS → `E_VALORE_MANCANTE`;
3. ⛔ **l'AF non è orfana** (`fattura_riga_id IS NOT NULL`) → codice dedicato.
   È la Q-4, ed è il guard che impedisce al verbo di diventare un modo per
   scollegare una fattura viva;
4. l'AF non è marcata `fatturato` → codice dedicato: non c'è niente da
   riportare, e dirlo è diverso dal punto 3.

**Le due scritture**, in **due statement separati** (padre e figlio nella stessa
CTE non passano mai sotto RLS — [[reference_rls_cte_stessa_snapshot]]):
AF liberata; `commesse_attivita` → `NON_EMESSA` **solo se `EMESSA`**.

**La traccia**: `vendite.commesse_attivita_log`, evento
`RIGA_RIPORTATA_DA_EMETTERE`, `dettaglio` con `attivita_fatturabile_id`,
`lock_batch_id` precedente e `stato_precedente`. ⭐ La colonna `evento` non ha
CHECK né tabella-vocabolario: **nessun seed da estendere** (stesso precedente di
`RIGA_MANUALE_ANNULLATA`). E l'`attivita_fatturabili_log` **non** è la sede: è il
log del flusso consumi, con FK su `attivita_consumi_id`, e nessuno ci scrive.

⭐ **La chiusura del giro è già garantita**:
`fn_emit_attivita_fatturabili_da_commessa` cerca l'AF esistente per
`(sorgente_tipo_id = COMMESSA, sorgente_uid = md5(segment_key))` e la **aggiorna**
invece di inserirne una seconda — quindi liberare l'AF (e non cancellarla) è
esattamente ciò che serve perché la riga rientri nel giro senza urtare
`uq_attivita_fatturabili_commessa_attivita`, che è 1:1.

**pgTAP di L5**: fixture **costruite**; il caso lecito, i due rifiuti (3 e 4), la
simmetria check ↔ mutazione, e l'asserzione che l'evento di log è stato scritto.

### 9.6 L6 — Documentazione

| File | Cosa cambia | Quando |
| --- | --- | --- |
| `docs/it/guide/cruscotti-fatturazione.md` §7.6 | l'avvertenza 🔴 su «Elimina dal lotto» **si toglie** e la riga della tabella torna a dire il vero | con L1 |
| stessa guida §3.1 | la card smette di essere «senza azione»; ⚠️ e va corretta la frase «se c'è un numero, qualcosa si è rotto» → è vera per il verbo di massa, non per la casella (§8.6) | con L5 |
| stessa guida §7.1 | il verbo nuovo entra in tabella con il suo permesso | con L5 |
| `docs/it/dbzero/vendite/manual/fn_cleanup_fatture_by_ids.md` | perché l'ordine è quello, in due righe | con L1 |
| `docs/it/dbzero/vendite/manual/` (nuovo) | scheda del verbo | con L5 |

⛔ Non editare la doc auto-gen ([[feedback_no_hand_edit_autogen_docs]]); ⛔ non
lanciare la build ([[feedback_no_build_doc]]); ⛔ negli YAML e nei `COMMENT` si
cita il **nome** del brief, mai il path `work-in-progress/`
([[feedback_no_path_wip_negli_yaml]]).

⚠️ **La §7.6 è condivisa con l'altro cantiere.** Vedi §11.3.

### 9.7 L7 — Il ritiro a monte (Q-5′ = strada **A**, decisa da Tid il 2026-08-26)

> **La decisione**: *il documento che si chiude ritira ciò che ha spinto*. È
> l'unica delle tre coerente con quello che il guard 4 di
> `fn_annulla_commessa_attivita` promette già per iscritto.

#### 9.7.1 ⛔ Il modello dice cose DIVERSE per sorgenti diverse, e non è dichiarato

Cercando dove agganciare il ritiro è emerso che la domanda «cosa succede alle
righe già spinte quando il documento si chiude?» ha **già due risposte opposte**
nel codice, e nessuna delle due è scritta come regola:

| Sorgente | Cosa fa oggi | Prova |
| --- | --- | --- |
| **Preventivo** | ⛔ **non si annulla affatto** se ha spinto in commessa | `script.fn_check_preventivo_annullabile`: `E_PREV_GIA_IN_COMMESSA` (righe in commessa) e `E_PREV_ANNULLA_COMMESSA_EMESSA` (righe `EMESSA`) |
| **Ordine, DDT, contratto, offerta, reso, consumi** | ✅ si annulla, e **non ritira niente** | nessuna `fn_check_*_annullabile` guarda `commesse_attivita`; la transizione → `ANNULLATO` è data-driven (`config.transizioni_stati_*` + `trgfn_*_guard_transizione`) |

⭐ Cioè: sul preventivo la porta è **sbarrata**, sull'ordine è **aperta e senza
rete**. È l'asimmetria che ha prodotto la Q-5, e la strada A la chiude scegliendo
**una** regola per tutte le sorgenti.

#### 9.7.2 La forma che ne esce, e perché tiene

Le due risposte di oggi non vanno mediate: vanno **divise per stato**, che è la
cosa che le distingue davvero.

| Stato della riga | Regola | Chi la applica |
| --- | --- | --- |
| `NON_EMESSA` | ⭐ **il documento la ritira** → `ANNULLATA` | il ritiro, alla transizione della testata |
| `EMESSA` | ⛔ **la testata NON si chiude**, e il messaggio nomina il rimedio | il guard di transizione, come già fa il preventivo |
| `ANNULLATA` | non si tocca | — |

⭐ **E qui i tre pezzi si incastrano.** Oggi `E_PREV_ANNULLA_COMMESSA_EMESSA`
blocca e **non nomina nessuna via d'uscita** — perché non ce n'era una. Con L5
ce n'è una: *«Riporta da emettere» → poi chiudi il documento → il ritiro prende
le righe*. Il messaggio diventa azionabile, e la sequenza che il §5 del brief
dava per funzionante (e non lo era, §8.5) **diventa vera** — non perché lo stato
cambia, ma perché nasce il ritiro che allo stato risponde.

#### 9.7.3 Gli oggetti

| Oggetto | Nota |
| --- | --- |
| `vendite.fn_ritira_commessa_attivita_da_sorgente(p_sorgente_tipo_id, p_sorgente_uid, p_motivo)` → `(ritirate int)` | ⭐ **una primitiva sola**, non una per documento: la sorgente è polimorfa e la coppia `(sorgente_tipo_id, sorgente_uid)` è già la chiave che tutto il dominio usa ([[reference_sorgente_polimorfa_key_selector]], [[reference_cleanup_primitiva_unica_e_figlie_da_pg_constraint]]). Porta ad `ANNULLATA` le sole `NON_EMESSA` e scrive `commesse_attivita_log` |
| `script.fn_check_sorgente_chiudibile(p_sorgente_tipo_id, p_sorgente_uid)` → `jsonb` | i motivi ostativi, nello stile di `fn_check_preventivo_annullabile`: oggi **solo** «ci sono righe `EMESSA`» |
| aggancio sulle transizioni | ✅ **deciso (Q-10): trigger.** Una funzione trigger **generica** parametrizzata su schema/tabella/sorgente — mai sei copie — in fase `_z90_`, `AFTER UPDATE OF <colonna stato>`. Il **freno** non si scrive: è una condizione in più sui `trgfn_*_guard_transizione` che esistono già. Motivazione completa nel §9.7.6 |
| codici errore | append a `messaggi_errore.csv`, id **992+** insieme a quelli di L5 |

#### 9.7.4 Cosa cambia altrove

- `fn_annulla_commessa_attivita`, guard **4**: il messaggio di
  `E_RIGA_COMMESSA_NON_MANUALE` dice *«il rimedio è SEMPRE a monte, sul
  documento»*. Da L7 quella frase **è vera**, e il messaggio può nominare il
  documento invece di lasciarlo cercare;
- `fn_check_preventivo_annullabile`: `E_PREV_ANNULLA_COMMESSA_EMESSA` **resta** e
  il suo testo guadagna il rimedio; ✅ **`E_PREV_GIA_IN_COMMESSA` si ritira**
  (Q-9, Tid 2026-08-26: *«si allinea al funzionamento degli altri»*) — vietava
  solo perché non c'era modo di disfare il push, e ora c'è. ⚠️ Il codice resta a
  catalogo, non si cancella; smette di essere sollevato;
- guida operativa: il ritiro è un comportamento che l'operatore deve **sapere
  prima** di annullare un ordine — chiudere un documento smette di essere
  un'operazione locale.

#### 9.7.5 ⚠️ Le trappole di L7

1. ⛔ **Un trigger che annulla lavoro è una cascata silenziosa.** Il ritiro deve
   lasciare traccia riga per riga in `commesse_attivita_log`, altrimenti «il
   lavoro è sparito» diventa indistinguibile da un difetto — che è esattamente
   il male da cui nasce questo brief;
2. ⚠️ **`ANNULLATA` è irreversibile**: `fn_approva_commessa_attivita` la filtra e
   non esiste ripristino (dichiarato nel `COMMENT` di
   `fn_annulla_commessa_attivita`). Riaprire un ordine annullato **non** riporta
   indietro le righe: le rifà il push, e solo se il documento è tornato
   spingibile. Da verificare su `fn_reconcile_sorgente` prima di scrivere;
3. ⚠️ **Le righe `RETTIFICA` sono sourceless** ([[reference_rettifiche_e_oneri_sono_sourceless]]):
   il ritiro per sorgente non le raggiunge, ed è giusto. Va detto nel `COMMENT`,
   non lasciato dedurre — è la stessa distinzione origine/natura che ha morso
   `fn_annulla_commessa_attivita` il 2026-08-20;
4. ⚠️ **Il ritiro è una scrittura multipla**: transizione della testata +
   N righe + N eventi di log. Unità atomica ([[feedback_atomicita_madre_db]]).

---

#### 9.7.6 Q-10 — dove si aggancia il ritiro ✅ **DECISO: trigger**

> **La domanda in una riga**: quando un documento si chiude, **chi si ricorda**
> di ritirare il lavoro che aveva spinto in commessa?
>
> ✅ **Risposta di Tid, 2026-08-26: il trigger.** Il confronto resta qui perché
> il *perché* è la parte che serve a chi eseguirà il lotto.

##### Quante porte ci sono, oggi

Non è una domanda retorica: lo stato di una testata si cambia da **molti** posti,
e sono destinati a crescere.

| Da dove | Quanti | Esempi |
| --- | ---: | --- |
| funzioni DB che scrivono sulle testate | **12** | `fn_cambia_stato_preventivo`, `fn_annulla_reso`, `fn_conferma_reso`, `fn_chiudi_contratto_per_successione`, `fn_genera_ddt_da_ordine`, … |
| `UPDATE` diretti dal BE | **4** | `ordini_repository` (×2), `ddt_repository.update_stato` (il commento lo dichiara: *«via UPDATE diretto»*), `offerte_repository` |

##### Le due strade

| | **1. Chiamata esplicita nei servizi** | **2. Trigger sulla testata** |
| --- | --- | --- |
| Come funziona | ogni punto che chiude un documento chiama anche il ritiro | la regola sta attaccata alla tabella: appena lo stato diventa `ANNULLATO`, il ritiro parte da solo |
| L'analogia | un **promemoria sul foglio delle istruzioni** | **la porta che si chiude da sola** |
| ✅ Pro | si vede leggendo il codice; si decide caso per caso; nessun effetto a sorpresa | **non si può dimenticare**: vale per il BE, per le funzioni DB, per le riconciliazioni e per il codice che nessuno ha ancora scritto |
| ⛔ Contro | i punti sono **16 oggi** e cresceranno: ne basta **uno** distratto e il buco torna, silenzioso identico a quello del §1 | è **azione a distanza**: chi legge il codice che annulla l'ordine non vede che sta annullando anche righe di commessa. E il giorno che sbaglia, sbaglia ovunque insieme |

##### ⭐ Perché la proposta è il trigger, e l'argomento è in questo stesso brief

Il difetto del §1 è nato **esattamente** dalla strada 1. La regola *«prima
riallinea, poi cancella»* viveva come **ordine dei passi dentro una funzione**,
cioè come disciplina. È bastato aggiungere una chiave esterna
(`20260728-11`) e la disciplina è saltata **senza un errore**, per quattro
settimane.

La lezione l'abbiamo appena applicata due lotti sopra, in **L3a**: il muro va
messo nella **struttura**, non nel commento. Qui vale identica.

⭐ E c'è un secondo argomento, sul modello: in questo progetto la transizione di
stato **è già data-driven** (`config.transizioni_stati_*`). Il progetto ha
quindi già deciso che *«cosa può diventare cosa»* è una proprietà del **dato**,
non del chiamante. Il ritiro è la **conseguenza** di quella transizione: metterlo
nel chiamante lo separerebbe dalla cosa che lo causa.

##### Il prezzo, e come si paga

1. ⚠️ **Un trigger che annulla lavoro è una cascata silenziosa.** Si paga con il
   **log riga per riga** in `commesse_attivita_log` (§9.7.5): chi chiude un
   ordine deve poter vedere *cosa* ha ritirato, non solo che l'ordine è chiuso;
2. ⚠️ **Una funzione generica, non sei copie.** Il progetto ha già l'idioma
   (`dbops.trgfn_child_requires_active_parent`, parametrizzata su schema/tabella/
   colonna): sei copie divergerebbero, ed è la stessa forma di difetto della
   regola del 2;
3. ⚠️ `automation_lock_columns` e le automazioni per pattern: un trigger nuovo su
   una testata convive con quelli generati, e i `BEFORE ROW` scattano in ordine
   **alfabetico** ([[reference_fk_nuova_genera_guard_che_oscura]]). Il nome va
   scelto sapendolo.

##### ⭐ La forma consigliata: il freno c'è già, si aggiunge solo il motore

Le due metà della regola del §9.7.2 vanno su **due fasi diverse dello stesso
`UPDATE`**, ed è la convenzione trigger già scritta nel progetto:

| Fase | Chi | Cosa fa |
| --- | --- | --- |
| `_a10_` (guard) | ⭐ **esiste già**: `trgfn_ordini_guard_transizione`, `trgfn_ddt_guard_transizione`, `trgfn_offerte_commerciali_guard_transizione`, `trgfn_resi_guard_transizione`, `trgfn_preventivi_guard_transizione` | **rifiuta** la chiusura se ci sono righe `EMESSA` — è il pezzo che dice «prima recupera» |
| `_z90_` (finale) | **nuovo**, generico | porta ad `ANNULLATA` le `NON_EMESSA` e scrive il log — è il pezzo che fa il lavoro |

⭐ Così **la cosa che blocca e la cosa che agisce restano separate**, e la prima è
già dove deve stare: si aggiunge una condizione a guard che esistono, invece di
inventare un secondo posto dove si decide se un documento si chiude.

## 10. Domande aperte, aggiornate

> Le Q-1…Q-5 del brief restano; qui hanno una proposta di risposta motivata sul
> modello, più le domande nuove che l'analisi ha aperto.
>
> 📌 **Stato al 2026-08-26: TUTTE LE DOMANDE SONO CHIUSE.** ✅ Q-5′ (strada
> **A**), Q-6 (primitiva in L1), Q-8 (sì, e va scritto), Q-2 (niente motivo, sì
> log), Q-7 (strada B + muro FK), Q-9 (il preventivo si allinea), Q-10 (trigger).
> ⚠️ Q-1, Q-3 e Q-4 restano sulla **proposta**, non contestata: si procede così
> salvo diverso avviso.
> ⭐ **Q-7 riaperta e migliorata da Tid** — *«non sarebbe logico togliere il
> timbro?»*: la risposta è sì. ✅ **Decisa il 2026-08-26: strada B + muro FK**
> (§9.3.6), spezzata in **L3a** (subito) e **L3b** (per ultimo).
>
> 📌 **E i dati di sviluppo non sono un vincolo** (Tid, 2026-08-26): si
> ricostruiscono solo se servono a qualcosa. Da qui L2 non è più codice (§9.2) e
> le 5 righe orfane diventano il banco di prova di L5.
> Q-1/Q-3/Q-4 restano sulla proposta, che nessuno ha contestato.
> ⭐ La Q-5′ ha aperto **Q-9** e **Q-10**, che nascono dal §9.7.

| # | Domanda | Proposta | Perché |
| --- | --- | --- | --- |
| **Q-1** | perimetro di D-4: una AF o una lista? | **lista di id** (`bigint[]`), con una sola AF come caso della lista | il FE le mostra per commessa e ne recupera più d'una insieme; ed è la stessa forma della selezione che l'altro brief adotta sui lotti (§11.2). Una funzione «una alla volta» costringe il BE a un ciclo, e un ciclo non è atomico |
| **Q-2** ✅ | motivo obbligatorio? | **no motivo**, ma **log obbligatorio**, deciso | il precedente di `fn_annulla_commessa_attivita` pretende il motivo perché *«l'annullamento è irreversibile e l'unica traccia del perché è l'evento di log»*. Qui non si distrugge: si rimette in coda. La traccia serve lo stesso — il *fatto*, non la *ragione* |
| **Q-3** | permesso nuovo o riuso? | **nuovo**, `riporta_da_emettere` | i permessi vivono in `config/azioni_processo.csv` (33ª riga) e il presidio sta sul BE. Riusare `reset_lotto_fattura_draft` legherebbe un verbo di recupero a chi può **cancellare** documenti: sono due mestieri diversi. ⚠️ `pericolosa = f`: l'azione è recuperativa |
| **Q-4** | guard sull'AF non orfana | **sì, con codice dedicato**, e senza GUC | §8.9: il trigger di riga dice già la stessa cosa. Il codice dedicato serve perché `E_RIGA_GIA_FATTURATA` non dice *cosa* si stava tentando |
| **Q-5′** ✅ | il ritiro a monte esiste? | ⛔ no. **Deciso: strada A** — il documento ritira ciò che ha spinto (§9.7) | §8.5: il guard **4** (origine) precede il **5** (stato). Per una riga da push, `NON_EMESSA` non apre nessuna porta. Serve una decisione, non un chiarimento |
| **Q-6** ✅ | primitiva condivisa in L1 o dopo? | **in L1**, deciso | §9.1: è la seconda occorrenza, e farla dopo significa scrivere due volte la stessa coppia e rifattorizzare una funzione appena corretta |
| **Q-7** ✅ | ~~il `CHECK` di L3 si fa?~~ → **togliere il doppione `fatturato`** | **strada B + muro FK**, decisa (§9.3.6) | §8.7: dichiara un'invariante che il codice già rispetta, e rende la classe impossibile invece di correggerne un'istanza. ⚠️ È un impegno permanente: da lì in poi il `SET NULL` su un'AF fatturata è un errore, non un fallback |
| **Q-8** ✅ | «Riporta da emettere» su un'AF di **RETTIFICA**? | **sì, e va detto**, deciso | rimettere in coda una rettifica orfana rigenera la nota di credito al giro successivo — che è già il comportamento dichiarato nella guida §7.6. ⚠️ Ma **origine e natura sono due fatti diversi**, e questa distinzione ha già morso il dominio il 2026-08-20 su `fn_annulla_commessa_attivita`: qui la risposta è opposta (nessuna whitelist) *perché il verbo non distrugge*, e questo va scritto nel `COMMENT`, non lasciato implicito |

### 10.1 ✅ La domanda che stava sotto la Q-5′ — RISPOSTA: strada A

Tid ha rifiutato esplicitamente uno «Scarta» sulla dashboard —
*«se apriamo questa porta significa che tutto quello che è arrivato qui da tutte
le sorgenti è come se fosse annullato»* — e ha chiesto **un tornare indietro**.

Il modello gli dà ragione: il rimedio è a monte. Ma a monte, oggi, **non c'è
nessun rimedio**: annullare l'ordine ferma i push futuri e non ritira ciò che è
già passato. Le tre strade, con quello che costano:

| Strada | Cosa vuol dire | Costo |
| --- | --- | --- |
| ✅ **A** — il documento ritira ciò che ha spinto | annullare/chiudere un ordine porta ad `ANNULLATA` le sue `commesse_attivita` non ancora emesse | **SCELTA da Tid il 2026-08-26.** È il rimedio che il guard 4 **promette già**. Le righe `EMESSA` non si ritirano: la testata non si chiude e il messaggio nomina «Riporta da emettere» — la forma completa è nel **§9.7** |
| **B** — si dichiara che il ritiro non esiste | il guard 4 smette di promettere un rimedio a monte e nomina la strada vera | costo zero di codice, ma la strada vera per una riga da push resta **fatturare** |
| **C** — «Scarta» sulla dashboard | la porta che Tid ha rifiutato | non riproporla se non chiede lui |

⭐ Nessuna delle tre blocca L1–L5. La A è l'unica coerente con ciò che il DB
dichiara oggi; la B è onesta e va scritta dove qualcuno la legge.

⚠️ **Scelta la A, l'analisi ha scoperto che il modello non parte da zero**: sul
**preventivo** la porta è già sbarrata (`E_PREV_GIA_IN_COMMESSA`,
`E_PREV_ANNULLA_COMMESSA_EMESSA`), sull'**ordine** è aperta e senza rete. La A
non aggiunge una regola dove non ce n'erano: ne **unifica due opposte**. Dettaglio
e conseguenze nel §9.7.1; le due domande che ne nascono sono Q-9 e Q-10.

### 10.2 Le due domande che la strada A ha aperto

| # | Domanda | Proposta | Perché |
| --- | --- | --- | --- |
| **Q-9** ✅ | con il ritiro attivo, `E_PREV_GIA_IN_COMMESSA` **si ritira** o il preventivo tiene la sua porta più stretta? | **si ritira — il preventivo si allinea agli altri** (Tid, 2026-08-26) | oggi vieta di annullare un preventivo che ha spinto *perché non c'era modo di disfare il push*. Con il ritiro c'è. Tenerlo significherebbe che l'ordine si annulla e il preventivo no, senza una ragione sul modello. ⚠️ `E_PREV_ANNULLA_COMMESSA_EMESSA` invece **resta**: le righe emesse sono in volo, e quella è una condizione vera |
| **Q-10** ✅ | dove si aggancia il ritiro: **trigger** su ciascuna testata, o chiamata esplicita nei servizi? | **trigger** — deciso da Tid il 2026-08-26. Freno sul guard `_a10_` **che esiste già**, motore su un `_z90_` nuovo e generico | confronto completo nel **§9.7.6** |

---

## 11. Collegamenti con `brief-be-fe-rendi-definitive-sui-lotti.md`

I due brief nascono dalla stessa conversazione del 2026-08-26 e si citano a
vicenda. Ma il legame non è di cortesia: si toccano in **quattro punti**, e in
uno si contendono lo stesso file.

### 11.1 ⭐ Il legame causale: il difetto nasce da una numerazione fallita

Il §2 ricostruisce il caso: la fattura `834` fallisce `numera_fatture` con
`E_FATTURA_NON_NUMERABILE_INCOERENTE` il 24/08, viene eliminata dal lotto, e le
sue 5 attività restano fuori dal giro.

L'altro brief cambia **proprio quel verbo**: «Rendi definitive» esce dalla Lente 1
e nasce sulla lista Lotti, con selezione di righe. Effetto laterale, e vale la
pena scriverlo: oggi, dopo un fallimento di numerazione su una fattura, per
riprovare bisogna agire sul mese o disfare qualcosa; **con la selezione, si
rinumera il solo lotto sistemato**. Meno pressione sul verbo raro, quindi meno
occasioni di incontrare il difetto del §1.

⚠️ Il che **non** cambia la priorità di L1: la rarità non è una difesa (§7.4).

### 11.2 ⭐ La stessa forma per due verbi: la selezione

L'altro brief sceglie il perimetro «selezione di righe» (sua D-4) e riusa il
precedente dell'emissione mirata. La **Q-1 di questo brief chiede la stessa
cosa**, un livello più giù. Risposta coerente: `bigint[]` in ingresso, guard
esplicito su array vuoto (l'altro brief lo chiama *«un errore di chiamante non
deve poter uscire come un dato»* — vale identico qui).

⚠️ **Ciò che invece non si eredita**: la coda. «Rendi definitive» passa da
`dbops.coda_lavori` e ha il problema della dedup (`gruppi_digest`, §5.1 di
quell'altro brief). «Riporta da emettere» è **sincrono**: due scritture, una
transazione, nessun job. Da dire esplicitamente in L5, altrimenti qualcuno lo
accoda per simmetria e si porta dietro un problema che qui non esiste.

### 11.3 ⛔ I due brief scrivono sullo stesso file di guida

`docs/it/guide/cruscotti-fatturazione.md` ha già cambiato **due volte** la riga
di «Rendi definitive» (la §7.1 lo dichiara: *«corretto ad agosto 2026, la riga
precedente indicava la card sbagliata»*), e l'altro brief avverte che la sua
realizzazione sarebbe **la terza**.

Questo brief ne aggiunge **altre due** sullo stesso file:

| Ordine | Chi | Sezione | Cosa |
| --- | --- | --- | --- |
| 1 | questo brief, L1 | §7.6 | via l'avvertenza 🔴 su «Elimina dal lotto» |
| 2 | questo brief, L5 | §3.1 + §7.1 | la card dei residui prende un verbo |
| 3 | altro brief | §7.1 + §6.3 | «Rendi definitive» lascia la Lente 1 |

⚠️ **Da coordinare, non da fare in parallelo.** Se il passo 3 arriva mentre il 2
è in volo, la tabella dei verbi della §7.1 viene riscritta due volte da due mani
e una delle due perde.

### 11.4 ⭐ Il principio che tiene insieme le due decisioni (e che va scritto)

Le due direzioni sembrano opposte: uno **toglie** un verbo dalla Lente 1, l'altro
ce ne **mette** uno. Non lo sono, e la regola che le distingue è una sola:

> **Un verbo sta dove sta l'elenco del suo oggetto.**

- «Rendi definitive» agisce su **lotti** e viveva accanto a un elenco di
  **commesse**: se ne va perché l'elenco giusto sta altrove;
- «Riporta da emettere» agisce su **attività residue**, e la card `Emesse non
  fatturate` è **l'unico posto al mondo** dove quell'elenco esiste: nessuna lista
  di lotti le mostra, perché il loro lotto non c'è più.

⭐ E c'è una simmetria che vale la pena notare: `Emesse non fatturate` è la card
su cui «Rendi definitive» stava **per errore** fino ad agosto 2026. Dopo i due
cantieri, quella card ospiterà **un solo verbo, e quello giusto**.

### 11.5 Cosa NON si tocca a vicenda

| | |
| --- | --- |
| il drill-down che sparisce | è quello della card **`Fatturate`** (altro brief, D-3). Quello della card **`Emesse non fatturate`** resta, ed è il supporto di D-4 |
| il perimetro `SQL_PERIMETRO_LOTTI_NUMERABILI` | è BE, riguarda solo l'altro brief |
| la primitiva condivisa | sono due estrazioni diverse (`gruppi_digest` là, `fn_libera_attivita_fatturabili` qui): stessa regola del 2, nessun oggetto in comune |

---

## 12. Aggiornamento del §6 (cosa aspetta BE/FE)

> ⚠️ La tabella del §6 resta valida ma è **incompleta** dopo questa analisi.
> Versione aggiornata:

| # | Prerequisito | Lotto | Blocca |
| --- | --- | --- | --- |
| D-1′ | riordino di `fn_cleanup_fatture_by_ids` | L1 | niente lato codice: correzione pura |
| D-2 | ⛔ nessuna bonifica: le 5 righe sono il banco di prova di L5 | L2 | niente |
| D-5a | FK → `NO ACTION` | L3a | niente: è un muro |
| D-5b | `fatturato` → colonna generata | L3b | ⚠️ **richiesta al BE**: il ramo aggregato di `pipeline_repository.py` smette di scrivere `fatturato`, e `mark_attivita_fatturata` (morta) si cancella. Finché non arriva, L3b non si applica |
| D-3 | presidi pgTAP + 4 dichiarazioni da correggere | L4 | niente |
| D-4 | `fn_riporta_attivita_da_emettere` + codici + permesso `riporta_da_emettere` | L5 | il verbo FE sulla card dei residui, e il gate permessi lato BE |
| Q-5′ | ✅ ritiro a monte, **strada A** | L7 | niente lato BE finché L7 non è scritto; poi cambia la guida operativa, il testo del guard 4 e il comportamento di «annulla ordine» |

---

## 13. Stato: piano CHIUSO, esecuzione NON iniziata

> ⛔ **Nessun file scritto, nessuna migrazione applicata, nessun changeSet
> creato.** Tid, 2026-08-26: *«mi hai convinto, aggiorna il brief ma non
> iniziare lo sviluppo.»*
> L'esecuzione parte su un «procedi» esplicito, **lotto per lotto**
> ([[feedback_no_commit_autonomo]], [[feedback_mai_applicare_migrazioni_db]]).

### 13.1 Le sette decisioni prese, in una tabella

| # | Decisione | Dove vive |
| --- | --- | --- |
| **Q-2** | «Riporta da emettere» **non** chiede un motivo; scrive **sempre** una riga di registro | §9.5 |
| **Q-5′** | **strada A**: il documento che si chiude ritira le righe `NON_EMESSA` che aveva spinto | §9.7 |
| **Q-6** | la coppia di scritture di ripristino diventa una **primitiva condivisa già in L1** | §9.1 |
| **Q-7** | ~~`CHECK`~~ → **muro** (FK `NO ACTION`) + **togliere il doppione** (`fatturato` generata) | §9.3 |
| **Q-8** | il verbo agisce anche sulle AF di **RETTIFICA**, e va scritto nel `COMMENT` | §9.5 |
| **Q-9** | il **preventivo si allinea agli altri**: `E_PREV_GIA_IN_COMMESSA` smette di essere sollevato | §9.7.4 |
| **Q-10** | il ritiro si aggancia con un **trigger** generico; il freno resta sui guard esistenti | §9.7.6 |

⚠️ **Q-1** (perimetro a lista), **Q-3** (permesso nuovo `riporta_da_emettere`) e
**Q-4** (guard sull'AF non orfana) restano sulla proposta del §10: non
contestate, si procede così.

### 13.2 L'ordine di esecuzione, con i cancelli

```text
L1  riordino fn_cleanup_fatture_by_ids + primitiva condivisa
     │                                    ⚠️ il rubinetto si chiude qui
     ├──▶ L3a  FK SET NULL → NO ACTION            (nessuna dipendenza)
     ├──▶ L4   presidi: 3 asserzioni + 4 dichiarazioni da correggere
     └──▶ L5   «Riporta da emettere» + codici + permesso
                │
                ├──▶ ⭐ collaudo sulle 5 righe VERE  (ex L2: niente changeSet)
                │
                ├──▶ L7  ritiro a monte (trigger + condizione sui guard)
                │
                └──▶ L3b  fatturato → colonna generata
                          ⛔ CANCELLO: richiede la consegna BE
                          ⛔ CANCELLO: dopo il collaudo di L5
L6  documentazione — segue L1 (§7.6) e L5 (§3.1, §7.1)
```

### 13.3 I tre cancelli da non forzare

1. ⛔ **L3b non parte prima della consegna BE.** Il ramo aggregato di
   `pipeline_repository.py` deve smettere di scrivere `fatturato`, e il metodo
   morto `mark_attivita_fatturata` va cancellato. Applicare prima significa
   migrate verde e **prima fatturazione rotta**;
2. ⛔ **L3b non parte prima del collaudo di L5**: ricalcolando `fatturato`
   cancella il banco di prova (§9.2.2);
3. ⛔ **L3a non parte prima di L1**: senza il riordino, la `NO ACTION` farebbe
   esplodere il percorso buono invece della quinta porta.

### 13.4 Cosa serve a Tid, quando si parte

| # | Cosa | Perché |
| --- | --- | --- |
| 1 | un **lotto vero con due fatture** in sviluppo, se è facile da produrre | il collaudo manuale di L1 sul percorso reale, non solo in transazione. ⭐ **Non serve ai pgTAP**: quelli si fabbricano i soggetti da soli, ed è l'unico modo perché restino verdi su un DB ricostruito da zero |
| 2 | **non toccare le 5 righe orfane** | sono il banco di prova di L5 (§9.2.2) |
| 3 | il «procedi» per ogni lotto, e l'autorizzazione **a parole** per ogni migrate | l'hook non si disattiva, e «procedi» sul lavoro non autorizza l'applicazione |
