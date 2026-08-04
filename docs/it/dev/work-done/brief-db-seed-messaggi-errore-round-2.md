# Brief BE → DB — seed round 2: i 28 codici che il check ha fatto emergere

> 🟢 **CHIUSO — 2026-08-04.** Seed applicato, rinomine fatte da entrambe le parti
> nell'ordine giusto, **controprova finale eseguita sul database vivo**:
>
> ```text
> script.fn_log_error_only(..., 'E_PIPELINE_DRIVER_MAX_ITER', ...)
>   registrato come: E_PIPELINE_DRIVER_MAX_ITER
>   messaggio      : Pipeline interrotta: superato il numero massimo di iterazioni.
>   fallback usato : nessuno — il codice si è risolto
> ```
>
> È il codice che aveva motivato il §9.6 del round-1: quello che finiva nel log
> senza essere dichiarato da nessuna parte, e che un confronto
> `error_policies.py` ↔ catalogo avrebbe dato per verde. Ora si nomina da solo.
>
> **Stato misurato dopo il merge di `Tito-dev`:**
>
> | Verifica | Esito |
> | --- | --- |
> | codici dichiarati dal BE senza riga a catalogo | **nessuno** (396 dichiarati, 635 righe CSV) |
> | seed applicato al database | ✅ 636 righe in `config.messaggi_errore` |
> | nomi vecchi (`E_COMPETENZA_*`, `E_EMITTENTE_NON_RISOLTO`) nel DB | **nessuno** — la finestra del §6.4 si è chiusa senza degradi |
> | rinomine R1/R2/R3 lato BE | ✅ nomi nuovi in `error_policies.py`, vecchi assenti dai call-site |
> | guardrail `test_error_codes_declared_guardrail` | ✅ verde nella suite (3563 test) |
>
> Il `migrate` che il §6.4 dava ancora da fare **è girato**: la nota «⏳ manca solo
> il migrate» è superata dai fatti sopra.
>
> **Cosa resta, e non è di questo brief:** il presidio del §6.2 lato DB è nato e
> al primo giro ha già trovato un orfano; la sua evoluzione (`plpgsql_check`) vive
> ora in [brief-db-bonifica-riferimenti-morti](../work-done/brief-db-bonifica-riferimenti-morti.md).
>
> ---

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Riferimento:** vostra risposta in
[brief-db-seed-messaggi-errore-mancanti.md](brief-db-seed-messaggi-errore-mancanti.md) §9.6
(«Palla al BE — codici che nessun catalogo può indovinare»), passo 5 della
lavorazione §9.8.

**In una riga:** il check anti-ricaduta lato BE è scritto e verde, e nel farlo ha
fatto emergere **28 codici** che il backend fa arrivare al log senza che nessuno
dei due registri li conosca. Sono dichiarati; ora servono a catalogo.

---

## 1. Il check c'è, ed è costruito come avete chiesto

[`apps/core/tests/test_error_codes_declared_guardrail.py`](../../../../backend/apps/core/tests/test_error_codes_declared_guardrail.py)
— analisi AST, nessun DB, gira in CI.

Confronta i **punti di chiamata** (`code=` / `error_code=`, letterali **e**
costanti di modulo risolte) con le dichiarazioni di `error_policies.py`. Avevate
ragione sul perché: il confronto `error_policies.py` ↔ catalogo avrebbe dato
verde proprio su `E_PIPELINE_DRIVER_MAX_ITER`, che è il caso che vi ha fatto
scrivere il §9.6. Ora quel codice è dichiarato e il guardrail lo presidia.

Sulla vostra domanda «solo i nuovi o tutti»: **tutti**, come dicevate. L'allowlist
esiste ma è **vuota**, e un test separato impedisce che diventi una discarica
(ogni voce esige una motivazione scritta).

Resta a voi il gemello simmetrico lato DB (codici sollevati dalle funzioni vive
contro `messaggi_errore.csv`): i due registri si sfilano per vie diverse.

## 2. Cosa ha trovato il primo giro — 28 codici, tre categorie

| Categoria | Quanti | Esempio |
| --- | --- | --- |
| Codici di dominio legittimi, mai dichiarati | 24 | `E_PRATICA_INSERT`, `E_FATTURAZIONE_GIRO_PAYLOAD` |
| Un **generico** usato per entità diverse | 4 call-site | `E_NOT_FOUND` su note, allegati e competenze flusso |
| Un codice **del catalogo DB** usato dal BE senza policy | 2 call-site | `E_VALIDAZIONE` in `views_indirizzi_ruolo` |

Le ultime due categorie le abbiamo **corrette al punto di chiamata**, non
dichiarate: un 404 che non dice *cosa* manca non è diagnosticabile a valle, e
`E_VALIDAZIONE` è vostro (ha causa e soluzione scritte da voi ieri) — il BE ora
usa `E_ANAG_VALIDAZIONE`, che già esisteva. Da qui i due codici nuovi
`E_ALLEGATO_NOT_FOUND` e `E_COMPETENZA_NOT_FOUND`.

`E_OFFERTA_XXX`, che segnalavate come probabile segnaposto: **non è un codice**.
È il testo di un commento in `offerte_service.py` che documenta la convenzione
`RAISE EXCEPTION USING MESSAGE='E_OFFERTA_XXX'`. Nessun call-site lo usa — l'ha
raccolto il grep testuale, l'AST no.

## 3. Cosa chiediamo: seed dei 28 in `config.messaggi_errore`, lingua `it`

Stessa forma del round 1: il testo è il `user_message` che `error_policies.py`
già restituisce all'utente. Nessun messaggio inventato, nessun `%s` (sono frasi
finite, §9.7), `causa`/`soluzione` stringa vuota come le altre.

| Codice | HTTP | Messaggio |
| --- | --- | --- |
| `E_ALLEGATO_INSERT` | 500 | Errore durante l'inserimento dell'allegato. |
| `E_ALLEGATO_NOT_FOUND` | 404 | Allegato non trovato. |
| `E_AMM_OPERATORE_NOT_FOUND` | 404 | Operatore non trovato. |
| `E_COMPETENZA_INSERT` | 500 | Errore durante l'inserimento della competenza del flusso. |
| `E_COMPETENZA_NOT_FOUND` | 404 | Competenza del flusso non trovata. |
| `E_EMAIL_ADMIN` | 400 | Operazione sulla configurazione email non riuscita. |
| `E_EMAIL_OP` | 400 | Operazione email non riuscita. |
| `E_EMITTENTE_ATTIVO_NON_VALIDO` | 403 | Emittente non selezionabile: inesistente, disattivato o fuori dal tuo perimetro. |
| `E_EMITTENTE_ATTIVO_TOKEN` | 400 | Refresh token richiesto per applicare il cambio di emittente. |
| `E_EMITTENTE_NON_RISOLTO` | 500 | Emittente fiscale non risolvibile per il documento. |
| `E_FATTURAZIONE_GIRO_NESSUN_LOTTO` | 422 | Nessun lotto da fatturare nel perimetro indicato. |
| `E_FATTURAZIONE_GIRO_PAYLOAD` | 400 | Parametri del giro di fatturazione non validi. |
| `E_FATTURAZIONE_NUMERA_PAYLOAD` | 400 | Parametri della numerazione non validi. |
| `E_FLUSSO_ID_INVALIDO` | 400 | Flusso non valido. |
| `E_FLUSSO_ID_OBBLIGATORIO` | 400 | Flusso obbligatorio. |
| `E_FLUSSO_INSERT` | 500 | Errore durante l'inserimento del flusso. |
| `E_FLUSSO_PRESA_IN_CARICO` | 500 | Errore durante la presa in carico del flusso. |
| `E_GENERAZIONE_PRATICA` | 500 | Errore durante la generazione della pratica dal flusso. |
| `E_GIORNALE_QUERY` | 500 | Errore durante la lettura del giornale. |
| `E_HANDLER_NON_REGISTRATO` | 500 | Handler di flusso non registrato: configurazione incompleta. |
| `E_NOTA_INSERT` | 500 | Errore durante l'inserimento della nota. |
| `E_PIPELINE_DRIVER_MAX_ITER` | 500 | Pipeline interrotta: superato il numero massimo di iterazioni. |
| `E_PRATICA_ID_INVALIDO` | 400 | Pratica non valida. |
| `E_PRATICA_ID_OBBLIGATORIO` | 400 | Pratica obbligatoria. |
| `E_PRATICA_INSERT` | 500 | Errore durante l'inserimento della pratica. |
| `E_PRATICA_QUERY` | 500 | Errore durante la lettura delle pratiche. |
| `E_PRATICA_SORGENTE_TIPO_INVALIDO` | 400 | Codice sorgente non presente in configurazione. |
| `E_SOSPENSIONE_INSERT` | 500 | Errore durante l'inserimento della sospensione. |

La colonna HTTP è lì per informazione (vive in `error_policies.py`, resta
nostra, §9.7): serve a voi solo per capire la natura della riga.

⚠️ **Due note su cosa NON è pulito, e lo sappiamo.**

1. `E_EMAIL_OP` e `E_EMAIL_ADMIN` sono **codici-modulo**: la stessa etichetta
   copre validazione, not-found e accesso negato. Andrebbero spacchettati per
   verbo, ma cambiarli ora significa cambiare lo status HTTP di endpoint già in
   uso — debito annotato nel codice, non risolto qui.
2. I due `E_EMITTENTE_ATTIVO_*` appartengono al cantiere impersonazione di scope
   (il vostro `20260804-13..15`), che lato BE non è ancora committato. Li abbiamo
   dichiarati noi perché il guardrail nascesse verde: se quel cantiere cambia
   idea sui nomi, il seed va rifatto per quelle due righe.

## 4. Cosa NON chiediamo

* **Niente `en`**: vale la conclusione del round 1, ora anche per la ragione
  giusta — la cascata l'avete messa in `fn_log_error_only` (`20260803-11`).
* **Niente bonifica** delle righe già degradate: si purgano da sole (§9.5) e da
  ieri il ripiego conserva comunque `context->>'codice_errore_originale'` (§9.9)
  — che, va detto, rende questo seed **meno urgente del primo**: senza, i 28
  sarebbero già oggi diagnosticabili, solo scomodi.
* **Nessun cambio a `error_policies.py` da parte vostra**: resta il registro
  applicativo, come da §9.7.

## 5. Definizione di «fatto»

* [x] **R1/R2/R3 rinominate lato BE** (§7) — resta al DB l'allineamento delle
      righe 805, 806 e 811 del CSV;
* [x] i 28 codici sono in `messaggi_errore.csv` (non solo nella tabella di un DB) — id **802–829**;
* [x] il gemello lato DB del check esiste, così i due registri si presidiano a vicenda — §6.2;
* [x] controprova su uno dei 28 (`E_PIPELINE_DRIVER_MAX_ITER`, il codice che ha
      motivato il §9.6) — compare in `error_log` **col proprio nome**, §6.6.

---

## 6. Risposta DB (2026-08-04)

### 6.1 Verifica dei 28, e seed

Ricontrollati uno per uno prima di seminare: 28 codici distinti, **tutti** dichiarati
in `error_policies.py`, **nessuno** già a catalogo, **nessun `%s`** nei testi (sono
frasi finite, coerenti con il §9.7). Appesi al CSV con `causa`/`soluzione` stringa
vuota come le altre, **id 802–829**, nessun changeSet nuovo: il loader `runOnChange`
li carica al prossimo `migrate`.

Sul segnaposto: confermiamo la vostra lettura di `E_OFFERTA_XXX`. Era rumore del
nostro grep testuale — cercava letterali `E_*` ovunque, commenti compresi. La vostra
analisi AST è la fonte giusta, e questo è un buon promemoria sul perché il gemello
lato DB non poteva essere un `grep` sugli YAML (§6.2).

### 6.2 Il gemello lato DB c'è — e al primo giro ha trovato un orfano

[`db/pgtap/script/test-catalogo-messaggi-errore-completo.sql`](../../../../db/pgtap/script/test-catalogo-messaggi-errore-completo.sql),
quattro casi. Il cuore è il test 2: estrae da **`pg_proc.prosrc`** i codici che le
funzioni passano a `fn_log_and_raise_error` / `fn_log_error_only` e verifica che
esistano a catalogo. Oggi sono **301 codici distinti su 342 funzioni**. Quando è
rosso, l'output nomina codice e funzione, e la riparazione è un append al CSV.

La fonte è il **database vivo**, non i file, e non è un dettaglio estetico: al primo
giro il test ha trovato

```text
E_FATTURA_NON_ANNULLABILE  <-  vendite.trgfn_fatture_numerata_non_annulabile
```

un trigger **attivo** che solleva un codice mai entrato in catalogo. Era invisibile
alla nostra analisi di ieri, che scandiva gli YAML di `migrations_v2`: quel trigger è
definito nella cartella **legacy** `db/changelog/migrations/39_vendite/`. Una scansione
dei sorgenti l'avrebbe mancato per sempre; `pg_proc` no.

Seminato anche lui, id **830**, con `causa` e `soluzione` scritte: la regola che
protegge (una fattura già numerata non può uscire dal registro con un cambio di stato,
o la sequenza fiscale resta con un buco) merita di essere spiegata nel punto in cui
qualcuno la incontra.

Stato del test: **rosso adesso**, verde dopo il `migrate` — è rosso *perché* il seed
non è ancora applicato. Verificato simulando l'apply in transazione: 4/4. Non va messo
in baseline.

### 6.3 Due nomi che il registro non saprà distinguere

Nessuno dei due blocca il seed — sono seminati come li avete scritti — ma è il momento
buono per cambiarli, perché costano tre righe di CSV oggi e un pezzo di storia domani.

**`E_EMITTENTE_NON_RISOLTO`.** A catalogo esistono già
`E_ORDINE_EMITTENTE_NON_RISOLTO`, `E_CONTRATTO_EMITTENTE_NON_RISOLTO` e
`E_PREV_EMITTENTE_NON_RISOLTO`, e ieri ne abbiamo riscritto i testi. Sembrano la
stessa famiglia, ma dicono il contrario: quelli significano «**chi crea** non ha un
emittente da cui derivare il default», il vostro (in `stampa_coda_drainer_service`)
significa «**il documento in coda** non ce l'ha, dato sporco». Chi leggerà `error_log`
li vedrà accanto e li tratterà come varianti. Proposta: **`E_FATTURA_EMITTENTE_NON_RISOLTO`**,
che si allinea alla convenzione per documento già in uso.

**`E_COMPETENZA_INSERT` / `E_COMPETENZA_NOT_FOUND`.** Qui la collisione è più
insidiosa perché la parola è la stessa ma il dominio no. A catalogo `E_COMPETENZA` e
`E_COMPETENZA_SUPERATA` (sollevati da `trgfn_attivita_fatturabili_guard_fonte`)
parlano di **competenza temporale** — il mese o l'intervallo dal/al di un'attività
fatturabile. I vostri parlano di **competenze del flusso**, che è un'altra cosa.
Proposta: **`E_FLUSSO_COMPETENZA_INSERT`** / **`E_FLUSSO_COMPETENZA_NOT_FOUND`**,
coerenti con la famiglia `E_FLUSSO_*` che avete già (`E_FLUSSO_INSERT`,
`E_FLUSSO_ID_INVALIDO`, `E_FLUSSO_PRESA_IN_CARICO`).

Se preferite tenerli così, va bene lo stesso: sono nomi, non difetti — ma allora vale
la pena scriverlo da qualche parte, perché fra sei mesi non si distinguono più. La
meccanica della rinomina, se la accettate, è nel §6.4.

### 6.4 Cosa resta al BE — richieste, non modifiche

Questo cantiere è **solo DB**: `error_policies.py`, i call-site e i test Python non
vengono toccati da noi (§9.7). Quello che segue è quindi una richiesta, con l'effetto
lato catalogo che ci impegniamo a fare **nello stesso giro**.

| # | Cosa | Dove, lato vostro | Cosa facciamo noi quando lo fate |
| --- | --- | --- | --- |
| R1 | `E_EMITTENTE_NON_RISOLTO` → **`E_FATTURA_EMITTENTE_NON_RISOLTO`** | `stampa_coda_drainer_service.py` (2 call-site), `error_policies.py` (1 `ErrorPolicy`), `test_stampa_coda_drainer_service.py` (1 assert) | rinominiamo la riga 811 del CSV e allineiamo il testo a «…per la fattura in coda di stampa» |
| R2 | `E_COMPETENZA_INSERT` → **`E_FLUSSO_COMPETENZA_INSERT`** | `pratiche_repository.py` (1), `error_policies.py` (1) | rinominiamo la riga 805 |
| R3 | `E_COMPETENZA_NOT_FOUND` → **`E_FLUSSO_COMPETENZA_NOT_FOUND`** | `pratiche_service.py` (1), `error_policies.py` (1) | rinominiamo la riga 806 |

> ✅ **Chiuso il 2026-08-04, nell'ordine giusto.** Il BE ha rinominato i tre codici
> (verificato: i nomi nuovi sono in `error_policies.py`, i vecchi non compaiono più in
> nessun call-site), e subito dopo abbiamo rinominato le tre righe del CSV — **id 805,
> 806, 811 invariati**, cambia solo il `codice`, quindi il loader `runOnChange`
> aggiorna le righe esistenti senza lasciare orfani.
>
> Il testo di 811 è stato allineato al `user_message` che il BE espone davvero
> («…per la fattura in coda di stampa»), non a quello che avevamo ipotizzato: il
> catalogo continua a dire esattamente ciò che dice l'API, che era il presupposto di
> tutto il seed. Verificato anche che **nessuna funzione del database** citasse i nomi
> vecchi, e che ogni codice dichiarato dal BE abbia una riga a catalogo.
>
> ⏳ Manca solo il `migrate`: finché non gira, il database ha ancora i nomi vecchi e
> i tre codici degradano — con il codice originale conservato nel `context`, quindi
> senza perdita di informazione.

⚠️ **L'ordine conta e la finestra si chiude.** Le tre righe sono seminate **con i nomi
attuali**, perché il catalogo deve nominare i codici esattamente come li emette il
backend: rinominarle prima di voi significherebbe che per qualche giorno quei tre
codici non si risolvono e degradano. E conviene decidere adesso: il seed **non è
ancora applicato** a nessun database, quindi oggi la rinomina costa tre stringhe;
dopo l'apply costa anche una riga di catalogo orfana e un pezzo di storia del log
sotto il nome vecchio.

Sui due `E_EMAIL_*` che segnalate voi stessi come debito (§3, nota 1): d'accordo sulla
diagnosi, e per la stessa ragione dei tre sopra. Non è una nostra richiesta perché
spacchettarli sposta lo status HTTP di endpoint in uso — decisione vostra, sulla vostra
metà.

### 6.5 Sul «meno urgente del primo»

È vero, e vale la pena dire perché con precisione: dal `20260803-11` il ripiego
conserva `context->>'codice_errore_originale'`, quindi **l'informazione non si perde
comunque**. Quello che si perde senza la riga a catalogo è la possibilità di
**contare**: `error_log` si unisce al catalogo per FK, quindi un codice non seminato
non compare in nessun raggruppamento per codice — c'è, ma solo se lo si va a cercare
nel jsonb. È la differenza fra un errore leggibile e un errore misurabile.

### 6.6 Attività svolte lato DB — registro

Perimetro rispettato: **nessun file di `backend/` è stato modificato.** Le tre
rinomine del §6.3 sono richieste al BE (§6.4), non modifiche applicate.

| # | Attività | File | Stato |
| --- | --- | --- | --- |
| 1 | Verifica dei 28 codici prima del seed: tutti dichiarati in `error_policies.py`, nessuno già a catalogo, nessun `%s`, nessun duplicato | — | ✅ |
| 2 | Seed dei 28 codici, lingua `it`, `causa`/`soluzione` vuote, **id 802–829** | `80_data/sql/config/messaggi_errore.csv` | ✅ append puro |
| 3 | Check gemello lato DB, quattro casi, legge `pg_proc.prosrc` | `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql` | ✅ nuovo |
| 4 | Seed di `E_FATTURA_NON_ANNULLABILE` (**id 830**) — orfano trovato dal check al primo giro, con `causa` e `soluzione` scritte | stesso CSV | ✅ |
| 5 | Verifica del check simulando l'apply in transazione con rollback | — | ✅ 4/4 |
| 6 | Risposta DB nel brief (§6) | questo documento | ✅ |
| 7 | Controprova su `E_PIPELINE_DRIVER_MAX_ITER` e su `E_FATTURA_NON_ANNULLABILE` in `dbops.error_log` | — | ✅ entrambi registrati col proprio nome |

**Numeri finali:** CSV a **628 righe**, +29 in append (28 richiesti + 1 orfano),
nessun `id` duplicato, nessuna coppia `(codice, lingua)` duplicata, nessuna riga
preesistente toccata.

**Esito dopo l'apply (2026-08-04).** Catalogo a **628 righe**, le 29 nuove tutte
dentro. Il check gemello è **4/4 verde** — il test 2, che prima nominava
`E_FATTURA_NON_ANNULLABILE`, è rientrato da solo con il seed. Non è mai stato messo in
`baseline-rossi.tsv`: era rosso *perché* il seed non era applicato, non per un difetto.
Da qui in avanti, se torna rosso, l'output dice quale codice e quale funzione, e la
riparazione è un append al CSV.

**Controprova, per esteso.** Due chiamate a `fn_log_error_only` e una rilettura di
`dbops.error_log` (righe riconoscibili da `function_name = 'round2-*'`):

| Codice | Prima | Ora |
| --- | --- | --- |
| `E_PIPELINE_DRIVER_MAX_ITER` | `MESSAGGIO_NON_DEFINITO` | «Pipeline interrotta: superato il numero massimo di iterazioni.» |
| `E_FATTURA_NON_ANNULLABILE` | `MESSAGGIO_NON_DEFINITO` | «Fattura %s gia' numerata: l'annullamento non e' ammesso.» |

Il secondo è la chiusura del cerchio: un codice che nessuno dei due registri conosceva,
trovato dal check e reso leggibile nello stesso giro.

---

## 7. Risposta BE (2026-08-04) — le tre rinomine sono fatte, palla al CSV

> **Chi scrive:** BE (`dev/backend-tid`), dopo il vostro apply del §6.6.

**R1, R2 e R3 accolte e applicate.** Le motivazioni del §6.3 reggono entrambe, e
la seconda è quella che ci ha convinti di più: `E_COMPETENZA_*` sembrava
innocuo finché non avete affiancato i due significati — competenza *temporale*
di un'attività fatturabile contro competenze *del flusso*. Sono due cose che
condividono solo la parola, ed è esattamente il tipo di ambiguità che non si
nota finché non si legge il registro con occhi diversi dai propri.

| # | Rinomina | Call-site toccati |
| --- | --- | --- |
| R1 | `E_EMITTENTE_NON_RISOLTO` → **`E_FATTURA_EMITTENTE_NON_RISOLTO`** | `stampa_coda_drainer_service.py` (2), `error_policies.py` (1), `test_stampa_coda_drainer_service.py` (1) |
| R2 | `E_COMPETENZA_INSERT` → **`E_FLUSSO_COMPETENZA_INSERT`** | `pratiche_repository.py` (1), `error_policies.py` (1) |
| R3 | `E_COMPETENZA_NOT_FOUND` → **`E_FLUSSO_COMPETENZA_NOT_FOUND`** | `pratiche_service.py` (1), `error_policies.py` (1) |

I conteggi del §6.4 erano esatti: verificati con una ricerca su tutto
`backend/` e `frontend/` prima di toccare, nessun call-site oltre quelli
elencati e nessun residuo dopo. Le tre stringhe non sono sottostringhe di altri
codici (`E_ORDINE_EMITTENTE_NON_RISOLTO` e compagnia non contengono
`E_EMITTENTE_NON_RISOLTO`), quindi la sostituzione non ha potuto sbordare.

### 7.1 Il testo di R1, per il vostro allineamento

Il `user_message` è stato allineato a quello che proponete:

> **`Emittente fiscale non risolvibile per la fattura in coda di stampa.`**

Usatelo tale e quale sulla riga 811, così i due registri dicono la stessa frase.
Per R2 e R3 i testi non cambiano.

Nel codice, accanto alla policy R1 è rimasta scritta la ragione della rinomina —
che le due famiglie dicono il **contrario** l'una dell'altra: là è chi crea a non
avere un emittente da cui derivare il default, qui è il documento già esistente
ad esserne privo. È la distinzione che il §6.3 fa, e volevamo che sopravvivesse
al brief: chi rileggerà quella policy fra un anno non avrà questo documento
aperto accanto.

### 7.2 Stato

Suite backend **verde sui perimetri toccati** (933 test fra `core`, `pratiche` e
il drainer di stampa) e **guardrail anti-ricaduta verde**: i tre nomi nuovi sono
dichiarati, quindi il check li presidia da subito.

> ⚠️ **La finestra del §6.4 si è chiusa mentre la scrivevate.** Il §6.4 dice «il
> seed non è ancora applicato», ma il §6.6 registra l'apply dello stesso giorno:
> le tre righe sono già a catalogo **col nome vecchio**. Non è un problema —
> nell'intervallo fra questo commit e il vostro allineamento del CSV i tre codici
> degradano a `MESSAGGIO_NON_DEFINITO`, conservando però
> `context->>'codice_errore_originale'` (§9.9 del round 1). Si perde la
> *contabilità* per quei tre codici, non l'informazione, e per il tempo di un
> giro di CSV. Era l'ordine che avevate indicato voi — prima il BE, poi il
> catalogo — e resta quello giusto.

### 7.3 Su `E_EMAIL_OP` / `E_EMAIL_ADMIN`

Confermiamo che resta debito nostro e non lo chiudiamo qui: spacchettarli per
verbo cambia lo status HTTP di endpoint già in uso dal frontend, quindi vuole il
suo giro con la verifica lato UI. È annotato nel codice, dove lo incontrerà chi
ci mette mano — non solo in questo brief.
