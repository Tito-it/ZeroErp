## 📘 Documentazione Concettuale – Vista `vendite.vw_lotti_gruppi_serviti`

> 👀 **Vedi anche**
>
> **Chi la usa:**
>
> • [vendite.fn_esito_gruppi_giro](/dbzero/vendite/funzioni/fn_esito_gruppi_giro) — il verdetto di un giro, che confronta questo **fatto** con il perimetro richiesto
>
> **Con cosa non va confusa:**
>
> • [vendite.fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) — il suo `gruppi_coperti` è una **previsione**, questa è la **misura**
> • [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi) — registra il **permesso**, non il servito
>
> **Su cosa è costruita:**
>
> • [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — unica fonte della chiave di gruppo
>
> **Piano:** [brief-db-emittibilita-visibile-e-sbloccabile](/dev/work-in-progress/brief-db-emittibilita-visibile-e-sbloccabile) §8.2 / §9

---

### 🎯 Scopo Principale

(latest review 15-08-2026)

**Quali gruppi fatturabili un lotto ha davvero servito.** Una riga per ogni
combinazione `(lotto, gruppo, commessa)` per cui esiste almeno un'attività
finita su una riga di fattura di quel lotto.

```text
lotto_id · gruppo_key · commessa_id · n_attivita_fatturate · n_fatture
```

---

### ⭐ Perché esiste: la differenza fra prevedere e misurare

Quando un operatore chiede di fatturare tre gruppi, il motore prima **scopre**
cosa può fare (`fn_list_emittibili_lane`, che da agosto dichiara anche
`gruppi_coperti`) e poi **esegue**. Fra i due momenti passa del tempo, e in quel
tempo le righe di un gruppo possono essere prese da un altro giro.

Il risultato è la forma di difetto peggiore, perché è muta:

```text
falliti = 0 · gruppi_non_coperti = [] · e un gruppo non è stato fatturato
```

L'esito legge «pieno successo» mentre del lavoro è rimasto fermo, e nessuno lo
va a cercare. Questa vista è la misura fatta **dopo**, l'unica che può
contraddire la previsione.

---

### 🧭 Come si legge la catena

La domanda «questa attività è stata fatturata, e da quale lotto?» si risolve in
quattro salti, tutti già esistenti:

```text
fatturazione_lotti_fatture → fatture → fatture_righe
                                     → attivita_fatturabili (fattura_riga_id valorizzato)
                                     → commesse_attivita    (la riga di origine)
```

Il perno è `attivita_fatturabili.commessa_attivita_id`, che è **UNIQUE**: ogni
riga di commessa ha al più una controparte fatturabile, quindi il conteggio non
può gonfiarsi. `fattura_riga_id` valorizzato è ciò che significa «fatturata»:
più attività possono condividere la stessa riga di fattura, ed è il motivo per
cui si contano le **attività**, non le righe.

---

### ⚠️ Tre cose da sapere prima di usarla

**1. La chiave viene da `commesse_attivita`, non da `attivita_fatturabili`.**
Le due tabelle hanno entrambe `sorgente_tipo_id`, `sorgente_uid`, `commessa_id`,
e costruire la chiave dalle gemelle sarebbe stato più corto. È proprio per
questo che non si fa: la lane, l'elenco dei gruppi e i filtri dell'emissione
mirata la calcolano tutti su `commesse_attivita`. Due copie della chiave
renderebbero incomparabili il servito e il richiesto — cioè l'unica cosa per cui
questa vista esiste.

**2. È una misura viva, non un registro storico.** Se un lotto torna a `DRAFT` e
le sue fatture spariscono, il gruppo smette di risultare servito. È corretto —
la fattura non c'è più — ma non è la cronaca di cosa fece quel giro quel giorno:
è la risposta **di oggi** alla domanda «di questo perimetro, cosa risulta
fatturato».

**3. Non c'è l'importo, ed è una scelta.** Il valore pro-quota di un'attività
(`imponibile_riga × qta_attività ÷ qta_riga`, perché N attività possono stare su
una riga sola) è una formula che vive già in
`vw_dash_competenza_attivita.valore_fatturato`. Riportarla qui sarebbe la terza
copia di una regola di calcolo, per una colonna che nessuno ha chiesto: la
domanda era *quali* gruppi, non *per quanto*.

---

### 🔍 Perché la commessa è nella grana

`gruppo_key`, per una riga con documento sorgente, vale
`<codice_interno>:<uid>` e **non contiene la commessa**. Nulla vieta in linea di
principio che lo stesso documento alimenti righe su due commesse.

Oggi non accade — `commesse_sorgenti` ha `UNIQUE (sorgente_tipo_id,
sorgente_uid)` e sul database di sviluppo i gruppi multi-commessa sono zero — ma
nessun vincolo lo impedisce su `commesse_attivita`, e
`vw_dash_competenza_gruppi` la commessa la tiene già nel proprio `GROUP BY`.
Tenerla costa una colonna e toglie di mezzo un collasso silenzioso.

---

### 🔒 Scope

`security_invoker = on`. Il cancello non è decorativo: `fatturazione_lotti_fatture`
e `attivita_fatturabili` **non** hanno RLS, mentre `fatture`, `fatture_righe` e
`commesse_attivita` sì — quindi il `JOIN` su quelle è ciò che limita la vista al
perimetro dell'operatore.

⚠️ Chi confronta questa vista con `fatturazione_lotti_gruppi` deve sapere che
quella tabella RLS **non ne ha**: senza un cancello anche sul richiesto, un
lotto invisibile produrrebbe falsi «non servito». Il cancello è dentro
`fn_esito_gruppi_giro`, che è la sede dove il confronto avviene.
