# Brief DB — Un documento con un numero che non è un numero non si genera

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB
> (`dev/db-tid`); poi BE (§4), che **attende** la consegna DB.
> **Origine:** L3 di [piano-be-type-checker.md](piano-be-type-checker.md) §5.3 — mypy
> ha segnalato in `apps/documenti/services/context_builders/_number_formatting.py`
> (righe 96 e 101) un'operazione che su NaN/Infinity va in `TypeError`.
> **Decisione:** di Tid, 2026-10-09 — **opzione C**: se un valore numerico di un
> documento è NaN o infinito, la generazione si **ferma** con un errore chiaro; non si
> stampa «NaN» e non lo si nasconde con un trattino.
> **Stato:** 🟡 D-1…D-3 decise da Tid il 2026-10-09 come da raccomandazione (§5.4).
> ✅ **DB chiuso il 2026-10-09** (§6): `20261009-10` … `-18` applicati su dev e su
> `zeroerp_ci`, codice nuovo nel catalogo, pgTAP verdi (corsa di Tid). ⏳ Resta la
> ricaduta BE (§4, con la correzione del §6.3).
> **Da leggere per primo:** §6.

## 1. Il difetto

PostgreSQL ammette nel tipo `numeric` i valori speciali `'NaN'` e (dalla 14)
`'Infinity'`/`'-Infinity'`. Se uno di questi arriva a un documento (importo, prezzo,
quantità), `format_misura` calcola `-d.as_tuple().exponent`, che per questi valori è
una **stringa** (`'n'`, `'N'`, `'F'`): il segno meno su una stringa è un `TypeError`,
cioè la generazione del PDF esce con un 500 anonimo. `format_importo` fa lo stesso per
gli infiniti (`quantize` solleva `InvalidOperation`).

⚠️ Un CHECK come `prezzo >= 0` **non** ferma `'NaN'`: in PostgreSQL `NaN` è maggiore
di ogni altro numero, quindi il CHECK lo lascia passare.

## 2. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **Un codice d'errore** per «il documento porta un valore numerico non finito», per esempio `E_DOCUMENTI_VALORE_NUMERICO_NON_VALIDO`, con la frase (un segnaposto per il campo, uno per il valore) e la classe. Proposta del BE sulla classe: **non** `DATO_ERRATO`, perché la richiesta dell'operatore è corretta e il difetto sta nel dato già scritto. La domanda «chi può rimediare» la decide il team DB. |
| **R-2** | **Da valutare (decisione di Tid):** il modo giusto di non arrivarci mai è che il valore non si **scriva**. Un controllo `<> 'NaN'` (e sugli infiniti) sulle colonne `numeric` di importi, prezzi e quantità dei documenti, con un guard o un CHECK, sul modello del guard comune delle date. Il BE non sa se un percorso oggi possa scriverli: la domanda è sul modello, non sui dati. |

## 3. Fuori da questo brief

- La formattazione delle date e dei valori non numerici (stringhe descrittive): restano
  come sono.

## 4. Ricaduta BE (dopo la consegna DB)

1. Policy generata e frase di ripiego (`error_messages_fallback.py`) per il codice nuovo,
   rigenerate **dopo** il pull della consegna DB, mai col DB avanti rispetto a git.
2. `_number_formatting.py`: `format_misura` e `format_importo` riconoscono un `Decimal`
   non finito (`not d.is_finite()`) e sollevano il codice nuovo col nome del campo. I 2
   rilievi mypy residui (righe 96 e 101) si sanano qui, e il registro scende a **zero**.
3. Test: NaN, `Infinity` e `-Infinity` (anche da stringa e da `float`) su una misura e su
   un importo → l'errore col codice; un numero normale → invariato.

## 5. Analisi del team DB (2026-10-09)

### 5.1 Che cosa ammette il modello

Prove in sola lettura sul PostgreSQL 18 di `zeroerp_ci`, 2026-10-09:

| Fatto | Conseguenza |
| --- | --- |
| `numeric(p,s)` **rifiuta** gli infiniti (overflow), ma **accetta** `NaN`; `numeric` senza scala accetta tutti e tre | il problema c'è su ogni colonna numerica; gli infiniti solo su quelle senza scala |
| `NaN` **contagia**: `NaN * 0 = NaN`, una somma con un `NaN` è `NaN`, `round(NaN) = NaN` | un solo valore rovina totali, riepiloghi IVA, plafond, capienze. Il documento è il punto in cui il difetto **si vede**, non quello in cui nasce né il solo in cui fa danno |
| `NaN` è maggiore di ogni numero: `NaN >= 0` è vero, `NaN > soglia` è vero | i CHECK di segno lo lasciano passare (il ⚠️ del §1 è confermato) e ogni confronto con una soglia risponde «sì» |
| `to_jsonb('NaN'::numeric)` è la **stringa** `"NaN"` | un contesto congelato in `documenti.documenti_generati.context_json` può portarlo come testo, e `_to_decimal` lo rifà `Decimal('NaN')`: il caso vale anche per la **ristampa** |
| Nessuna funzione né vista di `migrations_v2` usa `NaN`/`Infinity` come valore sentinella su un `numeric` (gli `infinity` del repo sono tutti **date**) | vietarli non toglie un significato a nessuno |

Struttura (contratto, non popolazione), stessa data: nessuna colonna `float` nelle
tabelle applicative; colonne `numeric` 170, di cui **48 senza scala** (45 in
`vendite`, 3 in `pagamenti`) e 122 con scala; **nessun** CHECK esclude `NaN`.

⚠️ **Una porta d'ingresso, da verificare dal BE**: `json.loads` di Python accetta i
letterali `NaN`, `Infinity`, `-Infinity` e li rende `float`; passati a psycopg
diventano un `numeric` non finito. Se l'envelope JSON non li rifiuta, un client
qualunque li scrive. Non serve sapere se oggi succede: il tipo lo ammette.
⚠️ Aggiornamento dello stesso giorno: il BE ha già un building block che rifiuta
`NaN` e infiniti nei payload (`apps/core/services/payload_helpers.py`, e
`_componenti_service_helpers` per gli override). La domanda resta se **ogni** percorso
numerico ci passi; con i CHECK del §6 la risposta non decide più niente, perché il DB
rifiuta comunque.

### 5.2 R-2 — la regola è del TIPO, non dei documenti

**Perimetro.** Tutte le colonne `numeric` delle tabelle applicative, non solo quelle
dei documenti: un prezzo di listino `NaN` arriva al documento **per copia**, e una
regola sui soli documenti lascerebbe aperta la sorgente. Escluso `storico`: le
tabelle ombra ricordano, non giudicano (come `DATE_VALIDITA`).

**Forma raccomandata: un CHECK, non un guard.**

- Chi scrive `NaN` non è una persona da un form (nessun campo numerico del FE lo
  produce): è un **chiamante rotto**. Una frase di dominio non avrebbe un lettore.
- Il CHECK è la regola **dichiarata**, non costa un trigger per riga e non entra
  nell'ordine dei guard `BEFORE ROW`. Un guard generico dovrebbe scorrere tutte le
  colonne numeriche di `NEW` a ogni scrittura, sulle tabelle di righe che sono le più
  calde del modello.
- **Un predicato solo** per tutte: `col > '-Infinity' AND col < 'Infinity'`. Provato:
  falso su `NaN`, `Infinity`, `-Infinity`; vero sui numeri; `NULL` passa, come in ogni
  CHECK. Sulle colonne con scala basterebbe `<> 'NaN'`, ma una forma unica si presidia
  meglio.

**Come si costruisce.** Un changeSet `00_schema` che aggiunge i CHECK alle colonne
esistenti (nome `ck_<tabella>_<colonna>_finito`, da tenere sotto i 63 caratteri), con
la `preCondition` che si ferma se una riga non passerebbe, sul modello di P-8. Poi un
**presidio** pgTAP che conta le colonne `numeric` senza quel CHECK e pretende zero:
così una colonna nuova non nasce senza.

L'alternativa è un'automazione sul modello di `DATE_VALIDITA`, montata da `ci_apply`
sulla sola presenza del tipo. È più coerente col precedente, ma un vincolo nato da
un'automazione **non sta nel DDL dichiarato**, e i vincoli generati hanno già dato
problemi (nomi troncati a 63 caratteri, vincoli che spariscono a una ricostruzione).
Raccomandazione: CHECK espliciti più presidio. **D-1.**

### 5.3 R-1 — il codice

- **Classe `TECNICO`.** Con R-2 fatto, un valore non finito in un documento è
  un'**invariante rotta** (il DB lo vieta): è il caso di
  `E_VENDITE_PRICING_ESITO_ASSENTE`. Anche senza R-2 nessuno rimedia da un form: su un
  documento emesso il dato è bloccato, e chi legge l'errore è chi diagnostica. Non è
  `DATO_ERRATO` (d'accordo col BE) e non è `CONFLITTO_STATO` (lo stato non c'entra).
- **Nome: `E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO`.** «Non valido» è la parola
  generica che il catalogo evita; «non finito» dice quale difetto.
- ⚠️ *Superato dal §6.3: la frase è senza segnaposto.* **Frase:** due segnaposti, il campo e il valore. Per un `TECNICO` nominare la
  variabile del template è giusto: il lettore è chi diagnostica (guida
  [Messaggi di Errore](../../guide/Messaggi-di-Errore-e-Generazione-Log.md), tabella
  «Il dato lo fornisce…», seconda riga).
- ⭐ **R-1 serve anche con R-2.** I CHECK sulle colonne non vedono dentro il
  `context_json` congelato di `documenti_generati`, che la ristampa rilegge: la
  difesa del BE resta la sola sede su quel percorso. Le due richieste non sono una
  l'alternativa dell'altra.

### 5.4 Decisioni per Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **D-1** | R-2 sì o no; e se sì, CHECK espliciti con presidio o automazione | sì, CHECK espliciti con presidio (§5.2) |
| **D-2** | Perimetro: tutte le colonne `numeric` applicative, o solo quelle dei documenti | tutte, `storico` escluso: la sorgente è a monte del documento |
| **D-3** | Classe e nome del codice di R-1 | `TECNICO`, `E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO` |

Richiesta al BE, indipendente dalle decisioni: verificare se l'envelope JSON
(`handle_post_json`) rifiuta i letterali `NaN`/`Infinity`. Se non li rifiuta, è la
porta da chiudere anche lì, perché oggi la apre il parser e non il dato.

✅ **Decise da Tid il 2026-10-09: D-1, D-2 e D-3 come da raccomandazione.**

## 6. Consegna DB (2026-10-09) — ✅ applicata, pgTAP verdi

### 6.1 Che cosa è stato scritto

| File | Cosa |
| --- | --- |
| `00_schema/<schema>/20261009-10` … `-18-add-chk-numerici-finiti-<schema>` | uno per schema (acquisti 16 colonne, anagrafiche 12, catalogo 4, config 4, documenti 4, magazzino 10, pagamenti 4, shop 2, vendite 114): **170 CHECK** `chk_<tabella>_<colonna>_finito`, un `ALTER TABLE` per tabella. `preCondition` `HALT` con `expectedResult 0` sui valori non finiti già scritti |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` (id 1228) | `E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO`, classe `TECNICO` |
| `db/pgtap/dbops/test-numerici-finiti-v1.sql` | il presidio (plan 8): ogni colonna `numeric` ha il CHECK nella forma esatta; la lente vede le colonne (>150) e le due forme del tipo; la stampa del catalogo, rimontata su una TEMP, rifiuta `NaN`, `Infinity`, `-Infinity` e accetta un numero e il `NULL` |
| `docs/it/linee-guida-sql.md` §7d | la regola per chi scrive una colonna nuova |

Sulle quattro colonne di `offerte_commerciali_eccezioni_componenti` il nome per esteso
superava i 63 caratteri: si usa la sigla di casa `chk_oce_comp_<colonna>_finito`.
L'elenco delle colonne viene dal catalogo, identico su `zeroerp` e `zeroerp_ci` il
2026-10-09.

### 6.2 Le prove (2026-10-09, prima dell'apply)

SQL **estratto dagli YAML** (`yaml.safe_load`), non riscritto:

- **`zeroerp_ci`, come owner, in una transazione annullata:** le nove `preCondition`
  danno 0; i changeSet creano i 170 vincoli; la lente del presidio passa da **0 su 170
  a 170 su 170**. Su ogni colonna di una tabella con righe (5 colonne su 170: lo
  scratch ha solo i seed) `NaN`, `Infinity` e `-Infinity` sono rifiutati — 14 dal CHECK
  o dal tipo, 1 prima ancora da un guard di `config.iva` (l'aliquota non si modifica).
  Le altre 165 colonne stanno su tabelle vuote: lì il rifiuto lo provano i test 4-8 del
  presidio, sulla stessa stampa del vincolo.
- **`zeroerp` (dev), come `zeroerp_app`:** otto `preCondition` su nove danno 0; quella
  di `shop` non si legge (l'app non ha `USAGE` sullo schema). ⚠️ Non è la prova che
  conta: sotto RLS l'app vede solo una parte delle righe. La prova vera la fa il migrate,
  che gira come proprietario e si ferma (`HALT`) se trova anche un solo valore.
- Il pgTAP **non è stato lanciato** (lo lancia Tid).

Altri presidi letti per vedere se 170 CHECK nuovi li fanno diventare rossi: quelli che
enumerano i CHECK li cercano per nome o per forma (`_comp_quantita_`, `data_consegna`,
`= ANY (ARRAY[`), e nessuno di questi corrisponde ai nomi nuovi. Le partizioni di
`vendite.note` (`test_note_vincoli_mappati_db.py`) non hanno colonne `numeric`.

### 6.3 ⚠️ Correzione alla richiesta R-1: la frase è senza segnaposto

R-1 chiedeva due segnaposto (campo e valore). A riempire un `%s` del catalogo è
`script.fn_log_and_raise_error`; un codice che solleva **solo il backend** non passa
di lì, e il `%s` uscirebbe a video così com'è (stessa regola di `E_MAGAZZINO_VALIDATION`
e dei suoi fratelli `*_VALIDATION`). Frase registrata:
*«Il documento non si può generare: un valore numerico non è un numero.»* Il campo e il
valore li porta il `ServiceError` del BE (`context.field` + `detail`), che è il canale
giusto per chi diagnostica.

### 6.4 Che cosa resta

1. ✅ **Tid, 2026-10-09:** apply di `20261009-10` … `-18` e del catalogo; pgTAP verdi,
   `test-numerici-finiti-v1` compreso. Verificato dal catalogo lo stesso giorno: 170
   vincoli `chk_*_finito` su `zeroerp` e su `zeroerp_ci` (nove changeSet `EXECUTED` alle
   11:20 nel `databasechangelog` di `zeroerp_ci`); `E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO`
   a catalogo con classe `TECNICO`. ✅ Lato DB chiuso.
2. **BE (§4), dopo il pull:** policy generata e frase di ripiego per il codice nuovo;
   `format_misura`/`format_importo` sollevano il codice con campo e valore nel contesto
   (§6.3). Da sapere: con i CHECK una scrittura con `NaN` esce come `23514` col nome del
   vincolo `chk_…_finito`, cioè un errore tecnico. È voluto (D-1): il BB dei payload
   dovrebbe averla già fermata prima.
