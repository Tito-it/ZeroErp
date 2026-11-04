# Brief BE — Il codice si salva in maiuscolo: che cosa cambia per il backend

## ✅ Chiuso il 2026-11-04

Chiuso da Tid dopo la prova a video. Fatti K-1 … K-5 (§7), la richiesta al team DB del §6 (commit
`4db6c06db`, PR #32) con la sua ricaduta BE (§7.1-bis), e le due decisioni di Tid: la chiave del tipo
ruolo è esatta in ogni ingresso (§7.2), e gli alias di `codice_interno` si chiamano
`*_codice_interno` (§7.4). La ri-normalizzazione una tantum è stata lanciata su dbdev da Tid.
Nessun residuo aperto.

> **Ultimo aggiornamento**: 4 novembre 2026
>
> **Destinatari:** backend (`dev/backend-tid`); il §6 è una richiesta al team DB (`dev/db-tid`). Il
> lato DB dell'automazione è applicato: commit `b26b103bae` su `dev/db-tid`, changeSet
> `20261104-01` … `-08`, applicato su dbdev il 2026-11-04 con i pgTAP verdi.
>
> **Stato:** ✅ chiuso il 2026-11-04. **Da leggere per primo: §2, che cosa cambia.**
>
> **Il disegno** sta nella guida [Framework di automazione DB §4.8](../../guide/automazione-db.md), §4.8 e il suo «Per il backend»:
> questo brief dice solo che cosa deve fare il BE.

---

## 1. Da dove viene

Il 2026-11-04 Tid ha deciso che il codice che l'operatore digita **non distingue le maiuscole**:
`VITE-M8` e `vite-m8` sono lo stesso articolo, non due. Il DB ora salva ogni colonna `codice` in
`upper(btrim(codice))`, con un trigger che l'automazione CODICE_MAIUSCOLO monta da sola su ogni
tabella dell'ambito: oggi 116 tabelle negli schemi `anagrafiche`, `catalogo`, `config`, `documenti`,
`magazzino`, `pagamenti`, `pratiche`, `vendite`. Una tabella nuova con la colonna `codice` nasce
già col trigger.

Le righe già scritte sono state normalizzate una volta (`sql-una-tantum-codice-maiuscolo.sql`).

**Restano come sono** (eccezioni, `dbops.automazione_codice_eccezioni`): `ui.lista_colonna`,
`ui.lista_definizione`, `ui.lista_preset`, `ui.widget`, `ui.dashboard_definizione`,
`ui.dashboard_preset`, `dbops.processi`, `config.aree_funzionali`, `config.assets_ownership`,
`config.note_stili`. Sono chiavi tecniche lette per nome. `codice_interno` non è toccato su nessuna
tabella, e gli schemi fuori dall'ambito (per esempio `dbops`, `ui`) nemmeno.

---

## 2. Che cosa cambia per il BE

| # | Che cosa | Effetto se non si fa |
| --- | --- | --- |
| K-1 | **Il valore salvato può essere diverso da quello inviato.** Dopo un INSERT o un UPDATE il codice va riletto dal DB (`RETURNING codice`, o la rilettura del dettaglio), non rimandato al client com'era nel payload | Il client mostra `vite-m8` mentre il DB ha `VITE-M8` |
| K-2 | **Una ricerca esatta per codice** su un input dell'utente (`WHERE codice = %s`, un filtro `?codice=`, una risoluzione «trova per codice») confronta con `upper(btrim(input))`. Le ricerche `ILIKE` non cambiano | `?codice=vite-m8` non trova niente |
| K-3 | **Il duplicato ora è senza maiuscole.** Creare `vite-m8` quando c'è `VITE-M8` dà la stessa violazione di unicità (23505 sul vincolo del codice) che prima dava solo il codice identico. La traduzione dell'errore che il BE già fa per il codice duplicato resta quella: va solo verificato che il messaggio non suggerisca «c'è già `vite-m8`» | Nessuno: è il comportamento voluto |
| K-4 | **`E_CODICE_MAIUSCOLO`**, codice nuovo, classe `TECNICO`. Nasce solo dal motore dell'automazione (migrate, job notturno), mai da una richiesta dell'utente: basta che `genera_error_policies` lo porti nel modulo generato | Il cancello «ogni codice che il DB può nominare ha una policy» resta rosso |
| K-5 | **I test Django** che creano un codice con lettere minuscole (un suffisso `uuid4().hex`, `token_hex`, `md5` senza `.upper()`) e poi lo cercano o lo confrontano per valore. La correzione è mettere `.upper()` sul **generatore** del suffisso, non sulle ricerche: è quello che si è fatto sui cinque pgTAP | Il test non trova la riga che ha appena creato |

⚠️ K-1 e K-2 valgono solo per le tabelle del perimetro. Un repository che legge una tabella in
eccezione o fuori ambito (`ui.*`, `dbops.*`) non cambia.

---

## 3. Il punto di partenza del censimento (dal lato DB, non esaustivo)

Un grep fatto dalla sessione DB il 2026-11-04, per dare un inizio, non un elenco chiuso: il
censimento vero lo fa il BE.

| Dove | Che cosa | Nota |
| --- | --- | --- |
| `anagrafiche/db/soggetti_repository.py` `resolve_tipo_ruolo` | `config.tipi_ruoli WHERE codice = %s OR codice_interno = %s ORDER BY (codice = %s)` | K-2: il payload può arrivare minuscolo |
| `core/db/email_repository.py` (lista `email_template`) | filtro `et.codice = %s` | K-2 |
| `vendite/tests/db/test_listini_create_db.py`, `pagamenti/tests/db/test_enti_incasso_create_db.py` | suffisso già `uuid4().hex[:8].upper()` | ✅ già a posto: sono la forma da copiare |
| 23 file in `backend/apps/*/tests` usano `uuid4().hex`, `token_hex` o `md5` | da guardare uno per uno | K-5 |
| `dbops_repository.py`, `pipeline_repository.py`, `processi_repository.py`, `ui_repository.py`, `dashboard_repository.py`, `lista_catalogo_repository.py` | ricerche esatte su `dbops.*` e `ui.*` | fuori perimetro: non cambiano |

Il censimento si chiude con la lista dei repository che fanno una ricerca esatta sul `codice` di una
tabella del perimetro. Per sapere se una tabella è nel perimetro:

```sql
SELECT schema_name, table_name
  FROM dbops.fn_codice_maiuscolo_perimetro(NULL)
 WHERE nel_perimetro AND NOT in_eccezione;
```

---

## 4. Il FE

Facoltativo, non una richiesta: un campo codice può mostrare il testo in maiuscolo mentre si digita,
così l'operatore vede subito come verrà salvato. Il DB normalizza comunque: il FE non deve ripetere
la regola.

---

## 5. Chiusura

Il brief si archivia in `work-done/` quando K-1 … K-5 sono fatti, il §6 è applicato con la sua
ricaduta sul BE, e i test Django sono verdi.

---

## 6. Richiesta al team DB — la forma del codice in una funzione sola

### 6.1 Il difetto

La forma del codice (`upper(btrim(…))`) oggi è scritta in **quattro** posti: nel trigger
`script.trgfn_codice_maiuscolo` e, ricopiata a mano, in tre query del BE che confrontano un input
dell'operatore con la colonna (K-2):

| Dove | Che cosa |
| --- | --- |
| `anagrafiche/db/soggetti_repository.py` `resolve_tipo_ruolo` | `codice = upper(btrim(%s))` (due volte: WHERE e ORDER BY) |
| `core/db/email_repository.py` lista `email_template` | `et.codice = upper(btrim(%s))` |
| `core/db/dbops_repository.py` filtro del diario per codice errore | `mm.codice = upper(btrim(%s))` |

Se la regola cambia, le tre copie del BE restano alla forma vecchia, e nessun errore lo segnala: la
ricerca torna una lista vuota. È la regola del 2 applicata alla frontiera DB/BE.

### 6.2 Il secondo difetto: la stessa parola in maiuscolo non è la stessa ovunque

Il database usa il provider `libc` con `it_IT.UTF-8`, e lì `upper()` applica la mappatura **semplice**
carattere per carattere. Il CSS (`text-transform: uppercase`, la classe `app-codice-input`) e
`String.prototype.toUpperCase()` di JavaScript applicano la mappatura Unicode **completa**. Su
alcuni caratteri le due mappature divergono, e l'operatore vede a video un codice diverso da quello
che il DB salva:

| Digitato | A video (CSS / JS) | Salvato oggi (`libc`) | Con `pg_unicode_fast` |
| --- | --- | --- | --- |
| `straße` | `STRASSE` | `STRAßE` | `STRASSE` |
| `ﬁ` (legatura) | `FI` | `ﬁ` | `FI` |

Fatto datato, misurato su dbdev il 2026-11-04 (PostgreSQL 18.6, `datlocprovider = c`). La ragione
del cambio non è nel numero dei casi: un codice che a video e a DB è diverso è un difetto del
modello, anche se oggi nessuna riga lo contiene.

### 6.3 Che cosa si chiede

1. **Una funzione, sede unica della forma**:
   `script.fn_codice_normalizzato(p_codice text) RETURNS text`, `IMMUTABLE`, `PARALLEL SAFE`,
   `STRICT`, corpo `upper(btrim(p_codice) COLLATE pg_unicode_fast)` (collation del provider `builtin`
   di PostgreSQL 18: mappatura Unicode completa, la stessa del browser). Il trigger
   `script.trgfn_codice_maiuscolo` la chiama invece di scrivere la formula.
2. **Ri-normalizzazione una tantum** delle righe già scritte nelle tabelle del perimetro, come
   `sql-una-tantum-codice-maiuscolo.sql`. Prima di scrivere, lo script **elenca le collisioni**:
   due righe che con la mappatura nuova diventano lo stesso codice (`STRAßE` e `STRASSE`)
   violerebbero l'UNIQUE. Una collisione la risolve Tid a mano, non lo script.
3. **pgTAP**: il trigger salva la forma della funzione (`straße` → `STRASSE`), e il trigger non
   contiene più la formula scritta a mano (presidio contro la copia che ritorna).
4. **Da valutare dal team DB**:
   * ⚠️ la mappatura completa può **allungare** il testo (`ß` → `SS`): su una colonna `varchar(n)`
     un codice al limite della lunghezza diventa un errore `22001`. Va deciso se è il
     comportamento voluto (l'errore è corretto: il codice salvato è più lungo) e con quale codice
     a catalogo arriva all'operatore;
   * ⚠️ `IMMUTABLE` con il provider `builtin`: la tabella Unicode è legata alla versione maggiore di
     PostgreSQL, non alla libc del sistema. Va confermato che è accettabile per un'espressione che
     finisce negli indici UNIQUE, e scritto nella guida §4.8.

5. **`config.fn_scrivi_profilo_accesso` cerca il codice grezzo** (trovato dal censimento K-1, §7.3).
   Il verbo fa `SELECT … WHERE pa.codice = p_codice` e, se non trova, `INSERT … VALUES (…, p_codice, …)`;
   l'INSERT passa dal trigger e salva il codice in maiuscolo. Un codice con minuscole o spazi ai bordi
   non si ritrova più alla chiamata dopo: la ricerca manca la riga, il verbo tenta un secondo INSERT
   e va contro `uq_profili_accesso_codice`. Il caso vivo è il profilo di reparto: il BE passa
   `REPARTO_<codice_interno>` (`amm_software_repository.put_profilo_reparto`), e
   `config.unita_organizzative.codice_interno` non ha regole sul maiuscolo. Dopo la prima scrittura
   il profilo di quel reparto non si modifica più.
   Correzione: il verbo normalizza `p_codice` una volta, con la funzione del punto 1, e usa il valore
   normalizzato nella ricerca e nell'INSERT. Così vale per ogni chiamante, non solo per il BE.
   pgTAP: due chiamate con lo stesso codice minuscolo restituiscono lo stesso id.
   ⭐ È la «rilettura per valore» di `script/manual/trgfn_codice_maiuscolo.md`: conviene che il team
   DB cerchi le altre funzioni che cercano per `codice = p_…` su una tabella del perimetro e poi
   scrivono, perché il BE non le vede.

**Ricaduta sul BE** (passo 4 del blocco in testa): i tre `upper(btrim(%s))` del §6.1 diventano
`script.fn_codice_normalizzato(%s)`. Il BE non scrive più la formula.

---

## 7. Giro BE del 2026-11-04

### 7.1 Fatto

* **K-2**: `resolve_tipo_ruolo`, lista `email_template`, filtro del diario per codice errore.
* **K-4**: `E_CODICE_MAIUSCOLO` nella policy generata e nel ripiego.
* **Copie della regola ritirate**: il BE metteva il codice in maiuscolo da sé (senza `btrim`) in
  `email_views` (account e template, creazione e PATCH) e in `catalogo_service` (`uom_tipi`,
  `unita_misura`). Il FE ha ritirato i due `toUpperCase()` sul payload.
* **FE**: classe `app-codice-input` sui campi codice, presidio `guard:campo-codice`.
* **Tipo ruolo per chiave**: `COALESCE(tr.codice_interno, tr.codice)` era scritto in 16 punti
  (`tipi_ruoli`, `tipi_indirizzi`). `codice_interno` è `NOT NULL` su tutte e due, quindi il ramo
  `codice` non scattava mai: era la forma vecchia della decisione già presa dal DB (ruoli risolti per
  `codice_interno`, `anagrafiche.fn_lookup_utilities_per_ba` rev. 2026-06-29). Ora il BE confronta
  `codice_interno`, come il DB. Nessun risultato cambia.

### 7.1-bis Ricaduta del §6 (2026-11-04, dopo `4db6c06db`)

* Le tre query del §6.1 confrontano con `script.fn_codice_normalizzato(%s)`. Il parametro non si
  converte al tipo della colonna: un codice che in maiuscolo si allunga dà «non trovato», non `22001`
  (richiesta del team DB).
* `E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO`: policy rigenerata (`genera_error_policies --check` allineato),
  testo di ripiego, e override `highlight_form_fields` in `error_ui_overrides.py`, perché il trigger
  manda `'campo' -> 'codice'` nel contesto (letto dalla funzione). I guardrail dei codici errore e del
  canale campi sono verdi.
* `email_views`: la creazione passa il codice com'è (solo lo `strip()` per il controllo
  «obbligatorio»), come chiede il team DB.

### 7.2 Chiave del tipo ruolo nell'URL — ✅ decisa e fatta (Tid, 2026-11-04: tutte esatte)

* **La chiave del tipo ruolo nell'URL non si confronta allo stesso modo nelle tre rotte.**
  `ruoli/{codice}/config-resolver/` è documentata «case insensitive» (`api_soggetti.md`, la view fa
  `.upper()`); `lookup/tipi-ruolo/{codice}/indirizzi/` e `/utilities/` confrontano esatto. Decisione
  di Tid: tutte esatte (rottura di contratto della prima) o tutte case-insensitive.
* **Fatto:** la view del config-resolver non fa più `.upper()`; il test
  `test_config_resolver_chiave_esatta` sostituisce quello «case insensitive»; `api_soggetti.md`
  aggiornato (anche la riga del 404, che citava ancora il ripiego sul `codice`). Il FE passa sempre
  le costanti di `TIPO_RUOLO`: tolti i due letterali rimasti (`"FO"` in `FornitoreDrawer`, `'CL'`
  locale in `PraticaDrawer`).
* **Esteso a ogni ingresso della chiave** (Tid, 2026-11-04: «dovrebbero essere codici interni»): anche
  i tre parametri di query che la mettevano in maiuscolo ora la passano com'è, con il solo `strip()`:
  `tipo_ruolo` di `SoggettiService.search_ruoli_lookup`, `ruolo` di
  `BillingAccountService.list_utilities_for_ba` (whitelist a tre valori) e `ruolo` del lookup
  `utilities-per-emittente`. I due test che fissavano `cl` → `CL` ora fissano la chiave esatta. Il FE
  passa sempre `TIPO_RUOLO.*` (e `RUOLO_PSP = 'PSP'`).

### 7.3 K-1, censimento esaustivo (2026-11-04)

Tutte le 116 tabelle del perimetro, una per una, sul BE e sui chiamanti FE: per ogni percorso di
scrittura si è guardato da dove viene il `codice` della risposta e che cosa riusa il FE dopo il
salvataggio.

* **Pannello generico** (`config.fn_pannello_scrivi` → `script.fn_scrivi_riga_da_jsonb`, che chiude
  con `RETURNING to_jsonb(t.*)` dopo i trigger): la creazione restituisce la riga del DB, la modifica
  `{"updated": true}` senza codice; il FE rilegge la lista. OK per tutte le tabelle del pannello.
* **Percorsi dedicati** (articoli, UoM, categorie clienti, emittenti, fornitori, enti incasso,
  magazzini, ubicazioni, lotti, listini, famiglie, registri, promo, template e asset documenti,
  email, codici postali, step dei flussi): rileggono la riga, o non restituiscono il codice. OK.
* **Codice generato dal DB** (soggetti, billing account, istanze, pratiche, commesse, offerte, lotti
  di fatturazione, vendite contabili): il codice non arriva dal payload. OK.
* **Senza scrittura dal BE**: le tabelle scritte solo dal seed o dal DB.
* **Un difetto, lato DB**: `config.fn_scrivi_profilo_accesso` (§6.3 punto 5).

Trovato strada facendo, fuori K-1: `FornitoreDrawer` dopo la creazione passava in modifica senza
rileggere il dettaglio (il watch guardava solo `visible`; `editRow` lascia il drawer aperto e cambia
`mode` e id). Ora guarda anche `mode` e `fornitoreId`, come `UomTipoDrawer` e `UnitaMisuraDrawer`. Da
provare a video: non c'è uno spec del drawer.

### 7.4 Il guardrail di naming vede gli alias che il `COALESCE` nascondeva — ✅ deciso e fatto (Tid, 2026-11-04: strada 1)

`test_naming_codice_interno_python.test_il_debito_non_cresce` è rosso dopo il ritiro del `COALESCE`
(§7.1). Il debito non è nuovo: `COALESCE(tr.codice_interno, tr.codice) AS ruolo_codice` esponeva già la
chiave logica sotto un nome di display, ma la regola del test non riconosceva l'espressione. Tolto il
`COALESCE`, `tr.codice_interno AS …` è visibile:

| File | Alias | Nel registro | Trovati |
| --- | --- | --- | --- |
| `anagrafiche/db/soggetti_repository.py` | `codice` | 1 | 2 |
| `anagrafiche/db/soggetti_repository.py` | `ruolo_codice` | 0 | 3 |
| `core/db/lookup_repository.py` | `codice` | 1 | 3 |
| `core/db/lookup_repository.py` | `fallback_codice` | 1 | 2 |

Regola (linee-guida-sql §6c): `codice_interno` → `*_codice_interno`. Correggerli cambia il contratto
delle risposte (`ruolo_codice` è letto da circa 40 punti BE/FE, `fallback_codice` da 7, il `codice`
della lookup dei tipi ruolo dal FE). Due strade, decisione di Tid:
1. **rinominare** gli alias in `ruolo_codice_interno` / `codice_interno` / `fallback_codice_interno`
   con tutti i consumatori, in questo giro;
2. **iscrivere** le voci nel registro del test come debito dichiarato, e aprire il rinomina come
   lavoro a parte.

**Fatto:** `ruolo_codice` → `ruolo_codice_interno` (ruoli del soggetto, lookup ricco soggetto-ruolo e
per id); `codice`/`fallback_codice` → `codice_interno`/`fallback_codice_interno` (le due matrici degli
indirizzi, e anche le due voci del registro, che erano lo stesso difetto); `codice` → `codice_interno`
nel lookup dei tipi ruolo per natura e nel dizionario interno del config-resolver. FE:
`useIndirizzoMultiTipo` (anche la chiave di `tipiStato`), `IndirizzoSoggettoForm`,
`IndirizziSoggettoDrawer`, `PraticaDrawer`, `SoggettoRuoloLookup`. Il registro del debito è sceso a
9 occorrenze in 7 punti. Le chiavi nuove sono provate con chiamate vere al DB, non solo coi mock.
Resta nel registro `soggetti_repository -> codice` (regola C, la chiave jsonb `'codice'` dei ruoli
nella lista soggetti): pregresso, non toccato in questo giro.
