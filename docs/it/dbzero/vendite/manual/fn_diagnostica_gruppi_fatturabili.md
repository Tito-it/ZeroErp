## 📘 Documentazione Concettuale – Funzione `vendite.fn_diagnostica_gruppi_fatturabili`

> 👀 **Vedi anche**
>
> **Di chi è lo specchio:**
>
> • [vendite.fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) — i criteri che questa fotografia conta uno per uno
> • [script.fn_check_commessa_pronta_fatturazione](/dbzero/script/funzioni/fn_check_commessa_pronta_fatturazione) — la sorella che risponde `sì/no` sulla testata
>
> **Con chi lavora:**
>
> • [vendite.fn_esito_gruppi_giro](/dbzero/vendite/funzioni/fn_esito_gruppi_giro) — dice *che fine ha fatto* un gruppo; questa dice *perché*
>
> **Su cosa è costruita:**
>
> • [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — unica fonte della chiave
>
> **Piano:** [brief-db-emittibilita-visibile-e-sbloccabile](/dev/work-done/brief-db-emittibilita-visibile-e-sbloccabile) §5.2 (offerta dal BE) e §9 F4 (accolta)

---

### 🎯 Scopo Principale

(latest review 15-08-2026)

**La fotografia di un gruppo fatturabile**: quante righe ha, in che stato sono,
e in che stato è la testata della commessa che le contiene. Serve a spiegare
all'operatore perché un gruppo che aveva chiesto di fatturare non è stato
servito.

```text
per (gruppo, commessa):  codice · stato (codice interno E descrizione) · emittibile
                         n_righe · n_emesse · n_annullate · n_rifiutate
                         n_non_approvate
                         n_fuori_competenza · n_pronte
```

---

### ⭐ Perché è scesa nel database

Fino al 2026-08-15 questa query stava in
`CommesseRepository.diagnostica_gruppi`: sessanta righe di SQL in Python che
riproducevano i filtri di `fn_list_emittibili_lane` — `APPROVATA`,
`NON_EMESSA`, `tipo_doc_fiscale_id NOT NULL`, competenza `<=`.

Era la stessa forma di duplicazione che il §7.1 del brief aveva già dovuto
estrarre una volta: il guard di transizione teneva in casa la condizione «almeno
una riga approvata» mentre le uscite terminali delegavano già alle funzioni
pure. Il backend lo aveva visto e si era offerto di passarla; la risposta è
arrivata il 2026-08-15, ed è stata sì.

---

### ⚠️ Il difetto che la copia Python aveva già

La versione in Python aggregava per `gruppo_key` con `min(commessa_codice)`,
`min(stato_commessa)` e `bool_or(commessa_emittibile)`.

Ma `gruppo_key`, per una riga con documento sorgente, vale
`<codice_interno>:<uid>` e **non contiene la commessa**. Se lo stesso documento
alimentasse righe su due commesse — una in `BOZZA` e una in
`PRONTA_FATTURAZIONE` — il `bool_or` direbbe «emittibile» perché *una* lo è, e
la diagnosi cadrebbe nel motivo generico invece di dire *«la commessa è in
BOZZA»*: cioè proprio il caso che questa diagnostica esiste per raccontare.

⚠️ `vw_dash_competenza_gruppi` la commessa la tiene **già** nel proprio `GROUP
BY`: la vista ammetteva il caso, il repository lo collassava. Qui la grana è
`(gruppo_key, commessa_id)`, e il difetto non può esistere.

**Calibrazione onesta.** Sul database di sviluppo i gruppi multi-commessa sono
**zero**, e `commesse_sorgenti` ha `UNIQUE (sorgente_tipo_id, sorgente_uid)` che
rende il caso improbabile. Ma nessun vincolo lo impedisce su
`commesse_attivita`: la domanda è *«può succedere?»*, non *«è successo?»*, e in
SQL evitarlo costa una colonna nel `GROUP BY`.

---

### 🧭 Dove passa la linea con il backend

Scende la **fotografia**, non la **prosa**.

| Sta nel DB | Sta nel backend |
| --- | --- |
| quante righe, in che stato, quale testata | «3 attività non sono ancora approvate» |
| i contatori, uno per criterio della lane | l'accordo di genere e numero, la scelta del motivo |

`classifica_gruppo_non_servito` compone frasi italiane: è presentazione, nel
database starebbe male e in inglese andrà comunque rifatta. Il DB dice *quanti*
e *in che stato*, il backend dice *come si racconta*.

---

### ℹ️ Le classi, e le due cose da sapere

**`n_fuori_competenza`** è la sola che dipende da `p_competenza_mese`: conta le
righe pronte con competenza **successiva** al mese richiesto, ed è il motivo per
cui il parametro esiste. Con `NULL` non c'è limite, la classe resta vuota per
costruzione e quelle righe finiscono in `n_pronte`. Il mese si normalizza al
primo giorno, come fa il chiamante.

**Il contatore che non c'è: `n_senza_tipo_doc`.** C'era nella prima stesura, ed
è durato mezza giornata. Contava le righe `APPROVATA` + `NON_EMESSA` senza tipo
documento — righe che `trgfn_commesse_attivita_guard_tipo_doc_emittibile` e un
`CHECK` di tabella rifiutano, quindi impossibili. Restava in vita per un solo
motivo: quel `CHECK` era `NOT VALID`, cioè le righe **preesistenti** non erano
mai state lette, e il ramo restava «forse» vivo.

`20260815-30` le ha lette (validazione del vincolo), `20260815-31` ha tolto il
contatore. Un ramo irraggiungibile non è prudenza: è codice che **sembra**
coperto e non lo è — la stessa ragione per cui il §7.2 del brief non aveva fatto
del tipo documento un motivo separato di `fn_check_commessa_pronta_fatturazione`.

⚠️ **Ricaduta sul backend**: `MOTIVO_TIPO_DOC_MANCANTE` in
`classifica_gruppo_non_servito` diventa morto anche lì. Quando il BE adotterà
questa funzione, quel ramo va tolto insieme alla chiave `n_senza_tipo_doc` di
`GruppoDiagnosi`.

---

### ⚠️ Un gruppo sconosciuto esce lo stesso

Se una chiave richiesta non corrisponde a nessuna riga, la funzione restituisce
comunque la sua riga, con `commessa_id` a `NULL` e i contatori a zero. Farla
sparire dal risultato sarebbe un silenzio: il chiamante non saprebbe
distinguere «chiave ignota» da «chiave mai chiesta».

Le chiavi in ingresso si normalizzano con `btrim`, come fa
`fn_build_gruppo_fatturabile_key`: una chiave con spazi in coda non combacerebbe
mai, e filtrerebbe zero righe senza dirlo.

---

### 🔒 Scope

`STABLE`, sola lettura, nessun `SECURITY DEFINER`. `commesse` e
`commesse_attivita` hanno la RLS: la fotografia è già limitata al perimetro
emittente dell'operatore, esattamente come lo era la query del repository.
