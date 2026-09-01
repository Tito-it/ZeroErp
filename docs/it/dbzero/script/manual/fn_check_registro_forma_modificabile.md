## 📘 Documentazione Concettuale – Funzione `script.fn_check_registro_forma_modificabile`

> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [vendite.trgfn_registri_fatturazione_guard_forma_numero](/dbzero/vendite/funzioni/trgfn_registri_fatturazione_guard_forma_numero) — il guard, che la **chiama** e solleva il primo motivo
> • la maschera del registro (CRUD in scrittura) — che tiene i tre campi **in sola lettura** e dice perché
>
> **Sorgente:**
>
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)
>
> **Gemelle:**
>
> • [script.fn_check_registro_disattivabile](/dbzero/script/funzioni/fn_check_registro_disattivabile) — l'altro divieto sullo stesso registro
> • [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva)

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — funzione nata il 2026-09-01)*

**Sorgente unica dei motivi per cui la forma del numero di un sezionale non si
può cambiare.** Ritorna `[]` se la si può cambiare, altrimenti l'array
**ordinato** dei motivi: `[{codice, reason, reason_key, dettaglio, valori}, …]`.

«Forma del numero» sono tre colonne di `vendite.registri_fatturazione`:
`prefisso`, `suffisso`, `lunghezza_numero`.

---

### ⛔ Il difetto che questa funzione esiste per impedire

Fino al 2026-09-01 quelle tre colonne **non erano presidiate da niente**. Un
aggiornamento su un registro che aveva già numerato passava, e il contatore in
`registri_fatturazione_progressivi` **proseguiva**.

Ne discendeva che il documento successivo usciva con una **forma nuova** e un
**numero che continuava la serie vecchia**. Sullo stesso sezionale, nello stesso
anno, convivevano due forme — e **nessun vincolo se ne accorgeva**, perché la
coppia *(forma, numero)* non è vincolata da nessuna parte.

⭐ È la stessa specie di difetto che il cantiere del prefisso aveva appena
riparato, presa dal verso opposto: là la forma restava identica mentre il
contatore ripartiva da 1.

⚠️ **E il rischio è nato proprio spostando il prefisso.** Prima viveva in
`config.sistema_codici`, che ha un pannello di amministrazione — ma lì
cambiarlo **non otteneva niente**, perché nessuno lo leggeva più. Ora si legge,
quindi cambiarlo funziona: la cosa che prima era inerte è diventata efficace, e
con l'efficacia è arrivato il danno possibile.

---

### ⭐ Il predicato: «ha consegnato un numero», non «ha una riga»

`vendite.fn_get_next_progressivo` inserisce la riga di contatore a
`last_numero = 0` e **nella stessa chiamata** la porta a `≥ 1`. Una riga ferma a
`0` significa quindi che da quel contenitore **non è mai uscito un numero**.

⇒ Il predicato è `esiste un progressivo con last_numero > 0`.

⚠️ **È di proposito più stretto di quello della disattivazione.**
`fn_check_registro_disattivabile` (motivo `HA_PROGRESSIVI`) guarda `attivo` a
prescindere dal contatore: lì si protegge il contatore *in quanto tale*, qui il
danno comincia col **primo numero consegnato**. Sono due divieti imparentati,
non lo stesso divieto — e chi li confonde finisce per unificarli.

---

### ⛔ `serie_default` non è coperta, e sono due ragioni indipendenti

**1. Sul modello.** `serie` entra nella **chiave del contatore**
(`uq_regprog_key`, che dal 2026-09-01 è `registro_id, anno, serie`). Cambiare `serie_default`
non fa proseguire un contatore sotto una forma nuova: apre un **contenitore
nuovo** che riparte da 1, sotto una serie che distingue i documenti da quelli di
prima. È il modo **legittimo** di aprire una serie nuova.

> 🔴 **Aggiornamento 2026-09-01, e cambia la seconda ragione.** Quando questa
> pagina è stata scritta il divieto su `serie_default` non esisteva. Ora esiste,
> **condizionato**: un registro non può portare una serie se la sua famiglia non
> dichiara `colonna_serie`. ⇒ La prima ragione qui sopra **resta vera** — la
> serie apre un contenitore nuovo, e dove il documento la registra è legittimo —
> mentre la seconda, qui sotto, era corretta per un divieto **secco** e non per
> uno condizionato: il mirror CSV tocca solo le fatture, che sono la famiglia
> dove la serie è ammessa. Vedi
> [`script.fn_check_registro_serie_ammessa`](/dbzero/script/funzioni/fn_check_registro_serie_ammessa).

**2. Strutturale, e da sola chiude la questione.** Il file
`80_data/sql/vendite/registri_fatturazione.csv` è un **mirror vivo** e fra le
sue colonne c'è `serie_default`. Un `BEFORE UPDATE OF serie_default` scatta
**anche quando il valore non cambia** — è l'aggiornamento a nominare la colonna
— quindi metterla nel divieto **farebbe fallire ogni migrazione**.

⭐ Lo stesso file dice cosa rende il divieto possibile: `prefisso`, `suffisso` e
`lunghezza_numero` **non sono fra le sue colonne**.

⚠️ **Residuo dichiarato.** Il commento della tabella dice che cambiare
`serie_default` su un registro vivo *«sposta il sezionale»*: resta vero, e resta
**senza presidio**. È un'altra decisione, e chi la prenderà dovrà fare i conti
col mirror qui sopra.

---

### ⭐ Perché il guard la CHIAMA invece di riscriverla

È la regola delle [linee guida SQL §12.5.2](/linee-guida-sql): la madre non
riscrive il predicato, lo **chiama**, e solleva il codice del primo motivo.

⭐ **Qui si poteva, e sulla disattivazione no.** Là a rifiutare è
`dbops.trgfn_prevent_deactivate_if_children`, un trigger **generico** guidato
dai propri argomenti e condiviso da un centinaio di tabelle: farlo chiamare una
verifica specifica dei registri ne romperebbe la genericità per un caso solo.
Il guard della forma invece è **nostro**.

⇒ Il presidio da scrivere non è «il messaggio e il rifiuto coincidono» — che
proverebbe solo l'oggi — ma **«il guard non contiene più il predicato»**, che è
una proprietà strutturale e non scade. È il test 8 del pgTAP.

---

### 📤 Cosa torna

| Chiave | Contenuto |
| --- | --- |
| `codice` | `E_REGISTRO_FORMA_NUMERO_IMMUTABILE` — a catalogo, classe `CONFLITTO_STATO` |
| `reason` | `HA_NUMERATO` — motivo macchina. ⛔ Senza prefisso `E_`, riservato ai codici a catalogo |
| `reason_key` | `amministrazione.registri_fatturazione.forma_blocco.ha_numerato` |
| `dettaglio` | `registro_id`, `codice`, `contatori`, `ultimo_numero` — la diagnosi, per chi può rimediare |
| `valori` | i due argomenti del messaggio: il **codice del sezionale** e l'**ultimo numero consegnato** |

---

### ⚠️ Note operative

* **`SECURITY INVOKER`, ed è motivato**: si leggono solo
  `registri_fatturazione` e `registri_fatturazione_progressivi`, e **nessuna
  delle due ha la RLS** (verificato il 2026-09-01). La gemella
  `fn_check_registro_disattivabile` è `SECURITY DEFINER` perché legge
  `vendite.fatture`, che ce l'ha. Un privilegio in più senza un caso che lo
  chieda non si prende.
* **Registro inesistente**: si **solleva** `E_VENDITE_CHIAMATA_NON_VALIDA`
  invece di rispondere `[]` — «la forma si può cambiare» su una riga che non
  esiste è una frase senza senso.
* **La chiave di traduzione è un debito verso il frontend**: va nei file di
  lingua `it`/`en` nello stesso giro del lavoro sulla maschera, o
  `scripts/check_i18n_keys.py` fallisce.

---

### 🚪 La via d'uscita, e perché il messaggio non ne promette una

Sulla famiglia `FATTURA` una strada c'è: il modello ammette **più registri** per
emittente, quindi se ne apre uno nuovo con la forma voluta.

⛔ **Sulle altre quattro famiglie no**: l'indice parziale
`uq_registri_fatturazione_famiglia_emittente_utility` ne ammette **uno solo**
per emittente e utility, e disattivare quello che c'è è a sua volta bloccato.

⇒ Il messaggio dice che non si può, e perché. **Non promette un rimedio che per
quattro famiglie su cinque non esiste.** Una via d'uscita vera — un verbo di
dominio «cambia forma e apri una serie nuova» — non esiste ancora, e inventarla
dentro un guard sarebbe inventarla di nascosto.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 8.*
