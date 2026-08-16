# Brief BE → DB — il template Preventivo passa dalla lista agli slot (l'ultimo dei sei)

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-16.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** il context builder del Preventivo ora espone `indirizzi` nella
**forma unica cross-dominio** — slot con nome, chiavi fisse — come ordini, DDT,
contratti e offerte. Serve una versione nuova del template Preventivo che la
legga. Era l'ultimo dominio a slot rimasto fuori.
**Nasce da:** §11.3 di
[brief-db-indirizzi-su-ordini-contratti-offerte.md](brief-db-indirizzi-su-ordini-contratti-offerte.md),
chiuso lo stesso giorno. Decisione di Tid del 2026-08-16.
**Correlati:** [brief-db-template-preventivo-indirizzi.md](brief-db-template-preventivo-indirizzi.md)
(§2 sul `.get()`, §7.2 sulla forma unica).

> 🟢 **CHIUSO — 2026-08-16.** Cantiere completo in giornata, sui due lati.
> **BE**: il context builder del Preventivo è passato alla forma unica
> (`context_version` 2), 1771 test verdi. **DB**: due changeSet `20260816-01`
> (bozza v4) e `-02` (pubblicazione), applicati; blocco renderizzato con
> `StrictUndefined` su sei casi presi dai **valori reali** dei 12 snapshot dei
> preventivi. **Verifica finale: Tid ha testato la stampa preventivi** — è
> l'ultima voce della checklist del §6, e la sua riuscita conferma anche che il
> `migrate` è passato, perché con la v3 il render sarebbe fallito.
>
> **La «finestra rotta» del §4 è chiusa**: è durata dal merge BE al `migrate`,
> poche ore dello stesso giorno.
>
> 🔴 **Una frase di questo brief era falsa, ed è corretta nel testo.** «Il
> Preventivo è l'ultimo template a leggere con `.get()`» vale per il **solo
> blocco indirizzi**: il `.get()` resta su righe e IVA in tutti i template
> (`off-comm` 37, `ord-ven` 29, `contratto` 21, `ddt-ven` 11). Rilievo del DB,
> accolto — §3 punto 1 e §6 riscritti, e §8.2 sul perché quella frase era più
> pericolosa dell'errore che conteneva. Corretta anche alla fonte, nel §11.3 di
> [brief-db-indirizzi-su-ordini-contratti-offerte.md](brief-db-indirizzi-su-ordini-contratti-offerte.md).
>
> 📌 **Documento unico dei due lati**, come chiesto dal DB: qui cambiava il lato
> che lavorava, non il soggetto. Il §8 porta la sede DB per intero; il file
> separato `brief-db-template-preventivo-slot-indirizzi.md` è stato ritirato
> dopo il travaso (§8.4).
>
> 🔎 **Se cercavi quel nome perché l'hai letto nel database, sei nel posto
> giusto.** I due changeSet marcano la riga della versione template con
> `meta->>'brief' = 'brief-db-template-preventivo-slot-indirizzi.md'`: il
> marcatore resta quello, perché sono già applicati e un changeSet eseguito non
> si riscrive (il checksum Liquibase). **Quel marcatore punta a questo
> documento.**

---

## 1. Perché adesso, visto che la v3 funziona

Il §7.2 del brief di agosto prometteva **una** forma per l'indirizzo, chiamata
da tutti e sei i builder. Ne sono arrivati quattro. Il Preventivo è rimasto alla
forma v1 — una lista da scorrere — e la fattura alla sua stringa già composta:

| Builder | Come il template legge l'indirizzo |
| --- | --- |
| ordine, contratto, offerta, ddt | `indirizzi.consegna.via` — slot con nome, chiavi fisse |
| **preventivo** | `{% for ind in indirizzi %}` poi `ind.snapshot.via` |
| fattura | `cliente.indirizzo` — stringa già composta |

Il Preventivo non si era mosso per una ragione scritta nel codice: non cambiare
il `context_hash` dei documenti già generati. **Quella ragione è caduta** — sono
documenti di test e il progetto non è in produzione (decisione di Tid). La
fattura resta fuori: non ha slot da stampare ma un solo indirizzo fiscale
composto su una riga, ed è una scelta a sé, non un debito di questo cantiere.

## 2. Cosa abbiamo già fatto (BE, in questo branch)

`PreventivoDocumentContextBuilder` chiama il BB condiviso
`_indirizzi_documento_helpers.shape_indirizzi_context`, come gli altri quattro.
Il `_meta.context_version` passa da **1 a 2**.

Slot dichiarati staticamente dai 4 tipi ammessi in ambito `PREVENTIVI`
(`config.tipi_indirizzi_allowed`: FATT 8, CON 10, FORNITURA 9, RES 1 — lo stesso
insieme di `OFFERTE`):

```python
_INDIRIZZI_CODICI = ("CON", "FATT", "FORNITURA", "RES")
```

Forma che arriva al template (invariata rispetto agli altri domini):

```python
"indirizzi": {
  "consegna":     {...} | None,   # slot SEMPRE presente, None se il documento non l'ha
  "fatturazione": {...} | None,
  "fornitura":    {...} | None,
  "residenza":    {...} | None,
}
# slot pieno = tutte le chiavi di SNAPSHOT_KEYS_ORDERED (intestazione, via,
# cap, citta, prov, stato, display, email, telefono, note), a None se il
# valore manca, + `display_compatto` (riga sola già composta).
```

⚠️ **Come già sapete dal §9.2**: garantiamo le **chiavi**, non i **valori**. La
guardia va messa **per campo**, non sul solo slot, altrimenti tornano le righe
vuote.

**Test:** 1444 verdi su `apps.vendite.tests.services` + `apps.documenti`,
inclusa la copertura nuova sulla forma a slot del Preventivo (slot pieno, slot
`None`, `display_compatto`).

## 3. Cosa chiediamo — una versione nuova del template Preventivo

Il template `test` (descrizione «Preventivo») è oggi alla **v3 PUBBLICATA**, e
il suo blocco indirizzi è quello del §3 del brief di agosto: itera `indirizzi`
come lista e legge con `.get()`. Con la forma nuova **non funziona più** — la
lista è diventata un dict.

Blocco da sostituire. Quattro slot invece di uno, quindi la coppia
etichetta/slot sta in un `for` inline: evita quattro blocchi copiati e tiene
l'accesso diretto:

```jinja
{% set slot_indirizzi = [
     ("Luogo di consegna",        indirizzi.consegna),
     ("Indirizzo di fatturazione", indirizzi.fatturazione),
     ("Punto di fornitura",        indirizzi.fornitura),
     ("Residenza",                 indirizzi.residenza)
   ] %}
{% if indirizzi.consegna or indirizzi.fatturazione
      or indirizzi.fornitura or indirizzi.residenza %}
  <section class="section">
    <div class="label">Indirizzi documento</div>
    <div class="box">
      {% for etichetta, ind in slot_indirizzi %}
        {% if ind %}
          <div{% if not loop.last %} style="margin-bottom: 8px;"{% endif %}>
            <strong>{{ etichetta }}</strong><br>
            {% if ind.intestazione %}{{ ind.intestazione }}<br>{% endif %}
            {% if ind.via %}{{ ind.via }}<br>
            {% elif ind.display %}{{ ind.display }}<br>{% endif %}
            {% if ind.cap or ind.citta or ind.prov %}
              {{ [ind.cap, ind.citta] | select | join(" ") }}{% if ind.prov %} ({{ ind.prov }}){% endif %}<br>
            {% endif %}
            {% if ind.stato %}{{ ind.stato }}{% endif %}
          </div>
        {% endif %}
      {% endfor %}
    </div>
  </section>
{% endif %}
```

Tre cose da notare, tutte volute:

1. **Niente `.get()` in questo blocco.** È il presidio del §2 del primo brief
   applicato **all'area indirizzi**, che è il perimetro di quel rilievo: il
   Preventivo è l'ultimo dei sei a leggere l'indirizzo in modo che un nome
   sbagliato stampi vuoto invece di far fallire il render. Se preferite
   `display_compatto` per la riga geografica, va benissimo — è pensato per
   questo — purché resti accesso diretto.

   > 🔴 **Correzione (2026-08-16, rilievo del DB).** La prima stesura diceva «il
   > Preventivo è **l'ultimo template** a leggere con `.get()`» e chiudeva il §2
   > per intero. **Falso**: il `.get()` resta su righe e IVA ovunque —
   > `off-comm` 37, `ord-ven` 29, `contratto` 21, `ddt-ven` 11, e sul Preventivo
   > stesso ~20 che questo blocco non tocca. Il perimetro di questo cantiere è
   > l'area indirizzi, e solo quella si chiude qui. Vedi §8.2.
2. **L'etichetta non è più `tipo_indirizzo_descrizione`.** Con gli slot il nome
   lo sceglie il template, non il dato: quelle quattro stringhe sono una
   proposta, cambiatele se avete una convenzione migliore.
3. **La guardia esterna elenca i quattro slot** invece di provare `{% if
   indirizzi %}`: il dict c'è sempre, quindi sarebbe sempre vero e stamperebbe
   una sezione vuota.

Il resto del template non si tocca.

> ✅ **Il blocco è stato renderizzato, non solo scritto.** Provato qui con Jinja
> e `StrictUndefined`, contesto costruito con la funzione vera del BE
> (`shape_indirizzi_context`) — sei casi, tutti puliti, zero righe vuote:
>
> ```text
> completo (1 slot)     Azienda PG Test Natura | PIAZZA PRIMO MAGGIO 77 | 75025 POLICORO (MT) | IT
> senza intestazione    PIAZZA PRIMO MAGGIO, 77/A | 75025 POLICORO (MT) | IT
> solo via              VIA X 1 | IT
> due slot (CON+FATT)   Acme | VIA A 1 | 00100 ROMA (RM) | IT   +   Acme Amm. | VIA B 2 | 20100 MILANO (MI) | IT
> tutti e quattro       4 blocchi, uno per slot
> nessun indirizzo      (sezione non stampata)
> ```
>
> ⚠️ **Una trappola trovata così, che vale la pena conoscere.** La prima
> stesura aveva `{% if ind.cap or ind.citta %}{{ ind.cap }} {{ ind.citta }}{% endif %}`
> e sull'ordine senza CAP stampava **`None ROMA`**: le chiavi ci sono sempre ma
> il valore è `None`, e Jinja lo rende come la stringa `"None"`. Il `select |
> join(" ")` del blocco sopra è lì per quello, non per eleganza. È la stessa
> famiglia del vostro §9.2 — «garantiscono le chiavi, non i valori» — un passo
> più in là: non basta guardare il campo, bisogna anche non concatenarne due.

## 4. La finestra rotta, e perché la accettiamo

Questa è una **modifica di forma su una chiave esistente**, non un'aggiunta:
qualunque ordine fra BE e DB lascia una finestra in cui il Preventivo non
renderizza. Al contrario del cantiere di agosto, dove il BE poteva andare avanti
da solo perché la chiave era nuova e il template la ignorava.

* **BE per primo** (com'è ora): la v3 itera un dict → il render fallisce.
* **DB per primo**: la v4 legge `indirizzi.consegna` che ancora non arriva →
  `StrictUndefined` → il render fallisce.

Abbiamo scelto **BE per primo**, per due ragioni. Il fallimento è **rumoroso**
in entrambi i casi — nessun PDF sbagliato può uscire, ed è esattamente il
comportamento per cui il §2 chiedeva di togliere i `.get()`. E non scriviamo un
ramo di compatibilità che accetti tutte e due le forme: sarebbe codice che nasce
già da rimuovere, e non siamo in produzione.

Quindi: **applicate quando vi torna comodo**, sapendo che nel frattempo la
stampa del preventivo è ferma. Se la finestra vi crea problemi ditelo e
sincronizziamo il merge.

## 5. Cosa NON chiediamo

* **Nessun tocco agli altri cinque template.** `ord-ven`, `contratto`,
  `off-comm` e `ddt-ven` sono già sulla forma unica e il loro contesto non
  cambia; la `fattura` resta com'è (§1).
* **Nessuna modifica allo snapshot né alle `fn_snapshot_indirizzo*`**: sono la
  fonte canonica e sono giuste.
* **Nessuna rinomina di `codice_interno`.** La questione `test` → `preventivo`
  è chiusa e resta chiusa: §9.4 del brief precedente, il lock è una policy.
* **Nessuna bonifica dei PDF già generati.** `valido_dal = current_date` come le
  altre volte: i preventivi emessi con la v3 restano com'erano, ri-renderizzabili
  sulla versione pinnata.
* **Nessun `btrim` difensivo**: §11.2, deciso il 2026-08-16.

## 6. Definizione di «fatto»

* [x] template Preventivo **v4** con il blocco a slot, v3 → OBSOLETA e ancora
      ri-renderizzabile — ⚠️ **scritto, si avvera col `migrate`**;
* [x] il blocco usa **accesso diretto** su ogni campo, con guardia **per campo**
      — chiude il §2 del brief di agosto **limitatamente all'area indirizzi**
      (vedi la correzione al §3 punto 1: righe e IVA restano su `.get()`);
* [x] un preventivo **senza** indirizzi non stampa la sezione (guardia esterna);
* [x] un preventivo **con** indirizzo di consegna, rigenerato, lo mostra sul PDF
      — **stampa preventivi testata da Tid il 2026-08-16**, dopo l'apply.

## 7. Una domanda per voi — risposta ricevuta: **un solo slot**

La domanda era se stampare tutti e quattro gli slot ammessi dall'ambito. Tid ha
deciso: *«la stampa è identica agli altri documenti»*, quindi **solo
`consegna`**, e il dato conferma — 46 snapshot indirizzo in tutto il database,
**46 su 46 di tipo `CON`**; sui preventivi 12 su 12.

⚠️ **Quindi il blocco del §3 è superato**: il `for` sulle quattro etichette non
si fa, e la posizione non è una sezione a sé ma il **riquadro «Cliente»**, dove
stanno gli altri cinque template. Il §3 resta qui come storia della richiesta,
non come cosa da implementare — chi ci mette mano guardi i changeSet.

Il contesto continua a esporre tutti e quattro gli slot: seguono la whitelist
dell'ambito, ed è il template a scegliere cosa stampare (§11.1 del brief
precedente). Nessuna modifica BE.

## 8. Risposta del DB (2026-08-16) e chiusura

> Scritta dal team DB su `dev/db-tid` e **fusa qui il 2026-08-16**, come loro
> stessi avevano chiesto: in questo cantiere cambiava il lato che lavorava, non
> il soggetto. Il documento DB separato è stato ritirato dopo la fusione — il
> record dell'implementazione sono i due changeSet in
> `db/changelog/migrations_v2/80_data/changelog/20260816-01…` e `-02…`.

### 8.1 Cosa è stato scritto

`20260816-01` crea la **bozza v4** dalla v3 pubblicata, `20260816-02` la
pubblica (`valido_dal = current_date`, v3 → OBSOLETA e ri-renderizzabile). Due
modifiche e non una: **entra** il blocco `indirizzi.consegna` nel riquadro
Cliente, **esce** la sezione «Indirizzi documento» della forma v1 — lasciarla
non solo pianterebbe il render (è lei a iterare il dict) ma, convertita,
stamperebbe l'indirizzo **due volte**. Sostituzioni ancorate a testo che deve
comparire esattamente una volta: se qualcuno ha ritoccato il template il
`migrate` si ferma invece di pubblicare una versione identica alla vecchia.

**Diff v3 → v4: `+20` righe e `−20`, nient'altro.** Provato in transazione poi
annullata: bozza creata, pubblicazione eseguita, v3 → `OBSOLETA`, v4
`PUBBLICATA dal 2026-08-16`.

Blocco renderizzato con `StrictUndefined` su sei casi scelti **sui valori reali
dei 12 snapshot dei preventivi**, non su casi inventati — ed è la verifica più
forte della mia (§3):

| Caso | Esito |
| --- | --- |
| completo | `Luogo di consegna: · Azienda PG Test Natura · PIAZZA PRIMO MAGGIO 77 · 75025 POLICORO (MT) · IT` |
| senza `intestazione` (3 su 12) | nessuna riga vuota |
| senza `cap`/`citta`/`prov` (5 su 12) | riga geografica non stampata |
| solo `display` | ramo `elif` esercitato |
| `cap` mancante e `citta` presente | `ROMA (RM)` — **non** `None ROMA` |
| nessun indirizzo | sezione non stampata |

⭐ **Perché la guardia è per campo e non per slot**, misurato: sui 12 snapshot
`intestazione` è valorizzata su **9**, `cap`/`citta`/`prov` su **7**, `via` e
`stato` su 12. Con la sola guardia sullo slot, **3 preventivi avrebbero stampato
una riga vuota e 5 una riga tronca**.

### 8.2 🔴 Il rilievo sul `.get()`: accolto, ed era il più utile dei due

La frase «il Preventivo è l'ultimo template a leggere con `.get()`» era falsa, e
il modo in cui era falsa è peggio del contenuto: **dichiarava chiusa una cosa
aperta**. Chi l'avesse riletta fra un anno avrebbe creduto che il presidio del
§2 di agosto fosse applicato ovunque, mentre vale per la sola area indirizzi.
Corretta al §3 e al §6, e anche nel §11.3 del brief precedente da cui era
partita.

Se il `.get()` su righe e IVA va tolto è un **cantiere suo**, con la sua misura:
lì un nome sbagliato non stampa un indirizzo monco ma una riga d'ordine vuota,
che su un documento con importi è un difetto di un'altra categoria. Non lo
apriamo qui e non lo lasciamo implicito: è annotato, non pianificato.

### 8.3 Il guard troppo largo: la lezione vale anche per me

Il DB aveva messo nel dry-run un presidio «nessun `.get()` nell'HTML
risultante», che è fallito sul `r.get("ordine")` delle righe — fuori perimetro
per il §5 di questo brief — e l'ha sostituito con due asserzioni precise (la
forma nuova c'è, la vecchia non c'è più). ⭐ *Un presidio che verifica più di
quanto il cantiere promette non è più sicuro: è solo più fragile.*

È lo stesso errore della frase di §8.2, in un'altra veste: **un guard che
sconfina e una frase che sopravvaluta dicono entrambi «ho chiuso più di quanto
ho chiuso»**. Il primo lo scopri subito perché il dry-run si pianta, la seconda
resta scritta per un anno — motivo in più per correggerla invece di sfumarla.

### 8.4 Fusione dei due brief — fatta

Il DB chiedeva giustamente di **fondere i due documenti in uno**: qui cambiava
il lato che lavorava, non il soggetto. Rimandata a cantiere chiuso apposta, così
il documento unico nascesse completo invece di essere fuso due volte — ed è
questo file.

`brief-db-template-preventivo-slot-indirizzi.md` è stato **ritirato** dopo il
travaso (ok di Tid, 2026-08-16): tutto ciò che conteneva vive qui — i due
changeSet e cosa fanno (§8.1), le ancore fail-loud, il diff, la tabella dei sei
casi di render, i due rilievi al BE (§8.2, §8.3). Il record vero
dell'implementazione restano i changeSet YAML in repo, e la storia del file è
nel git log.

⚠️ **Una coda che il ritiro non può togliere, ed è giusto sapere.** I due
changeSet scrivono il nome del file ritirato **dentro il dato**:

```text
20260816-01: c_brief CONSTANT text := 'brief-db-template-preventivo-slot-indirizzi.md';
             → finisce in template_documenti_versioni.meta->>'brief'
20260816-02: lo rilegge per trovare la bozza da pubblicare
```

Sono **già applicati**, quindi il marcatore resta quello: un changeSet eseguito
non si riscrive senza rompere il checksum Liquibase, e non vale una migrazione
nuova per allineare una stringa descrittiva. Chi interroghi la riga della v4 e
cerchi quel documento **non lo trova**: per questo il redirect è scritto nel
banner in testa a questo file. Se un domani si preferisce il puntamento esatto,
la strada onesta è un changeSet che aggiorna `meta`, non la modifica di uno
applicato.

---

## 9. Chiusura (2026-08-16)

Cantiere aperto e chiuso in giornata, dai due lati.

| Lato | Cosa | Esito |
| --- | --- | --- |
| BE | builder Preventivo sulla forma unica, `context_version` 2, test | ✅ 1771 verdi |
| DB | changeSet `20260816-01` + `-02`, v4 pubblicata, v3 → OBSOLETA | ✅ applicati |
| Tid | **stampa preventivi testata** | ✅ |

**Cosa lascia dietro, oltre al PDF giusto:**

* la **forma unica** degli indirizzi vale ora su **5 builder su 6**. Fuori resta
  la sola `fattura`, con la sua stringa già composta: scelta consapevole
  (indirizzo fiscale unico), annotata in §11.3 del brief precedente e **non** un
  debito di questo cantiere;
* il presidio del `.get()` è applicato **all'area indirizzi di tutti e sei** i
  template. Su **righe e IVA** resta ovunque: cantiere a sé, annotato e non
  pianificato — lì un nome sbagliato non stampa un indirizzo monco ma una riga
  d'ordine vuota, che su un documento con importi è un'altra categoria di
  difetto (§8.2);
* due lezioni gemelle, che è la ragione per cui questo documento è più lungo
  della modifica che descrive: **un guard che sconfina** (§8.3) e **una frase
  che sopravvaluta** (§8.2) dicono la stessa cosa — «ho chiuso più di quanto ho
  chiuso». Il primo si pianta nel dry-run entro un minuto, la seconda resta
  scritta per un anno.
