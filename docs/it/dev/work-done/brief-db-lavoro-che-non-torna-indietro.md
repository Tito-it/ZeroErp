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
> [brief-be-fe-rendi-definitive-sui-lotti.md](../work-in-progress/brief-be-fe-rendi-definitive-sui-lotti.md)
> (l'altro esito della stessa conversazione)
>
> ✅ **CHIUSO il 2026-08-26 — lato DB tutto consegnato e applicato.**
> **16 changeSet** (`20260826-23` … `20260826-38`), 5 file pgTAP nuovi, 18
> corretti, 7 codici errore nuovi, 2 ritirati, 1 permesso, 7 schede concettuali
> nuove e 2 corrette. Consuntivo nel **§14.11**.
>
> ⛔ **La riga qui sotto diceva «nessuna migrazione applicata»: era vera quando è
> stata scritta, la mattina del 2026-08-26, ed è diventata falsa la sera dello
> stesso giorno.** In un documento archiviato una testata stantia è la
> dichiarazione convincente che il prossimo lettore prende per buona — il difetto
> del §8.3, quello che ha tenuto in vita questo stesso cantiere per quattro
> settimane. Per questo la testata è stata riscritta e non lasciata com'era.
>
> 📌 **Dove sono finiti i punti rimasti aperti** (nessuno è stato perso
> nell'archiviazione — verificati uno per uno):
>
> | Cosa restava | Dove vive adesso |
> | --- | --- |
> | `BE-1` la fatturazione ferma · `BE-2` le policy dei 7 codici | ✅ **fatti**, [brief-be-fe-lavoro-che-non-torna-indietro.md](../work-in-progress/brief-be-fe-lavoro-che-non-torna-indietro.md) §2 e §3 |
> | il verbo «Riporta da emettere» a video | stesso brief, §4 e §5 — ⛔ **bloccato** da un prerequisito DB |
> | il prerequisito DB (la chiave del verbo e la card che conta due popolazioni) | [brief-db-residui-competenza-dimensione-e-chiave.md](../work-in-progress/brief-db-residui-competenza-dimensione-e-chiave.md) |
> | ⏸️ la guida operativa: chiudere un documento adesso **ritira lavoro** | brief BE/FE, §7 |
> | ⏸️ il messaggio di `E_RIGA_COMMESSA_NON_MANUALE`, la cui frase da L7b **è vera** | brief DB residui, **D-6** |
> | 🟠 il rientrato `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` in `codici-errore-baseline.sh` | brief BE/FE, §9 — ⚠️ **non è di questo cantiere e la baseline non è stretta** |
>
> 📌 **Seconda passata, 2026-08-26** — analisi critica nel **§8**, piano in **§9**,
> domande nel **§10**, collegamenti con l'altro brief nel **§11**, **stato e
> ordine di esecuzione nel §13**.
> ✅ **Tutte le domande aperte sono state chiuse da Tid il 2026-08-26** (elenco
> nel §13.1). ⚠️ *La riga «l'esecuzione non è iniziata» che stava qui è stata
> tolta: l'esecuzione è iniziata e finita lo stesso giorno (§14).*
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

> ✅ **ESEGUITO il 2026-08-26 — file scritti e verificati, migrazione NON
> applicata.** Il registro con i tre changeSet reali, le prove e i due scarti
> dal piano è nel **§14.1**. Il testo qui sotto resta come pianificato.

**File**: `db/changelog/migrations_v2/20_code/vendite/20260827-NN-update-fn-cleanup-fatture-by-ids-ordine-ripristino-mctit.yaml`
⚠️ *superato*: sono **tre** file datati `20260826`, elenco nel §14.1.

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
| D-1′ ✅ | riordino di `fn_cleanup_fatture_by_ids` — **applicato 2026-08-26** | L1 | niente lato codice: correzione pura |
| D-2 | ⛔ nessuna bonifica: le 5 righe sono il banco di prova di L5 | L2 | niente |
| D-5a ✅ | FK → `NO ACTION` — **applicato 2026-08-26** | L3a | niente: è un muro |
| D-5b | `fatturato` → colonna generata | L3b | ⚠️ **richiesta al BE**: il ramo aggregato di `pipeline_repository.py` smette di scrivere `fatturato`, e `mark_attivita_fatturata` (morta) si cancella. Finché non arriva, L3b non si applica |
| D-3 ✅ | presidi pgTAP — **fatti 2026-08-26** (le dichiarazioni erano **5**, non 4: §14.3c) | L4 | niente |
| D-4 | `fn_riporta_attivita_da_emettere` + codici + permesso `riporta_da_emettere` | L5 | il verbo FE sulla card dei residui, e il gate permessi lato BE |
| Q-5′ | ✅ ritiro a monte, **strada A** | L7 | niente lato BE finché L7 non è scritto; poi cambia la guida operativa, il testo del guard 4 e il comportamento di «annulla ordine» |

---

## 13. Stato: piano CHIUSO, esecuzione INIZIATA (L1 scritto, non applicato)

> ⚠️ **SUPERATO in parte dal §14 (2026-08-26).** L'esecuzione è partita: **L1 è
> scritto e verificato**, e la migrazione **non** è stata applicata. Il testo qui
> sotto resta come stato di partenza.

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

---

## 14. Registro di esecuzione

> Un lotto per sezione, in ordine di esecuzione. ⛔ **Nessuna migrazione è stata
> applicata**: l'autorizzazione si chiede a parole, per quel comando
> ([[feedback_mai_applicare_migrazioni_db]]).

### 14.1 L1 — riordino + primitiva condivisa · ✅ SCRITTO E VERIFICATO, non applicato (2026-08-26)

**I tre changeSet**, in ordine di timeline (l'autogen ordina per `NN` e mescola
`00_schema` e `20_code`: la primitiva ha numero **più basso** del suo
consumatore — [[reference_liquibase_autogen_ordina_per_numero]]):

| # | File | Cosa |
| --- | --- | --- |
| **23** | `00_schema/vendite/20260826-23-comment-attivita-fatturabili-fattura-riga-ordine-mctit.yaml` | `COMMENT ON COLUMN … fattura_riga_id`: la `ON DELETE SET NULL` è **la rete, non il meccanismo** (dichiarazione **#1** del §8.3) |
| **24** | `20_code/vendite/20260826-24-create-fn-libera-attivita-fatturabili-mctit.yaml` | `vendite.fn_libera_attivita_fatturabili(bigint[]) → (updated_attivita, riemesse_attivita)` — la primitiva condivisa (Q-6) |
| **25** | `20_code/vendite/20260826-25-update-fn-cleanup-fatture-by-ids-ordine-ripristino-mctit.yaml` | il riordino **D-1′** + i commenti **#2** e **#3** del §8.3 riscritti |

#### Due scarti dal piano, e perché

1. ⚠️ **Data `20260826`, non `20260827`.** Il piano scriveva `20260827-NN`
   perché immaginava di partire il giorno dopo. La numerazione è **globale per
   data** ([[feedback_liquibase_numerazione_globale_per_data]]) e il 26 agosto
   era arrivato a **22**: i tre lotti prendono 23, 24, 25.
2. ⚠️ **L1 è TRE file, non due.** Il piano metteva il `COMMENT ON COLUMN` dentro
   il changeSet del riordino. È il commento di una **colonna di tabella**, e in
   `migrations_v2` quelli vivono in `00_schema` (287 file contro 24): mescolarlo
   a una funzione avrebbe messo una dichiarazione di schema in un lotto di
   codice. Non ha dipendenze, quindi sta per primo.

#### Una cosa in più, che il piano non chiedeva

⭐ **`p_lock_batch_id` si ancora con `%TYPE`** a
`vendite.attivita_fatturabili.lock_batch_id` — la colonna che il predicato
confronta davvero — invece di restare un `uuid` nudo
([[feedback_type_anche_in_firma_e_returns_table]]).

- ✅ **L'identità della funzione NON cambia**: `%TYPE` si risolve al `CREATE`, e
  `pg_get_function_identity_arguments` continua a rispondere
  `p_fatture_ids bigint[], p_lock_batch_id uuid`. Nessun `DROP`, nessun
  overload, nessun chiamante da toccare.
- ⚠️ Ed è una **fotografia, non un link** ([[feedback_type_in_firma_e_una_fotografia]]):
  chi cambia il tipo di quella colonna deve ricreare anche questa funzione. È
  scritto nell'intestazione del file.
- ⛔ `p_fatture_ids` resta `bigint[]`: `colonna%TYPE[]` non esiste in PostgreSQL.
  E i **quattro risultati sono contatori** (`GET DIAGNOSTICS ROW_COUNT`): non
  specchiano nessuna colonna, quindi ancorarli sarebbe un `%TYPE` finto.

#### La prova che conta: rosso prima, verde dopo

Fixture **costruita** dentro `BEGIN … ROLLBACK` (fattura DRAFT + riga + attività
portata a mano nello stato che la pipeline lascia), poi
`fn_cleanup_fatture_by_ids(ARRAY[fattura], NULL::uuid)` — il **percorso
per-fattura**, l'unico che il difetto colpiva (C-22).

| | `updated_attivita` | `riemesse_attivita` | `fatturato` | lucchetto | `commesse_attivita` |
| --- | ---: | ---: | --- | --- | --- |
| **prima** (codice vivo) | **0** | **0** | `t` | ancora messo | ferma su `EMESSA` |
| **dopo** (con i 3 changeSet) | **1** | **1** | `f` | tolto | `NON_EMESSA` |

⭐ Il difetto si riproduce **esattamente** come descritto nel §1, compreso il
dettaglio che lo rende invisibile: `fattura_riga_id` risulta già `NULL` *prima*
che il ripristino giri — l'azione referenziale ha fatto il suo lavoro a fine
istruzione, e l'`UPDATE` non ha più niente da agganciare.

#### Le altre verifiche

| Cosa | Esito |
| --- | --- |
| SQL **estratto dallo YAML** (non riscritto) ed eseguito in `BEGIN; … ROLLBACK;` col wrapper **nel file eseguito** | ✅ ([[feedback_verificare_sql_estratto_non_riscritto]], [[feedback_verifica_sql_wrapper_transazione]]) |
| `diff` del corpo nuovo contro `pg_get_functiondef` vivo | ✅ cambiano **solo** i quattro punti voluti; il resto è identico byte a byte |
| firma, arità, `RETURNS TABLE`, `prosecdef` | ✅ invariati; nessun overload |
| i due `COMMENT` arrivano interi (nessun letterale troncato) | ✅ 3571 e 1929 caratteri |
| il corpo non nomina più `v_ca_ids`, usa la primitiva, e il ripristino sta **prima** del `DELETE FROM vendite.fatture_righe` | ✅ verificato su `position()` in `prosrc` |
| la primitiva **non** chiama `set_config` e non ha `proconfig` | ✅ (§8.9: impostare la GUC la renderebbe il modo di scollegare una fattura viva) |
| `liquibase status` | ✅ i tre changeSet compaiono, nell'ordine giusto |
| `liquibase updateSQL` (**non applica**) | ✅ exit 0 |
| guardrail `runOnChange`, letterali SQL, `gen_master_autogen --strict` | ✅ tutti verdi |

#### ⛔ I cinque pgTAP restano verdi — e questo NON è la prova

`test-riporta-lotto-a-draft-v1` (11), `test-annulla-lotto-vuoto-v1` (6),
`test-cleanup-fattura-copertura-figlie-v1` (9),
`test-fatturazione-reset-lotto-draft` (12), `test-elimina-fattura-da-lotto-v1`
(12): **verdi prima, verdi dopo**, piano rispettato in tutti e cinque.

⛔ È **esattamente il §8.4**: erano verdi anche con il difetto in casa, perché
asseriscono su `deleted_fatture`, una colonna a sinistra di quella che si era
rotta. Servono a dire *«il riordino non ha rotto altro»*, non *«il riordino
funziona»*. Quella la dice la tabella rosso/verde qui sopra — e le asserzioni
mancanti arrivano con **L4**.

#### ⚠️ Un limite del metodo di verifica pre-apply, che vale per tutti i lotti

Per provare un pgTAP **contro codice non ancora applicato** si ricompone il file
come `BEGIN; <changeSet>; <test>; ROLLBACK;`. Il DDL però lo può fare solo
l'owner, e **`titodb` non è membro di `zeroerp_app`**: `SET ROLE zeroerp_app`
viene rifiutato. Quindi quella corsa gira **come owner**, e la RLS **non è
esercitata** — mentre la corsa vera, dal 2026-08-07, gira come l'applicazione.

⭐ Qui non cambia la conclusione (i cinque file sono verdi anche in modalità
owner **senza** la patch: stessa base di confronto). ⚠️ Ma su un lotto che tocca
`commesse_attivita` sotto policy — **L5** e **L7** — la corsa pre-apply non può
sostituire quella vera: là il verde si guadagna solo dopo il migrate.

#### Cosa resta, e cosa NON è stato fatto

- ⛔ **La migrazione non è applicata.** Serve l'autorizzazione a parole per
  quel comando; l'hook non si disattiva.
- ⚠️ **Le 5 righe orfane sono ancora lì**, ed è voluto: sono il banco di prova di
  L5 (§9.2.2). L1 chiude il rubinetto, non bonifica.
- ▶️ **Prossimi cancelli aperti da L1**: **L3a** (FK → `NO ACTION`), **L4**
  (i presidi), **L5** (il verbo).
  ⚠️ *aggiornato*: L1 è stato **applicato** (§14.1-bis) e **L3a è scritto** (§14.2).

### 14.1-bis L1 — ✅ **APPLICATO** il 2026-08-26 (Tid), verificato sul vivo

`databasechangelog`: `20260826-23/24/25` → `EXECUTED`, ordine 13928–13930
([[feedback_stato_apply_si_legge_dal_databasechangelog]]).

| Verifica sul DB dopo il migrate | Esito |
| --- | --- |
| `pg_get_function_identity_arguments` di `fn_cleanup_fatture_by_ids` | ✅ `p_fatture_ids bigint[], p_lock_batch_id uuid` — invariato, **nessun overload** nato dal `%TYPE` |
| `fn_libera_attivita_fatturabili` esiste, arità 1 | ✅ |
| `COMMENT` della colonna aggiornato | ✅ |
| i cinque pgTAP con il **runner reale** (`zeroerp_app`, RLS attiva) | ✅ tutti `PASS` |
| probe funzionale sul codice **vivo** | ✅ `updated_attivita = 1`, `riemesse_attivita = 1`, attività libera, `commesse_attivita` → `NON_EMESSA` |

⚠️ La doc auto-gen di `fn_cleanup_fatture_by_ids` si è rigenerata da sola e ora
mostra il corpo riordinato: è la conferma che l'oggetto vivo è quello scritto.

---

### 14.2 L3a — FK `SET NULL` → `NO ACTION` · ✅ SCRITTO E VERIFICATO, non applicato (2026-08-26)

**File**: `00_schema/vendite/20260826-26-alter-fk-attivita-fatturabili-fattura-riga-no-action-mctit.yaml`

#### Il censimento delle porte, che è la ragione per cui il muro è sicuro

| Chi può cancellare una riga di fattura | Quanti | Come si è misurato |
| --- | ---: | --- |
| funzioni DB con `DELETE FROM vendite.fatture_righe` | **1** — `fn_cleanup_fatture_by_ids` | scansione su `pg_proc.prosrc` |
| funzioni DB con `DELETE FROM vendite.fatture` (⚠️ `fk_fatture_righe_fat` è **CASCADE**: la testata porta via le righe) | **1** — la stessa | idem |
| backend Django: SQL diretto | **0** | `grep` su `backend/**/*.py` |
| backend Django: modelli ORM su quelle tabelle (cascata ORM) | **0** | `grep` su `db_table` |

⭐ **E il fatto portante, che non è nel piano**: `vendite.attivita_fatturabili`
**non ha row level security** (`pg_class.relrowsecurity = false`). La `SELECT`
che alimenta il ripristino vede quindi *tutte* le righe, anche fuori dallo scope
di chi chiama: quando il `DELETE` arriva, non ne resta nessuna agganciata.
⚠️ Se quella tabella avesse la RLS, questo muro trasformerebbe un «non lo vedo»
in un errore ([[reference_trigger_guard_legge_sotto_rls]]) e sarebbe un'altra
cosa. Va riletto se un giorno la RLS ci arriva.

#### Il `COMMENT` della colonna si riscrive una seconda volta

⚠️ `20260826-23` (L1) motivava la `SET NULL` come *«la rete, non il meccanismo»*.
Era vero finché la `SET NULL` c'era. Toglierla e lasciare quella frase
produrrebbe la **quinta dichiarazione falsa** di questo cantiere: il commento è
riscritto nello stesso changeSet che cambia la cosa che descrive.

#### Le prove

| Prova (in `BEGIN … ROLLBACK`) | Esito |
| --- | --- |
| **porta 1** — `DELETE` di una riga con un'attività attaccata | ✅ **23503**, `fk_attivita_fatturabili_fattura_riga` |
| **porta 2** — `DELETE` della **testata** (cascata su `fk_fatture_righe_fat`) | ✅ **23503**, stesso vincolo |
| percorso buono — `fn_cleanup_fatture_by_ids(…, NULL)` | ✅ `1` / `1`, attività libera, `NON_EMESSA` |
| l'indice `ix_attivita_fatturabili_fattura_riga_id` sopravvive al `DROP`/`ADD` | ✅ (un `DROP CONSTRAINT` di FK non possiede indici) |
| `dbops.fk_index_policy` | ✅ nessuna riga per questa FK, e il **nome non cambia**: niente da riseminare |
| guard automatici rigenerati | ✅ nessuno: `trgfn_child_requires_active_parent` nasce solo verso un padre con colonna `attivo`, e `fatture_righe` non ce l'ha ([[reference_fk_nuova_genera_guard_che_oscura]]) |
| **tutta la suite `vendite`** (213 file) con la patch in transazione, contro la stessa corsa senza | ✅ **zero differenze** |
| i 7 pgTAP di altri schemi che nominano le due tabelle | ✅ zero differenze |
| `liquibase status` · `updateSQL` · guardrail `runOnChange` / letterali · `gen_master_autogen --strict` | ✅ |

#### ⛔ Una trappola per L4, scoperta qui

`pg_get_constraintdef()` **non stampa `ON DELETE NO ACTION`**: è il default, e
la definizione esce come

```text
FOREIGN KEY (fattura_riga_id) REFERENCES vendite.fatture_righe(id) ON UPDATE CASCADE
```

⚠️ Un presidio scritto come `… ~ 'NO ACTION'` sarebbe **verde mai** — o, peggio,
lo si «aggiusta» invertendolo e diventa verde **sempre**. Il presidio di L4 va
scritto su `pg_constraint.confdeltype = 'a'`, oppure sulla stringa esatta qui
sopra. È la stessa famiglia di
[[reference_check_tabella_e_guard_funzione_dissentono]]: il vincolo non si
verifica dal nome di ciò che si crede di aver scritto.

#### Cosa resta

- ⚠️ *superato*: la migrazione **è stata applicata** da Tid lo stesso giorno — §14.2-bis.
- ▶️ Sbloccato da qui: il presidio (d) di **L4**, che asserisce la definizione del vincolo.

### 14.2-bis L3a — ✅ **APPLICATO** il 2026-08-26 (Tid)

`databasechangelog`: `20260826-26` → `EXECUTED`, ordine 13939.

| Verifica sul vivo | Esito |
| --- | --- |
| `pg_constraint.confdeltype` | ✅ `a` (NO ACTION); `confupdtype` = `c`, non deferrable |
| `pg_get_constraintdef` | ✅ `FOREIGN KEY (fattura_riga_id) REFERENCES vendite.fatture_righe(id) ON UPDATE CASCADE` |
| `ix_attivita_fatturabili_fattura_riga_id` | ✅ sopravvissuto al `DROP`/`ADD` |
| `COMMENT` della colonna riscritto | ✅ |
| `scripts/pgtap-baseline.sh vendite` (230 file, runner reale) | ✅ **nessuna regressione**: 5 rossi, tutti già in baseline |

---

### 14.3 L4 — I presidi (D-3) · ✅ FATTO il 2026-08-26 (nessuna migrazione: sono file pgTAP)

> ⭐ Il criterio con cui è stato scritto: **un presidio che è verde anche col
> difetto in casa non è un presidio.** Ogni asserzione nuova è stata provata
> rimettendo in transazione la funzione **pre-L1**, per vedere che diventi rossa.

#### (a) `test-fatturazione-reset-lotto-draft.sql` — 12 → **16** test

La fixture c'era già ed era giusta; mancavano le asserzioni. Aggiunte:
`updated_attivita = 1`, `riemesse_attivita = 1`, l'attività libera
(timbro + legame + lucchetto + `stato_esecuzione`), la `commesse_attivita` a
`NON_EMESSA`.

- ⚠️ La `commesse_attivita` dello slot `RL2` viene portata a **`EMESSA` prima**
  della chiamata: nasceva `NON_EMESSA`, e senza quel passo `riemesse_attivita`
  varrebbe 0 con la correzione **e** senza — verde per sottrazione.
- ⚠️ La mutazione è stata spostata in un'**istruzione separata**, con l'esito
  materializzato in una temp: chiamata dentro l'asserzione, la snapshot di
  statement leggerebbe lo stato *prima* delle scritture
  ([[reference_pgtap_stessa_istruzione_snapshot]]).

| Con la funzione **pre-L1** | Esito |
| --- | --- |
| test 1–12 (compreso `deleted_fatture`) | ✅ **verdi** — è la dimostrazione del §8.4 |
| test 13, 14, 15, 16 | ⛔ **rossi** |

#### (b) `test-elimina-fattura-da-lotto-effetti-v1.sql` — **nuovo**, 11 test

Il caso a **due fatture** che il §3.2 chiedeva, con fixture **costruite**
(commessa, due righe di commessa già `EMESSA`, lotto, due fatture, due righe, due
attività agganciate e lucchettate sul batch del lotto).

⚠️ **Le due fatture si inseriscono direttamente**, non con
`fn_get_or_create_fattura_header`: quella è una *get*-or-create, e due attività
dello stesso billing account / tipo documento / valuta ricadrebbero per
costruzione sulla **stessa** fattura — cioè proprio ciò che questo file non deve
avere. Il soggetto è l'effetto dell'eliminazione, non la creazione della testata.

⭐ **Il file tiene insieme due proprietà opposte, e le prove lo mostrano**:

| Scenario messo in transazione | Cosa diventa rosso |
| --- | --- |
| funzione **pre-L1** (il difetto) | 4, 5, 6, 7 — il lavoro della fattura tolta non torna |
| **«correzione sbagliata»**: `fn_elimina_fattura_da_lotto` che passa il `lock_batch_id` del lotto invece di `NULL` | 4, 5, **8, 9** — libera anche il lavoro dell'**altra** fattura |

⭐ Cioè: la regola **C-22** smette di essere una frase in un commento e diventa
una cosa che qualcuno verifica. Era il punto del §3.2, ed è il motivo per cui
una correzione plausibile poteva rompere il dominio in silenzio.

#### (c) `test-cleanup-fattura-copertura-figlie-v1.sql` — 9 → **11** test

- ⛔ **Corretta la dichiarazione #4 del §8.3**: diceva *«la pulizia lo azzera
  comunque a mano insieme al lock … e l'attività torna in coda»*. Sul percorso
  per-fattura non lo azzerava mai. Ora la motivazione descrive `NO ACTION` +
  «sgancia prima di cancellare», e rimanda al test che lo verifica.
- ⛔ **E una quinta dichiarazione che stava per nascere**: la voce
  `fk_attivita_fatturabili_fattura_riga_rettificata` motivava l'indicizzazione
  per vincolo dicendo *«la stessa tabella ha anche … in SET NULL»*. Da L3a sono
  **entrambe NO ACTION**, e quella frase avrebbe invitato il prossimo lettore a
  verificarla, trovarla falsa e «semplificare» l'inventario tornando a
  indicizzarlo per tabella. ⭐ La ragione vera è più forte: **l'azione
  referenziale è la stessa, ed è il TRATTAMENTO a essere opposto** — una la
  pulizia la sgancia di proposito, l'altra non deve toccarla mai.
- ⭐ **Test 10 (il «9-bis» del §9.4)**: «GESTITA» non vuol dire *«la pulizia la
  nomina»*, vuol dire *«la nomina PRIMA di cancellare il padre»*. È il presidio
  che mancava, ed è ciò che ha permesso al difetto di sopravvivere quattro
  settimane con un inventario verde.
  ⚠️ Il corpo si legge **senza i commenti** (`regexp_replace` sulle righe `--`):
  con i commenti dentro, il nome della tabella compare già nell'intestazione
  della funzione e la posizione misurerebbe la prosa, non il codice.
  ⚠️ E si legge il corpo della **sola** `fn_cleanup_fatture_by_ids`: il
  `tmp_corpo` del test 3 è uno `string_agg` di due funzioni **senza `ORDER BY`**,
  innocuo per un `ILIKE` e fatale per un confronto di posizioni.
  → con la funzione pre-L1 il test 10 è **rosso**.
- ⭐ **Test 11 (il presidio del §9.4d, riformulato)**: il `CHECK` è caduto con la
  Q-7, quindi il presidio è sulla **definizione del vincolo**.

#### ⛔ La trappola del test 11, e perché il presidio è scritto così

`pg_get_constraintdef()` **non stampa `ON DELETE NO ACTION`**: è il default. Un
test scritto come `… ~ 'NO ACTION'` sarebbe **rosso per sempre**, e chi lo
«aggiusta» invertendolo lo rende **verde per sempre**. Il test asserisce quindi
la **stringa intera**, che in un colpo solo fissa colonne, bersaglio, `ON UPDATE`
e il non essere `DEFERRABLE`.
⭐ La prova che morde c'è stata da sola: scritto prima che L3a fosse applicata,
il test 11 era rosso e nel messaggio diceva *have: … ON DELETE SET NULL / want:
… ON UPDATE CASCADE*. È diventato verde con il migrate.

#### Stato della suite

`scripts/pgtap-baseline.sh vendite` (230 file, runner reale `zeroerp_app` + RLS):
**nessuna regressione**, 5 rossi tutti già noti in baseline. Guardrail preambolo
pgTAP: verde, e il debito `throws_ok` resta alla sua soglia.

---

### 14.4 L6 — Documentazione, la parte legata a L1 e L3a · ✅ FATTA il 2026-08-26

| File | Cosa è cambiato |
| --- | --- |
| `docs/it/guide/cruscotti-fatturazione.md` §7.6 | ⛔ tolta l'avvertenza 🔴 «difetto aperto» e la riga della tabella dei verbi torna a dire il vero: le righe della fattura tolta **rientrano** nel giro, quelle delle altre fatture no. ⚠️ Resta detto che le attività rimaste indietro **prima** della correzione non si sbloccano da sole |
| stessa guida §3.1 | la causa è dichiarata chiusa; il 🔴 resta **solo** sul fatto che la card non ha ancora un verbo per i residui già formati |
| `docs/it/dbzero/vendite/manual/fn_cleanup_fatture_by_ids.md` | ⭐ l'ordine dei passi diventa la **prima cosa** della sezione «Cosa ripristina», con il perché; riscritto il paragrafo «le due popolazioni», che descriveva il meccanismo vecchio (due filtri identici scritti due volte); aggiunta la primitiva ai «Vedi anche» |

⚠️ **Non fatta, ed è dell'altro lotto**: la §7.1 (il verbo nuovo in tabella) e la
correzione della frase *«se in quella casella c'è un numero, qualcosa si è
rotto»* (§8.6: la card contiene **due popolazioni**) restano con **L5**.
⚠️ E la §7.1 è il file conteso con l'altro cantiere (§11.3): va coordinata, non
fatta in parallelo.

---

### 14.5 Dove siamo

> ⚠️ **Istantanea di meta' giornata, superata dal §14.11.** Non cancellata:
> e' lo stato in cui il cantiere era quando restavano cinque lotti.

```text
L1   ✅ applicato      riordino + primitiva condivisa
L3a  ✅ applicato      FK SET NULL -> NO ACTION (il muro)
L4   ✅ fatto          presidi: 4+11+2 asserzioni, 2 dichiarazioni corrette
L5   ✅ applicato      «Riporta da emettere» — collaudato sulle 5 righe VERE (in rollback)
L7a  ✅ applicato      fn_check_sorgente_chiudibile + fn_ritira_...
L7b  ✅ applicato      freno + motore generici, 7 trigger, i due divieti RITIRATI (Q-9)
L6   ◐ parziale       L1/L3a fatte; §3.1 corretta; §7.1 attende la consegna BE/FE
L2   —                 le 5 righe orfane restano dove sono (il recupero e' un gesto FE)

L3b  ✅ applicato      `fatturato` e' generata; 15 fixture pgTAP sistemate, suite senza regressioni
                     ⛔ RESTA la consegna BE (§14.8.4): finche' non arriva, la fatturazione e' ferma
```

---

### 14.6 L5 — «Riporta da emettere» (D-4) · ✅ SCRITTO E VERIFICATO, non applicato (2026-08-26)

| # | File | Cosa |
| --- | --- | --- |
| **27** | `20_code/script/20260826-27-create-fn-check-attivita-riportabile-da-emettere-mctit.yaml` | i motivi ostativi, funzione **pura** |
| **28** | `20_code/vendite/20260826-28-create-fn-riporta-attivita-da-emettere-mctit.yaml` | il verbo, `SECURITY INVOKER`, consuma la primitiva di L1 |
| — | `80_data/sql/config/codici_errore.csv` · `messaggi_errore.csv` (id **996–1000**) · `azioni_processo.csv` (id **33**) | ⛔ **solo append**: i mirror `loadUpdateData` esistenti li ripescano, nessun loader nuovo |
| — | `db/pgtap/vendite/test-riporta-attivita-da-emettere-v1.sql` | **nuovo**, 15 test |
| — | `docs/it/dbzero/vendite/manual/fn_riporta_attivita_da_emettere.md` | **nuova**, la scheda del verbo |

#### ⛔ Due trappole incontrate, e la seconda avrebbe fermato il migrate

**1. Il perimetro di *scope* non sta sull'attività.** ⚠️ Misurato sul catalogo:
`vendite.attivita_fatturabili` **non ha row level security**;
`vendite.commesse_attivita` sì (`rls_commesse_attivita_ef_whitelist`, per
`commessa_id`). Una `fn_check_*` che leggesse la sola `attivita_fatturabili`
sarebbe **fail-open sullo scope** — e il danno non sarebbe un permesso concesso
a vuoto: la mutazione libererebbe l'attività (tabella senza RLS) e **non**
riporterebbe la riga di commessa a `NON_EMESSA` (tabella con RLS, zero righe
toccate). ⭐ Cioè **esattamente lo stato spezzato** — un livello torna in coda e
l'altro no — per impedire il quale esiste la primitiva condivisa di L1.
→ L'attività si risolve **passando per `commesse_attivita`**: quel `JOIN` *è* il
perimetro, ed è scritto come tale nel corpo e nel `COMMENT`.

**2. ⛔ Una `preCondition` sui codici errore avrebbe fermato il migrate.** La
prima stesura del changeSet 28 pretendeva i cinque `E_ATTIVITA_*` già a
catalogo. ⚠️ Ma nel master `80_data` gira **dopo** `20_code`
([[feedback_liquibase_phase_ordering_preconditions]]): quella preCondition
sarebbe fallita alla prima applicazione, e su un database ricostruito da zero —
cioè **in CI** — avrebbe fermato l'intero migrate con `onFail: HALT`.
→ Tolta prima di applicare, con il **perché** scritto in testa al file, così la
prossima persona non la rimette. Il presidio della registrazione esiste ed è un
altro: `dbops.vw_codici_errore_da_dichiarare` più il cancello lato backend, che
guardano il database **a regime** e non a metà di una passata.
⭐ Verificato: i due changeSet si applicano puliti su un DB che i codici **non
ha** — cioè nella condizione vera del migrate.

#### Uno scarto dal piano, motivato

Il §9.5 elencava come guard 4 *«l'AF non è marcata `fatturato`»*. ⛔ Non si può:
il §9.5.0 (scritto dopo) stabilisce che il perimetro **non usa `fatturato`**,
perché con la colonna generata di L3b quel predicato diventa sempre falso. Il
guard 4 è quindi diventato **due** guard sulle condizioni vere, che sono anche
più informative:

| | Condizione | Codice | Cosa dice all'operatore |
| --- | --- | --- | --- |
| 4 | non è lucchettata | `E_ATTIVITA_GIA_DA_EMETTERE` | è già in coda: non c'è niente da fare |
| 5 | lucchettata ma `stato_esecuzione <> COMPLETED` | `E_ATTIVITA_IN_LAVORAZIONE` | il lotto sta girando adesso: quello non si tocca |

⭐ È il §8.6 che diventa codice: la card contiene **due popolazioni**, e la
seconda condizione è ciò che le separa.

#### I cinque codici, e perché nessuno è riusato

| Codice | Classe | Perché non un codice esistente |
| --- | --- | --- |
| `E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA` | `TECNICO` | ⛔ non `E_PARAMETRO_INVALIDO`: quel codice è **un debito, non una sede** (D11). Qui il lettore è uno sviluppatore, e il valore nella frase è il nome della funzione — deliberato |
| `E_ATTIVITA_FATTURABILE_NON_TROVATA` | `NON_TROVATO` | copre **due casi di proposito** (riga sparita / fuori perimetro): da fuori sono indistinguibili, e dire «non hai il permesso» rivelerebbe un documento altrui |
| `E_ATTIVITA_ANCORA_IN_FATTURA` | `CONFLITTO_STATO` | ⛔ non `E_RIGA_GIA_FATTURATA` (il guard di riga): quello è generico e non dice **cosa** si stava tentando |
| `E_ATTIVITA_GIA_DA_EMETTERE` | `CONFLITTO_STATO` | «è già a posto» e «è dentro un documento» sono opposti, e il rimedio della prima è **non fare niente** |
| `E_ATTIVITA_IN_LAVORAZIONE` | `CONFLITTO_STATO` | è la condizione che separa l'orfana dal transito legittimo |

⭐ I **valori** nei messaggi sono l'etichetta che l'operatore vede sulla card
(«commessa `<codice>`, competenza `<MM/AAAA>`»), mai un id tecnico; gli id
viaggiano nel **bersaglio** — `COMMESSA` in testa (l'unico posto dove quella
riga si vede), poi `FATTURA` (la cosa da sistemare). ⛔ Sul motivo aggregato
«non trovata» **nessun bersaglio**: un pulsante verso una riga invisibile è un
vicolo cieco.

#### Le prove

15 test su 15 verdi con i changeSet applicati in transazione. Il caso lecito
(3–7, compreso l'evento di log con lotto e stato precedenti), i **quattro
rifiuti** ciascuno col proprio codice (8–12), e i due che valgono di più:

- **13 — la simmetria check ↔ mutazione**: per ogni rifiuto, il codice che la
  `fn_check_*` nomina è lo stesso che il verbo solleva. Se le due metà
  divergessero, l'interfaccia direbbe «si può fare» e il salvataggio no —
  oppure nasconderebbe un'azione che sarebbe passata;
- **14 — il verbo non chiama `set_config`** (letto sul corpo **senza commenti**:
  lì dentro il nome della GUC compare di proposito, per spiegare perché non la
  si imposta).

Altre verifiche: `liquibase status` e `updateSQL` verdi; guardrail
`runOnChange`, letterali SQL, preambolo pgTAP e `gen_master_autogen --strict`
verdi; i tre CSV riparsati con il modulo `csv` (nessuna colonna anomala); i sei
pgTAP che leggono `config.codici_errore` / `azioni_processo` **identici** prima
e dopo i cinque codici nuovi.

#### ℹ️ Un avviso della prova pre-apply, che non è un difetto

Durante i test in transazione, `script.fn_log_error_only` avverte che non riesce
a persistere il log (`fk_error_log_messaggio_errore_id`). ⭐ È corretto così:
quel log passa da **dblink**, cioè da una connessione con una transazione
**sua**, che non vede i codici seminati e non ancora committati. L'errore di
dominio esce giusto lo stesso — i test 8–12 lo dimostrano — e dopo il migrate il
log tornerà a scrivere. ⚠️ Da non inseguire come rosso.

#### 🟠 Un rosso preesistente incontrato, e non toccato

`scripts/codici-errore-baseline.sh` segnala **un rientrato**:
`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`. ⛔ Non è di questo cantiere e la
baseline **non è stata stretta**: farlo qui nasconderebbe la storia di un altro
lavoro dentro questo. Va allineata da chi possiede quel codice
(`scripts/codici-errore-baseline.sh --update`).

#### La documentazione, e cosa NON è stato scritto

| Fatto | Cosa |
| --- | --- |
| ✅ guida §3.1 | ⛔ corretta la frase **falsa** *«se in quella casella c'è un numero, qualcosa si è rotto»* (§8.6): la casella contiene **due popolazioni**, e quella frase era vera solo per il verbo di massa. Ora c'è una tabella che le distingue |
| ✅ `manual/fn_riporta_attivita_da_emettere.md` | la scheda del verbo |
| ⏸️ guida §7.1 | ⚠️ **rinviato alla consegna BE/FE**, non al migrate DB. Mettere il verbo nella tabella dei verbi mentre il pulsante non esiste documenterebbe una cosa che l'operatore non può fare. ⚠️ Ed è il file conteso con l'altro cantiere (§11.3): va coordinato |
| ⏸️ guida §3.1, il 🔴 «la card non ha un'azione» | resta finché il pulsante non c'è: oggi è ancora vero |

#### ⚠️ E finché non si applica, un rosso ATTESO

`db/pgtap/vendite/test-riporta-attivita-da-emettere-v1.sql` è **rosso adesso**, e
lo dice con la frase giusta: *«la funzione script.fn_check_attivita_riportabile_da_emettere
non esiste»*. Diventa verde con il migrate — è già stato provato, 15 su 15, con i
changeSet applicati in transazione. ⛔ Non va messo in baseline: un rosso che ha
una data di scadenza non è debito, è un lotto che aspetta.

#### Cosa resta

- ⛔ **Migrazione non applicata**: serve l'autorizzazione a parole per quel comando.
- ⭐ **Il collaudo vero è sulle 5 righe orfane** (§9.2.2), dall'interfaccia, dopo
  la consegna BE/FE. ⚠️ Se il verbo non le prende, non è la bonifica ad aver
  fallito: è il perimetro a essere sbagliato, ed è meglio scoprirlo lì.
- ▶️ Sbloccato da qui: **L7** (il ritiro a monte) e, dopo il collaudo **e** la
  consegna BE, **L3b**.

---

### 14.6-bis L5 — ✅ **APPLICATO** il 2026-08-26 (Tid), e collaudato sulle 5 righe VERE

`databasechangelog`: `20260826-27/28` → `EXECUTED` (13954, 13955). I cinque codici
sono a catalogo, il permesso `riporta_da_emettere` è la riga 33, e
`test-riporta-attivita-da-emettere-v1` è **verde, 15 su 15**.

#### ⭐ Il collaudo sulle 5 righe, fatto in `BEGIN … ROLLBACK` (non le tocca)

| | |
| --- | ---: |
| tutte e 5 dentro il perimetro del verbo | ✅ (`fattura_riga_id IS NULL`, lucchettate, `COMPLETED`) |
| `fn_check_…` sulle 5 | `[]` — nessun motivo ostativo |
| `fn_riporta_attivita_da_emettere` | **riportate 5, riemesse 5** |
| casella «Emesse non fatturate» dopo | **0** |
| righe di commessa tornate `NON_EMESSA` | 5 (id 551, 552, 553, 554, 1953) |
| eventi `RIGA_RIPORTATA_DA_EMETTERE` scritti | 5, con lotto e stato precedenti |
| ⭐ rientrano nel predicato di `fn_select_attivita_fatturabili` | **5 su 5** |

⛔ **La transazione è stata rollata: le 5 righe sono ancora dove erano.** Il
recupero vero va fatto dall'interfaccia, quando il verbo ci arriva — resta il
banco di prova, ma **la metà DB non è più da collaudare: è collaudata**.

#### ⭐ E qui cade un cancello di L3b

Il §9.2.3 diceva che il pezzo 2 di L3 (la colonna generata) avrebbe ricalcolato
`fatturato` sulle 5 orfane e **fatto sparire il banco di prova**, quindi doveva
venire dopo il collaudo di L5.

⚠️ **Non è più vero, e la ragione è nel §9.5.0**: il perimetro del verbo non usa
`fatturato` — usa `fattura_riga_id`, `lock_in_fatturazione` e
`stato_esecuzione`, e **nessuna delle tre è toccata da L3b**. Il banco di prova
sopravvive. ⭐ Il vincolo d'ordine «L3b dopo il collaudo di L5» **decade**: dei
tre cancelli del §13.3 ne resta **uno**, ed è la consegna BE.

---

### 14.7 L7 — ⛔ La premessa del §9.7.1 è SBAGLIATA, e va corretta prima di agganciare

> **Metodo**: mappa rifatta sul **contratto** (corpo delle funzioni, `pg_proc`,
> `pg_trigger`), con due controesempi sui dati usati solo per smentire.

#### La mappa vera

| Sorgente | Oggi, se ha spinto in commessa | Dove vive il freno |
| --- | --- | --- |
| **PREVENTIVO** | ⛔ **non si annulla** — `E_PREV_GIA_IN_COMMESSA` | `fn_check_preventivo_annullabile`, chiamata da `fn_cambia_stato_preventivo`, da `fn_available_actions_preventivo` **e** da `trgfn_preventivi_guard_annullamento` (trigger: non aggirabile) |
| **ORDINE** | ⛔ **non si annulla** — `E_ORD_ANNULLA_IN_COMMESSA` | `fn_check_ordine_annullabile`, chiamata dalla **Regola 3** di `trgfn_ordini_guard_transizione` (trigger: non aggirabile) |
| **DDT · CONTRATTO · OFFERTA · RESO · CONSUMI** | ✅ si chiudono, e **non ritirano niente** | nessun freno |

⛔ **Il §9.7.1 dice che sull'ordine «la porta è aperta e senza rete». È falso**:
l'ordine è sbarrato esattamente come il preventivo, e da un trigger. L'asimmetria
non è «preventivo vs tutti gli altri»: è **due sorgenti su sei sbarrate, quattro
aperte**.

⚠️ **Conseguenza sulla Q-9.** La decisione era *«il preventivo si allinea agli
altri: `E_PREV_GIA_IN_COMMESSA` smette di essere sollevato»*. Ma «gli altri»
includono l'ordine, che sbarra pure — quindi applicata alla lettera la Q-9
renderebbe il **preventivo il più permissivo** e lascerebbe l'ordine bloccato:
la stessa asimmetria di prima, girata. La logica della strada A implica che si
ritirino **entrambi**, ma Tid ha deciso su una mappa in cui il codice
dell'ordine non compariva. **È la domanda del §14.7.1.**

#### ⭐ Una scoperta che vale oltre questo lotto: le due chiavi polimorfe

| Tabella | Cosa contiene `sorgente_uid` |
| --- | --- |
| `vendite.commesse_attivita` | **`<testata>.uid::text` per TUTTE le sorgenti** — verificato sul corpo delle cinque `fn_list_*_da_pushare`, che compongono tutte `x.uid::text` |
| `vendite.commesse_sorgenti` | **varia**: `uid` per il preventivo, `id::text` per l'ordine |

⭐ È il motivo per cui `fn_check_preventivo_annullabile` confronta `v_uid::text`
e `fn_check_ordine_annullabile` confronta `p_ordine_id::text`: **non sono in
disaccordo**, ognuna segue la chiave della propria sorgente
([[reference_sorgente_polimorfa_key_selector]]).
⛔ Ed è la trappola operativa del ritiro: sbagliare chiave **non solleva niente**
— ritira zero righe. Per questo `fn_ritira_…` restituisce un **conteggio** e chi
la chiama deve guardarlo, e per questo c'è un test apposta.

#### 14.7.1 ⛔ La domanda, e cosa blocca

> Con il ritiro attivo, **si ritirano ENTRAMBI** i freni «ha già spinto in
> commessa» — `E_PREV_GIA_IN_COMMESSA` **e** `E_ORD_ANNULLA_IN_COMMESSA` — o
> solo quello del preventivo come dice la Q-9 alla lettera?

**La proposta**: **entrambi**. Vietavano perché non c'era modo di disfare il
push; adesso c'è, ed è lo stesso per le due sorgenti. Al loro posto resta un
freno solo — «ci sono righe `EMESSA`» — che è una condizione **vera** e ha una
via d'uscita che il messaggio nomina.
⚠️ Non la applico da solo: ritirare un codice che oggi **blocca** l'annullamento
di un ordine è un cambio di comportamento su un documento vivo, e la Q-9 è stata
una decisione esplicita, non un default.

#### 14.7.2 L7a — le due primitive · ✅ SCRITTE E VERIFICATE, non applicate

| # | File | Cosa |
| --- | --- | --- |
| **29** | `20_code/script/20260826-29-create-fn-check-sorgente-chiudibile-mctit.yaml` | i motivi: oggi uno, «ci sono righe `EMESSA`» |
| **30** | `20_code/vendite/20260826-30-create-fn-ritira-commessa-attivita-da-sorgente-mctit.yaml` | il ritiro: porta ad `ANNULLATA` le sole `NON_EMESSA`, e ne lascia traccia |
| — | `codici_errore.csv` · `messaggi_errore.csv` (id **1001–1002**) | `E_RITIRO_SORGENTE_PARAMETRO_MANCANTE` (TECNICO) · `E_SORGENTE_CON_RIGHE_EMESSE` (CONFLITTO_STATO) |
| — | `db/pgtap/vendite/test-ritiro-commessa-attivita-da-sorgente-v1.sql` | **nuovo**, 10 test |

⭐ **Perché queste due si possono scrivere adesso**: servono identiche sotto
qualunque risposta alla §14.7.1. È l'aggancio — il trigger generico e quali
codici si ritirano — che dipende dalla decisione.

⭐ **E il ritiro è l'oggetto di una promessa che il modello faceva già per
iscritto**: il guard 4 di `fn_annulla_commessa_attivita` dice *«per una riga da
push il rimedio è SEMPRE a monte, sul documento»*, e a monte non c'era nessun
rimedio. Le due funzioni sono **complementari**: quella rifiuta le righe con
sorgente e lavora sulle sourceless, questa lavora solo su quelle con sorgente.
⚠️ `ONERE` e `RETTIFICA` restano irraggiungibili dal ritiro, ed è corretto: la
loro via è `fn_annulla_commessa_attivita` e `fn_annulla_accredito_riga_reso`.

**Le prove** (10/10, changeSet in transazione): il ritiro prende **una** riga (la
sola `NON_EMESSA`), non tocca la `EMESSA` né la `ANNULLATA`, scrive la traccia
col motivo e lo stato precedente, il freno nomina il suo codice e **tace** quando
non ci sono più righe emesse, i due guard di parametro rifiutano — e il test 7,
che è quello che vale: **con la chiave sbagliata il ritiro ritira zero e non
solleva**.

#### Cosa NON è stato scritto, e perché

- ⏸️ **L7b — l'aggancio**: il trigger generico `_z90_` e il freno sulle
  transizioni. Dipende dalla §14.7.1. ⭐ Nota per quando si farà: il **motore**
  può essere una funzione trigger sola parametrizzata, perché su
  `commesse_attivita` la chiave è uniforme (`NEW.uid::text`); il **freno**, dove
  una `fn_check_*_annullabile` esiste già (ordine, preventivo), va aggiunto come
  **motivo lì dentro** e non come condizione nel trigger — perché è quella
  funzione a spegnere anche il **pulsante** (`fn_available_actions_*`).
  Sulle altre quattro sorgenti una `fn_check_*` non c'è, e va decisa la forma.
- ⏸️ **Q-9** (ritiro dei due codici): §14.7.1.

---

### 14.8 L3b — `fatturato` diventa generata · ✅ SCRITTO E VERIFICATO ⛔ **non applicabile ancora**

> **Decisione di Tid, 2026-08-26**: *«io consiglio di fare tutto poi il BE si
> allinea»* → **scrivo e applico subito**, accettando che la fatturazione resti
> ferma finché il backend non è allineato.
> ⛔ **La misura fatta scrivendo ha cambiato il quadro**: il costo non è
> «4 punti di scrittura». Sono 4 **più 13 file pgTAP**. Dettaglio in §14.8.3 —
> è l'unica ragione per cui il lotto non è pronto ad andare.

| # | File | Cosa |
| --- | --- | --- |
| **31** | `20_code/vendite/20260826-31-update-fn-libera-attivita-senza-timbro-mctit.yaml` | la primitiva smette di scrivere il timbro |
| **32** | `20_code/vendite/20260826-32-update-fn-emit-attivita-senza-timbro-mctit.yaml` | l'emissione lo toglie dalla lista dell'`INSERT` |
| **33** | `00_schema/vendite/20260826-33-alter-attivita-fatturabili-fatturato-generata-mctit.yaml` | `DROP` + `ADD ... GENERATED ALWAYS AS (fattura_riga_id IS NOT NULL) STORED NOT NULL` + l'indice ricreato |

⚠️ **L'ordine è nei numeri**: 31 e 32 (gli scrittori smettono) prima di 33 (la
colonna cambia), così nessuno dei due incontra mai l'errore. ⭐ La finestra fra
i due **si sana da sola**: `ADD COLUMN ... GENERATED ... STORED` ricalcola tutte
le righe.

#### 14.8.1 Il raggio, censito prima di toccare

| Cosa | Quante | Esito |
| --- | ---: | --- |
| viste che dipendono dalla colonna (`pg_depend`/`pg_rewrite`) | **0** | niente da ricreare |
| indici che la contengono | **1** | `ix_attivita_articolo_flags`, ricreato nello stesso changeSet |
| `CHECK` / policy RLS che la nominano | **0** | — |
| trigger con `UPDATE OF … fatturato` | **0** | — |
| righe in `dbops.automation_lock_columns` | **0** | — |
| lo **storico** | — | è un `to_jsonb(NEW)`, non una copia colonna per colonna: lo spostamento della colonna in fondo non lo tocca |
| `fn_select_attivita_fatturabili` (`RETURNING a.*`) | — | dichiara `RETURNS SETOF vendite.attivita_fatturabili`, cioè il tipo composito **della tabella stessa**: si adatta da solo |
| il backend che legge quelle righe | — | usa una **lista di colonne esplicita**, non `a.*` posizionale |

#### 14.8.2 Le prove (in transazione, poi rollata)

`attgenerated = 's'`, `NOT NULL`, espressione `(fattura_riga_id IS NOT NULL)`;
indice ricreato identico; **zero righe disallineate** su tutta la tabella; e
scrivere la colonna adesso **è rifiutato** (`SQLSTATE 428C9`).

⭐ Quest'ultima è la prova che il cantiere cercava: lo stato «timbrata senza
fattura» — quello che il difetto di luglio produceva in silenzio — **non è più
rappresentabile**. Non è vietato: è impossibile.

#### 14.8.3 ⛔ Il costo vero, che il §9.3.2 non aveva contato

Il §9.3.2 diceva: *«legge — ~60 punti: **nessuno da toccare**»*. È vero per chi
**legge**. Ma fra quei punti ce ne sono che **scrivono**, e quelli si rompono:

| Chi scrive | Quanti | Stato |
| --- | ---: | --- |
| funzioni DB | **2** | ✅ changeSet 31 e 32 |
| backend (`pipeline_repository.py`) | **2** | ⛔ richiesta, §14.8.4 |
| ⛔ **fixture pgTAP** | **13 file** | ⛔ **non ancora sistemate** |

I tredici: `anagrafiche/test-billing-account-guard-parent`,
`vendite/test-accredito-kit-meta-v1`, `test-annulla-accredito-riga-reso-v1`,
`test-annulla-reso-gate-accredito-v1`, `test-attivita-fatturabili`,
`test-elimina-fattura-da-lotto-effetti-v1`, `test-fatturazione-draft`,
`test-fatturazione-reset-lotto-draft`, `test-fn-accredita-riga-reso-v1`,
`test-rinuncia-gate-accredito-v1`, `test-riporta-attivita-da-emettere-v1`,
`test-vw-dash-competenza-v1`,
`test-vw-partite-merce-riconsegna-dopo-nc-v1`.

⛔ **E non è un lavoro meccanico.** Una fixture che scrive `fatturato = true`
**senza** valorizzare `fattura_riga_id` stava costruendo proprio lo stato che
adesso è impossibile: togliere la riga non basta, va deciso se quel test voleva
un'attività **davvero agganciata a una riga di fattura** (e allora la fixture
deve crearne una) oppure soltanto **lucchettata** (e allora il timbro non
c'entrava). Sono tredici decisioni piccole, non tredici `sed`.

⚠️ **Conseguenza sulla decisione «applico subito»**: applicare adesso non ferma
solo la fatturazione (che era messo in conto) — rende rosse tredici fixture, e
un rosso di massa è il modo migliore per perdere di vista quale conta. Il lotto
è **scritto e provato**; manca questo passo prima di poterlo applicare.

#### 14.8.4 ⚠️ La richiesta al BACKEND, precisa

File: `backend/apps/vendite/db/pipeline_repository.py`

| Riga (≈) | Cosa | Azione |
| ---: | --- | --- |
| 2760 | `fatturato = TRUE,` dentro **`mark_attivita_fatturata`** | ⛔ il metodo è **morto**: nessun riferimento fuori dal file oltre a un doppione in un test. **Si cancella**, metodo e test |
| 2962 | `fatturato = TRUE,` nel **ramo aggregato** | è lo scrittore **vivo**: lo statement deve smettere di nominare la colonna. Nient'altro cambia — `fattura_riga_id` è già nello stesso `SET`, e da lì il timbro si deriva |

⭐ **Le letture non si toccano**: `a.fatturato IS FALSE` (righe ~1590 e ~2786)
continua a funzionare identico — una colonna generata si legge come qualunque
altra.

⛔ Finché la riga 2962 esiste, **la prima fatturazione fallisce**: scrivere una
colonna generata è un errore, non un no-op.

---

### 14.8-bis L3b — ✅ **APPLICATO** il 2026-08-26 (Tid), e le fixture sistemate

`databasechangelog`: `20260826-29/30/31/32/33` → `EXECUTED` (13965–13969), quindi
**anche L7a è applicata**. Sul vivo: `attgenerated = 's'`, `NOT NULL`,
espressione `(fattura_riga_id IS NOT NULL)`, indice ricreato, `COMMENT` in
posto.

#### ⛔ Le fixture erano 15, non 13 — e il censimento sbagliato è istruttivo

Il primo conteggio (§14.8.3) diceva 13 file. Erano **15**: la ricerca cercava
`fatturato` **seguito da virgola**, e due file lo hanno **in fondo** alla lista
di colonne — `…, fattura_riga_id, fatturato)`.

⚠️ I due mancanti, `test-lista-commessa-attivita-fatturata-v1` e
`test-esito-gruppi-giro-v1`, non sarebbero rimasti nascosti: erano rossi. Ma il
modo in cui sono saltati fuori conta — non da una rilettura del `grep`, da una
**seconda ricerca fatta con un'altra forma** (scansione delle liste `INSERT`
invece del pattern testuale). ⭐ È la regola dei presidi che globbano un livello
solo: quando ne trovi uno, cerca i gemelli **cambiando strumento**, non
raffinando lo stesso.

#### Come sono state sistemate: tre casi, non uno

| Caso | Quanti | Cosa si è fatto |
| --- | ---: | --- |
| il **puntatore c'è già** nella stessa istruzione (`SET fattura_riga_id = X, fatturato = true`) | 12 | tolta la scrittura del timbro: era **ridondanza già prima**, e ora si deriva. Stato costruito identico |
| il timbro valeva **`false` senza puntatore** | 2 | tolto: `NULL` sul puntatore dà `false` da sé |
| ⛔ il timbro veniva **scritto senza puntatore, e serviva** | 1 | la fixture ha ora una **fattura vera** |

⭐ **Il terzo caso è quello che vale.** In
`anagrafiche/test-billing-account-guard-parent` il test 6 faceva
`SET fatturato = true` per far passare il guard che vieta di staccare un parent
con attività non fatturate. Cioè **diceva «fatturata» a un'attività che nessuna
fattura conteneva**: costruiva esattamente lo stato incoerente che questo
cantiere ha reso impossibile, e su quello interrogava il guard.
Adesso la fixture crea una fattura e una riga, aggancia l'attività, e poi le
smonta — perché il cleanup finale cancella le attività e dal `NO ACTION` di L3a
non si cancella un'attività ancora agganciata.
⚠️ La fatturazione sta **fuori** dal `lives_ok`: è setup, e il test 6 asserisce
che il parent si stacchi, non che si riesca a fatturare.

#### Un falso positivo, e perché non si toglie e basta

`vendite/test-attivita-fatturabili` era nell'elenco per una riga in un
`RETURNING`, cioè una **lettura**: il file passava. ⚠️ Ma asseriva
*«Default fatturato = false»*, e un default non c'è più — il valore si deriva.
L'asserzione resta identica e continua a valere; l'**etichetta** è stata
corretta, perché lasciarla avrebbe mandato il prossimo lettore a cercare un
`DEFAULT` inesistente. È la stessa specie di debito del §8.3.

#### Lo stato della suite

| Verifica | Esito |
| --- | --- |
| i 15 file, runner reale (`zeroerp_app` + RLS) | ✅ **tutti PASS** |
| `scripts/pgtap-baseline.sh vendite` — 232 file | ✅ **nessuna regressione**, 5 rossi tutti già noti |
| i 7 pgTAP di altri schemi che toccano quelle tabelle | ✅ tutti PASS |
| guardrail preambolo pgTAP | ✅, debito `throws_ok` alla sua soglia |
| scritture residue di `fatturato` in tutta `db/pgtap` e `backend/pgtap` | ✅ **zero** (verificato con due ricerche di forma diversa) |

#### ⛔ Cosa resta rotto, e non è un difetto: è la finestra dichiarata

La **fatturazione è ferma** finché il backend non smette di scrivere la colonna
(§14.8.4). Il database è pronto e i test lo dimostrano; l'unico scrittore vivo
rimasto è `pipeline_repository.py` riga ~2962.

---

### 14.9 L7b — L'aggancio · ✅ SCRITTO, VERIFICATO e **APPLICATO** (2026-08-26)

> **La decisione della §14.7.1**: ✅ *«si ritirano **entrambi** i freni»* —
> `E_PREV_GIA_IN_COMMESSA` **e** `E_ORD_ANNULLA_IN_COMMESSA`.

| # | File | Cosa |
| --- | --- | --- |
| **34** | `20_code/vendite/…-create-trgfn-doc-guard-chiusura-sorgente-mctit.yaml` | il **freno** generico, fase `_a10_` |
| **35** | `20_code/vendite/…-create-trgfn-doc-ritira-commessa-attivita-mctit.yaml` | il **motore** generico, fase `_z90_` |
| **36** | `00_schema/vendite/…-create-trigger-ritiro-commessa-su-testate-mctit.yaml` | i **7 trigger** sulle quattro testate |
| **37** | `20_code/script/…-update-fn-check-ordine-annullabile-ritiro-mctit.yaml` | l'ordine ritira il suo divieto e delega |
| **38** | `20_code/script/…-update-fn-check-preventivo-annullabile-ritiro-mctit.yaml` | il preventivo ritira il suo e delega |
| — | `codici_errore.csv` | i due codici marcati `obsoleto_dal = 2026-08-26`, con il perché nella nota |
| — | `db/pgtap/vendite/test-ritiro-alla-chiusura-documento-v1.sql` | **nuovo**, 7 test |

#### ⭐ Tre scelte che migliorano il piano, e una che lo corregge

**1. Ci si aggancia a `is_abortito`, non a `'ANNULLATO'`.** Il piano
parametrizzava il trigger su un *codice di chiusura*. ⭐ Ma tutti e quattro i
vocabolari (`config.stati_doc_preventivi|ordini|ddt|contratti`) hanno già il
flag **`is_abortito`** — verificato. È lo stesso asse su cui il dominio già
lavora, e il giorno che nasce un secondo stato abortito il guard lo copre **da
solo**. Con un codice cablato non l'avrebbe coperto, e in silenzio.

**2. Le testate sono QUATTRO, non sei.** Sono quelle che spingono davvero,
cioè quelle con una `fn_list_*_da_pushare`: preventivi, ordini, DDT, contratti.
⚠️ `attivita_consumi` **non si monta** — non ha una colonna di stato con
vocabolario (ha `stato_calcolo`, un varchar senza `is_abortito`) ed è un flusso
non ancora acceso. Offerte e resi non spingono: non hanno niente da ritirare.

**3. ⛔ Sui preventivi si monta SOLO il motore.** Q-9 ha deciso che
`E_PREV_ANNULLA_COMMESSA_EMESSA` **resta**. Montando anche il freno generico, la
**stessa condizione** sarebbe uscita con **due codici diversi** a seconda di
quale trigger parla per primo: per l'operatore lo stesso rifiuto con due nomi,
per il frontend due `reason_key` da mappare.
⭐ E la regola resta **una sola** lo stesso: la `fn_check_preventivo_annullabile`
**delega** il conteggio a `script.fn_check_sorgente_chiudibile` e si limita a
**rietichettare** il motivo col proprio codice. *Una implementazione, due
superfici.*

**4. Il freno non si scrive nel trigger dove una `fn_check_*` esiste già.** Sul
preventivo e sull'ordine il gate è la loro `fn_check_*_annullabile`, ed è la
stessa funzione che accende il **pulsante** (`fn_available_actions_*`): mettendo
la condizione lì, l'azione smette di essere proposta invece di fallire al click.

#### ⛔ Un cambio di chiave che sarebbe passato inosservato

Il vecchio conteggio dell'ordine leggeva `vendite.commesse_sorgenti` con
**`id::text`**; la primitiva legge `vendite.commesse_attivita` con
**`uid::text`**. ⚠️ Sono chiavi polimorfe **diverse e deliberate**: passare
quella vecchia non darebbe un errore, darebbe **zero motivi** — cioè un freno
che lascia passare tutto. È scritto nel corpo, nel `COMMENT` e nella nota del
codice ritirato, ed è il motivo per cui il ritiro restituisce un **conteggio**
invece di `void`.

#### Le prove (7/7, e con gli oggetti vivi)

| # | Cosa | Perché conta |
| ---: | --- | --- |
| 2 | con una riga `EMESSA` la chiusura è **rifiutata**, col suo codice | il freno |
| 3 | la `fn_check_*` nomina lo **stesso** motivo che il guard solleva | le due metà non si separano |
| 4 | tolta la riga emessa, la chiusura **passa** | ⭐ è il presidio di **Q-9**: prima veniva rifiutata; se qualcuno rimettesse il divieto, torna rosso |
| 5 | le righe sono `ANNULLATA`, con la traccia, il motivo e lo stato precedente | il prezzo dell'azione a distanza |
| 6 | le righe di **un altro documento**, nella stessa commessa, non sono toccate | ⛔ se diventa rosso, il ritiro lavora per *commessa* invece che per *sorgente* |
| 7 | riscrivere lo **stesso** stato non ritira di nuovo | nessun doppione nel registro |

⭐ **Il test 4 fa un `UPDATE` nudo sulla testata**, senza passare da nessuna
funzione di dominio: è precisamente il percorso che una chiamata esplicita nei
servizi **non** coprirebbe, ed è l'argomento di Q-10 messo alla prova invece che
dichiarato.

Verifiche sul vivo: i **7 trigger** montati come previsto (preventivi solo
`_z90_`); i due codici **non più sollevati** da nessuna funzione (occorrenze
residue solo nei commenti, verificato a commenti spogliati) e marcati
`obsoleto_dal` a catalogo. Guardrail `runOnChange`, letterali SQL, preambolo
pgTAP e `gen_master_autogen --strict`: verdi.

#### ⛔ Una regressione, trovata da Tid — e che avrei dovuto prevedere

`vendite/test-ordini-guard-transizione-v1`, test **7 e 8**: asserivano che un
ordine già in commessa venisse **rifiutato** con `E_ORD_ANNULLA_IN_COMMESSA`.
Cioè asserivano **la regola che abbiamo appena ritirato**.

⚠️ **L'errore di metodo è mio, ed è nominabile.** La regola in casa —
[[feedback_guard_breaks_existing_tests]] — dice di cercare i test esistenti
prima di toccare un guard, e io l'ho applicata solo nella direzione
*restrittiva* (un guard nuovo rende rossi i test). Qui il guard è stato
**allargato**, e un test che asseriva la restrizione è caduto per lo stesso
meccanismo, al contrario. ⭐ La regola vale nei due sensi: *quando si cambia un
guard si cercano i suoi consumatori dal CODICE*, non dalla direzione del cambio
([[feedback_consumatori_messaggio_si_cercano_dal_nome]]).

**Come è stata sistemata** — non spegnendo l'asserzione, ma portandola sulla
regola nuova:

| | prima | adesso |
| --- | --- | --- |
| cosa costruisce la fixture | l'ordine collegato a una commessa | **più** una riga di commessa già `EMESSA` |
| cosa asserisce il 7 | rifiutato perché «ha spinto» | rifiutato perché **c'è lavoro in volo** |
| cosa asserisce l'8 | `E_ORD_ANNULLA_IN_COMMESSA` | `E_SORGENTE_CON_RIGHE_EMESSE` |

⭐ E il file ci guadagna un presidio che non aveva: la fixture usa `uid::text`
per `commesse_attivita` e `id::text` per `commesse_sorgenti` **nella stessa
pagina**, con scritto perché — le due chiavi polimorfe della stessa sorgente,
una accanto all'altra.

#### La caccia agli altri, fatta col criterio giusto

Cercati **tutti** i pgTAP che chiudono un documento (17 file, per stato
abortito o `stato_ann`): ✅ **tutti verdi** tranne
`script/test-seed-stati-doc-ordini-evaso-v1`, che è un **rosso già in
baseline** (`ASSERZIONE`) e riguarda `EVASO` — nulla a che vedere con questi
trigger, che si svegliano solo entrando in uno stato abortito.

Cercati anche i consumatori dei due codici ritirati fuori dal DB: restano nelle
tabelle di fallback del backend e nelle chiavi i18n del frontend, e **è
corretto** — un codice ritirato non si cancella. ⚠️ Ma il codice **nuovo**
`E_SORGENTE_CON_RIGHE_EMESSE` ha bisogno della sua policy HTTP/UI e della sua
`reason_key`: è una richiesta a BE/FE, §14.9.1.

#### 14.9.1 ⚠️ La richiesta a BE/FE

| Cosa | Dove |
| --- | --- |
| policy HTTP/UI per `E_SORGENTE_CON_RIGHE_EMESSE` (classe `CONFLITTO_STATO`) | `apps/core/services/error_policies_generated.py` |
| messaggio di fallback | `apps/core/services/error_messages_fallback.py` |
| `reason_key` `vendite.sorgenti.azione_reason.righe_commessa_emesse` | `frontend/src/locales/it.json` e `en.json` |
| ⚠️ le chiavi `…azione_reason.gia_in_commessa` di ordini e preventivi | **non si cancellano** (un codice ritirato può essere ancora nei log), ma smettono di comparire |

#### 🟠 Il rosso preesistente, ancora non toccato

`codici-errore-baseline.sh` continua a segnalare **un rientrato**,
`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`. ⛔ Non è di questo cantiere e la
baseline **non è stata stretta**: va allineata da chi possiede quel codice.

#### Cosa resta di L7

- ⏸️ **La documentazione operativa**: chiudere un documento adesso ritira lavoro,
  ed è un comportamento che l'operatore deve **sapere prima**. Va nella guida —
  ⚠️ ma quella pagina è contesa con l'altro cantiere (§11.3) e la §7.1 aspetta
  comunque la consegna BE/FE.
- ✅ **FATTO il 2026-08-27** (changeSet `20260826-56`, brief
  [brief-db-residui-competenza-dimensione-e-chiave](../work-in-progress/brief-db-residui-competenza-dimensione-e-chiave.md)
  D-6). Il messaggio di `E_RIGA_COMMESSA_NON_MANUALE` (guard 4 di
  `fn_annulla_commessa_attivita`) diceva *«il rimedio è SEMPRE a monte, sul
  documento»*: ⭐ **da L7b quella frase è vera**, e adesso il messaggio **nomina**
  il documento invece di lasciarlo cercare — il terzo segnaposto riceveva
  `sorgente_uid`, cioè un UUID, e ora arriva da
  `vendite.fn_get_sorgente_documento_ref`, lo **stesso** resolver della colonna
  «Origine». ⭐ E la `soluzione` a catalogo ha smesso di consegnare una `SELECT`
  all'operatore: dice che chiudere il documento **ritira da sé** le righe non
  ancora emesse. Presidio: test **18-bis** di
  `db/pgtap/vendite/test-annulla-commessa-attivita-v1.sql`, visto rosso prima.

---

### 14.10 Documentazione DB — le schede concettuali · ✅ FATTA (2026-08-26)

**Sette funzioni nuove, sette schede** in `docs/it/dbzero/<schema>/manual/`:

| Schema | Scheda | Cosa fissa |
| --- | --- | --- |
| `vendite` | `fn_libera_attivita_fatturabili` | perché è **una primitiva** e non due `UPDATE` copiate; perché **non** imposta la GUC; perché il timbro non si scrive più e il **lucchetto sì** |
| `vendite` | `fn_riporta_attivita_da_emettere` | il perimetro **senza `fatturato`**; lo scope che sta sulla **commessa**; i cinque rifiuti |
| `vendite` | `fn_ritira_commessa_attivita_da_sorgente` | è **l'oggetto** della promessa del guard 4; complementare a `fn_annulla_commessa_attivita`; la chiave che sbagliata **non dà errore** |
| `vendite` | `trgfn_doc_guard_chiusura_sorgente` | il **freno**, `is_abortito` invece di `'ANNULLATO'`, dove non è montato e perché, il **limite RLS** |
| `vendite` | `trgfn_doc_ritira_commessa_attivita` | il **motore**, e l'argomento di Q-10 per esteso: perché trigger e non chiamata nei servizi |
| `script` | `fn_check_attivita_riportabile_da_emettere` | i quattro motivi nell'ordine, il motivo 1 **aggregato**, la forma del bersaglio |
| `script` | `fn_check_sorgente_chiudibile` | **le due chiavi polimorfe**, e perché sbagliarle dà zero motivi |

#### ⛔ E due schede ESISTENTI che erano diventate false

Non erano funzioni nuove: erano pagine che descrivevano una regola che abbiamo
cambiato oggi. ⚠️ È esattamente la specie di debito del **§8.3** — una
dichiarazione convincente che il prossimo lettore prende per buona.

| Scheda | Cosa diceva | Cosa dice adesso |
| --- | --- | --- |
| `script/manual/fn_check_ordine_annullabile` | *«MOTIVO 2: ordine già entrato in una commessa»*, e `E_ORD_ANNULLA_IN_COMMESSA` in tabella | il motivo 2 è **righe già `EMESSA`**; il codice è barrato e marcato **ritirato**, non cancellato |
| stessa scheda, sezione chiavi | *«Il MOTIVO 2 usa la chiave `id::text`»* | legge `commesse_attivita` con **`uid::text`**, e la pagina spiega **perché le due tabelle usano chiavi diverse** — `commesse_sorgenti` registra *chi* ha spinto, `commesse_attivita` porta *cosa* |
| `script/manual/fn_check_preventivo_annullabile` | non nominava il terzo motivo | dichiara che `E_PREV_GIA_IN_COMMESSA` è **ritirato**, che il motivo 2 **delega** e rietichetta, e perché sui preventivi il guard generico **non** si monta |

⭐ La correzione della scheda dell'ordine ha anche **guadagnato** un pezzo che non
c'era: le due chiavi polimorfe della stessa sorgente, spiegate una accanto
all'altra invece che dedotte per simmetria — che è la trappola che aveva già
tenuto spento un motivo per tre changeSet.

#### Il criterio con cui sono scritte

Ogni scheda segue lo standard delle esistenti (`Scopo Principale` con la data di
revisione, `Vedi anche`, `Esempio d'uso`, `Note operative`, firma), e in più
fissa **le tre cose che un `COMMENT` non riesce a tenere**:

1. **perché** la funzione esiste, non solo cosa fa;
2. **cosa succederebbe** se qualcuno la cambiasse nel modo che sembra ovvio —
   la GUC aperta dalla primitiva, il perimetro fondato su `fatturato`, il freno
   montato anche sui preventivi, la chiave presa dalla tabella sbagliata;
3. **i limiti dichiarati** invece che dedotti: il conteggio sotto RLS che non
   ferma chi non vede, le righe sourceless irraggiungibili, `ANNULLATA`
   irreversibile.

⚠️ Tutti i collegamenti delle sette schede sono stati **verificati uno per uno**
contro i file esistenti, e `db/pgtap/dbops/test-riferimenti-morti-v1` è verde.

---

### 14.11 Stato finale della giornata (2026-08-26)

```text
L1   ✅ applicato   riordino «prima si ripristina, poi si cancella» + primitiva condivisa
L3a  ✅ applicato   FK SET NULL -> NO ACTION: il muro
L3b  ✅ applicato   `fatturato` colonna GENERATA + 15 fixture pgTAP sistemate
L4   ✅ fatto       presidi: le asserzioni che mancavano, 5 dichiarazioni corrette
L5   ✅ applicato   «Riporta da emettere» — collaudato sulle 5 righe VERE (in rollback)
L7a  ✅ applicato   fn_check_sorgente_chiudibile + fn_ritira_commessa_attivita_da_sorgente
L7b  ✅ applicato   freno + motore generici, 7 trigger, i due divieti RITIRATI (Q-9)
L6   ✅ fatto       guida operativa + 7 schede nuove + 2 schede corrette
L2   —              le 5 righe orfane restano dove sono: il recupero e' un gesto FE
```

**16 changeSet** (`20260826-23` … `20260826-38`), **5 file pgTAP nuovi**,
**18 file pgTAP corretti**, **7 codici errore nuovi**, **2 ritirati**,
**1 permesso**.

#### ⛔ Le due cose che restano, e sono entrambe fuori dal DB

| # | Cosa | Perché blocca |
| --- | --- | --- |
| **BE-1** | `pipeline_repository.py` riga ~2962 deve smettere di scrivere `fatturato` (e il metodo morto `mark_attivita_fatturata` va cancellato) | ⛔ **la fatturazione è ferma** finché non arriva: scrivere una colonna generata è un errore, non un no-op. §14.8.4 |
| **BE-2** | policy HTTP/UI e `reason_key` per i **7 codici nuovi** | senza, l'operatore vede un messaggio generico al posto di quello scritto. §14.9.1 |

⭐ E il **verbo FE** su «Emesse non fatturate»: la metà DB è collaudata sulle
righe vere, manca il pulsante.

#### Il filo che tiene insieme tutto il cantiere

Il difetto di partenza non era «mancava un controllo». Era una regola che viveva
come **disciplina** — l'ordine dei passi dentro una funzione — ed è bastata una
chiave esterna aggiunta altrove per farla saltare **senza un errore**, per
quattro settimane.

Ogni lotto ha spostato una regola dalla disciplina alla **struttura**:

| Lotto | Da | A |
| --- | --- | --- |
| L1 | «ricordati di riallineare prima» | l'ordine dei passi, con il perché scritto dove serve |
| L3a | «la SET NULL sgancia in silenzio» | `NO ACTION`: la quinta porta **esplode** invece di sganciare |
| L3b | «i due dati devono restare allineati» | una colonna sola: il disaccordo **non è rappresentabile** |
| L4 | «il test è verde» | asserzioni che **cadono** se la regola si rompe |
| L7b | «chi chiude si ricordi di ritirare» | un trigger: **non si può dimenticare** |

⚠️ E ogni volta il presidio è stato provato **rosso prima e verde dopo**, perché
un presidio che non si è mai visto fallire non è un presidio: è una speranza.
