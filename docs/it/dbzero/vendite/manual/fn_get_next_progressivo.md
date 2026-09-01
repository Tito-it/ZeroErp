## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_next_progressivo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
> • [vendite.fn_get_anno_registro](/dbzero/vendite/manual/fn_get_anno_registro)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_anno_registro](/dbzero/vendite/funzioni/fn_get_anno_registro)   
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
La funzione **`vendite.fn_get_next_progressivo`** restituisce il prossimo numero
di registro, con **lock della riga** progressivi per evitare doppioni.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_registro_id` | `vendite.registri_fatturazione.id%TYPE` | Registro fiscale. |
| `p_data` | `vendite.fatture.data%TYPE` | Data documento. |
| `p_competenza_mese` | `vendite.fatture.competenza_mese%TYPE` | Competenza del documento, per il **limite di emissione** (dal 2026-08-26). `NULL` = «non la so»: si ripiega sul mese di `p_data`. |
| `p_serie` | text | Serie **già risolta** dal chiamante. |
| `p_fattura_id` | `vendite.fatture.id%TYPE` | Solo per il **bersaglio** dell'errore (dal 2026-08-25). |

⚠️ **`p_competenza_mese` è obbligatorio e sta in TERZA posizione**, prima dei due
che hanno un default: in PostgreSQL i parametri con `DEFAULT` stanno in coda.
Chi aggiorna una chiamata posizionale scritta prima del 2026-08-26 deve
ricontarne gli argomenti — al terzo posto ora c'è una **data**, non la serie.

⚠️ **`p_serie` arriva già risolta.** Qui `NULL` vale la serie **vuota**, non il
`serie_default` del registro: a fare il `COALESCE(f.serie, r.serie_default, '')`
è `fn_assign_numero_fattura`. La primitiva di lettura
[`fn_get_pavimento_sequenza`](/dbzero/vendite/funzioni/fn_get_pavimento_sequenza)
si comporta all'**opposto**, ed è voluto: lì `NULL` significa «quella del
registro».

---

### Regola applicata

* ⭐ **L'anno del SECCHIO lo decide la politica del registro** (rev 2026-09-01):
  `reset_policy = 'ANNUALE'` → `vendite.fn_get_anno_registro(p_data)`;
  `'NESSUNA'` → `0`, cioè **un secchio solo** e numerazione continua fra gli anni.
  ⛔ Da non confondere con l'anno del **documento** (`fatture.anno`, `ddt.anno`, …),
  che è sempre quello solare e lo compone `vendite.fn_assegna_numero_documento`:
  sono due cose diverse che si chiamano uguale.
* ~~Mese fisso `0` (reset annuale).~~ 🔴 **Superata il 2026-09-01**: la colonna
  `mese` è stata tolta dalla chiave del contatore — stava lì e in nessun
  documento, quindi era una dimensione dormiente. Questa era l'unica funzione che
  la leggeva.
* `pg_advisory_xact_lock` su **registro/serie** per evitare interleaving.
* ⭐ **Il cancello di monotonia**, sotto il lock (vedi sotto).
* `SELECT ... FOR UPDATE` sulla riga progressivo.
* Se la riga non esiste, viene creata con `last_numero = 0`.
* `ultima_data` aggiornata con `GREATEST`: **non arretra mai**.

---

### Note operative

* La funzione deve essere chiamata **solo in emissione** (non in bozza).
* Evita **doppioni**, ma i buchi possono comparire in caso di rollback.

---

### ⭐ rev 2026-08-25 — il cancello di monotonia

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-8**).

> **Un numero non si consegna a un documento la cui data è anteriore all'ultima
> già numerata sullo stesso sezionale.**

Prima non lo guardava nessuno. `uq_fatture_numero` garantisce l'unicità del
numero e **null'altro**: sulle date non dice niente. Misurato sul registro 3 il
2026-08-25: **tre inversioni** su undici numeri — e con tre vie d'innesco (lotto
singolo, giro per competenza che ordinava per id di lotto, backstop del worker di
stampa che non ordina affatto) l'inversione non era un incidente, era il
comportamento atteso.

#### Perché qui, e non in `fn_assign_numero_fattura`

Due ragioni, entrambe necessarie:

1. **È l'unico punto non aggirabile.** Tutte e tre le vie che consumano un numero
   passano di qui.
2. **Un controllo letto *prima* del lock è soggetto a corsa.** Due transazioni
   leggono lo stesso massimo, passano entrambe, poi si serializzano sul contatore
   e producono proprio l'inversione che il cancello doveva impedire. Sotto il
   lock, lettura e incremento sono **lo stesso atto**.

#### 🔴 Il lock ha perso l'anno, ed è la parte che conta

La chiave dell'advisory lock era `registro | anno | serie`. Ora è
`registro | serie`.

Il cancello legge il massimo **attraverso gli anni**, e il `FOR UPDATE` blocca la
sola riga del proprio anno. Con l'anno nella chiave, due numerazioni con date in
anni diversi sullo stesso sezionale avrebbero preso **lock diversi**, letto lo
stesso massimo e passato entrambe: il cancello sarebbe stato aggirabile **proprio
nel caso che dichiara di coprire** — il documento retrodatato all'anno scorso.

> ⭐ **La regola, che vale oltre questa funzione:** *il perimetro del lock deve
> coincidere con quello del controllo che ci sta dentro.* Un lock più stretto di
> ciò che il controllo legge non serializza niente.

Costo: si serializzano fra loro due numerazioni dello stesso sezionale in anni
diversi, cioè qualche transazione a cavallo di Capodanno. È un **restringimento**,
non un cambio di semantica.

#### Da dove viene il pavimento

Da `registri_fatturazione_progressivi.ultima_data`, **non** da `vendite.fatture`.

⛔ Quella tabella ha la RLS e questa funzione è `SECURITY INVOKER`: un `max(data)`
letto lì sotto un perimetro emittente ristretto tornerebbe `NULL`, e un cancello
che legge `NULL` direbbe **«via libera» proprio quando non sa**. Il contatore non
ha RLS: la risposta è sempre completa, è `O(1)`, ed è su una riga che il cancello
ha già bloccato.

#### La chiave è `(registro, serie)`, non il solo registro

Il modello ammette **due serie sullo stesso registro**:
`tipi_doc_fiscale_registri` mappa `(tipo_doc, natura) → (registro, serie)` e la
sua `UNIQUE` lo consente apposta. Sul solo registro, due sequenze indipendenti si
bloccherebbero a vicenda.

#### L'errore

`E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO`, classe **`DATO_ERRATO`** — la data la
sceglie una persona, in un dialog, e può correggerla.

* nella **frase** va solo **la data dell'ultimo numerato**, in formato italiano:
  è l'unico dato che serve a scegliere quella giusta. Nessun id, nessun nome di
  colonna;
* `context.campo = 'data_documento'`, per accendere il campo nel dialog;
* **bersaglio** a due elementi — il documento da numerare (da `p_fattura_id`) e
  l'ultima numerata del sezionale, quest'ultima **solo se visibile** a chi opera.
  ⚠️ Si cerca **per data**, non per numero: in un registro con inversioni già
  scritte «l'ultimo per numero» porterebbe una data diversa da quella che la
  frase nomina, e il messaggio si contraddirebbe da solo.

⭐ Tutto questo gira **solo nel ramo d'errore**: sul percorso felice il cancello è
un `max()` su una tabella di due righe.

#### ✅ La stessa data è ammessa

`>=`, non `>`. È il caso **più comune** — due fatture emesse lo stesso giorno —
quindi un cancello scritto stretto bloccherebbe l'esercizio normale invece
dell'eccezione.

#### ⚠️ Cosa i pgTAP NON possono provare

Che il cancello stia **sotto** il lock. pgTAP è mono-sessione, il lock non si
contende, e spostando il controllo prima del lock
`db/pgtap/vendite/test-registri-progressivi.sql` resterebbe interamente **verde**.
La posizione si presidia in **review**. Ciò che quei test provano è il
*predicato*: quali date passano e quali no.


### ⭐ rev 2026-08-26 — il cancello guarda anche il LIMITE DI EMISSIONE

Brief: `brief-db-limite-emissione-e-data-verificata` (**DB-10**).

> **Un numero non si consegna nemmeno a un documento la cui data è troppo
> vecchia perché il documento sia ancora emettibile.**

I pavimenti diventano **due**, e il cancello non li compone più a mano: li chiede
a [`fn_get_pavimento_data_documento`](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento),
che torna il **pavimento effettivo** (il maggiore) e l'**origine** (quale dei due
ha vinto). Prima qui c'era un `max(ultima_data)` scritto a mano, cioè una delle
tre copie della stessa regola.

⚠️ La lettura resta **sotto il lock**: la metà di sequenza legge il contatore, ed
è proprio quella che va serializzata.

#### Due codici, e li sceglie `origine`

| origine | codice | rimedio |
|---|---|---|
| `SEQUENZA` | `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` | risalire alla fattura che porta quel numero — **bersaglio** a due elementi |
| `EMISSIONE` | `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE` | avvicinare la data a oggi — ⛔ **nessun secondo bersaglio**: dietro il limite non c'è nessun documento da aprire, e un pulsante verso il nulla è peggio di nessun pulsante |

A parità di data vince `SEQUENZA`, perché la sua frase può portare l'operatore su
un documento vero.

#### ⛔ La frase nomina il pavimento EFFETTIVO

Fino al 2026-08-25 il messaggio portava il pavimento di **sequenza**, perché era
l'unico. Con due pavimenti deve portare il **maggiore**: se nominasse quello di
sequenza mentre a mordere è il limite, direbbe all'operatore di scegliere una data
**che verrebbe rifiutata di nuovo**.

#### ⭐ La competenza arriva dalla RIGA, non dal lotto

`fn_assign_numero_fattura` **legge già** la riga della fattura per numerarla: la
competenza è una colonna in più in una `SELECT` che c'è già.

⛔ **Non si legge dal lotto**, e la ragione è la stessa per cui il pavimento di
sequenza si legge dal contatore: `vendite.fatturazione_lotti` ha la RLS e questa
funzione è `SECURITY INVOKER`. Un lotto fuori dal perimetro di chi opera si
leggerebbe come assente, la competenza uscirebbe `NULL` e il cancello direbbe
**«via libera» proprio quando non sa** — un presidio *fail-open* nel punto che
esiste apposta per non esserlo.

⚠️ **Il ripiego su `date_trunc('month', p_data)`** copre le fatture nate prima
del 2026-08-26, che hanno la colonna a `NULL`: è la risposta di allora, quindi
mai peggiore. ⛔ Il prezzo, dichiarato: col ripiego il cancello **non distingue**
un 31/07 che è davvero di luglio da uno che in realtà è di giugno. Chi la
competenza vera ce l'ha è la porta di dichiarazione
([`fn_imposta_data_documento_lotto`](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)),
dove il controllo resta **stretto** — due severità diverse, e la differenza è
scritta in entrambi i posti apposta.

---

{% include-markdown "signature-core.md" %}
