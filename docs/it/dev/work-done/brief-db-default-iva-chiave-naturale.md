# Brief DB — `DEFAULT_IVA_ID` è l'ultimo parametro che stocca un id, e ora la chiave c'è

> ## ✅ CHIUSO lato DB — 2026-08-31
>
> **Fatto e APPLICATO**, nell'ordine obbligato del §2-bis: `20260831-36` (la
> check accetta il vuoto), riga 5 in `parameter_fk_surrogate.csv`, e il rename in
> `parameters.csv` — `DEFAULT_IVA`, valore **`22`**. Presidio:
> `db/pgtap/config/test-parameter-fk-surrogate-vuoto-v1.sql`, 9 casi, e **metà
> verificano che il RIFIUTO regge ancora**: provare solo che il vuoto passa
> vorrebbe dire allargare un cancello senza controllarlo.
>
> ⛔ **E QUI IL BE È ROTTO ADESSO, non «da fare».** Il §3 diceva «nello stesso
> giro, non prima»; il giro DB è passato e quello BE no.
> `apps/catalogo/services/catalogo_service.py` legge ancora `DEFAULT_IVA_ID`, che
> a catalogo **non esiste più**: da lì prende il ripiego, **in silenzio**, e il
> form-defaults dell'articolo smette di proporre l'aliquota. Non fallisce, non
> logga: propone un campo vuoto.
>
> ⚠️ E il valore nuovo è `22`, che è un **numero**: un lettore che facesse `int()`
> non fallirebbe, otterrebbe l'**id 22** — oggi inesistente in `config.iva`, ma il
> modello lo ammette. È la ragione per cui il gemello negativo del §4 non è una
> formalità.

> **Destinatario:** team DB (`dev/db-tid`). **Voce unica**, e sblocca la slice
> `F6` del piano
> [brief-be-fe-iva-fase-3-consumatori-risolutore.md](brief-be-fe-iva-fase-3-consumatori-risolutore.md).
>
> 📌 **La richiesta operativa è raccolta con le altre** in
> [brief-db-richieste-aperte-dal-backend.md](brief-db-richieste-aperte-dal-backend.md):
> quello è l'ordine di lavoro, questo è il ragionamento. ⛔ Se le due divergono,
> vale questo — l'elenco rimanda, non ricopia.
>
> **Origine.** Decisione di Tid del 2026-08-31 (`P8` del piano di Fase 3), presa
> a valle di `D28` del cantiere IVA — che è il passo che rende la cosa
> possibile.
>
> **Stato.** 2026-08-31 — verificato sulla **struttura** (`parameters.csv`,
> doc auto-generata di `config.iva`, `linee-guida-sql §6b`). Nessuna misura sui
> dati.
>
> 🔨 **COSTRUITO e APPLICATO il 2026-08-31** — changeSet `20260831-36` piu' i
> due seed. Il §2-bis racconta il prerequisito che il brief non prevedeva.
>
> **Correlati:**
> [config.iva](/dbzero/config/tabelle/iva) ·
> [linee-guida-sql §6b](../../linee-guida-sql.md) ·
> [brief-db-be-iva-risolutore-e-regime-cliente §D28](brief-db-be-iva-risolutore-e-regime-cliente.md)

---

## 1. Il fatto: la guida descrive questa migrazione, e nomina questo parametro

`linee-guida-sql §6b` — *«Riferimenti esterni a tabelle di catalogo (chiave
naturale stabile)»* — porta un **tech debt riconosciuto**, e l'esempio è
letteralmente il nostro:

> *«parametri legacy che oggi stoccano id numerici a tabelle di catalogo che **non
> espongono ancora** una chiave naturale stabile (es. `DEFAULT_IVA_ID` →
> `config.iva.id`). Restano fuori scope del framework finché la tabella target
> non viene dotata della chiave (aggiungere `codice_interno` → il lock
> automatico viene provisionato dal runner → **rinominare il parametro** →
> **aggiungere riga al registry**).»*

⭐ **La condizione sospensiva è caduta.** `D28` (changeSet `20260829-43`) ha dato
a `config.iva` la sua `codice_interno`, con backfill `= codice` e il lock nello
stesso trigger delle due colonne del trattamento. I primi due passi dei quattro
sono **fatti**; restano il terzo e il quarto, che sono DB.

Oggi il seed dice:

```csv
11,DEFAULT_IVA_ID,16,"ID IVA di default per creazione clienti (config.iva.id=16, IVA 22%)",…
```

⛔ Un `16` che vale finché nessuno riseeda `config.iva`. È esattamente ciò che il
principio §6b vieta: *«l'id è dettaglio implementativo soggetto a reseed; la
chiave naturale è il contratto cross-ambiente»*.

---

## 2. La richiesta

| # | Cosa | Nota |
| --- | --- | --- |
| **1** | **Rinominare** il parametro — `DEFAULT_IVA_ID` → `DEFAULT_IVA` | ⚠️ Il suffisso `_ID` diventerebbe una **bugia** appena il valore è un codice, ed è la specie di nome che poi qualcuno rilegge come intero. La guida prescrive proprio «rinominare», non solo cambiare il valore |
| **2** | **Cambiare il valore** da `16` al `codice_interno` corrispondente, e riscrivere la descrizione (che oggi cita `config.iva.id=16`) | La descrizione è la sede in cui il debito è rimasto leggibile: va aggiornata insieme, o afferma il falso |
| **3** | **Riga nel registry** `config.parameter_fk_surrogate`: `code_pattern` EXACT su `DEFAULT_IVA`, target `config.iva.codice_interno` | ⭐ Nessun codice DB nuovo: il dispatcher `trgfn_parameters_fk_surrogate_dispatch` esiste già e da quel momento **valida il valore** — un codice IVA inesistente viene rifiutato con `E_PARAMETER_DEFAULT_VALUE_INVALID` invece di restare a marcire |

📌 **E il registry è il vero guadagno**, più della chiave in sé: oggi nessuno
verifica che quel `16` punti a qualcosa. Con la riga nel registry il parametro
smette di poter mentire.

⭐ **Il valore nuovo è `22`** — il `codice_interno` della riga `id = 16` di
`config.iva`, verificato sul seed. L'`id` della riga di `parameters` resta
**11**: il mirror è un `loadUpdateData` con `primaryKey: id`, quindi è un
`UPDATE` e non nasce nessun orfano.

---

## 2-bis. ⛔ Il prerequisito che non era nel brief: `parameters.csv` non è riscrivibile

> **Trovato il 2026-08-31**, verificando la voce prima di eseguirla. È la
> ragione per cui questa voce, nell'ordine di lavoro, **è scesa dal terzo posto
> all'ultimo**: la richiesta «costa minuti» era vera solo finché nessuno aveva
> guardato il file da toccare.

I passi 1 e 2 chiedono di editare una riga di `parameters.csv`. ⛔ **Quel file
non si può toccare**, e la storia è già scritta nell'intestazione di
`20260826-03`, dove è esplosa il 2026-08-25:

* il mirror `20250715-01-upsert_parameters` è `runOnChange: true`: **qualunque**
  modifica al CSV ne cambia il checksum e lo **sveglia**;
* svegliato, rilegge tutto il file — riga 11 compresa: `12,DEFAULT_UTILITY,`
  con `default_value` **stringa vuota**;
* il dispatcher `config.trgfn_parameters_fk_surrogate_dispatch` esce presto
  **solo su `NULL`**; su `''` chiama la check, che cerca `''` in
  `config.utilities.codice_interno` e non lo trova →
  `E_PARAMETER_DEFAULT_VALUE_INVALID` → **migrate fermo**.

⚠️ **E la riga è irriscrivibile in entrambi i versi**: il token `NULL` non si può
mettere, perché `config.parameters.default_value` è **`NOT NULL`** (verificato
sulla doc auto-generata). Né `''` né `NULL`.

⚠️ **Non si aggira con un CSV dedicato ri-ancorato**, che sarebbe il pattern di
casa: lascerebbe in `parameters.csv` una riga `DEFAULT_IVA_ID,16` **stantia**
davanti a un mirror **dormiente**, e il primo che tocca quel file per un altro
motivo riporta indietro il parametro in silenzio. Sarebbe costruire di proposito
la trappola che il progetto ha già catalogato.

### ✅ Decisione (Tid, 2026-08-31): la stringa vuota **è** l'assenza

Si allarga il ramo di uscita in testa a `script.fn_check_parameter_fk_surrogate`
da `p_value IS NULL` a *«nullo o vuoto»*.

⭐ **L'argomento è sul modello, non sul far passare il migrate.** La colonna è
`NOT NULL`: su `config.parameters` la stringa vuota **è l'unica forma che
"nessun valore" può assumere**. Il ramo `NULL` della check, per quella tabella,
è irraggiungibile — serve agli override, dove la colonna è un'altra. La funzione
oggi dichiara una regola che sulla sua tabella principale non può mai
applicarsi, e la riga `DEFAULT_UTILITY` è il controesempio che lo dimostra: la
sua stessa `description` dice *«NULL = nessun default»*, cioè afferma una cosa
che quella colonna non può contenere.

⛔ **Le due alternative, scartate e per quale motivo:** dare a `DEFAULT_UTILITY`
un `codice_interno` vero **cambia il comportamento** delle maschere che oggi non
propongono nulla; `enabled = false` sulla riga di registry **toglie il presidio**
proprio mentre se ne sta aggiungendo un altro.

### L'ordine dei passi, da qui in poi obbligato

| # | Fase | Cosa |
| --- | --- | --- |
| 1 | `20_code` | `fn_check_parameter_fk_surrogate`: il vuoto passa come il nullo |
| 2 | `80_data` | la riga di registry su `DEFAULT_IVA` |
| 3 | `80_data` | `parameters.csv`: rename, valore `22`, descrizione riscritta |

⚠️ **Il passo 1 viene PRIMA del 3 per forza**: il 3 sveglia il mirror, e il
mirror rilegge `DEFAULT_UTILITY`. Se la check non è ancora larga, il migrate si
ferma lì — cioè il difetto di questa sezione, riprodotto.

⚠️ **E il pgTAP del passo 1 deve provare DUE cose**: `''` ammesso **e** un
codice inesistente ancora **rifiutato**. Con la sola prima si sta allargando un
cancello senza verificare che regga ancora, che è il modo in cui un presidio
diventa verde per sottrazione.

---

## 3. La metà BE, che va nello stesso giro

⛔ **Non prima**, o il lettore si rompe. Il consumatore è **uno solo**, verificato:
`apps/catalogo/services/catalogo_service.py` (~1422-1441), il form-defaults
dell'**articolo** — che è la domanda giusta a cui quel parametro risponde
(l'aliquota ordinaria della merce, cioè lo stadio A del risolutore).

Oggi fa `ParameterService.get_defaults(["DEFAULT_IVA_ID"])` e casta a intero.
Dopo leggerà `DEFAULT_IVA` e risolverà l'id con
`apps/core/db/_helpers.resolve_config_id_by_codice_interno`, che **esiste già** ed
è il building block previsto per questo.

⚠️ **Il lettore sbagliato è già morto**: fino al 2026-08-29 questo parametro lo
leggeva anche la creazione cliente, ed è caduto con `S1` della Fase 1 (`D7-bis`,
l'IVA non appartiene al cliente). Quello che resta è l'unico corretto — motivo in
più per sistemarlo invece di ritirarlo.

---

## 4. Presidio atteso

* ⭐ **Il test che discrimina, e non è «il parametro si legge»**: con un valore
  che **non esiste** in `config.iva.codice_interno`, il seed deve essere
  **rifiutato** — è ciò che la riga di registry compra, e senza quella prova non
  si sta verificando il registry ma solo il rename;
* il form-defaults dell'articolo continua a proporre la stessa aliquota di prima
  (il rename non deve cambiare il comportamento a video);
* ⚠️ e il **gemello negativo**: cercare `DEFAULT_IVA_ID` per nome nudo in
  `backend/` e nei seed → zero occorrenze. Un rename che lascia indietro un
  lettore non fallisce: legge un parametro che non c'è più e prende il ripiego.

⛔ **E il gemello negativo NON è una formalità, per una coincidenza del valore.**
Il `codice_interno` è **`22`**, cioè un numero. Un lettore rimasto indietro che
facesse `int(...)` **non fallirebbe**: otterrebbe l'**id 22**, che oggi in
`config.iva` non esiste — ma che il modello **ammette** eccome, e il giorno che
esistesse sarebbe un'aliquota sbagliata applicata in silenzio, su un documento
fiscale. La ricerca per nome nudo è l'unica prova che nessun lettore vecchio è
sopravvissuto.

---

## 5. Fuori perimetro, dichiarato

* ⛔ **Il ritiro del parametro.** Era stato ipotizzato dal piano di Fase 1 («se il
  seed vada tolto lo decide il team DB, a Fase 3 chiusa»): la risposta è **no**,
  il parametro serve e resta — cambia solo come referenzia il catalogo;
* 📌 **Gli altri parametri legacy** che stoccano id. La guida dice
  *«migrazione tracciata caso per caso, non bulk»*, e questo brief tratta il caso
  che `D28` ha appena sbloccato. Nessun altro.

---

## 6. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 (3) | 🔨 **COSTRUITO e APPLICATO**, nell'ordine obbligato: `20260831-36` (la check accetta il vuoto), riga 5 in `parameter_fk_surrogate.csv`, e il rename in `parameters.csv` — `DEFAULT_IVA`, valore **`22`**, descrizione riscritta. ⚠️ Il CSV è stato toccato con una sostituzione **di riga**, non riscrivendolo: un `csv.writer` aveva ri-quotato 11 righe di altri parametri, rumore che nel diff sembra una modifica vera. Presidio: `test-parameter-fk-surrogate-vuoto-v1`, 9 casi, e **metà verificano che il RIFIUTO regge ancora** — provare solo che il vuoto passa vorrebbe dire allargare un cancello senza controllarlo. ⛔ Resta la metà BE: `catalogo_service.py` legge ancora `DEFAULT_IVA_ID`, che a catalogo **non esiste più** — da lì prende il ripiego, in silenzio, e il form-defaults dell'articolo smette di proporre l'aliquota |
| 2026-08-31 (2) | ⛔ **Trovato che la voce non si può eseguire come scritta**: `parameters.csv` è una mina dormiente già esplosa il 25/08, e la riga `DEFAULT_UTILITY` non accetta né `''` (dispatcher) né `NULL` (colonna `NOT NULL`). Decisa da Tid la strada `A` — la stringa vuota vale come assenza, e l'argomento sta sul modello: su una colonna `NOT NULL` il vuoto **è** l'unica forma dell'assenza, quindi il ramo `NULL` della check per `config.parameters` è irraggiungibile. ⭐ Aggiunto §2-bis con l'ordine obbligato dei tre passi, e la trappola del valore `22` che un `int()` legge come un id plausibile |
| 2026-08-31 | Brief nato eseguendo `F6` del piano di Fase 3 e scoprendo che la voce **non è BE**: tre passi su quattro sono seed DB, e il piano la classificava come lavoro di backend. ⭐ La condizione che la bloccava è caduta con `D28` del cantiere IVA, che ha dato a `config.iva` la sua `codice_interno` — la guida §6b nominava **questo parametro** come esempio del debito e descriveva **questi quattro passi** come la via d'uscita |
