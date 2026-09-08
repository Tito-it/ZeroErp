# Brief DB — la coda che si ripete: sollevare il primo motivo in un posto solo

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-08.
>
> **In una riga:** **ventitré** punti del database sollevano il codice del
> **primo motivo** di una `fn_check_*`. Le righe non sono il problema: dentro ci
> stanno **tre convenzioni che, sbagliate, non fanno fallire niente**.
> ⚠️ **Ma solo dieci si estraggono**: gli altri tredici chiamano check che non
> emettono `valori`, quindi compongono la frase da sé e non sono la stessa coda
> (§2.2). Il perimetro del cantiere è **dieci**, il perimetro del presidio è
> **quello che si deriva**.
>
> **Origine.** Non da un difetto in campo: dalla domanda di Tid del 2026-09-08,
> durante il cantiere della chiave del contatore — *«queste funzioni ormai sono
> molto simili, possono essere unificate in una sola?»*. La risposta sulle due
> guard di `registri_fatturazione` è **no** (§3), ma la misura fatta per
> rispondere ha trovato la duplicazione vera, che sta **altrove e su più
> tabelle**. Perimetro suo, per decisione di Tid nella stessa conversazione.
>
> 🔴 **Riveduto il 2026-09-08, contro le funzioni vive.** La prima stesura era
> stata scritta leggendo dieci corpi; riletti tutti e ventitré, **§1, §2, §3 e
> §5 dicevano il falso** — e il §5 diceva l'opposto della verità proprio sulla
> riga che segnalava. Le correzioni sono nel corpo, ognuna col suo perché: un
> brief che si limita a cambiare la conclusione insegna la stessa cosa sbagliata
> a chi lo rilegge.
>
> ⛔ **Nessuna misura decide niente qui.** I conteggi sono **fatti datati** e
> servono a un uso solo: dire quanto è largo il perimetro. A decidere è la
> struttura.
>
> **Correlati:**
> [brief-db-registri-numerazione-chiave-del-contatore](../work-in-progress/brief-db-registri-numerazione-chiave-del-contatore.md) — il cantiere in cui la domanda è nata ·
> [linee-guida-sql §12.5](../../linee-guida-sql.md) — le azioni per riga, dove la regola «la madre CHIAMA la check» è scritta ·
> [linee-guida-sql §5](../../linee-guida-sql.md) — i canali di `fn_log_and_raise_error` (codice, campo, bersaglio, valori)

---

## 1. ⭐ Cosa si estrae davvero — non le righe, le convenzioni

La coda **canonica** è questa:

```sql
v_primo := v_motivi -> 0;
PERFORM script.fn_log_and_raise_error(
    'area', 'funzione', v_primo ->> 'codice',
    COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
        || jsonb_build_object('campo', 'nome_colonna'),
    NULL::uuid,
    VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));
```

⚠️ **«Canonica» e non «identica», ed è una correzione del 2026-09-08.** Questa
sezione diceva *«la coda è questa, identica in dieci punti»*. **Non lo è**:
questa forma esatta compare in **tre** dei dieci
(`trgfn_famiglie_documento_guard_struttura`,
`trgfn_registri_fatturazione_guard_forma_numero`,
`trgfn_registri_fatturazione_guard_serie_ammessa`). Gli altri sette compongono
il contesto in sei modi diversi, e due delle differenze non sono estetiche —
l'elenco sta nel §4, perché è **lì** che decide qualcosa: una firma che non le
sa esprimere non è un'estrazione, è una riscrittura di comportamento in
silenzio.

⛔ **Quattro righe risparmiate per sito non valgono un building block.** Il
motivo per farlo sono le **tre cose che ci stanno dentro e che sbagliano in
silenzio** — nessuna delle tre fa fallire qualcosa, tutte e tre producono un
messaggio o un log sbagliato:

| Cosa | Se si sbaglia | Chi se ne accorge |
| --- | --- | --- |
| **`-> 0`** — si solleva il **primo** motivo | il tooltip della maschera dice una cosa e l'errore un'altra: l'ordine dell'array **è il contratto** (§12.5.2) | nessuno, finché un utente non li legge entrambi |
| **il `tx_id`** — dipende dalla **fase e dal NOME** del trigger (§5) | 🔴 **niente, e questa riga è stata corretta il 2026-09-08**: `fn_log_error_only` ripiega sulla transazione di sessione quando riceve NULL. Resta una riga che *afferma* una cosa falsa, non una perdita | — |
| **lo spacchettamento del `VARIADIC`** | i `%s` del messaggio si riempiono da una lista che non è quella attesa — arità giusta, **frase falsa** | solo chi **legge la frase resa** |

⚠️ **La terza ha già morso, ma non dove questa sezione diceva.** Il 2026-09-01,
su `E_REGISTRO_SERIE_NON_AMMESSA`, a video usciva *«Registro X1»* dove `X1` era
la **serie**: due segnaposto, due valori, nessun cancello rosso. ⛔ **Quel
difetto non era nello spacchettamento: era nell'ORDINE dei `valori`**, che vive
dentro la `fn_check_*` — e le check il §8 dice di non toccarle.
⇒ **L'helper non difende da quel caso**, e va detto invece che lasciarlo
credere: l'unica difesa su quella riga è un `throws_like` sulla frase resa
(§6, P-0). Ciò che l'helper toglie di mezzo è il **gesto meccanico** — che il
`->` sia `0`, che il `tx_id` sia quello giusto, che l'array arrivi spacchettato
e non come scalare.
⚠️ La seconda ha un precedente registrato pure lei: **`fn_log_and_raise_error`
chiamata con cinque argomenti non risolve** — il `VARIADIC` va passato sempre,
anche vuoto.

⇒ **Un posto solo, con un test suo.** È la ragione dell'estrazione; le righe in
meno sono un effetto collaterale.

---

## 2. Il censimento — fatto datato, 2026-09-08 (riveduto lo stesso giorno)

🔴 **La prima stesura contava dieci punti. Sono ventitré**, e la differenza non
è di misura: è che il conteggio era stato fatto sulla **stringa** della coda
(`VARIADIC ARRAY(SELECT jsonb_array_elements_text`) invece che sul **fatto**
(«si solleva il codice del primo motivo di una check»). Cercare un letterale
dà per perimetro quel letterale — ed è esattamente il difetto che il presidio
del §7 rischiava di ereditare.

### 2.1 Forma A — la coda con `v_primo` (dieci punti, dieci funzioni)

| Funzione | Natura | `campo` | `motivi` | `tx_id` | Oggi |
| --- | --- | :---: | :---: | --- | :---: |
| `anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard` | trigger `_z90_` **AFTER** | ✅ | ⛔ | `NEW.tx_id` | ✅ |
| `anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito` | trigger `_z90_` **AFTER** | ✅ | ⛔ | `NEW.tx_id` | ✅ |
| `anagrafiche.trgfn_stiva_movimenti_guard_annullo` | trigger `_a10_` BEFORE | ⛔ | ✅ | `NEW.tx_id` | ✅ (§5) |
| `vendite.trgfn_famiglie_documento_guard_disattivazione` | trigger `_a10_` BEFORE | ⛔ | ⛔ | `NULL::uuid` | ✅ |
| `vendite.trgfn_famiglie_documento_guard_struttura` | trigger `_a10_` BEFORE | ✅ | ⛔ | `NULL::uuid` | ✅ |
| `vendite.trgfn_registri_fatturazione_guard_forma_numero` | trigger `_a10_` BEFORE | ✅ | ⛔ | `NULL::uuid` | ✅ |
| `vendite.trgfn_registri_fatturazione_guard_serie_ammessa` | trigger `_a10_` BEFORE | ✅ | ⛔ | `NULL::uuid` | ✅ |
| `anagrafiche.fn_annulla_movimento_titolo_iva` | madre | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `anagrafiche.fn_guard_ba_cambio_emittente` | madre | ⛔ | ⛔ | `NULL::uuid` | ✅ |
| `vendite.fn_annulla_accredito_riga_reso` | madre | ⛔ | ⛔ | `NULL::uuid` | ✅ |

### 2.2 Forma B — NON è lo stesso gesto (tredici punti, dodici funzioni)

🔴 **Questa sezione diceva «lo stesso gesto scritto inline». È falso**, e la
misura che lo smentisce è del 2026-09-08, fatta preparando H-4:

| | La `fn_check_*` chiamata emette `valori`? |
| --- | --- |
| le **otto** check della forma A | ✅ **8 su 8** |
| le **tredici** check della forma B | ⛔ **0 su 13** |

⇒ Non sono due scritture della stessa cosa: sono **due contratti diversi della
check**.

* **Forma A** — la check dice anche **cosa scrivere nella frase** (`valori`):
  il sito può delegare tutto, e l'helper è a casa sua;
* **Forma B** — la check dice **solo perché** si rifiuta. La frase la compone
  **il chiamante**, dai propri dati: `v_numero`, `p_gruppo_key`, `NEW.codice`,
  `v_riga.resi_riga_id`, `COALESCE(v_motivi -> 0 ->> 'dettaglio', '0')`.

⛔ **Riscriverli con l'helper romperebbe tredici messaggi.** L'helper prende i
valori dal motivo; lì non ce ne sono, quindi passerebbe un `VARIADIC` vuoto e le
frasi uscirebbero **coi `%s` grezzi a video** — provato dal test 7 di `P-1`.
Sarebbe la «frase falsa» del §1, causata dal cantiere che esiste per impedirla.
⛔ E l'unica scappatoia — un `p_valori` nell'helper — lo **svuoterebbe**: il
chiamante ricomporrebbe i valori a mano, cioè la terza convenzione tornerebbe a
essere sua. Un involucro attorno a niente.

⭐ **La frontiera vera, e non è come è scritta la coda:**

> **La check dice anche COSA scrivere nella frase, o solo PERCHÉ si rifiuta?**

È un asse di **modello**, non di stile — e spiega anche perché tutti e tredici
mettono `motivi` nel contesto: senza `valori`, quello è l'unico canale che porta
i motivi al backend.

⚠️ **Cosa resta vero della forma B**: condivide con la A le altre due
convenzioni — quale elemento si solleva (`-> 0`) e quale `tx_id` si passa. Ed è
lì che stanno i cinque difetti del §5.

`v_motivi -> 0 ->> 'codice'` senza la variabile d'appoggio. **Tutti in
`vendite`.**

| Funzione | Natura | `campo` | `motivi` | `tx_id` | Oggi |
| --- | --- | :---: | :---: | --- | :---: |
| `fn_annulla_lotto_da_draft` | madre | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `fn_cambia_stato_preventivo` | madre | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `fn_elimina_fattura_da_lotto` | madre | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `fn_escludi_documento_da_giro` | madre | ⛔ | ✅ + `bersaglio` | `NULL::uuid` | ✅ |
| `fn_riapri_riconsegna_reso` | madre | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `fn_riporta_attivita_da_emettere` | madre | ⛔ | ✅ + `bersaglio` | `NULL::uuid` | ✅ |
| `fn_riporta_lotto_a_draft` | madre | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `trgfn_doc_guard_chiusura_sorgente` | trigger `_a10_` BEFORE (su **3** tabelle) | ⛔ | ✅ | `NULL::uuid` | ✅ |
| `trgfn_commesse_guard_transizione` | trigger `_a10_` BEFORE | ⛔ | ✅ | `NEW.tx_id` | 🔴 §5 |
| `trgfn_ordini_guard_transizione` (2 rami) | trigger `_a10_` BEFORE | ⛔ | ✅ | `NEW.tx_id` | 🔴 §5 |
| `trgfn_preventivi_guard_annullamento` | trigger `_a10_` BEFORE | ⛔ | ✅ | `NEW.tx_id` | 🔴 §5 |
| `trgfn_preventivi_guard_transizione` | trigger `_a10_` BEFORE | ⛔ | ✅ | `NEW.tx_id` | 🔴 §5 |

⭐ **La forma B non è «un altro caso»: è la maggioranza, ed è quella che sbaglia.**
I cinque 🔴 del §5 stanno tutti lì, e il `'motivi'` nel contesto — che nella
forma A compare in **due** punti su dieci — nella B c'è in **tutti e tredici**.
Il conteggio delle due forme è **15 su 23**: chi decide la firma dell'helper
(§4) sta decidendo per quindici siti, non per due.

⚠️ **Si conta per PUNTO DI CHIAMATA, non per funzione**: **tredici** delle
ventidue sollevano in più rami (fino a sei volte), e quasi sempre solo **uno**
per funzione è la coda del primo motivo — l'eccezione è
`trgfn_ordini_guard_transizione`, che ne ha **due**. Gli altri rami sono rifiuti
con codice fisso, e **non entrano** in questo cantiere.

⚠️ **E il perimetro cresce da sé**: il cantiere della chiave del contatore ne ha
aggiunto uno il 2026-09-01 e ne stava aggiungendo un altro il 2026-09-08. Chi
scrive una `fn_check_*` copia la coda dalla guard accanto — è così che si arriva
a ventitré senza che nessuno abbia deciso niente.

---

## 3. ⛔ Cosa NON si unisce, ed è la domanda da cui si è partiti

Le due guard di `registri_fatturazione` **sembrano** gemelle e non lo sono:

| | `guard_serie_ammessa` | `guard_forma_numero` |
| --- | --- | --- |
| evento | `INSERT` + `UPDATE OF (serie_default, famiglia_documento)` | `UPDATE OF (prefisso, suffisso, lunghezza_numero, anno_nel_numero)` |
| `campo` nel contesto | `serie_default` | il campo della forma, **scelto a runtime** |
| domanda | «questa famiglia registra la serie?» | «questo sezionale ha già numerato?» |

⛔ **E il `campo` è uno per regola**: è il canale che accende l'input giusto nel
form. Un campo solo per due regole accende quello sbagliato — è la §12.5.4
(«un verbo, una colonna») letta sul lato che solleva.

⛔ **La clausola `UPDATE OF` risparmia risvegli, non protegge da niente.**
🔴 Questa sezione diceva che l'`UPDATE OF` è *«ciò che tiene il guard fuori dai
piedi del mirror CSV»*. **È falso, e la smentita è scritta dentro la funzione
che questa sezione esamina**:

> *«`UPDATE OF` scatta quando lo statement NOMINA la colonna, anche a valore
> invariato — e il mirror CSV dei registri riscrive `serie_default` a OGNI
> migrate. Senza questo confronto, ogni migrate fallirebbe.»*
> — `vendite.trgfn_registri_fatturazione_guard_serie_ammessa`

Il mirror `80_data/sql/vendite/registri_fatturazione.csv` scrive **tutte** le
colonne sorvegliate dai due guard (`serie_default`, `famiglia_documento`,
`prefisso`, `suffisso`, `lunghezza_numero`): entrambi si svegliano a ogni
migrate, e a tenerli fuori dai piedi è il **confronto di no-op**, che ciascuno
dei due ha già.
⇒ Cade anche il corollario *«due confronti di no-op invece di uno»*: i confronti
sono già due oggi, uno per funzione, e unendo le funzioni resterebbero due.

**Le due gambe che reggono davvero il «no»**, e bastano: gli **eventi sono
diversi** (una scatta anche in `INSERT`, l'altra solo in `UPDATE`), e il
**`campo` è uno per regola**. Unite, il trigger si sveglierebbe sull'unione
delle colonne e ogni regola dovrebbe ricontrollare da sé se la riguarda — più
codice, non meno.

⭐ **La lezione generale, che è il motivo per cui questo §3 sta qui**: *due
funzioni che finiscono uguali non sono due funzioni da unire — sono due funzioni
che chiamano la stessa cosa.* Si estrae la coda, non si fondono le teste.

⚠️ **E la lezione della correzione**, che vale oltre questo paragrafo: la
conclusione era giusta e l'argomento no. È il caso peggiore, non il migliore —
non c'è niente da correggere nel risultato, e intanto la ragione scritta insegna
una cosa falsa sul funzionamento di `UPDATE OF`.

---

## 4. La forma dell'helper

```sql
script.fn_raise_primo_motivo_se_presente(
    p_area          text,
    p_funzione      text,
    p_motivi        jsonb,
    p_campo         text  DEFAULT NULL,
    p_tx_id         uuid  DEFAULT NULL,
    p_context_extra jsonb DEFAULT '{}'::jsonb) RETURNS void
```

⚠️ **Il nome dice che può tacere, e non è pedanteria.** [linee-guida-sql §5](../../linee-guida-sql.md)
vieta esattamente questo: *«una volta `fn_check_*` che fa RAISE, una volta
`fn_guard_*` che torna boolean → diventa impossibile capire dal nome se la
funzione lancia o verifica soltanto»*. Un `fn_raise_*` che a volte non solleva
è quella ambiguità. Il comportamento è giusto (sotto); il nome deve portarlo.

* ⭐ **Tace su un array vuoto.** `[]` o `NULL` ⇒ non fa niente. Così il sito
  chiamante perde anche l'`IF`, e diventa una riga sola. ⛔ E non è fail-open:
  «nessun motivo» è esattamente la risposta che dice *passa*;
* ⛔ **Ma NON tace su un non-array, e la prima stesura sbagliava.** Un oggetto o
  uno scalare al posto dell'array è un **contratto rotto della check**, e deve
  restare rumoroso: `jsonb_array_length` gli alza 22023 da solo, come già
  succedeva nei ventitré siti. Una riga `jsonb_typeof(...) <> 'array'` in più —
  che c'era, messa «per igiene» — l'avrebbe reso **silenzioso**, cioè avrebbe
  scambiato un guasto per un *«passa»*: un rifiuto tolto senza far fallire
  niente, che è la classe di difetto per cui questo cantiere esiste.
  ⚠️ *Un guard non si allarga per igiene* — e il test 3 di `P-1` è rosso se
  qualcuno lo «ripulisce» di nuovo;
* **`p_campo` NULL ⇒ la chiave `campo` non entra nel contesto.** Su un errore
  `TECNICO` non c'è nessun campo da accendere, e promettere un input che non
  esiste è peggio del contrario ([api.md §ui_action](../api.md));
  🔴 questa riga si motivava anche con *«perché cinque dei dieci non la
  passano»* — un conteggio al posto di un argomento, in un brief che apre
  dichiarando il contrario. Tolto: la ragione strutturale accanto basta da sola;
* ⭐ **`'motivi'` lo mette SEMPRE l'helper**, da `p_motivi`. Quindici dei
  ventitré lo portano già, ed è la chiave che
  `fn_escludi_documento_da_giro` documenta così: *«l'elenco COMPLETO nel
  contesto: il backend può mostrarli tutti anche se la frase ne nomina uno»*.
  ⛔ Un helper che lo lascia cadere toglierebbe al BE una cosa che ha, senza che
  nessun test se ne accorga;
* ⛔ **L'ordine di fusione lo decide l'helper, e vince `p_campo`**:
  `p_context_extra || COALESCE(p_motivi->0->'dettaglio','{}') || {campo, motivi}`.
  Oggi due siti fondono al contrario (`campo` prima, quindi **vince
  `dettaglio`**) e otto nell'ordine opposto. È una divergenza che non fallisce
  mai e che si vede solo il giorno in cui un `dettaglio` porta una chiave
  `campo`: si chiude qui, dichiarandola;
* ⛔ **Normalizza `valori`, e solo quello.** `COALESCE` non basta:
  `v_primo->'valori'` su una chiave con `null` JSON torna `'null'::jsonb`, non
  SQL NULL, e `jsonb_array_elements_text` alza **22023 dentro il percorso
  d'errore** — cioè il rifiuto di dominio non viene mai sollevato. Serve
  `CASE WHEN jsonb_typeof(...) = 'array' THEN ... ELSE '[]'::jsonb END`;
* `SECURITY INVOKER`, `VOLATILE` (scrive nel log attraverso la madre);
* ⛔ **Non inventa niente sul motivo**: prende il primo elemento e lo passa. Se
  un giorno servisse sollevarne un altro, la regola da cambiare è **l'ordine
  dell'array nella check**, che è dove il contratto vive.

### 4.1 ⛔ `p_context_extra` va in firma dal PRIMO giorno

Non è una previsione: è ciò che i ventitré siti **oggi** mettono nel contesto e
che una firma a cinque parametri **non sa esprimere**.

| Cosa viaggia in più | Dove | Se l'helper non lo porta |
| --- | --- | --- |
| chiavi di dominio (`movimento_id`, `resi_riga_id`, `lotto_id`, `titolo_iva_id`, …) | quasi tutti | il log perde l'unico riferimento alla riga |
| `'reason'` | `fn_guard_ba_cambio_emittente`, `fn_annulla_accredito_riga_reso` | ⛔ è il **motivo macchina** che il FE legge sulle azioni di riga (§12.5.1) |
| `'bersaglio'` | `fn_escludi_documento_da_giro`, `fn_riporta_attivita_da_emettere` | ⛔ il canale `DATATYPE` si svuota: niente gesto *«apri il documento»* |
| `'dettaglio'` **annidato** (non fuso) | `fn_annulla_accredito_riga_reso` | il BE lo cerca dove non c'è |
| `'parametro'` | convenzione in 225 punti | ⚠️ è il **ripiego** del canale `COLUMN` in `fn_log_and_raise_error`: un contesto ricostruito da zero lo perde, e il campo smette di illuminarsi |

⚠️ **E si decide in H-1, non dopo.** `CREATE OR REPLACE` **non cambia la lista
dei parametri**: aggiungere `p_context_extra` più tardi vuol dire `DROP` +
ricreazione + i dieci siti da ripuntare, oppure un **overload** che è
esattamente la cosa da non lasciare in giro.

⚠️ **Cosa NON entra nell'helper**: l'`IF` di uscita anticipata del guard
(`RETURN NEW`), i confronti di no-op sui valori e la scelta di quale check
chiamare. Sono la **testa**, ed è diversa in ognuno dei ventitré.


### 4.2 ⛔ L'alternativa scartata — «una funzione sola», e perché no

> **Origine:** domanda di Tid, 2026-09-08, letto il §4: *«un letterale è il primo
> elemento di un array. Se tutti i messaggi passassero il codice come elemento di
> un array, ci sarebbe una funzione sola — a questo punto si potrebbe pensare
> altro?»*

⭐ **Sul modello ha ragione**, e va scritto prima delle obiezioni: un codice
letterale **è** il caso degenere di un array a un motivo — stessa informazione
(codice, valori, dettaglio). Con una forma sola non ci sarebbe niente da
scegliere, e *rendere impossibile* batte sempre *rendere rilevabile*.

**Il fatto che circoscrive il problema** (provato in transazione, 2026-09-08):

| Prova | Esito |
| --- | --- |
| un `jsonb` di motivi passato **alla primitiva** | `42883` — la funzione non esiste. ⛔ **non lega** |
| un **codice letterale** passato **all'helper** | `22P02` — sintassi non valida per json. ⛔ **esplode** |
| la **coda ricopiata a mano** (primitiva + `v -> 0 ->> 'codice'`) | `P0001`. ✅ **lega benissimo** |

⇒ **Sbagliare _funzione_ è già impossibile: i tipi non legano.** L'unico modo di
sbagliare è **non usarla**, e quello è silenzioso. È il buco che chiude il §7, e
non lo chiuderebbe nemmeno l'unificazione.

**Perché l'unificazione non si fa** — e la prima ragione non è quella che sembra:

1. ⚠️ **Non è il catalogo dei codici.** Verrebbe da dire «così i presidi perdono
   il letterale `'E_…'` sulla riga»: **falso**,
   `jsonb_build_object('codice','E_X')` il letterale ce l'ha ancora. Questa
   obiezione non decide;
2. ⛔ **Le due funzioni non rispondono alla stessa domanda.** La primitiva dice
   *«solleva QUESTO errore»* — chi chiama sa già cosa rifiuta. L'helper dice
   *«solleva il PRIMO di questi motivi»* — chi chiama **non sa quale**: lo decide
   l'ordine dell'array, che è il contratto della check. Il secondo ha dentro una
   **politica di scelta** (`-> 0`); su un array a un elemento è un no-op, ma la
   si insegnerebbe a **1200** punti dove non c'è niente da scegliere;
3. ⛔ **Il lettore ci perde.** Su un rifiuto a codice fisso, il codice **sulla
   riga** è ciò che chi legge il sorgente cerca. Avvolgerlo lo sposta due
   annidamenti più in là, e trasforma `VARIADIC v_numero, v_stato` — il modo
   naturale di scrivere «i pezzi della frase» — in un `jsonb_build_array`;
4. ⛔ **1200 riscritture per togliere una decisione che esiste su 23**, e ognuna
   può rompere una frase senza che nessun test se ne accorga (§6.1).

⭐ **La parte che vale, e va nel §7.3.** Il problema vero non è che le funzioni
siano due: è che i ventitré passano il codice come **valore**, e sono perciò
invisibili ai tre presidi del catalogo codici. «Rendili la stessa cosa» si
realizza **dal lato che guarda**, non da quello che scrive — una vista che impara
a leggere anche quella forma. Costo: **una vista**, invece di milleduecento
riscritture.

---

## 5. 🔴 La variante del `tx_id`, e la regola che la scioglie

🔴 **Questa sezione diceva che un `_a10_` con `NEW.tx_id` manda nel log un
errore «senza la transazione che l'ha prodotto». È FALSO**, e la smentita è
nella primitiva stessa:

```sql
-- script.fn_log_error_only
IF p_tx_id IS NULL THEN
    p_tx_id := dbops.fn_get_or_create_session_tx_id();
```

⇒ Passare `NULL::uuid` **non perde niente**: il canale di log risolve la
transazione da sé, dalla sessione. Fatto datato 2026-09-08: **0 righe su
126.860** in `dbops.error_log` hanno `tx_id` NULL.

⚠️ E la misura derivata dal catalogo lo conferma su scala: **54 guard
`BEFORE ROW` su 58**, in sei schemi, passano `NEW.tx_id` dove quel valore è
NULL. Non sono 54 difetti — è la **convenzione di fatto** del progetto, e non
costa niente perché la primitiva ripiega.

⇒ **La differenza fra `NEW.tx_id` e `NULL::uuid` in un guard `BEFORE` è
puramente dichiarativa.** Resta una riga che *sembra* portare la transazione e
non la porta; non è una perdita di dato. ⛔ E per questo **H-5 è ritirato**:
correggere i cinque punti incontrati per caso, lasciandone quarantanove
identici, sarebbe stato «rincorrere gli esistenti» nella forma più pura.

Quindici punti passano `NULL::uuid`, otto passano `NEW.tx_id`. Non è
disordine: la regola si deriva — ma su **due assi**, non su uno.

🔴 **Questa sezione diceva «`_a10_` ⇒ NULL, `_z90_` ⇒ `NEW.tx_id`», e con quella
regola marcava 🟠 l'unico sito in cui il codice è GIUSTO.** L'errore era
mettere la fase al posto del meccanismo: la fase e il meccanismo coincidono
quasi sempre, e «quasi» è il punto.

| Asse | Perché | `tx_id` |
| --- | --- | --- |
| **`AFTER`** | tutti i `BEFORE` sono già passati, `trgfn_tx_id_managed` compreso. L'ordine alfabetico **non c'entra niente** | ⇒ `NEW.tx_id` **c'è**, e passarlo è giusto |
| **`BEFORE`** | i `BEFORE` di riga girano in ordine **lessicografico sul NOME INTERO del trigger**, confrontato contro `trg_<tabella>_gen_tx_id_ins_upd` | ⇒ dipende dal nome, si legge caso per caso |

✅ I due `_z90_` di `anagrafiche` sono **AFTER**: fanno la cosa giusta, e per la
prima delle due ragioni.

⭐ **Il caso che smentisce la regola scritta come «`a10` < `gen`»** —
`trgfn_stiva_movimenti_guard_annullo`, che la prima stesura marcava 🟠:

```
trg_soggetti_titoli_iva_movimenti_gen_tx_id_ins_upd   BEFORE INSERT   ← 'so' < 'st'
trg_stiva_movimenti_a10_guard_annullo_ins             BEFORE INSERT
```

Il guard **abbrevia** il nome della tabella (`stiva_` per
`soggetti_titoli_iva_`) e il confronto avviene sul nome intero: `gen_tx_id`
scatta **prima**. E `dbops.trgfn_tx_id_managed` valorizza sempre — sessione, id
registrato, o la sentinella `script.uuid_nil()`. ⇒ Lì `NEW.tx_id` **c'è**, e la
riga che lo passa è corretta.
⛔ **«Sanarla» con `NULL::uuid` cancellerebbe dal log la transazione che
l'errore ha davvero** — cioè il difetto n. 2 del §1, introdotto dalla bonifica
che doveva chiuderlo.

🔴 **I cinque casi veri stanno nella forma B**, ed erano fuori dal censimento
della prima stesura. Tutti `_a10_` **BEFORE**, tutti con `'a10' < 'gen'` sul
nome intero, tutti passano `NEW.tx_id` che lì è **NULL**:

| Punto | Trigger | Contro |
| --- | --- | --- |
| `trgfn_commesse_guard_transizione` | `trg_commesse_a10_guard_transizione_upd` | `trg_commesse_gen_tx_id_ins_upd` |
| `trgfn_ordini_guard_transizione` (ramo 1) | `trg_ordini_a10_guard_transizione_upd` | `trg_ordini_gen_tx_id_ins_upd` |
| `trgfn_ordini_guard_transizione` (ramo 2) | idem | idem |
| `trgfn_preventivi_guard_annullamento` | `trg_preventivi_a10_guard_annullamento_upd` | `trg_preventivi_gen_tx_id_ins_upd` |
| `trgfn_preventivi_guard_transizione` | `trg_preventivi_a10_guard_transizione_upd` | idem |

Non è un difetto di comportamento — il log riceve NULL in entrambi i casi — ma
sono **cinque righe che affermano una cosa falsa**: sembrano portare la
transazione e non la portano. Il giorno che uno di quei guard passasse a
`_z90_`/`AFTER`, o che qualcuno copiasse la riga in una madre, la differenza
diventerebbe vera.

⭐ **La regola da scrivere nelle linee guida, e non è «a10 contro gen»**:
*un guard `BEFORE` che abbrevia il nome della tabella si sposta nell'ordine di
esecuzione.* Il prefisso di fase è una convenzione di lettura; a decidere è la
stringa intera.

---

## 6. Il piano

| Passo | Cosa | Dove |
| --- | --- | --- |
| **P-0** | ⭐ **La prova di equivalenza della CODA, sito per sito**: a parità di `v_motivi` sintetico, la coda vecchia e la chiamata nuova devono produrre gli **stessi** quattro canali (frase resa, `CONSTRAINT`, `COLUMN`, `DATATYPE`). ⭐ Non serve nessuna fixture — la coda non tocca tabelle — quindi gira **prima** di applicare qualsiasi cosa, e le differenze VOLUTE (§4.1) si vedono invece di passare in silenzio | banco in transazione |
| **H-1** | `script.fn_raise_primo_motivo_se_presente`, firma completa del §4.1 | `20_code/script` |
| **H-2** | I sette **trigger** della forma A riscritti per chiamarla — uno per changeSet | `20_code/<schema>` |
| **H-3** | Le tre **madri** della forma A, stessa forma | `20_code/<schema>` |
| **H-4** | ⛔ I tredici punti della forma B **NON si riscrivono con l'helper** — §2.2. Approvato il 2026-09-08 «tutti insieme», **ritirato lo stesso giorno** quando la misura ha mostrato che le loro check non emettono `valori`. Resta aperto un cantiere **suo**: far emettere `valori` a quelle tredici check e poi riscrivere i siti — ⚠️ ma quello cambia tredici frasi rese e tocca le check, che il §8 dichiara intoccabili | *(non in questo cantiere)* |
| **H-5** | ⛔ **RITIRATO il 2026-09-08.** Non è un difetto: `fn_log_error_only` ripiega sulla transazione di sessione (§5). E il perimetro vero sarebbe **54 guard in sei schemi**, non cinque | — |
| **D-1** | ⭐ **Il discriminante e la regola scritti dove si leggono**: `.codex/AGENTS.md` (letto a inizio sessione), `linee-guida-sql §5` e la guida [Messaggi di Errore e Generazione Log](../../guide/Messaggi-di-Errore-e-Generazione-Log.md) — ✅ decisione di Tid 2026-09-08: **a fine sviluppo**, quando la forma è ferma | doc |
| **P-1** | Il pgTAP dell'helper: primo motivo, array vuoto, `valori` assente / `null` JSON / con più valori, `campo` assente, ordine di fusione | `db/pgtap/script` |
| **P-2** | ⭐ Il presidio che tiene chiuso il rubinetto (§7) | `db/pgtap/script` + `ci-validate` |

### 6.0 ⭐ Il discriminante — una domanda sola, e si vede nella riga che si scrive

> **Il codice che sollevo lo sto LEGGENDO da un array di motivi, o lo sto
> SCRIVENDO come letterale?**

| Quello che scrivi | Cosa chiami | Punti |
| --- | --- | ---: |
| `'E_QUALCOSA'` — un letterale | `script.fn_log_and_raise_error` | **1200** |
| `v_motivi -> 0 ->> 'codice'` | `script.fn_raise_primo_motivo_se_presente` | **23** |

Non c'è niente da valutare: o il codice è nel sorgente, o lo dà la check. ⭐ Ed è
proprio perché il discriminante è **greppabile** che il rubinetto del §7 può
esistere.

⚠️ **Perché è un passo del piano e non una riga di questo brief** (D-1): la
regola che nessuno legge non esiste. Il precedente è misurato e sta in
`AGENTS.md`: la regola di `<ListaConfigurabile>` non stava dove si legge, e i
file con `DataTable` grezza sono **risaliti da 48 a 57**.

⚠️ **Uno per changeSet e non un giro solo.** Sono funzioni vive su **cinque**
tabelle per H-2/H-3, **dieci** col perimetro esteso di H-4: un changeSet unico
che le riscrive tutte è un rosso che non dice quale.
⛔ E il corpo di ognuna si prende dalla **funzione viva**, non dagli YAML.

### 6.1 ⚠️ «Rilanciare i pgTAP della tabella» non è una rete, e serve saperlo prima

I test esistono per tutti e dieci, ma **non si trovano cercando il nome della
funzione** — nominano il trigger o il codice errore. La mappa, per non
cercarla due volte:

| Sito | pgTAP |
| --- | --- |
| `…_ambiti_guard` · `…_guard_ambito` | `anagrafiche/test-soggetti-titoli-iva.sql` (test 9-12) |
| `trgfn_stiva_movimenti_guard_annullo` · `fn_annulla_movimento_titolo_iva` | `anagrafiche/test-stiva-movimenti-annullo-v1.sql` |
| `famiglie_documento` ×2 | `vendite/test-famiglie-documento-crud-v1.sql` |
| `…_guard_forma_numero` | `vendite/test-registro-forma-numero-immutabile-v1.sql` |
| `…_guard_serie_ammessa` | `vendite/test-chiave-contatore-assi-dichiarati-v1.sql` (test 7-8) |
| `fn_guard_ba_cambio_emittente` | `anagrafiche/test-ba-cambio-emittente-storia-v1.sql` · `…-storia-solo-numerati-v1.sql` |
| `fn_annulla_accredito_riga_reso` | `vendite/test-annulla-accredito-riga-reso-v1.sql` (+4) |

⛔ **Ma quei test asseriscono lo SQLSTATE `P0001`, non il codice** — che dal
2026-08-05 viaggia nel canale `CONSTRAINT` — né la frase. Se l'helper
sollevasse `-> 1`, o perdesse un `%s`, o cambiasse il `campo`, **restano tutti
verdi**. Rilanciarli prova che il guard rifiuta ancora, non che rifiuta
**dicendo la stessa cosa** — ed è esattamente ciò che il cantiere si propone di
non rompere.
⇒ È il motivo per cui **P-0 viene prima di H-1** e non dopo: senza, H-2/H-3 è
la riscrittura non presidiata di dieci funzioni vive.

---

## 7. ⭐ I presidi — e il rubinetto conta più della bonifica

1. **L'helper fa quel che dice**: il pgTAP di `P-1`, coi casi limite.
2. ⭐⭐ **Il rubinetto, e si scrive sul FATTO, non sulla stringa.** Un presidio
   che conta «la coda copiata» ha per perimetro quel letterale: chi domani
   scrive la forma B **passa** — ed è la forma che oggi è maggioranza.
   ⇒ Si conta la **riga di `prosrc` che chiama `fn_log_and_raise_error` e
   contiene `-> 0`**, e si pretende zero — ⛔ **ma solo fra i siti la cui
   `fn_check_*` emette `valori`**, che sono quelli dove l'helper può stare
   (§2.2). Sugli altri il `-> 0` è **legittimo**, e pretendere zero anche lì
   sarebbe un cancello che boccia il caso giusto: dopo due blocchi sbagliati
   qualcuno lo spegne.
   ⭐ Il perimetro non si scrive a elenco: si **deriva**, chiedendo al `prosrc`
   della check se nomina `valori`. Così una check che domani li aggiunge fa
   entrare il suo sito nel perimetro **da sola**.
   ⚠️ A soglia decrescente finché H-2/H-3 non sono finiti: **può solo calare**,
   come il debito dei `throws_ok` senza SQLSTATE.
   ⚠️ E va montato **anche come cancello statico in `ci-validate`**, non solo
   come pgTAP: la suite pgTAP non gira sulle PR verso `Tito-dev`, che è il ramo
   dove un changeSet arriva per primo.
3. ⭐ **L'occasione da non perdere.** Tutti e ventitré passano il codice come
   **valore jsonb**, quindi sono **invisibili** a
   `dbops.vw_codici_errore_forme_condizione` — che cerca un letterale `'E_…'`
   sulla riga della chiamata — e quindi al rubinetto degli accumulatori B-7.
   Ogni sito nuovo di questa famiglia sottrae un pezzo di stato al presidio.
   Centralizzando su un nome solo, il presidio può risalire dalla chiamata alla
   `fn_check_*` e ai codici che quella nomina: la famiglia passa da **invisibile**
   a **dichiarata**.
   ⭐ **È qui che atterra l'alternativa scartata del §4.2**: «rendere tutti i
   codici la stessa cosa» è giusto come obiettivo e sbagliato come cantiere — si
   fa dal lato che **guarda** (una vista) invece che dal lato che **scrive**
   (milleduecento riscritture).

### 7.1 🔴 Il presidio era verde per costruzione, e l'ha detto una mutazione

La prima stesura di `P-2` cercava il marcatore **`-> 0 ->> 'codice'`**. Sembra
giusto, ed è quello con cui è stato fatto il censimento del §2.2. Ma prende
**solo la forma scritta inline**: i dieci siti della forma A usano una variabile
d'appoggio —

```sql
v_primo := v_motivi -> 0;        -- riga a sé
...  v_primo ->> 'codice'  ...   -- dentro la chiamata
```

⇒ **Proprio i dieci siti appena bonificati non erano presidiabili**, e il
rubinetto sarebbe partito verde e sarebbe rimasto verde per sempre.

⭐ **L'ha trovato una prova per mutazione**, non una rilettura: rimessa in
transazione la coda vecchia su `trgfn_registri_fatturazione_guard_serie_ammessa`,
il conteggio *non si è mosso*. A mordere era solo l'altro test, quello che conta
le funzioni che chiamano l'helper.

⇒ Il marcatore vero è **`->> 'codice'`**, cioè l'invariante *«il codice non è un
letterale, viene da un motivo»* — lo stesso fatto che rende questi siti
invisibili al rubinetto degli accumulatori (§7.3). ⚠️ E il test 7 del presidio è
una **canarina**: verifica che il marcatore riconosca ancora la forma usata
dall'helper stesso, così un restringimento futuro diventa rosso invece di
rendere il cancello muto.

⭐ **La regola generale, e vale oltre questo file**: *un cancello che non si è
visto diventare ROSSO non è un cancello.* Il verde iniziale non prova niente,
perché può venire dal fatto che non guarda dove deve.

⛔ **Cosa NON si prova con un test**: che il messaggio renda bene. Quello si
guarda **leggendo la frase resa**, ed è la ragione per cui questo cantiere
esiste — un cancello sull'arità non lo vedrebbe.

---

## 8. ⛔ Cosa non si tocca

* **Le teste delle ventidue funzioni**: quale check chiamare, su quali colonne,
  con quale no-op. Restano dove sono, ed è il §3.
  🟠 **Un'eccezione, dichiarata**: in
  `vendite.trgfn_registri_fatturazione_guard_forma_numero` il confronto di no-op
  guarda **quattro** colonne (`anno_nel_numero` aggiunta il 2026-09-08) ma il
  `CASE` che sceglie `v_campo` ne ha **tre** — cambiando solo
  `anno_nel_numero`, il form accende `lunghezza_numero`. È la stessa classe di
  difetto per cui esiste questo cantiere («un messaggio sbagliato, nessun
  cancello rosso»), sta in una funzione che H-2 riscrive comunque, e si ripara
  **in quel changeSet**. Lasciarlo per rispetto della regola sarebbe rispettare
  la lettera contro lo scopo.
* **`script.fn_log_and_raise_error`**: la firma non cambia. L'helper la
  **chiama**, non la sostituisce.
  ⚠️ Ma il nome **sparisce dai dieci corpi**, e va detto: dopo H-2 chi cerca
  `fn_log_and_raise_error` su `vendite.trgfn_registri_*` non trova niente, e
  l'indagine ha un salto in più. È il costo ordinario di un'estrazione — si
  paga, non si nega.
* **L'ordine dell'array dei motivi**: è il contratto della `fn_check_*`, e si
  cambia lì. ⛔ Ed è per questo che l'incidente del 2026-09-01 **non** è coperto
  dall'helper (§1).
* **Le `fn_check_*`**: hanno predicati diversi, non c'è niente da unire.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.

---

## 9. Stato dell'opera — 2026-09-08

### 9.1 Fatto e applicato

| changeSet | Cosa |
| --- | --- |
| `20260908-17` | `script.fn_raise_primo_motivo_se_presente` |
| `20260908-21..27` | H-2 — i sette **trigger** della forma A |
| `20260908-28..30` | H-3 — le tre **madri** della forma A |

**Verifiche** (tutte sul database, non a lettura):

* SQL **estratto dagli YAML** — `changes` **e** `rollback` — provato in
  transazione: pulito;
* `P-0`, equivalenza dei canali coda-vecchia / chiamata-nuova su 10 siti × 5
  motivi sintetici: **35 identici su 50**, le 15 differenze classificate una per
  una (§9.2);
* i **dodici pgTAP** dei siti toccati: verdi;
* `P-1` (pgTAP dell'helper, plan 15): verde;
* `P-2` (il rubinetto, plan 7): verde **e provato per mutazione** (§7.1).

### 9.2 ⭐ I due difetti VIVI trovati dalle prove, e riparati

1. ⛔ **Un `dettaglio` non-oggetto trasformava il contesto in un ARRAY.** In
   jsonb, `oggetto || scalare` non è un oggetto: è un array. I cinque siti che
   fondevano `COALESCE(v_primo -> 'dettaglio', '{}')` producevano, su un motivo
   con `dettaglio` scalare, un contesto **array** — e `context->>'campo'` su un
   array vale NULL. ⇒ **il campo da accendere spariva in silenzio**, e il carico
   del log era malformato.
   ⚠️ Non è teorico: `script.fn_check_accredito_annullabile` emette davvero un
   `dettaglio` scalare (l'id di riga, nudo).
   ⇒ L'helper lo ripara per costruzione: oggetto ⇒ fuso, non-oggetto ⇒
   **conservato sotto la sua chiave**, contesto sempre un oggetto.
2. ⛔ **Il `CASE` di `guard_forma_numero` aveva tre rami e il no-op quattro
   colonne** (`anno_nel_numero`, entrata il 2026-09-08): cambiando solo quella,
   il form accendeva `lunghezza_numero`. Riparato in `20260908-26`, ed è
   l'eccezione dichiarata al §8.

### 9.3 ⚠️ Le tre misure sbagliate al primo colpo

Vale la pena scriverle, perché tutte e tre sembravano ragionevoli e sono state
trovate solo perché il **risultato** sembrava strano:

| La misura | Il difetto |
| --- | --- |
| «quanti punti restano» contato **per riga** | la chiamata è su più righe: dava **0** su 13 |
| il marcatore `-> 0` | prende `fn_cleanup_fatture_by_ids`, che solleva un codice **letterale**: falso positivo |
| la CTE che cerca il trigger `gen_tx_id` | escludeva `trgfn_tx_id_managed` **anche** dal termine di paragone: nessun risultato |

⭐ *Anche la misura è un programma, e può avere il suo difetto* — e nessuna delle
tre sarebbe stata vista rileggendo la query.

### 9.4 Cosa resta

* ⛔ **I tredici della forma B**: non si riscrivono con l'helper (§2.2). Il
  cantiere che li chiuderebbe è **far emettere `valori` alle loro check**, e
  cambia tredici frasi rese: perimetro suo, e tocca le check che il §8 dichiara
  intoccabili;
* il debito è **dichiarato e presidiato**: soglia 13 nel test 4 di `P-2`, e può
  solo calare;
* ✅ **D-1 fatto**: il discriminante è in `.codex/AGENTS.md`, in
  `linee-guida-sql §5` e nella guida
  [Messaggi di Errore e Generazione Log](../../guide/Messaggi-di-Errore-e-Generazione-Log.md).

### 9.5 ⭐ I due residui, e dove sono andati

Chiuso questo, restano due cose **misurate** che questo cantiere non poteva
prendere. Non sono un elenco di buone intenzioni: hanno i loro numeri, e sono
la stessa cosa vista da due lati — *i motivi portano informazione che si ferma
dentro la check e non arriva né ai presidi né alla frase.*

| | Misura del 2026-09-08 |
| --- | --- |
| codici nominati **solo** dentro una `fn_check_*`, invisibili al rubinetto degli accumulatori | **35** (tutti a catalogo: il cancello del terzo lato non perde niente) |
| check della forma B i cui codici hanno un **numero di segnaposto diverso**, mentre il chiamante passa valori in numero fisso | **6 su 13** |

⇒ Raccolti in [brief-db-i-motivi-si-fermano-dentro-la-check](../work-in-progress/brief-db-i-motivi-si-fermano-dentro-la-check.md).

⚠️ **E vanno insieme**, non separati: far emettere `valori` alle tredici check
chiude il secondo **e** rende i loro siti estraibili con l'helper — cioè l'H-4
che qui è stato ritirato.

---

## 10. ✅ Chiuso il 2026-09-08

Tutto ciò che il §6 elencava è **fatto** o **ritirato con la ragione scritta**.
Il presidio che tiene il rubinetto vive in
`db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` e la regola che evita di
riaprirlo sta in `.codex/AGENTS.md`, in `linee-guida-sql §5` e nella guida dei
messaggi — cioè **dove si legge**, che era il punto di D-1.
