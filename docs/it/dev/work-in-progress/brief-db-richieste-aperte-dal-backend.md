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
> serve davvero (voce 4) si clicca.
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
4. vendite.fatture_atti          tabella + FK       ⭐ è quello che sblocca la chiusura
```

⭐ **Le prime tre costano minuti**, la quarta è un cantiere piccolo. Se si fa
una cosa sola, la **1**: è l'unica che tiene un presidio rosso.
⭐ Se si fa una cosa sola *che sposta il cantiere*, la **4**: senza, `I4` non si
chiude, e `I6` — l'ultima voce del cantiere IVA — viene dopo `I4`.

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

⛔ **Non è «una colonna», ed è il motivo per cui c'è un brief**: una riga
FatturaPA porta **un** blocco `DatiContratto` per atto, con
`RiferimentoNumeroLinea` a puntare le sue righe. Una fattura può mescolare
contratti diversi, quindi né la testata né una colonna di riga reggono il caso.

📌 **Metà BE, dichiarata nel brief e non richiesta qui**: `contratto_id` deve
entrare nella chiave di aggregazione delle righe di fattura, altrimenti il
satellite è una sede che non si può riempire. È lavoro nostro, va con `I4`.

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
| 2026-08-31 | Elenco nato dalla richiesta di Tid, dopo che le richieste al DB erano diventate quattro e nate in momenti diversi — la stessa dispersione che il §8-nonies del brief madre aveva già risolto con un elenco unico. ⭐ Scritto verificando **tutte e quattro sul repo**, non ricordandole: una era già stata applicata (l'annullo) e una era cambiata sotto (il seed del codice errore, arrivato per un codice e mancante per un altro dello stesso cantiere) |
