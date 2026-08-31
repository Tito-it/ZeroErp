## 📘 Documentazione Concettuale – Tabella `vendite.registri_fatturazione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
`vendite.registri_fatturazione` definisce i **sezionali di numerazione**: serie,
regole di reset, politica della data e collegamento all'emittente fiscale. Ogni
documento numerato si aggancia a un registro, che ne governa numerazione e
perimetro.

⛔ **Il nome dice meno di quello che la tabella fa, ed è un debito dichiarato:**
dal 31 agosto 2026 qui non vivono più solo le fatture. Vedi la sezione in fondo.

---

### Campi chiave (semantica)

* **Identita`**: `id`, `uid`, `codice`.
* **Emittente**: `emittente_soggetto_ruolo_id` (ruolo fiscale che emette).
* **Utility**: `utility_id` (opzionale, per registri specifici di utility).
* **Numerazione**: `serie_default`, `reset_policy` (es. ANNUALE).
* **Stato**: `attivo`.
* **Governance**: `meta`, `storicizza`, `tx_id`, audit.

---

### Relazioni principali

* `vendite.fatture.registro_id` → determina la numerazione.
* `vendite.registri_fatturazione_progressivi` mantiene i contatori per anno/mese/serie.
* `vendite.tipi_doc_fiscale_registri` associa il registro al tipo documento fiscale.

---

### Nota sulla FK emittente

La FK su `emittente_soggetto_ruolo_id` e` **coerente** con un modello multi‑emittente:
ogni registro appartiene a un emittente fiscale specifico. In presenza di piu`
aziende abilitate, la separazione dei registri evita collisioni di numerazione.

---

### 🔄 rev 2026-08-25 — il registro dice anche CHE DATA porta il documento

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-3**, **DB-12**).

#### Nuova colonna `politica_data_documento`

| valore | data del documento |
| --- | --- |
| `OGGI` (default) | `script.fn_data_operativa()` — fattura immediata |
| `FINE_MESE_COMPETENZA` | ultimo giorno di `fatturazione_lotti.competenza_mese` — fattura differita |

⭐ **Perché sul registro e non sul lotto.** Il registro **è** il sezionale: è lì
che vive la sequenza, e la regola della data deve stare accanto alla regola del
numero — altrimenti si può configurare un registro la cui data litiga con la sua
numerazione.

E c'è un guadagno che una colonna sul lotto non darebbe: **un lotto può contenere
documenti di registri diversi** (la natura instrada la nota di credito su un
sezionale suo). Con la regola sul registro, ogni documento prende la data giusta
**da sé**.

⚠️ Una data valorizzata su `fatturazione_lotti.data_documento` **scavalca** questa
politica, per tutti i documenti di quel lotto.

⚠️ **`FINE_MESE_COMPETENZA` e il cancello di monotonia collidono per
costruzione**, e non è un difetto: è il comportamento normale della differita in
ritardo. Un lotto di competenza arretrata lavorato oggi prende la data di fine di
quel mese, che è anteriore all'ultimo numero emesso, e viene rifiutato —
l'operatore ridichiara la data dal dialog. 📌 Misurato il 2026-08-25: 4 lotti
hanno competenza giugno e fatture datate luglio/agosto, e uno di essi porta una
fattura **già numerata**. ⭐ Per questo la `minDate` esposta al frontend
([`fn_get_data_minima_numerabile_lotto`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto))
non è un abbellimento: è ciò che rende vivibile la politica.

#### `reset_policy` scende a **una voce sola**

Il `CHECK` ammette ora solo `ANNUALE`. Prima accettava anche `NESSUNA` e
`MENSILE`, che erano **dichiarate e non implementate**: la chiave del contatore
porta `mese = 0` fisso e `uq_fatture_numero` il mese non lo contiene, quindi
`NESSUNA` si comportava come `ANNUALE` e `MENSILE` pure.

⛔ Un catalogo che promette tre comportamenti e ne fa uno è **peggio** di un
catalogo con una voce sola: prima o poi qualcuno sceglie `MENSILE`, e
un'implementazione a metà finisce in violazione di `UNIQUE`.

⚠️ Se un giorno `MENSILE` servisse davvero non basta riaprire il `CHECK`: serve
il mese **nel contatore** (c'è già) **e in `uq_fatture_numero`** (non c'è), più un
`fn_get_anno_registro` che riceva il registro.

⚠️ **Il `serie_default` è portante, non un'etichetta.** È da lì che
`fn_assign_numero_fattura` risolve la serie di un documento che non ne dichiara
una (`COALESCE(f.serie, r.serie_default, '')`), quindi **rinominarlo sposta il
sezionale**: le righe di `registri_fatturazione_progressivi` restano sulla serie
vecchia e vanno spostate a mano, o il contatore riparte da zero e il cancello
resta senza pavimento.

---

### 🔄 rev 2026-08-31 — il registro numera **cinque famiglie**, non solo le fatture

Brief: `brief-db-registri-di-numerazione-emittente-e-trasloco` (**C2**).

#### La colonna `famiglia_documento`

Dice **che specie di documento** questo registro numera: `FATTURA`, `DDT`,
`ORDINE`, `COMMESSA`, `RESO` — le voci sono quelle di
[`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento).

⭐ **Il motore era già neutro.** Documenti di trasporto, ordini, commesse e resi
avevano ciascuno il proprio contatore, e nessuno dei tre sapeva ripartire a
Capodanno né distinguere due aziende. Portarli qui non ha richiesto un motore
nuovo: nel generatore la fattura compariva ormai solo nel ramo dell'errore.

⚠️ **Un registro appartiene a UNA azienda**, e non è una preferenza: è la chiave
del contatore. Due aziende sullo stesso registro non producono numeri doppi — il
contatore è uno solo — ma **spezzano l'attribuzione**, e nessuna delle due ha più
una progressione propria. Nessun errore lo segnala: è il motivo per cui esiste un
controllo apposta e per cui l'emittente è obbligatorio dal 30 agosto 2026.

#### ⚠️ Il cancello della data vale **solo per le fatture**

Il pavimento di sequenza — *«non numeri un documento con data anteriore
all'ultimo già numerato»* — è una regola **fiscale** e vive dove c'è il registro
fiscale.

⛔ Acceso anche altrove sarebbe un rifiuto nuovo, non un modo diverso di dare il
numero: emesso un documento di trasporto datato oggi, su quel registro **nessuno
datato prima passerebbe più** — e il documento per la spedizione di ieri, inserito
stamattina, verrebbe respinto. Lo governa il flag `presidia_data_documento` sul
catalogo delle famiglie.

⭐ **L'anno invece resta quello della data del documento** per tutti, ed è
indipendente da quel flag.

#### ⛔ Il debito sul nome, dichiarato

La tabella si chiama `registri_fatturazione` e numera anche merce in uscita e
ordini. **Il nome non si cambia**, e non per pigrizia: rinominarla significa
rinominare la tabella dei progressivi, i trigger, le funzioni, le viste, i vincoli
e le colonne `registro_id` di cinque tabelle di documento.

⭐ È un lavoro che non cambia **nessun** comportamento — cioè esattamente quello
che non va infilato dentro un cantiere che ne cambia molti, dove un errore di
rinomina si confonderebbe con un errore di trasloco.

⚠️ **Ne discende una regola di lettura:** chi trova questo nome in giro non deve
dedurne «fattura». La specie si chiede a `famiglia_documento`, e la funzione che
risolve il registro di un documento **rifiuta** proprio la famiglia `FATTURA` —
quella ha una strada sua, che passa dal tipo di documento fiscale e dalla natura
dell'operazione.

---

{% include-markdown "signature-core.md" %}
