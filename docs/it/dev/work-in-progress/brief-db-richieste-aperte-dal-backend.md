# Richieste aperte dal backend — l'elenco unico per il team DB

> **Destinatario:** team DB (`dev/db-tid`). ⭐ **È un ORDINE DI LAVORO, non un
> brief di analisi**: qui c'è *cosa fare*, in ordine, con lo stato verificato.
> Il *perché* sta nei brief linkati e **non viene ricopiato**.
>
> **Origine.** Richiesta di Tid del 2026-08-31: *«possiamo mettere tutto in un
> unico brief per non disperdere il lavoro?»*. Le richieste erano quattro,
> nate in momenti diversi, e chi apriva un file solo non vedeva le altre.
>
> ⛔ **Perché l'elenco NON sostituisce i brief**, ed è la stessa scelta del
> §8-nonies del brief madre IVA: *«là c'è il ragionamento, qui c'è solo
> l'elenco con il rimando — duplicare la motivazione la farebbe divergere»*.
> Le voci qui sono corte perché la richiesta è corta; dove il ragionamento
> serve davvero (voci 4 e 5) si clicca.
>
> **Stato.** 2026-08-31, verificato sul repo a `e22a25ba7` — non ricordato.
> Ogni riga «Verificato» qui sotto è il risultato di un controllo fatto
> quel giorno, non una previsione.

---

## L'ordine, e perché è questo

```text
1. seed del codice errore        1 riga + 1 riga    ⛔ un cancello è ROSSO adesso
2. fn_create_contratto           3 stringhe         fermo dal 29/08
3. DEFAULT_IVA                   rename + registry  va col BE nello stesso giro
4. vendite.fatture_atti          tabella + FK       ⭐ sblocca I4
5. fatture_righe: capofila       colonna + guard    ⭐ sblocca I4  ← nuova, 31/08
```

⭐ **Le prime tre costano minuti**, la quarta e la quinta sono un cantiere
piccolo. Se si fa una cosa sola, la **1**: è l'unica che tiene un presidio
rosso.
⭐ Se si fa una cosa sola *che sposta il cantiere*, la **4** o la **5** — ma
vanno **insieme**: `I4` ha bisogno di entrambe, e `I6` — l'ultima voce del
cantiere IVA — viene dopo `I4`.

⚠️ **La quinta è nata il 2026-08-31 controllando, e non era nell'elenco**: la
decisione `N3` sceglieva le due righe legate padre/figlia da settembre, ma
nessuno aveva verificato che `fatture_righe` **non ha** una colonna per
reggerle. Era un lavoro dichiarato bloccato su un prerequisito che non era mai
stato chiesto.

---

## 1. ⛔ Il seed di `E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO`

**Non c'è un brief: è una riga.** Due, per la precisione — una in
`codici_errore.csv` e una in `messaggi_errore.csv`.

**Verificato il 2026-08-31**: il codice **non esiste in nessun punto di git** —
né nei due CSV, né in un changeSet, né in un brief. Esiste **solo sul database
di sviluppo**. Viene dal cantiere
[registri di numerazione](brief-db-registri-di-numerazione-emittente-e-trasloco.md).

**Cosa blocca.** Il backend non può rigenerare `error_policies_generated.py`.
`manage.py genera_error_policies --check` gira in CI e confronta il file
**carattere per carattere** col catalogo: in CI il database si ricostruisce da
zero, quindi quel codice non c'è e il file rigenerato risulterebbe divergente —
rosso su una PR che coi registri non c'entra niente.

⇒ Finché manca, **nove** codici restano senza policy: i quattro dell'IVA, i tre
dell'annullo forzatura, quello del registro emittente, e questo. Un codice senza
policy che il DB solleva arriva all'operatore come **400 «errore di
validazione»** invece che sulla sua classe — su un `TECNICO` significa dire «hai
sbagliato tu» per un guasto.

⚠️ **E va detto perché è la seconda volta.** Il 2026-08-30 era successo identico
con `E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE`, dello **stesso** cantiere:
applicato sul DB di sviluppo, seminato il giorno dopo. Non è un rimprovero — è
che finché il seed arriva in ritardo il cancello dei codici resta rosso e nessun
altro lavoro può rigenerare quel file. ⭐ Il modo di non ripeterlo è quello che
il piano dei registri già scrive alla voce **C1-4**: *«solo append al CSV»*,
nello stesso commit del codice che lo solleva.

---

## 2. `fn_create_contratto` non whitelista i tre riferimenti dell'atto

📌 **Brief:** [brief-db-fn-create-contratto-codici-atto.md](brief-db-fn-create-contratto-codici-atto.md)
(scritto il 2026-08-29).

**La richiesta, per intero:** estendere `v_testata_allowed` di
`vendite.fn_create_contratto` con `'codice_cig'`, `'codice_cup'`,
`'codice_commessa'`. Nient'altro: le tre colonne esistono già coi loro
`COMMENT`.

**Verificato il 2026-08-31**: la whitelist non li contiene ancora.

**Cosa blocca.** La slice `S3-b`: in **PATCH** il backend li scrive già, in
**CREATE** no — e la funzione non solleva, **scarta**. Il contratto nasce,
l'operatore non vede errori, e il CIG non va da nessuna parte.

⚠️ Le tre avvertenze (changeSet nuovo, corpo dalla doc auto-gen e non dallo
YAML, `COMMENT` aggiornato) sono nel brief. ⭐ E il motivo per cui non è una
comodità: **è lo stesso difetto già costato un giro su questa stessa funzione**
il 2026-07-27 con `fatturazione_immediata`, documentato nel commento che gli sta
accanto.

---

## 3. `DEFAULT_IVA_ID` è l'ultimo parametro che stocca un id

📌 **Brief:** [brief-db-default-iva-chiave-naturale.md](brief-db-default-iva-chiave-naturale.md).

**La richiesta, per intero:**

1. rinominare il parametro `DEFAULT_IVA_ID` → `DEFAULT_IVA`;
2. cambiarne il valore da `16` al `codice_interno` corrispondente, e riscrivere
   la descrizione (che oggi cita `config.iva.id=16`);
3. una riga in `config.parameter_fk_surrogate`: `code_pattern` EXACT su
   `DEFAULT_IVA`, target `config.iva.codice_interno`.

**Verificato il 2026-08-31**: il seed dice ancora `DEFAULT_IVA_ID,16`.

⭐ **La condizione che lo bloccava è caduta**: `linee-guida-sql §6b` nomina
proprio questo parametro come tech debt e descrive quattro passi; i primi due
(`codice_interno` su `config.iva` + lock automatico) li ha fatti `D28`
(`20260829-43`). Restano il terzo e il quarto, che sono seed.

⚠️ **Il lettore BE si adegua nello stesso giro, non prima** — è uno solo, il
form-defaults dell'articolo. Se il seed cambia da solo, quel lettore cerca un
parametro che non c'è più e prende il ripiego.

---

## 4. ⭐ `vendite.fatture_atti` — il satellite dei riferimenti dell'atto

📌 **Brief:** [brief-db-fatture-atti-riferimenti-contratto.md](brief-db-fatture-atti-riferimenti-contratto.md).
⚠️ **Questa è l'unica voce in cui il ragionamento serve davvero**: la forma è
stata scelta dopo aver verificato come la FatturaPA modella il blocco.

**La richiesta, in sintesi** (dettaglio, vincoli e presidi nel brief):

* tabella `vendite.fatture_atti` — una riga per `(fattura, contratto)`, con lo
  **snapshot** di numero, data e i tre codici;
* `vendite.fatture_righe.fattura_atto_id`, **nullable**, FK verso quella;
* montare `trgfn_fattura_satellite_guard_congelamento` (⭐ è già parametrica da
  `D34`: basta `TG_ARGV = ('fattura_id')`, **nessun codice errore nuovo**);
* classificare la tabella in `test-cleanup-fattura-copertura-figlie-v1.sql`,
  che diventerà rosso e ne farà il nome — ⚠️ e la sua intestazione dice che la
  categoria si **decide**, non si aggiunge per far tornare il verde.

**Verificato il 2026-08-31**: la tabella non esiste.

**Cosa blocca.** `I4` — la riga di fattura che ri-risolve l'IVA e porta i
riferimenti dell'atto — e a cascata `I6`, che è l'ultima voce del cantiere IVA.
⚠️ Da sola non basta: serve anche la **5**.

⛔ **Non è «una colonna», ed è il motivo per cui c'è un brief**: una riga
FatturaPA porta **un** blocco `DatiContratto` per atto, con
`RiferimentoNumeroLinea` a puntare le sue righe. Una fattura può mescolare
contratti diversi, quindi né la testata né una colonna di riga reggono il caso.

✅ **La metà BE è FATTA** (2026-08-31, prima della tabella e apposta):
`contratto_id` è entrato nella chiave di aggregazione delle righe di fattura —
senza, il satellite sarebbe una sede che non si può riempire, perché una riga
aggregata apparterrebbe a due atti. Finché la tabella non c'è l'atto della riga
vive nello `meta` (`group_key.contratto_id`), quindi al momento del popolamento
**il dato per riempirla esiste già**.

---

## 5. ⭐ `vendite.fatture_righe` — la riga capofila, per la riga che si spezza

📌 **Il ragionamento è già scritto**, e non si ricopia: decisione `N3` del
[piano BE/FE di Fase 3](brief-be-fe-iva-fase-3-consumatori-risolutore.md#n3), §3.

**Il fatto.** In fattura il risolutore riceve l'imponibile **vero**, quindi può
tornare **due** parti: la quota che il plafond del titolo copre e il resto. Una
riga FatturaPA porta **una** `AliquotaIVA` e **una** `Natura` ⇒ due trattamenti
sullo stesso imponibile sono due `DettaglioLinee`, **per obbligo di formato**.
La spezzatura non si può evitare: si può solo decidere chi la regge.

**La scelta già fatta (`N3`, opzione `a'`)**: le due parti sono **due
`fatture_righe` in relazione padre/figlia**, e `attivita_fatturabili.
fattura_riga_id` continua a puntare la **capofila**. Dall'attività si raggiunge
la capofila, dalla capofila le sue parti. ⭐ Nessuna modifica a
`attivita_fatturabili`, nessuna unique violata, e `fatturato` —
`GENERATED ALWAYS AS (fattura_riga_id IS NOT NULL)` — resta `true` da sé.

**⛔ E la colonna che regge quel legame NON ESISTE.** Verificato il 2026-08-31
sulla doc auto-generata di `vendite.fatture_righe`: ci sono `kit_key`,
`kit_articolo_padre_id`, `kit_descrizione_padre` — e basta.

⚠️ **Riusare le colonne del kit sarebbe la scorciatoia sbagliata**, ed è il
motivo per cui questa voce esiste invece di non esistere: `kit_key` dice *«queste
righe vengono dallo stesso kit venduto»*. Una riga spezzata dal plafond non viene
da nessun kit, e marcarla così farebbe leggere al prossimo — e a
`vw_fattura_righe_esposte`, che le aggrega — un fatto che non è vero.

**La richiesta.**

1. `vendite.fatture_righe.riga_capofila_id`, **nullable**, FK verso
   `vendite.fatture_righe(id)`. `NULL` sulla capofila (che è essa stessa la
   prima parte), valorizzata sulle parti successive;
2. un guard che tenga **due** invarianti — e sono i due che, se violati,
   non darebbero nessun sintomo:
   * ⛔ **niente catene**: una riga con `riga_capofila_id` deve puntare a una
     riga che ce l'ha `NULL`. Senza, «capofila → parti» smette di essere una
     lettura a un salto e chi somma prende metà valore;
   * ⛔ **stessa fattura**: la capofila deve stare sulla `fattura_id` della
     parte. Una parte che punta a un altro documento è un totale che non torna
     su due fatture insieme.
3. `vw_fattura_righe_esposte` deve conoscere la relazione nuova — ⭐ ma conosce
   già quella del kit, quindi la forma non si inventa.

**Cosa blocca.** `I4`, esattamente come la voce 4 — e per la stessa slice.
⛔ Senza, la riga **non si può spezzare**, quindi il risolutore in fattura non si
può chiamare con l'imponibile vero, quindi il plafond non si consuma: il registro
costruito in Fase 2 resta una promessa.

**Presidio atteso.** ⭐ Quello che discrimina non è «la INSERT riesce» — riesce
comunque: è **una parte che punta a una parte** (la catena) e **una parte che
punta a una riga di un'altra fattura**, entrambe **rifiutate**. E il gemello
positivo: due parti sulla stessa capofila della stessa fattura, **ammesse**.
Senza il terzo, un guard che rifiuta sempre passerebbe i primi due.

⚠️ **Una nota sul momento, che è del BE ma va saputa anche qui**: la spezzatura
deve avvenire mentre la fattura è ancora `EMESSA`.
`trgfn_fattura_satellite_guard_congelamento` legge lo stato **vivo** al momento
della scrittura — in una transazione che porta prima a `DEFINITIVA` e poi scrive
le righe, il guard vede `congela_fiscale = t` e rifiuta.

---

## ✅ Cosa NON è più da fare

⭐ **L'annullo di una forzatura è APPLICATO** (merge `#1438`, 2026-08-31):
`anagrafiche.soggetti_titoli_iva_movimenti.annulla_movimento_id` c'è, con
`CHECK`, FK, unique e guard trigger. Il brief
[brief-db-titoli-iva-movimenti-annullo.md](brief-db-titoli-iva-movimenti-annullo.md)
è chiuso, e sblocca `T3-b` del [piano BE/FE dei titoli](brief-be-fe-titoli-iva-soggetto.md).

---

## Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 (2) | ⭐ **Aggiunta la voce 5** — la colonna capofila su `fatture_righe`. Trovata rispondendo alla domanda «c'è qualcosa di Fase 3 che non aspetta il DB?»: `N3` sceglieva le due righe legate da giorni, ma nessuno aveva verificato che la sede del legame non esiste. ⛔ Il lavoro risultava bloccato su un prerequisito **mai chiesto**. Nello stesso giro la metà BE della voce 4 (`contratto_id` nella chiave di aggregazione) è passata da «da fare» a **fatta** |
| 2026-08-31 | Elenco nato dalla richiesta di Tid, dopo che le richieste al DB erano diventate quattro e nate in momenti diversi — la stessa dispersione che il §8-nonies del brief madre aveva già risolto con un elenco unico. ⭐ Scritto verificando **tutte e quattro sul repo**, non ricordandole: una era già stata applicata (l'annullo) e una era cambiata sotto (il seed del codice errore, arrivato per un codice e mancante per un altro dello stesso cantiere) |
