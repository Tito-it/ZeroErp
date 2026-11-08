## 📘 Documentazione Concettuale – Funzione `vendite.fn_diagnostica_gruppi_fatturabili`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [vendite.vw_commesse_attivita_emittibilita](/dbzero/vendite/views/vw_commesse_attivita_emittibilita) — la sede unica della classe di ogni riga, che questa funzione conta
> * [vendite.vw_documenti_trattenuti_da_lotto](/dbzero/vendite/views/vw_documenti_trattenuti_da_lotto) — i documenti che un lotto trattiene
>
> Approfondimento funzioni:
>
> * [vendite.fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) — la lane, che filtra la stessa classe che qui si conta
> * [script.fn_check_commessa_pronta_fatturazione](/dbzero/script/funzioni/fn_check_commessa_pronta_fatturazione) — la sorella che risponde sì o no sulla testata
> * [vendite.fn_esito_gruppi_giro](/dbzero/vendite/funzioni/fn_esito_gruppi_giro) — dice che fine ha fatto un gruppo; questa dice perché
> * [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — l'unica fonte della chiave

---

### 🎯 Scopo Principale

`vendite.fn_diagnostica_gruppi_fatturabili` è la fotografia di uno o più gruppi fatturabili: quante
righe hanno, in che classe di emittibilità sono, in che stato è la testata della commessa che le
contiene, in quale corsia ricade il lavoro ancora pronto e quale lotto trattiene quello che non lo è.

Serve a spiegare all'operatore perché un gruppo che aveva chiesto di fatturare non è stato servito.

---

### Che cosa restituisce

Una riga per coppia (gruppo, commessa), con:

* la testata: codice della commessa, stato (codice interno e descrizione) e il flag `commessa_emittibile`;
* `n_righe` e un contatore per classe di emittibilità: `n_emesse`, `n_annullate`, `n_rifiutate`,
  `n_non_approvate`, `n_trattenute`, `n_pronte`;
* `n_fuori_competenza`: le righe pronte, ma con competenza successiva al mese richiesto;
* `terne_pronte`: le corsie (emittente, tipo di documento fiscale, utility) in cui ricadono le righe
  pronte;
* `lotti_trattenenti`: i lotti, con id e codice, che trattengono le righe trattenute.

Senza nessun gruppo richiesto la funzione non restituisce niente: è l'identità, non un errore.

---

### ⭐ I criteri non sono scritti qui: si contano

La classe di ogni riga si legge da `vendite.vw_commesse_attivita_emittibilita`, la stessa sede che
`vendite.fn_list_emittibili_lane` filtra. Lane e diagnostica non possono più dissentire: quando i
criteri erano scritti due volte, un criterio aggiunto alla lane e non alla diagnostica le faceva
rispondere «era pronto» su un documento che la lane non aveva offerto.

⚠️ **Il secondo fattore resta separato.** `commessa_emittibile` descrive la testata, la classe
descrive la riga, e non si fondono: è ciò che permette di dire «le righe sarebbero pronte, è la
commessa a essere in `BOZZA`», la sola cosa che questa funzione sa dire meglio della lane.

---

### ⚠️ La grana è (gruppo, commessa)

La chiave di gruppo di una riga con documento sorgente è fatta dal tipo e dall'uid del documento, e
**non contiene la commessa**. Se lo stesso documento alimentasse righe su due commesse, una in `BOZZA`
e una pronta, un'aggregazione per sola chiave direbbe «emittibile» perché una lo è, e la diagnosi
cadrebbe sul motivo generico invece di dire «la commessa è in `BOZZA`».

Il caso è del modello: un documento sta in una sola commessa aperta alla volta, ma il link verso una
commessa chiusa o annullata resta come storia, e il documento rimandato vive in una commessa nuova.
Per questo la grana è (gruppo, commessa), come in `vendite.vw_dash_competenza_gruppi`.

---

### Le classi e le colonne da sapere

* **`n_fuori_competenza`** è la sola che dipende dal mese di competenza: conta le righe `PRONTA` con
  competenza successiva al mese richiesto. «Fuori competenza» non è una classe: la riga è pronta, solo
  non per quel mese. Senza mese non c'è limite, la colonna resta a zero e quelle righe finiscono in
  `n_pronte`. Il mese si normalizza al primo giorno, come fa il chiamante.
* **`n_pronte` e `terne_pronte`** guardano lo stesso predicato, «pronta per questo mese»: il conteggio e
  l'elenco delle corsie non possono raccontare due cose diverse.
* **`terne_pronte`** è un elenco e non tre colonne, perché un gruppo può stare su più corsie: il tipo di
  documento fiscale sta sulla riga. La corsia non si prevede, si legge sul presente: sono le tre
  colonne su cui la lane raggruppa. Incrociata con le corsie fallite di un giro, che il backend ha
  negli esiti, distingue «non servito perché il perimetro non lo ammetteva» (si corregge) da «non
  servito perché l'esecuzione si è rotta» (si riprova).
* **`n_trattenute` e `lotti_trattenenti`** dicono che il gruppo è trattenuto da un lotto, e da quale:
  «trattenuto» senza dire da che cosa non è azionabile. Le righe trattenute non entrano in `n_pronte`.
* ⚠️ `terne_pronte` e `lotti_trattenenti` valgono un elenco vuoto, mai nullo, quando non c'è niente:
  «niente» e «non calcolato» devono restare distinguibili. Entrambi, e il risultato, hanno un ordine
  deterministico: il chiamante compone una frase coi primi elementi, e due chiamate uguali devono dare
  la stessa frase.

**Il contatore che non c'è: righe pronte senza tipo documento.** Le rifiutano
`trgfn_commesse_attivita_guard_tipo_doc_emittibile` e un `CHECK` di tabella validato: sono impossibili,
e un ramo irraggiungibile sembra coperto e non lo è.

---

### ⚠️ Un gruppo sconosciuto esce lo stesso

Se una chiave richiesta non corrisponde a nessuna riga, la funzione restituisce comunque la sua riga,
con la commessa vuota e i contatori a zero. Farla sparire sarebbe un silenzio: il chiamante non
saprebbe distinguere «chiave ignota» da «chiave mai chiesta».

Le chiavi in ingresso si ripuliscono dagli spazi, come fa `vendite.fn_build_gruppo_fatturabile_key`:
una chiave con spazi in coda non combacerebbe mai, e filtrerebbe zero righe senza dirlo.

---

### 🧭 Dove passa la linea con il backend

Scende la fotografia, non la prosa: il database dice quanti, in che stato, in quale corsia e trattenuti
da chi; il backend compone la frase, con l'accordo di genere e numero e la scelta del motivo. La prosa
è presentazione, e in un'altra lingua andrebbe comunque rifatta.

---

### 🔒 Perimetro

`STABLE`, sola lettura, senza `SECURITY DEFINER`. Le commesse e le loro righe hanno la RLS: la
fotografia è già limitata al perimetro dell'emittente dell'operatore.

---

### Test

* `vendite/test-diagnostica-gruppi-fatturabili-v1` — contatori, grana, gruppo sconosciuto, corsie e
  trattenute.
* `vendite/test-specchio-lane-diagnostica-v1` — i gruppi che la lane copre sono esattamente quelli che
  la diagnostica conta pronti, col fattore di testata applicato.

---

### Note di migrazione

* 2026-08-15 — la query scende dal backend (`CommesseRepository.diagnostica_gruppi`, che aggregava per
  chiave di gruppo collassando le commesse) nel database. Il contatore `n_senza_tipo_doc` nasce e si
  ritira lo stesso giorno, dopo la validazione del `CHECK`; arriva `terne_pronte`
  (brief-db-emittibilita-visibile-e-sbloccabile). Ricaduta sul backend: il motivo
  `MOTIVO_TIPO_DOC_MANCANTE` è morto anche lì.
* 2026-09-09 — i criteri escono dalla funzione: la classe si legge da
  `vendite.vw_commesse_attivita_emittibilita`; arrivano `n_trattenute` e `lotti_trattenenti`
  (brief-db-il-trattenuto-passa-lo-stesso).
* 2026-10-12 — un documento può avere più link di commessa (uno aperto, gli altri storia): la pagina
  diceva che l'unicità globale di `commesse_sorgenti` rendeva il caso improbabile.
* 2026-11-07 — la chiave del gruppo di una riga di commessa la costruisce
  `vendite.fn_gruppo_fatturabile_key_di_attivita` dalla `segment_key`; la forma della chiave non cambia
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
