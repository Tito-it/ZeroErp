# Linee guida Trigger (PostgreSQL + Liquibase)

> **Ultimo aggiornamento**: 8 novembre 2026
>
> **Destinatari**: chi scrive o modifica un trigger o una funzione trigger
>
> **Vedi anche**:
>
> * [Linee guida SQL](linee-guida-sql.md) — §5 check e guard, `fn_log_and_raise_error`; §11.5 il divieto di DDL sui trigger generati
> * [Framework di automazione DB](/guide/automazione-db) — i trigger che il database genera da solo (audit, `tx_id`, storico, ATTIVO, lucchetti)

---

## Scopo

Questa pagina è la sede unica delle regole sui **trigger** e sulle **funzioni trigger**: come si
chiamano, in che ordine scattano, su quali eventi, e i casi in cui un trigger scritto bene sulla
carta lascia passare quello che doveva fermare.

Prima di scrivere un trigger, una domanda: **lo genera già il framework?** Audit, `tx_id`, storico,
ATTIVO, lucchetti di colonna, regola del periodo, codice in maiuscolo li monta il giro delle automazioni, dalla
struttura della tabella. Quelli non si scrivono a mano (vedi [I trigger generati](#i-trigger-generati)).

---

## Il nome del trigger

```text
trg_<schema_opzionale>_<tabella>_<fase>_<descrizione_breve>_<eventi>
```

| Parte                | Regola                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| `trg_`               | sempre                                                                                                  |
| `<schema_opzionale>` | solo se esiste una tabella con lo stesso nome in un altro schema                                        |
| `<tabella>`          | il nome della tabella                                                                                   |
| `<fase>`             | l'ordine di esecuzione, vedi sotto                                                                      |
| `<descrizione_breve>`| snake_case, verbo + oggetto: `guard_codice_forma`, `set_validita`, `only_allowed_tipi`                  |
| `<eventi>`           | `ins`, `upd`, `dlt`, combinati in quest'ordine: `ins_upd`, `upd_dlt`, `ins_upd_dlt`                       |

⚠️ **63 caratteri.** PostgreSQL tronca i nomi più lunghi; il framework, sui trigger che genera, tronca
e aggiunge un hash. Un nome generato si scrive in un documento o in un test **solo dopo averlo letto**
su `pg_trigger`; in un pgTAP si cerca per **funzione e argomenti**, non per nome.

---

## La fase: l'ordine di esecuzione

PostgreSQL esegue i trigger dello stesso momento (`BEFORE` o `AFTER`, per riga) in **ordine
alfabetico di nome**. La fase è il modo di governarlo: la **lettera** dice la zona, il **numero**
ordina dentro la zona.

| Fase       | Zona e uso                                                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `a05`      | **il rifiuto che deve parlare per primo**: l'immutabilità («questa cosa non si tocca»: documento fuori bozza, forma di un codice)             |
| `a10`      | **verifica e blocco**: i guard. Se la regola non è rispettata, sollevano l'errore e l'operazione non passa                                   |
| `a15`, `a20` | **derivazioni e normalizzazioni** che vengono dopo i guard: un valore calcolato da altri (`set_validita`, `set_periodo`)                  |
| `m10` … `m50` | passi intermedi (per esempio `m50` per la scadenza `cleanup_at` alla nascita)                                                           |
| `z10` … `z95` | **effetti finali**, a valle di tutto; `z90` è lo storico, generato                                                                        |

⭐ **Fra due guard che possono rifiutare la stessa riga, parla quello col nome minore**, e la frase
che l'operatore legge è la sua. Prima l'immutabilità, poi la validità del valore nuovo: se una cosa
non si può cambiare, dire che il valore nuovo era sbagliato manda l'operatore a correggere la cosa
sbagliata. Si governa col nome (`a05` prima di `a10`, e dentro `a10` l'alfabeto della descrizione) e
si presidia con un pgTAP che asserisce **la frase** (`throws_like`), così un rinomina futura diventa
rossa. `a05` non è una fascia «più importante»: è una precedenza fra rifiuti, da usare solo quando
l'ordine è dominio.

Una fase nuova non si inventa: si sceglie la zona che dice il suo posto, e un numero libero dentro.

---

## Il nome della funzione trigger

La funzione **non** porta né fase né eventi: la stessa funzione può servire più trigger, in fasi
diverse.

```text
trgfn_<schema_opzionale>_<tabella>_<descrizione_breve>
es.  trgfn_vendite_ddt_righe_qta_from_operativa
     trgfn_config_stati_prevent_delete_if_used
```

Un building block che serve più tabelle sta nello schema `script` (o `dbops` per gli strumenti) e
non porta il nome di una tabella: `script.trgfn_lock_columns`, `script.trgfn_guard_date_validita`.
Riceve le differenze per tabella come **argomenti del trigger** (`TG_ARGV`).

⚠️ Chi legge quegli argomenti da fuori (una capability, un presidio che interpreta `pg_trigger.tgargs`)
non ricopia la loro grammatica: la estrae in una funzione condivisa che usano sia il trigger sia il
lettore (per la famiglia ATTIVO, `dbops.fn_trigger_attivo_argomenti`). `TG_ARGV` parte da 0,
`dbops.fn_trigger_argomenti` da 1: la funzione condivisa rinumera, e nessun chiamante conta
posizioni. Gli argomenti si leggono per nome e senza valori di riserva: un ripiego che indovina
una colonna dà una colonna sbagliata che non si vede.

Check e guard — che cosa restituisce una `fn_check_*` e che cosa solleva una `fn_guard_*` — e come si
solleva un errore sono in [Linee guida SQL, §5](linee-guida-sql.md).

---

## `UPDATE` o `UPDATE OF colonna`

### Che cosa fa davvero `UPDATE OF`

`UPDATE OF colonna` **non** vuol dire «quando la colonna cambia». Vuol dire «quando la colonna è
**scritta nel `SET`** dell'istruzione». Da qui due conseguenze, ed entrambe mordono:

| Caso                                                                                              | `UPDATE OF colonna`                                   |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `SET colonna = <stesso valore>`                                                                   | **scatta**, anche se non cambia niente                |
| la colonna la cambia **un altro trigger `BEFORE`** (un ricalcolo, una normalizzazione, un default) | **non scatta**, anche se il valore è cambiato         |
| la colonna la cambia una FK `ON UPDATE CASCADE`                                                   | scatta (la cascata scrive un `UPDATE … SET`)          |

⛔ **Il secondo caso è quello pericoloso.** Un guard o una propagazione agganciati con `UPDATE OF` su
una colonna **derivata** si aggirano cambiando la colonna da cui deriva. Caso reale: sulle righe dei
documenti `quantita` la calcola un trigger da `qta_operativa`, e la propagazione ai componenti del kit
era `AFTER UPDATE OF quantita`: un `UPDATE` del solo `qta_operativa` cambiava la quantità del padre e
lasciava i componenti con quella vecchia.

### La regola

* **Se il trigger reagisce a un CAMBIO di valore**, si scrive `UPDATE` senza `OF` e il confronto va
  nel `WHEN`: `WHEN (OLD.colonna IS DISTINCT FROM NEW.colonna)`. Il `WHEN` vede la riga **dopo** i
  trigger `BEFORE` che vengono prima in ordine alfabetico; in un trigger `AFTER` vede la riga
  **finale**. È la forma per le propagazioni e per i guard su colonne che altri trigger possono
  scrivere.
* **`UPDATE OF` resta giusto** quando la domanda è proprio «qualcuno ha **chiesto** di scrivere questa
  colonna?», e la colonna non ha scrittori automatici sulla stessa tabella: il lucchetto di colonna,
  un guard su una colonna che solo l'operatore compila. Il corpo confronta comunque `OLD` e `NEW`,
  perché `UPDATE OF` scatta anche a valore uguale.
* Prima di agganciare un trigger con `UPDATE OF colonna`, si guarda se un altro trigger `BEFORE` della
  tabella scrive `NEW.colonna`. Se sì, `OF` è la forma sbagliata.
* Se la logica dipende dal **record intero** (storico, audit), si usa `UPDATE` senza `OF` e senza `WHEN`.

### ⛔ Una colonna nuova entra anche nell'elenco `OF`

Estendere il **corpo** di un guard a una colonna nuova non basta: se il trigger è
`BEFORE INSERT OR UPDATE OF col_a, col_b`, un `UPDATE` della sola colonna nuova non lo fa scattare, e
la riga passa senza essere giudicata. L'`INSERT` invece passa dal guard, quindi tutto sembra
presidiato. Il trigger si ridefinisce con la colonna nell'elenco nello stesso changeSet, e il pgTAP
del guard prova un `UPDATE` che tocca **solo** la colonna nuova.

### Colonne derivate: due trigger, non uno

Dentro un trigger si vedono i **valori**, non quali colonne il chiamante ha messo nel `SET`. Quando
una colonna la deriva il database e da fuori non si scrive, servono due trigger:

* un guard `a10`, `BEFORE INSERT OR UPDATE OF <colonne derivate>`, che rifiuta se il loro valore
  cambia (valore, non menzione: un salvataggio che riscrive tutta la riga deve passare);
* la derivazione `a20`, `BEFORE UPDATE OF <colonna da cui derivano>`, che scrive le derivate in `NEW`
  e non riattraversa il guard.

---

## `BEFORE` e `AFTER`: che cosa vede il trigger

* ⛔ **Un `BEFORE ROW` sulla riga che sta cambiando, se rilegge la tabella, legge la riga di ieri.**
  In un `BEFORE UPDATE` la tabella contiene ancora `OLD`. Una funzione di controllo chiamata dal guard
  che rilegge la riga per id fa la sua verifica sui valori vecchi, e un valore sbagliato scritto nella
  stessa istruzione entra senza errore. Le colonne giudicate entrano come **parametri** (i valori di
  `NEW`); dalla tabella si legge solo il resto (righe figlie, cataloghi). Si prova con **una sola**
  istruzione (`SET colonna = X, stato_id = …`), non con due `UPDATE` separati, che sono verdi con
  entrambe le forme.
* ⚠️ **Un `BEFORE ROW` parla prima dei vincoli della tabella.** Montare un guard anche su `INSERT`
  sposta la sede del rifiuto: lo SQLSTATE passa da `23514` (CHECK) a `P0001` (dominio), e un pgTAP che
  asseriva il vincolo diventa rosso. È un miglioramento — il guard dice i valori ammessi, il CHECK no
  — ma va dichiarato, e il CHECK **resta**, con un'asserzione sua sulla sua esistenza: presidia le
  strade che il trigger non percorre.
* ⛔ **Un guard che decide su una riga correlata non la legge sotto la row level security di chi
  scrive.** Una funzione trigger gira con l'identità di chi scrive: il padre, il figlio, il
  documento collegato fuori dal suo perimetro risultano assenti, e il guard decide su un'assenza
  che non c'è — rifiuta per la ragione sbagliata, o lascia passare. In un trigger differito conta
  per di più il contesto di chi chiude la transazione. La lettura va in una funzione
  `SECURITY DEFINER` del proprietario, con `search_path` fissato, che risponde il minimo che
  serve. ⛔ Se la funzione esegue SQL dinamico **non riceve nomi di tabelle o colonne**: riceve il
  trigger (tabella e nome) e legge gli argomenti dal montaggio, e risponde solo per tabelle del
  proprietario — altrimenti chiunque la chiami legge qualunque colonna. Esempio:
  `dbops.fn_trigger_padre_stato` e `dbops.fn_trigger_figlie_presenti`, le letture dei guard ATTIVO.
* ⛔ **Un trigger che scrive una colonna lucchettata non la «difende».** Riassegnare
  `NEW.colonna := OLD.colonna` «per sicurezza» annulla anche le scritture che passano dalla porta del
  lucchetto (`zeroerp.allow_lock_columns_override`), e lo fa senza errore. A parità di condizione
  `RETURN NEW`, e a giudicare resta il lucchetto.

---

## Trigger differiti (`CONSTRAINT TRIGGER`)

Un `CONSTRAINT TRIGGER … DEFERRABLE INITIALLY DEFERRED` scatta al **commit** invece che a fine riga:
serve quando la regola si giudica solo a transazione completa (un padre e i suoi figli scritti in più
istruzioni). Tre cose da sapere:

* esiste in **due** cataloghi, `pg_trigger` e `pg_constraint`: una rinomina con `ALTER TRIGGER` o con
  `ALTER TABLE … RENAME CONSTRAINT` ne aggiorna uno solo e lascia un nome morto nell'altro. Si toglie
  (`DROP TRIGGER IF EXISTS`, porta via entrambe le voci) e si ricrea;
* i pgTAP girano con `SET CONSTRAINTS ALL IMMEDIATE`, come le fixture: lì un trigger differito scatta a
  fine istruzione, anche dentro i verbi;
* un evento differito in sospeso fa fallire un `ALTER TABLE` nella stessa transazione («pending trigger
  events»).

⚠️ **Un effetto «alla nascita» che deve cedere a scritture successive non è un trigger.** Se il
documento nasce e subito dopo il verbo o il backend scrivono le sue righe collegate, un trigger
all'`INSERT` arriva prima e vince sulla scrittura che doveva vincere. La forma è «chi crea chiama il
building block» dopo le sue scritture; il trigger va bene sui **cambi** (`AFTER UPDATE … WHEN`).

---

## I trigger generati

I trigger di audit, `tx_id`, storico, ATTIVO, lucchetti di colonna, regola del periodo e codice in
maiuscolo li monta il
[framework di automazione](/guide/automazione-db), leggendo la struttura delle tabelle. I loro nomi
seguono i template del framework, non la regola delle fasi qui sopra
(`trg_<tabella>_audit_data_user_upd`, `trg_<tabella>_gen_tx_id_ins_upd`,
`trg_<tabella>_z90_storico_upd_dlt`, `…_a10_lock_columns_upd`, …).

* ⛔ **Non si scrivono a mano**, nemmeno con la stessa funzione e lo stesso stile di nome: un trigger
  che sembra generato e non è registrato non lo ricrea nessuno, se sparisce.
  L'unica eccezione è il lucchetto di colonna su una tabella fuori dall'ambito delle automazioni,
  dove il runner non arriva: lì lo monta una migrazione e il registro lo dichiara comunque (vedi
  [Automazione DB §4.1](/guide/automazione-db)).
* ⛔ **Un changeSet non fa DDL né `preCondition` su di loro**: su un database ricostruito da zero
  nascono dopo, nella passata `ci_apply`. Regola e presidio in
  [linee-guida-sql §11.5](linee-guida-sql.md).
* ⚠️ **Un trigger nuovo che deriva o rifiuta passa anche dai seed già scritti.** Su un database da zero
  tutto il codice gira prima di tutti i dati: un backfill di `80_data` di ieri attraversa il trigger
  scritto oggi. Si cercano i changeSet di `80_data` che scrivono la stessa tabella o colonna.

---

## Che cosa si usa dentro

* Gli errori si sollevano con le funzioni di progetto — `script.fn_log_and_raise_error` per un codice
  scritto come letterale, `script.fn_raise_primo_motivo_se_presente` per il primo motivo di una
  `fn_check_*` — mai con un `RAISE EXCEPTION` nudo: codici, contesto e frase per l'operatore sono in
  [Linee guida SQL, §5](linee-guida-sql.md).
* Le regole sullo stato di un documento passano dai building block esistenti (lucchetti, «solo in
  bozza», guard di riga): prima di scriverne uno si cerca negli schemi `script` e `dbops`.

---

## Checklist rapida (da usare nei PR)

* [ ] Il framework non lo genera già (audit, `tx_id`, storico, ATTIVO, lucchetti, periodo, codice in maiuscolo).
* [ ] Nome `trg_<schema_opzionale>_<tabella>_<fase>_<descrizione>_<eventi>`, sotto i 63 caratteri; la funzione `trgfn_…` senza fase né eventi.
* [ ] Fase scelta per zona: `a05` immutabilità, `a10` guard, `a20` derivazioni, `z…` effetti finali. Fra due rifiuti possibili, parla prima l'immutabilità.
* [ ] `UPDATE OF colonna` solo se nessun altro trigger `BEFORE` scrive quella colonna; per reagire a un cambio di valore, `WHEN (OLD.x IS DISTINCT FROM NEW.x)`.
* [ ] Una colonna nuova giudicata da un guard esistente è anche nel suo elenco `OF`.
* [ ] Un guard `BEFORE ROW` non rilegge per id la riga che sta cambiando: i valori entrano come parametri.
* [ ] Il pgTAP prova `INSERT` e `UPDATE`, l'`UPDATE` in un'istruzione sola, e asserisce la frase quando conta chi parla per primo.
* [ ] Cercati i seed di `80_data` che scrivono la stessa tabella.

---

{% include-markdown "signature-core.md" %}
