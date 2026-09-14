# Brief DB — Avviare un processo dall'interfaccia: il lavoro di coda che lo chiede

> **Da leggere per primo: §4 — cosa si chiede, in tre righe.**
> Chi scrive: backend (`dev/backend-tid`), 2026-09-14. Decisione di Tid del
> 14-09, dopo aver rilanciato a mano le due cadenze del digest.
> Origine: [analisi-riavvio-processi-da-interfaccia.md](analisi-riavvio-processi-da-interfaccia.md)
> §4.1-bis (addendum 14-09) — il verbo **«Esegui ora»** si stacca da «Riavvia»
> e parte per primo, **senza host**: un timer è un orario attorno a un
> comando, e il comando si lancia da solo.
>
> **In una riga:** un tipo di coda, un processo di classe `MANUTENZIONE` e
> canale `CODA` sotto cui metterlo, un'azione di processo. Nessuna colonna
> nuova, nessun host, `attivo = false` fino alla release del backend.

---

## 1. Il gesto, e perché passa dalla coda

Una persona autorizzata, dal drawer del processo in *Amministrazione →
Processi automatici*, preme «Esegui ora» sulla sveglia
`zeroerp-digest-presidi-settimanale`. Il web **non esegue niente**: scrive un
lavoro su `dbops.coda_lavori`, il drenatore dell'host lo prende e lancia
`bin/run-command.sh digest_presidi --cadenza settimanale` come sottoprocesso —
la stessa riga che il timer esegue, meno l'orario. Il comando si registra sul
giornale sotto **il suo** processo (`digest_presidi:settimanale`, origine
`COMMAND`, `auth_user_id` di chi ha premuto); il lavoro di coda si registra
sotto il processo di questo brief: è l'audit del **gesto**, distinto
dall'audit dell'**esecuzione**. Due righe, due domande, nessuna tabella nuova.

È il disegno del §4 dell'analisi («la UI dichiara, l'host esegue»), con una
differenza sola: niente `systemctl`, niente `sudoers`, niente host. Il §3
dell'analisi resta vero per «Riavvia», che è un altro cantiere.

## 2. Che cosa NON si chiede, e perché

* ⛔ **Nessuna colonna `host`** su `coda_lavori`, nessun registro degli host
  (analisi §5, D1): un comando che parla col DB gira uguale da qualunque host
  con il checkout. La domanda dell'host arriva con «Riavvia», non prima.
* ⛔ **Niente `abilita` a catalogo**: resta un fatto di deploy in
  `sveglie.json` (brief dei quattro processi, §10.2). Un timer spento su
  questa installazione ha il pulsante spento, con il motivo (analisi D-A).
* ⛔ **Il comando NON sta nel database.** Il client manda il `processo_codice`
  e la `unit`; il backend risolve il comando dalla whitelist di deploy
  (`sveglie.json`, campo `comando`, che è la stessa riga resa nel template
  systemd). Un comando letto da una tabella sarebbe un comando che una
  scrittura sbagliata può cambiare.
* ⛔ **Nessun ritentativo automatico** (`max_tentativi_default = 1`): un
  processo partito e caduto a metà non è idempotente per natura — chi vuole
  ripetere, preme di nuovo, e il giornale porta due righe.

## 3. Il precedente, riga per riga

`NOTIFICA_DIGEST_MUTO` / `guardiano_digest` (brief-db-quattro-processi-senza-presidio,
§10.2): tipo nato `attivo = false` e acceso dal DB a release BE avvenuta —
**la regola del binding** — sotto un processo `MANUTENZIONE` che non tocca i
dati di nessuna azienda. Qui vale identica, con una differenza di canale: là
`PGAGENT` (lo accoda una macchina), qui **`CODA`** (lo accoda una persona, e
l'identità è la sua — `run_as = OPERATORE`, `auth_user_id` gratis dallo
`scope`, come già scritto in `processi_repository.py` per il canale `CODA`).

## 4. Cosa si chiede — tre righe di catalogo

### 4.1 `dbops.processi` (seed `80_data/sql/dbops/processi.csv`)

| campo | valore | perché |
| --- | --- | --- |
| `codice` | `avvio_manuale` | il gesto, non l'unit: domani ospiterà anche «Riavvia» |
| `descrizione` | *Avvio manuale di un processo dall'interfaccia: una persona autorizzata preme «Esegui ora» su una sveglia, il web accoda un lavoro `ESEGUI_PROCESSO`, il drenatore lancia il comando del timer come sottoprocesso. MANUTENZIONE perché non tocca i dati di nessuna azienda; CODA perché lo accoda una persona e l'identità è la sua. Il run di questo processo è l'audit del gesto; il comando lanciato registra il suo run sotto il processo eseguito.* | |
| `classe` | `MANUTENZIONE` | niente utente tecnico, niente emittente |
| `canale` | `CODA` | lo accoda una persona |
| `tolleranza_minuti` / `segno_di_vita` | `NULL` / `GIORNALE` | non ha una cadenza: gira quando qualcuno preme. ⚠️ Se il panorama pretende una tolleranza per ogni processo `attivo`, ditelo: è un processo che «sta bene» anche se non gira per mesi |
| `jobname_pgagent` | `NULL` | |

### 4.2 `dbops.coda_lavori_tipi` (seed `coda_lavori_tipi.csv`)

| campo | valore |
| --- | --- |
| `codice` | `ESEGUI_PROCESSO` |
| `handler_code` | `esegui_processo_default` |
| `descrizione` | *Esegue adesso, una volta, il comando di una sveglia di deploy (`sveglie.json`, forma `timer`): lo accoda l'endpoint `processi/<codice>/esegui-ora/` con l'identità di chi preme, lo esegue il drenatore come sottoprocesso `run-command.sh <comando>`, senza `sudo` e senza systemd. Payload: `processo_codice`, `unit`. Nato `attivo=false` (regola del binding: seed spento fino alla release BE).* |
| `run_as_default` | `OPERATORE` |
| `max_tentativi_default` | **`1`** (§2) |
| `attivo` | **`false`** |
| `processo_codice` | `avvio_manuale` |

### 4.3 `config.azioni_processo` (seed `config/azioni_processo.csv`)

| campo | valore | perché |
| --- | --- | --- |
| `area_id` | `13` (`strumenti`) | accanto a `code_manage` (id 28) |
| `permission_codename` | `processo_avvia` | **non** `code_manage`: chi può requeue-are un lavoro non è per questo chi può avviare un giro di fatturazione — due fiducie, due decisioni di profilo (analisi D8, D-C) |
| `descrizione` | *Avvio manuale di un processo dall'interfaccia («Esegui ora» su una sveglia)* | |
| `pericolosa` | **`t`** | un click avvia un giro di fatturazione; la conferma a video è il minimo (D-D) |

## 5. Cosa fa il backend, per chi rilegge

Nell'ordine, dopo l'apply (tutto in `analisi-riavvio-processi-da-interfaccia.md`
§9-bis): `comando` in `sveglie.json` e `__COMANDO__` nei template systemd (una
sede); `job_run()` che legge origine e attore dall'ambiente; l'handler
`esegui_processo_default` (whitelist, `abilita`, sottoprocesso a lista con
timeout, esito dall'exit code); l'endpoint con `post_permission =
"processo_avvia"` e `Idempotency-Key`; la capability di riga sulle sveglie nel
dettaglio del processo; il pulsante nel drawer. ⚠️ Finché il tipo è
`attivo = false`, `fn_accoda_lavoro` rifiuta: è il cancello giusto, e il
backend chiede l'accensione quando l'handler è in servizio.

## 6. Come si verifica che è arrivato

```sql
SELECT codice, classe, canale, tolleranza_minuti FROM dbops.processi WHERE codice = 'avvio_manuale';
SELECT codice, handler_code, run_as_default, max_tentativi_default, attivo, processo_codice
  FROM dbops.coda_lavori_tipi WHERE codice = 'ESEGUI_PROCESSO';
SELECT permission_codename, area_id, pericolosa FROM config.azioni_processo WHERE permission_codename = 'processo_avvia';
```

Lato backend, le tre righe attese saranno dichiarate in un registro **a
ritiro**, sul modello di `_IN_ATTESA_DI_CATALOGO` in `presidi_repository.py`
(test `test_il_debito_delle_viste_in_attesa_e_rientrato`, diventato rosso in
CI il giorno dell'apply di `dbops.presidi` nominando la riga da togliere):
stesso verso, stessa prova.

## 7. Domande al DB

1. `tolleranza_minuti = NULL` su un processo `attivo` di canale `CODA`: il
   panorama lo tratta come «senza contratto» (come gli altri di coda) o
   pretende un numero?
2. Il guard di classe di `fn_accoda_lavoro` (un lavoro di dominio non si accoda
   come `SISTEMA`) ha qualcosa da dire su `MANUTENZIONE` + `OPERATORE`? Il
   precedente `NOTIFICA_DIGEST_MUTO` è `SISTEMA`: qui l'identità serve
   all'audit, non al perimetro.
3. pgTAP: basta il presidio esistente sui tipi (handler/processo/classe), o
   volete un test che il tipo sia sotto un processo `CODA` e non `PGAGENT`?

*Scritto il 2026-09-14. Nessuna riga di codice applicativo scritta; il
backend parte dopo l'apply, e chiede l'accensione del tipo a handler in
servizio.*

*Aggiornamento 14-09 (sera): il solo pezzo di **deploy** — `comando` in
`sveglie.json` e `__COMANDO__` nei template, §9-bis punto 2 dell'analisi — è
fatto, perché non dipende dalle tre righe. Handler, endpoint e pulsante restano
in attesa dell'apply.*
