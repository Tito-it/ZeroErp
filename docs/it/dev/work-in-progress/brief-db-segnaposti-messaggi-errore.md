# Brief DB — L'arità dei segnaposto nel catalogo messaggi

> **Origine**: nota del 2026-08-18 su `E_ARTICOLO_NON_COMPOSITO` — «il `%s` arriva
> a video letterale: nessun chiamante lo riempie».
> **Stato**: catalogo corretto (2 codici) · presidio scritto · **8 correzioni ai
> chiamanti specificate, non applicate** (§7) — decise il 2026-08-18, vanno in un
> lotto loro subito dopo questo; poi il ripiego di `fn_log_and_raise_error` (§8, D-2).
> **Perimetro**: DB. Le richieste al backend stanno in §10.

---

## 1. Il rilievo di partenza, e cosa ha trovato la passata

Il rilievo era su un messaggio:

```
E_ARTICOLO_NON_COMPOSITO → «Articolo deve essere composito = true . (%s)»
```

È confermato. Ma la passata che ne è nata ha trovato **una seconda classe di
difetto, peggiore**, che nessuno stava guardando: non il segnaposto che resta a
video, ma il segnaposto che **cancella l'errore di dominio**.

| | Classe | Punti | Cosa vede l'operatore | SQLSTATE |
|---|---|---|---|---|
| A | il chiamante passa **zero** valori | **2** | il `%s` a video, letterale | `P0001` (integro) |
| B | il chiamante passa **meno** valori dei segnaposto | **8** | un errore tecnico opaco | **`22023`** |

La classe A è quella segnalata. La classe B è la stessa svista contata
diversamente, e costa molto di più.

---

## 2. Il meccanismo, in sei righe

`script.fn_log_and_raise_error` compone il testo così:

```sql
-- 4) Format placeholder con VARIADIC values, se presenti.
IF array_length(p_valori, 1) IS NOT NULL THEN
    v_msg := format(v_msg, VARIADIC p_valori);
END IF;
```

Due comportamenti diversi a seconda di quanti valori arrivano:

- **zero valori** (`VARIADIC ARRAY[]::text[]` → `array_length` è `NULL`) — il
  ramo si **salta**. `v_msg` resta il template e il template arriva al client:
  l'operatore legge `(%s)`. L'errore di dominio sopravvive: è solo il testo a
  essere rotto.
- **da uno in su, ma meno dei segnaposto** — `format()` **alza**, e alza da
  dentro `fn_log_and_raise_error`. Il `RAISE` di dominio, che sta due righe
  sotto, non viene mai eseguito.

⚠️ **La seconda è la più grave e la meno visibile.** Il contratto DB→backend è
«`P0001` + campo `CONSTRAINT` valorizzato = errore di dominio»
(`guardrail_codice_errore_strutturato.sql`). Con un `22023` non arriva né il
`P0001`, né il `CONSTRAINT` col codice, né il `COLUMN` col campo da correggere.
Il guard **blocca lo stesso** — quindi il dato resta integro e niente sembra
rotto — ma il backend non ha più il codice su cui decidere 409/404/403, e
l'operatore legge un errore interno al posto della frase scritta per lui.

## 3. Le due classi riprodotte sul DB di sviluppo

Sola lettura, senza scrivere log, ripercorrendo gli stessi passi della funzione:

```
=== A) LEAK ===
NOTIFICA: MESSAGGIO CHE ARRIVA AL CLIENT --> Articolo deve essere composito = true . (%s)

=== B) CRASH === (1 valore su 2 segnaposto)
ERRORE: 22023: numero di argomenti non sufficiente per format()
```

---

## 4. La misura

Fatta **due volte, in modo indipendente**, e le due misure coincidono:

- un analizzatore Python sulle definizioni in `docs/it/dbzero/*/funzioni/*.md`
  (la doc auto-generata, cioè l'oggetto vivo) — **998 punti**;
- un analizzatore SQL su `pg_proc.prosrc` (le funzioni vive, direttamente) —
  **1001 punti**, 368 codici letterali distinti, 385 funzioni.

Lo scarto di 3 sono funzioni che vivono nella cartella legacy
`db/changelog/migrations/` e non hanno doc auto-generata — cioè lo scanner SQL
vede *di più*, ed è quello che è finito nel presidio.

### Classe A — zero valori, il `%s` esce letterale

| Codice | Messaggio | Chiamante |
|---|---|---|
| `E_ARTICOLO_NON_COMPOSITO` | `Articolo deve essere composito = true . (%s)` | `catalogo.trgfn_articoli_componenti_guard_is_composito` |
| `E_TXID_GENERATION` | `Fallita generazione tx_id: %s` | `dbops.trgfn_tx_id_managed` |

### Classe B — meno valori dei segnaposto, `22023`

| Codice | Passa | Servono | Chiamante |
|---|---|---|---|
| `E_CANALE_ORIGINE_IMMUTABILE` | 1 | 2 | `script.trgfn_canale_origine_immutable` |
| `E_DEFAULT_ERRATO` | 2 | 3 | `script.fn_get_default_by_param` (**primo** dei due punti) |
| `E_RIGA_LISTINO_VERSIONE_CHIUSA` | 2 | 3 | `vendite.trgfn_listini_righe_guard_stato` |
| `E_SHOP_RICEVUTA_BA_CANALE_INVALIDO` | 1 | 2 | `shop.trgfn_ricevute_guard_ba_canale` |
| `E_SOGGETTI_RUOLI` | 1 | 3 | `anagrafiche.trgfn_identita_digitali_guard_coerenza` |
| `E_SORG_KEY_MISSING` | 1 | 2 | `script.trgfn_guard_sorgente_polimorfa_testuale` |
| `E_SORG_KEY_MISSING` | 1 | 2 | `script.trgfn_guard_sorgente_polimorfa_tipizzata` (**due** punti) |
| `E_SOSPENSIONI_FLUSSO_NON_COERENTE` | 1 | 2 | `pratiche.trgfn_sospensioni_guard_coerenza_flusso` |

⭐ **Cinque di questi otto hanno la stessa forma, e non è «mi sono dimenticato un
valore».** Il chiamante passa **una frase già composta** — `format(...)` o
`concat(...)` — come valore unico, mentre a catalogo il messaggio ha i suoi
segnaposto. Sono **due messaggi scritti due volte**, uno nel plpgsql e uno nel
CSV, che non si compongono. Ed è un difetto anche quando non alza: la frase
composta dentro alla funzione **non è traducibile**, perché non passa da
`config.messaggi_errore`.

### Il terzo gruppo, innocuo ma non muto

61 punti passano **più** valori dei segnaposto. `format()` ignora quelli di
troppo, quindi a video non succede niente. Vale la pena saperlo per due motivi:
i valori in eccesso finiscono comunque in `dbops.error_log` (il log è più ricco
del messaggio, non più povero), e chi un giorno aggiungerà un `%s` a uno di quei
messaggi lo vedrà riempirsi **da solo** — il che è comodo, ma solo se sa che
sta succedendo.

---

## 5. Perché i «43 messaggi con `(%s)`» non erano la misura giusta

Il conteggio dei `(%s)` a catalogo è una spia utile — è così che il difetto è
saltato fuori — ma non è la proprietà da verificare: **conta i messaggi, mentre
il difetto sta nell'incontro fra un messaggio e un chiamante**.

Dei 43, la grande maggioranza è sana: il `(%s)` è riempito dal punto che
solleva. E per converso, 7 degli 8 difetti di classe B hanno un messaggio che
nel conteggio dei `(%s)` non compare affatto. La misura giusta è l'**arità**:
quanti valori passa il chiamante, contro quanti segnaposto ha il messaggio nella
lingua della sessione.

---

## 6. Cosa è stato fatto

### 6.1 Catalogo — i 2 codici di classe A

In `80_data/sql/config/messaggi_errore.csv` (mirror `runOnChange`: si corregge
il CSV, il loader riallinea al migrate — nessun changeSet nuovo).

- **`E_ARTICOLO_NON_COMPOSITO`** — il valore che il `(%s)` avrebbe portato è il
  `prodotto_id`, che per l'operatore non è un'informazione: resta nel context e
  nel log. Il messaggio diventa una frase intera, e per la prima volta ha
  `causa` e `soluzione`:
  > L'articolo indicato non è composito: non può avere una distinta base.

  ⭐ È anche la frase che il backend si era già scritto per conto suo in
  `error_messages_fallback.py` — vedi §10.
- **`E_TXID_GENERATION`** — stesso vizio. Il dettaglio (`SQLERRM`) era già nel
  context e la `soluzione` rimandava già al log: il `: %s` prometteva a video un
  dettaglio che non arrivava mai.
  > Generazione dell'identificativo di transazione non riuscita.

### 6.2 Il presidio — `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql`

⚠️ **Il presidio c'era già, e non presidiava.** Il test 4 di quel file si
chiamava «nessun messaggio con più di sei segnaposto `%s`», mentre in testata,
sopra, era scritta la proprietà vera:

> «Il numero di `%s` del messaggio va calibrato sull'arità MINIMA dei call-site:
> in `fn_log_and_raise_error` la `format()` non è protetta da EXCEPTION, quindi
> un segnaposto di troppo trasforma l'errore di dominio in un “too few arguments
> for format()”.»

La proprietà era **dichiarata e non misurata**: la soglia dei sei segnaposto è
una *proxy*, e nessuna proxy sul numero di segnaposto può dire quanti valori
passa un chiamante. Con quel test verde, oggi il catalogo aveva 2 punti di
classe A e 8 di classe B.

Ora il file ha 6 test: il 4 misura la classe A, il 5 la classe B, il 6 è la
vecchia proxy (che resta: intercetta i refusi di *seed*, che sono un'altra
cosa). L'incrocio è **per lingua** — un messaggio `en` con un numero di
segnaposto diverso dall'italiano romperebbe le sole sessioni inglesi, ed è
esattamente il caso che non si nota. Oggi c'è una sola riga `en` e il catalogo è
coerente; la verifica costa zero e c'è.

**Due trappole incontrate scrivendo lo scanner**, entrambe annotate nel file
perché chiunque lo tocchi le ritroverà:

1. **I commenti vanno via prima.** Nei corpi ci sono commenti in italiano fra un
   argomento e l'altro, e un apostrofo dentro a un commento
   (`NEW.target_riga_id e' bigint`) fa credere a qualunque conteggio che da lì
   in poi sia aperta una stringa. Senza quel passo,
   `trgfn_note_validate_generic` risultava passare 1 valore invece di 3: un
   **falso positivo su un punto sano**.
2. **`btrim(x)` con un argomento solo toglie gli spazi, non i newline.** Con gli
   argomenti scritti a capo — la forma normale qui dentro — il terzo argomento
   resta `\n            'E_...'` e non somiglia più a un letterale. Lo scanner
   perdeva **metà dei punti in silenzio** (490 su 1001) e rispondeva «tutto a
   posto».

⚠️ La seconda è la ragione per cui il numero della prima colonna di §4 è scritto
due volte con due strumenti diversi: uno scanner che sbaglia per difetto dà
sempre l'esito che si spera.

### 6.3 Baseline

Il file è **rosso** e registrato in `db/pgtap/baseline-rossi.tsv` con la causa.
Non è una regressione: è il debito che finalmente si vede. Rientra in due tempi
— test 4 al primo migrate che ricarica il CSV, test 5 quando arrivano le
correzioni di §7 — e a quel punto **la riga va tolta**.

---

## 7. Cosa resta: le 8 correzioni ai chiamanti

Nessuna richiede di toccare il catalogo: i valori che il messaggio nomina il
chiamante **ce li ha già**. Ognuna è un `CREATE OR REPLACE` con corpo preso
dalla doc auto-gen e un file nuovo con numerazione successiva (da `20260818-47`
in avanti). **Non applicate**: attendono il via libera.

| # | Funzione | Da | A |
|---|---|---|---|
| 1 | `script.trgfn_canale_origine_immutable` | `format('Modifica canale_origine vietata su %s.%s (%s -> %s)', ...)` | `TG_TABLE_SCHEMA, TG_TABLE_NAME` |
| 2 | `script.fn_get_default_by_param` (1° punto) | `p_table_schema, p_table_name` | i 3 valori del 2° punto, che è già corretto |
| 3 | `vendite.trgfn_listini_righe_guard_stato` | `OLD.id::text, v_stato` | `TG_OP, OLD.id::text, v_stato` |
| 4 | `shop.trgfn_ricevute_guard_ba_canale` | `format('Ricevuta shop %s: ...', ...)` | `NEW.id::text, COALESCE(v_ba_canale::text,'NULL')` |
| 5 | `anagrafiche.trgfn_identita_digitali_guard_coerenza` | `NEW.soggetto_ruolo_id::text` | i 3 con `'NULL'` sui due ignoti, come già fa `script.fn_guard_soggetto_ruolo` |
| 6 | `script.trgfn_guard_sorgente_polimorfa_testuale` | `concat(tipo, ' key_selector:', sel)` | `NEW.sorgente_tipo_id::text, v_selector` |
| 7 | `script.trgfn_guard_sorgente_polimorfa_tipizzata` (×2) | idem | idem |
| 8 | `pratiche.trgfn_sospensioni_guard_coerenza_flusso` | `concat('Il flusso ', ..., ' non appartiene alla pratica ', ...)` | `NEW.flusso_id::text, NEW.pratica_id::text` |

⚠️ **Il caso 5 merita una riga in più.** Il trigger solleva `E_SOGGETTI_RUOLI`
(«Non è stata assegnata la relazione») quando in realtà la condizione è
«`soggetto_ruolo_id` non trovato»: i due valori mancanti mancano *perché la riga
non esiste*. La correzione di arità lo rende innocuo, ma il codice resta
impreciso — è materia del **quarto lato**
(`scripts/sql/check_messaggio_vs_condizione.sql`), non di questa passata.

⚠️ Stessa cosa, più piccola, sul caso 2: il primo punto di
`fn_get_default_by_param` scatta quando la tabella **non ha chiave primaria**,
ma il messaggio dice «non ha valori per». Segnalato, non toccato.

---

## 8. Decisioni — prese il 2026-08-18

**D-1 — Si applicano le 8 correzioni in questo lotto o in uno suo? → LOTTO SUO, SUBITO DOPO.**
Sono 8 funzioni vive su 6 schemi. Il lotto è meccanico (una riga di argomenti
ciascuno) ma tocca guard di dominio, e finché non entra il test 5 resta rosso in
baseline. *Raccomandazione: lotto suo, subito dopo questo, così il rosso dura
poco e la revisione resta leggibile.* ✅ **Deciso così.** Prossimo passo:
changeSet `20260818-47` .. `-54`, uno per funzione, corpo dalla doc auto-gen.

**D-2 — `fn_log_and_raise_error` va resa a prova di arità? → SÌ, IN UN CHANGESET A SÉ.**
Oggi, se il conteggio non torna, la funzione che serve a **riportare** un errore
lo **distrugge**. Si può fare in modo che, quando i valori sono meno dei
segnaposto, invece di alzare `22023` cada sul template grezzo (cioè degradi da
classe B a classe A, che è brutta ma non perde il codice di dominio) e scriva un
`W_` nel log, che è la convenzione già in uso qui per «lo dico ma non blocco».

Il contro è reale: un ripiego rende il prossimo disallineamento silenzioso. Con
il test 5 in piedi non lo sarebbe — il presidio parla comunque — quindi le due
cose stanno insieme bene. *Raccomandazione: sì, ma solo dopo D-1, e come
changeSet suo:* è la funzione con **1001 punti di chiamata**, non è il posto
dove mettere due modifiche nello stesso commit. ✅ **Deciso così**: entra
**dopo** il lotto delle 8, da sola. A quel punto le due metà si tengono — il
ripiego impedisce che un errore di dominio si perda, il test 5 impedisce che il
ripiego diventi il modo normale di funzionare.

⚠️ Nota per chi la scriverà: il ripiego va nel ramo `format()`, non intorno al
`RAISE`. E deve distinguere i due esiti — `array_length` `NULL` (già oggi salta
la `format()`) è la classe A e resta com'è; il ripiego serve solo al caso
«array non vuoto ma corto», che è l'unico che oggi alza.

**D-3 — Il test 5 va anche in `guardrail_codice_errore_strutturato.sql`? → NON ORA.**
Il pgTAP in CI gira sulle PR verso `main` e sui push a `Tito-dev` che toccano
`db/`; il guardrail gira a ogni `ci-validate`. Portarci il controllo (come
controllo `(G)`) lo anticiperebbe. *Raccomandazione: no per ora* — sarebbe la
stessa regola scritta in due posti, e la prima cosa che diverge sono le
esclusioni. Da riconsiderare se il test 5 tornasse rosso dopo essere rientrato.

---

## 9. Come si rifà la misura

```bash
PGTAP_RUNNER=app scripts/testpgtap.sh script/test-catalogo-messaggi-errore-completo.sql
```

I test 4 e 5 stampano codice, lingua, funzione e — per il 5 — quanti valori
passa contro quanti ne servono. Non serve altro: lo scanner vive nel file, in
`pg_temp`, e non lascia niente nel database.

---

## 10. Richieste al backend

**BE-1 — `error_messages_fallback.py` conteneva già la frase giusta.**
Per `E_ARTICOLO_NON_COMPOSITO` il backend si era scritto
«L'articolo indicato non e' composito: non puo' avere una distinta base.» — cioè
qualcuno, trovandosi in mano un messaggio inservibile, se n'è fatto uno suo. Da
oggi quella frase è a catalogo (con accenti veri, `causa` e `soluzione`). Se il
fallback resta, resta come ripiego per DB irraggiungibile, non come **seconda
versione** del testo: vanno riallineati o il messaggio dipende da quale dei due
canali ha risposto.

**BE-2 — La stessa passata, lato Python.** Qui è stata misurata l'arità dei
punti di sollevamento **nel DB**. `ErrorManager.require(...)` e i `ServiceError`
sollevano gli stessi codici dal backend: se lì un messaggio con segnaposto viene
formattato con meno valori, il difetto è identico e questa passata non lo vede.
Il gemello BE del test 2 di quel file esiste già (analisi AST): è il posto dove
aggiungere il controllo.

**BE-3 — Per informazione, non è un'azione.** Se D-2 viene accolta, un errore
oggi `22023` diventerà `P0001` con il suo codice. È un **miglioramento** per il
backend (un caso in meno che cade nel ramo generico), ma cambia lo SQLSTATE
osservato: se da qualche parte c'è un test che si aspetta il generico, va rifatto.

---

## 11. File toccati

- `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv` — 2 righe
- `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql` — test 4/5 scritti, vecchio 4 → 6
- `db/pgtap/baseline-rossi.tsv` — registrato il rosso con la causa
- *(da fare, §7 — lotto successivo)* 8 changeSet in `20_code/`, da `20260818-47`
- *(da fare, §8 D-2 — dopo il lotto delle 8)* 1 changeSet su `script.fn_log_and_raise_error`
