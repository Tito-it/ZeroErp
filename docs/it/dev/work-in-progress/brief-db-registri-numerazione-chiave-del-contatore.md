# Brief DB — la chiave del contatore, e i documenti che non la portano

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-01.
>
> **In una riga:** il contatore dei registri distingue i numeri su **quattro**
> assi — `(registro_id, anno, mese, serie)` — ma i documenti che quei numeri li
> ricevono ne portano **al massimo tre**, e due di loro ne portano due. Dove
> manca un asse, il contatore può consegnare un numero che il documento non è in
> grado di ospitare.
>
> **Origine.** Non è nata da un difetto in campo: è emersa il 2026-09-01
> scrivendo il guard sulla forma del numero
> ([brief CRUD registri](brief-be-fe-crud-registri-di-numerazione.md) §8),
> chiedendosi *perché* `serie_default` potesse restare fuori dal divieto. La
> risposta — «perché la serie distingue i documenti» — è vera per tre documenti
> su cinque. Poi la domanda di Tid: *«questo comporta che i documenti che
> vogliono la numerazione di registro debbano tutti avere la chiave completa?»*
> Sì. E il seguito è questo brief.
>
> ⛔ **Nessuna misura ha deciso niente qui.** I conteggi che compaiono sono
> **fatti datati** e servono a un uso solo: dire se qualcosa *smentisce* il
> piano. Ciò che decide è la struttura — quali colonne esistono, quali vincoli
> le presidiano.
>
> **Correlati:**
> [brief-db-prefisso-sul-registro](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md) ·
> [brief-db-registri-di-numerazione-emittente-e-trasloco](../work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md) ·
> [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)

---

## 1. ⭐ L'invariante, e non era scritta da nessuna parte

> **Tutto ciò che discrimina il CONTATORE deve discriminare anche l'unicità del
> DOCUMENTO.**

Il contatore vive su `uq_regprog_key = (registro_id, anno, mese, serie)`. Ogni
combinazione è un **secchio** che riparte da 1.

Se il documento non porta uno di quegli assi nel proprio vincolo di unicità, il
contatore può dargli un numero che per il documento è **già usato**. Non è un
caso limite: è la definizione stessa di due secchi che si affacciano sullo
stesso spazio di numeri.

⚠️ **E il difetto non si vede finché quell'asse non si muove.** È il motivo per
cui è rimasto invisibile: gli assi che mancano oggi sono fermi.

---

## 2. Come sta oggi — struttura, verificata il 2026-09-01

| Asse del contatore | `fatture` | `ddt` | `ordini` | `resi` | `commesse` |
| --- | --- | --- | --- | --- | --- |
| `registro_id` | ✅ | ✅ | ✅ | ✅ | ⛔ |
| `anno` | ✅ | ✅ | ✅ | ✅ | ~ dentro la stringa |
| `serie` | ✅ | ✅ | ✅ | ⛔ | ⛔ |
| `mese` | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |

I vincoli, per esteso:

```text
fatture   uq_fatture_numero              (registro_id, anno, COALESCE(serie,''), numero)
ddt       uq_ddt_v_anno_serie_numero     (registro_id, anno, serie, numero)
ordini    uq_ordini_v_anno_serie_numero  (registro_id, anno, serie, numero)
resi      uq_resi_anno_numero            (registro_id, anno, numero)          ⛔ senza serie
commesse  uq_commesse_codice             (codice)                             ⛔ una stringa sola
```

⚠️ **`vendite.commesse` non ha nemmeno `registro_id`**: le sue uniche colonne
utili sono `codice` e `emittente_soggetto_ruolo_id`. Del registro che l'ha
numerata non resta traccia se non dentro la stringa del codice.

---

## 3. ⛔ Il caso `resi` — cosa succede davvero

`vendite.resi` **non ha la colonna `serie`**. `trgfn_resi_gen_numero` non passa
nessuna serie a `fn_assegna_numero_documento`, quindi eredita il `serie_default`
del registro — e **non la scrive da nessuna parte**.

Cambiando `serie_default` su un registro `RESO` **a metà anno**:

1. la serie entra nella chiave del contatore ⇒ si apre un secchio nuovo, che
   riparte da **1**;
2. il primo reso della serie nuova prova a scrivere il numero 1;
3. `uq_resi_anno_numero` è su `(registro_id, anno, numero)` — la serie non c'è —
   e quel numero nell'anno **esiste già** ⇒ **violazione di unicità**;
4. la transazione fallisce, e col rollback torna indietro **anche l'incremento
   del contatore** ⇒ al tentativo successivo riparte da 1 e sbatte di nuovo.

⇒ **Non un dato sporco: un reso che non si riesce più a numerare**, con un
errore che parla del numero e non nomina la causa.

⭐ **Il morso è confinato all'anno**, ed è la ragione per cui è sopravvissuto:
`reset_policy` è `ANNUALE`, l'anno sta nella chiave del contatore e il reso
scrive `anno` dalla stessa chiamata che gli dà il numero. Cambiare
`serie_default` **a gennaio**, prima del primo reso, non rompe niente — e non lo
nota nessuno, perché la serie sul reso non è scritta.

⚠️ **Il punto 4 è dedotto dal meccanismo, non provato su un reso vero**:
costruirne uno richiede DDT e partita. I punti 1-3 sono struttura verificata.

---

## 4. ⛔ Il caso `commesse` — lo stesso difetto, scritto in un altro modo

L'unicità della commessa è `uq_commesse_codice`, su **una stringa sola**. Il
codice incorpora sigla, anno e progressivo — **non la serie**, e nemmeno il
registro.

⇒ Stessa dinamica del §3: la serie cambia, il progressivo riparte, il codice
ricalcolato collide con uno già emesso, e la commessa non nasce.

⚠️ **Ma la cura non è la stessa, e va detto**: sul reso manca *una colonna*; qui
manca **tutto l'aggancio** — registro, anno, serie e progressivo vivono solo
dentro una stringa. Allineare la commessa è un lavoro di dimensione diversa, e
non si infila nello stesso passo.

---

## 5. ✅ `mese` si TOGLIE — decisione di Tid, 2026-09-01

### 5.1 Perché è un residuo e non una colonna inutilizzata

`mese` sta nella chiave del contatore e **non compare in nessun vincolo di
unicità di nessun documento**. Oggi è innocuo, ma non per progetto: è innocuo
perché è **inchiodato in due punti**.

```text
vendite.fn_get_next_progressivo   v_mese ... := 0;     -- e non viene mai riassegnato
chk_registri_fatturazione_reset   CHECK (reset_policy = 'ANNUALE')
```

⛔ **Una dimensione dormiente in una chiave non è «inutilizzata»: è ARMATA.** Il
giorno che qualcuno accende un reset mensile — cioè fa esattamente la cosa per
cui quella colonna esiste — il contatore riparte da 1 **ogni mese** e collidono
**tutti e cinque** i documenti, non i due del §3-§4. È lo stesso difetto della
serie, moltiplicato per dodici.

⭐ **E oggi a tenerlo chiuso non è un vincolo: è una rinuncia.** Quando il
`CHECK` fu ristretto ad `ANNUALE`, `MENSILE` e `NESSUNA` uscirono perché
*«dichiarate e non implementate»*. Quella scelta è l'unica cosa che separa il
database dal difetto — e una rinuncia si può revocare per distrazione, un
vincolo no.

### 5.2 ⭐ Il censimento dei LETTORI — verificato il 2026-09-01

Prima di cancellare una fonte si censiscono i suoi lettori, e il censimento si fa
sulla **lettura**, non sulla parola: «mese» nel progetto è quasi sempre
`competenza_mese` o «il primo del mese», che non c'entrano niente.

| Dove | Chi legge `registri_fatturazione_progressivi.mese` |
| --- | --- |
| funzioni PL/pgSQL | **una sola**: `vendite.fn_get_next_progressivo` |
| viste / viste materializzate | **nessuna** |
| backend Python | **nessuno** — `backend/` non nomina mai la tabella |
| pgTAP | **nessuno** — i file che dicono «mese» parlano di `competenza_mese` o del giorno del mese del limite di emissione |
| CSV di seed | **nessuno** che porti la colonna |

⚠️ `vendite.fn_calcola_data_documento` la nomina **solo in un commento**: è prosa
su `competenza_mese`, non una lettura.

### 5.3 Cosa la tiene attaccata alla tabella

```text
uq_regprog_key                 UNIQUE (registro_id, anno, mese, serie)
uq_registri_progressivi_scope  UNIQUE INDEX (registro_id, anno, COALESCE(mese,0), COALESCE(serie,''))
chk_regprog_mese_valid         CHECK (mese = 0 OR mese BETWEEN 1 AND 12)
                               NOT NULL
```

### 5.4 ⭐ E togliendola si scopre un UNIQUE ridondante che nessun presidio vede

`registro_id`, `anno`, `mese` e `serie` sono **tutte e quattro `NOT NULL`**.
⇒ I due `COALESCE` di `uq_registri_progressivi_scope` sono **no-op**, e
quell'indice esprime **esattamente la stessa chiave** di `uq_regprog_key`.

⛔ **`dbops.vw_duplicate_indexes` non lo segnala** — verificato: zero righe. Il
confronto lavora sulle colonne, e qui una chiave è una lista di colonne e
l'altra è una lista di **espressioni**: due cose che il presidio non sa
riconoscere come uguali.

⭐ *Un duplicato nascosto dietro espressioni che non fanno niente è invisibile
proprio al presidio nato per trovare i duplicati.* Va tolto nello stesso giro,
e la cecità del presidio va **dichiarata** — non è detto valga la pena
insegnargliela, ma va saputa.

### 5.5 ⚠️ Cosa preclude toglierla, dichiarato

Toglie la possibilità di un **reset mensile** del contatore senza un cantiere
che rimetta la colonna.

⭐ Ed è coerente: il `CHECK` quella possibilità l'ha già chiusa, e riaprirla
domani vorrebbe comunque dire **prima** dare l'asse `mese` a tutti e cinque i
documenti (§1). Cioè il lavoro vero non è la colonna sul contatore: è la chiave
sui documenti. Tenere la colonna non anticipa niente — tiene solo il difetto
aperto nel frattempo.

### 5.6 Il fatto datato che avrebbe potuto smentire il piano

Al 2026-09-01 le righe di `registri_fatturazione_progressivi` sono **10, tutte
con `mese = 0`**. ⇒ Nessuna riga distinta collasserebbe sulla chiave nuova.

⚠️ **Questo numero non decide niente**: serviva solo a cercare un
controesempio, e non ce n'è. Se ne fosse comparso uno, il piano sarebbe caduto —
ed è l'unico uso legittimo di una misura.

---

## 6. La serie — allineare chi non la porta

| | Cosa manca | Dimensione |
| --- | --- | --- |
| `resi` | la colonna `serie`, e la serie nel vincolo | **una colonna + un vincolo** |
| `commesse` | tutto l'aggancio: registro, anno, serie, progressivo vivono solo dentro `codice` | **un cantiere suo** |

⭐ **La cura è dare l'asse, non vietare il campo.** Un divieto su
`serie_default` sarebbe il rimedio sbagliato per tre ragioni: renderebbe
impossibile aprire una serie nuova anche dove è legittimo (fatture, DDT,
ordini), non si potrebbe comunque montare com'è — il mirror CSV
`80_data/sql/vendite/registri_fatturazione.csv` riscrive `serie_default` a ogni
migrate — e lascerebbe il modello asimmetrico, che è la causa vera.

⚠️ **`commesse` resta fuori da questo brief.** Va nominata perché il difetto c'è,
ma allinearla significa decidere come una commessa si aggancia al registro — che
è una domanda di modello, non un `ALTER TABLE`.

---

## 7. Il piano

> ⛔ Ordine vincolante: **prima il codice, poi lo schema**. La funzione deve
> smettere di nominare la colonna prima che la colonna cada.
> ⚠️ L'autogen ordina per NN mescolando `00_schema` e `20_code`: l'ordine si
> impone con la numerazione, non con la cartella.

| Passo | Cosa | Dove |
| --- | --- | --- |
| **M-1** | `fn_get_next_progressivo` senza `mese` — chiave del secchio a tre assi | `20_code/vendite` |
| **M-2** | `chk_regprog_mese_valid` e `uq_registri_progressivi_scope` via; `uq_regprog_key` ricreata su `(registro_id, anno, serie)`; `DROP COLUMN mese` | `00_schema/vendite`, NN **maggiore** di M-1 |
| **M-3** | pgTAP: il contatore distingue su tre assi, e la colonna non c'è più | `db/pgtap/vendite` |
| **S-1** | `vendite.resi` guadagna `serie` (NOT NULL, default `''`) e `uq_resi_anno_numero` diventa `(registro_id, anno, serie, numero)`; `trgfn_resi_gen_numero` scrive la serie che il motore gli restituisce | `00_schema` + `20_code` |
| **S-2** | pgTAP: cambiando `serie_default` il reso si numera lo stesso, e i due numeri convivono | `db/pgtap/vendite` |
| **P-1** | ⭐ Il presidio dell'invariante — vedi §8 | `db/pgtap/vendite` |

⚠️ **`fn_assegna_numero_documento` restituisce già `serie`** e il suo commento
dice *«la serie risolta esce perché chi ha quella colonna deve scriverla»*: S-1
non cambia il motore, dà al reso la colonna che gli mancava per obbedirgli.

---

## 8. ⭐⭐ Il presidio che conta — l'invariante, non i casi

⛔ **Un test che verificasse «resi ha la serie» proverebbe l'oggi.** Il difetto
non è che a un documento manchi una colonna: è che **nessuno controlla** che i
documenti numerati sui registri portino la chiave del contatore. È così che sono
entrati `resi` e `commesse`, col trasloco, senza che niente diventasse rosso.

Il presidio da scrivere **deriva** i due elenchi e li confronta:

* gli assi della chiave del contatore, letti da `uq_regprog_key`;
* per ogni famiglia registrata in `vendite.famiglie_documento`, gli assi presenti
  nel vincolo di unicità del numero della sua tabella.

Il giorno che una famiglia nuova entra sui registri senza la chiave completa, il
test è **rosso prima del merge** invece che dopo, in campo.

⭐ È la stessa forma del test 6 di `test-fn-check-registro-disattivabile-v1.sql`
— *«il giorno che ne compare una quarta diventa rosso»* — ed è la forma che ha
già funzionato una volta su questa stessa tabella.

⚠️ **`commesse` sarà rossa dal primo giorno**, e va bene: è debito **dichiarato**,
non un difetto nuovo. O si esclude con un motivo scritto, o il test nasce già a
fallire — e la scelta va fatta esplicitamente, non per omissione.

---

## 9. ⛔ Cosa non si tocca

* **`serie_default` non si vieta.** La cura è dare l'asse ai documenti (§6).
* **Il mirror CSV di `registri_fatturazione`** resta com'è: nessun guard nuovo
  sulle colonne che riscrive.
* **`config.sistema_codici`** non c'entra: la forma del numero è uscita di lì il
  2026-08-31 di proposito.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.
