# Brief BE → DB — l'indirizzo c'è, ma tre PDF su sei non lo stampano

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-05.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** ordini, contratti e offerte **congelano** l'indirizzo del documento e
poi non lo stampano. Il contesto PDF ora glielo passa (fatto, lato BE): mancano
le versioni di template che lo rendano. Più la rinomina del template Preventivo,
che si chiama ancora `test`.
**Nasce da:** vostra risposta del 2026-08-04 al brief
[template Preventivo / chiavi snapshot](../work-done/brief-db-template-preventivo-indirizzi.md),
§7. Le due domande che ci avete rimandato hanno risposta lì; questo è il seguito
operativo, deciso da Tid il 2026-08-05.

---

## 1. Il fatto, misurato

| Dominio | Snapshot persistito | Contesto PDF | Template |
| --- | --- | --- | --- |
| preventivo | 11 righe | `indirizzi` (lista) | area indirizzi ✅ v3 |
| ddt-ven | 16 righe | `indirizzi.consegna.*` | area consegna ✅ |
| fattura | 0 righe | `cliente.indirizzo` (stringa) | riga cliente ✅ |
| **ord-ven** | **14 righe** | ✅ **`indirizzi.*` (dal 2026-08-05)** | ❌ **manca l'area** |
| **contratto** | **1 riga** | ✅ **`indirizzi.*` (dal 2026-08-05)** | ❌ **manca l'area** |
| **off-comm** | 0 righe | ✅ **`indirizzi.*` (dal 2026-08-05)** | ❌ **manca l'area** |

Non era una scelta di prodotto: il dato veniva raccolto e lasciato cadere dal
context builder, quindi il template non avrebbe potuto stamparlo nemmeno
volendo. Tid ha deciso il 2026-08-05: **si stampa**, su tutti e tre.

## 2. Cosa abbiamo già fatto (BE, in questo branch)

I tre context builder ora espongono `indirizzi`, con la **forma del DDT**
generalizzata ed estratta a building block condiviso
(`_indirizzi_documento_helpers.shape_indirizzi_context`, regola del 2, ok Tid).

```python
"indirizzi": {
  "consegna": {                       # None se il documento non ha quello slot
    "intestazione": "...", "via": "...", "cap": "...", "citta": "...",
    "prov": "...", "stato": "...", "display": None,
    "email": None, "telefono": None, "note": None,
    "display_compatto": "Intestazione — via, cap citta, prov",
  },
  "fatturazione": None,
}
```

Tre proprietà che contano per voi:

1. **Gli slot ci sono sempre**, anche quando il documento non ha quell'indirizzo
   (valore `None`). È la ragione per cui il template può usare l'**accesso
   diretto** — vedi §4;
2. i nomi degli slot sono semantici e uguali su tutti i domini (`consegna` =
   `CON`, `fatturazione` = `FATT`, `fornitura` = `FORNITURA`, `residenza` =
   `RES`), per ambito secondo `config.tipi_indirizzi_allowed`;
3. `display_compatto` è pre-composto dal BE (mirror del FE
   `formatSnapshotDisplay`): una riga sola già pronta, se preferite quella.

Slot per dominio, così sapete cosa avete a disposizione:

| Template | Slot disponibili nel contesto |
| --- | --- |
| `ord-ven` | `consegna`, `fatturazione` |
| `contratto` | `consegna`, `fatturazione`, `fornitura` |
| `off-comm` | `consegna`, `fatturazione`, `fornitura`, `residenza` |

⚠️ **`context_version` è passata a 2** per i tre domini (era 1). Il DDT resta a
2 e il suo contesto è **invariato byte per byte** — verificato confrontando la
vecchia proiezione con la nuova su un DDT reale (id 82), chiavi e ordine
compresi: la ristampa fedele dei DDT già generati non si muove.

## 3. Cosa chiediamo — tre versioni nuove

Una versione nuova per `ord-ven`, `contratto` e `off-comm` (le attuali sono
PUBBLICATE e il vostro trigger le protegge, giustamente), con l'area indirizzi.
Blocco proposto, da adattare allo stile di ciascun template:

```jinja
{% if indirizzi.consegna %}
  <section class="section">
    <div class="label">Indirizzo di consegna</div>
    <div class="box">
      {{ indirizzi.consegna.intestazione }}<br>
      {{ indirizzi.consegna.via }}<br>
      {{ indirizzi.consegna.cap }} {{ indirizzi.consegna.citta }}
      {%- if indirizzi.consegna.prov %} ({{ indirizzi.consegna.prov }}){% endif %}
      {% if indirizzi.consegna.stato %}<br>{{ indirizzi.consegna.stato }}{% endif %}
    </div>
  </section>
{% endif %}
```

Stesso blocco per `fatturazione` dove ha senso (l'indirizzo di fatturazione su
una conferma d'ordine è informazione utile; su un'offerta forse no — decidete
voi, il contesto ce l'ha).

## 4. La differenza che vi chiediamo di cogliere: niente `.get()`

Il blocco sopra usa **`indirizzi.consegna.via`**, non `s.get("via")`. È il
presidio del §2 del brief precedente, che avete sottoscritto, e qui è
applicabile **per costruzione** perché il BE garantisce le chiavi:

* se domani qualcuno rinomina una chiave dello snapshot, il render **si pianta**
  in sviluppo invece di stampare un indirizzo monco;
* è esattamente come il difetto del Preventivo è sopravvissuto fino al
  2026-08-04: `.get()` trasformava la chiave sbagliata in stringa vuota, e il
  PDF usciva plausibile.

Il `{% if indirizzi.consegna %}` esterno resta necessario — quello sì — perché
lo slot può essere `None`: è la sola difesa che serve.

## 5. La rinomina: `test` → `preventivo`

Il template che produce i preventivi ha `codice_interno = 'test'` (vostra
segnalazione del 2026-08-04, confermata: `codice` = «Preventivo», `descrizione`
= «Preventivo», v3 PUBBLICATA). Tid ha deciso: **si rinomina in `preventivo`**,
la famiglia dei codici nudi già in uso (`contratto`, `fattura`).

✅ **Verificato che non rompe nulla lato BE:** nessun percorso Python risolve un
template per `codice_interno` — la risoluzione passa da `sorgente_tipo_id` /
`context_builder_code`. `codice_interno` è esposto solo come campo di lista e
ricerca nelle API admin del motore documentale. Il rischio «rinomina che
sfila un binding» qui non c'è.

## 6. Cosa NON chiediamo

* **Nessuna modifica ai template `test`(preventivo), `ddt-ven`, `fattura`**: le
  loro aree indirizzi funzionano. Il preventivo resta con `.get()` fino alla
  prossima riscrittura del suo blocco — non vale una v4 solo per quello;
* **nessuna modifica a `fn_snapshot_indirizzo`** né allo shape canonico;
* **nessuna bonifica dei PDF già generati**: la ristampa fedele li ri-renderizza
  con la versione pinnata, ed è il comportamento voluto.

## 7. Definizione di «fatto»

* [ ] `ord-ven`, `contratto`, `off-comm`: versione nuova PUBBLICATA con l'area
      indirizzi, le precedenti a OBSOLETA e ancora ri-renderizzabili;
* [ ] i tre blocchi usano l'accesso diretto (`indirizzi.consegna.via`), non
      `.get()`, con il solo `{% if indirizzi.<slot> %}` a difesa;
* [ ] un ordine con indirizzo di consegna, rigenerato, lo mostra sul PDF;
* [ ] `template_documenti.codice_interno` del Preventivo = `preventivo`.

## 8. Una domanda per voi

Gli slot che il contesto espone seguono `config.tipi_indirizzi_allowed`, ma
**quali stampare** è una scelta di documento, non di configurazione: su
un'offerta commerciale ha senso l'indirizzo di residenza? Se la risposta è «solo
consegna e fatturazione ovunque», ditecelo e restringiamo la dichiarazione nei
builder — meglio un contesto che espone tre slot usati che quattro di cui uno
non si stampa mai.

---

## 9. Risposta del DB (2026-08-05)

> Scritta dal team DB su `dev/db-tid`, **migrazioni applicate il 2026-08-05**.
> Due delle vostre quattro voci del §7 sono fatte; una cade contro una regola
> voluta; la quarta tocca a voi. La vostra domanda del §8 ha una risposta
> misurata.

### 9.1 Fatto — le tre versioni, applicate

**`20260805-09` e `20260805-10` sono EXECUTED** sul database di sviluppo
(2026-08-05, 10:52). Il primo crea le bozze con l'area consegna, il secondo le
pubblica via `fn_pubblica_template_documento_versione`, che manda da sola le
precedenti a OBSOLETA lasciandole ri-renderizzabili.

Stato letto dal database dopo l'apply, non previsto prima:

| Template | Versione nuova | `valido_dal` | Precedente |
| --- | --- | --- | --- |
| `ord-ven` | **v4** PUBBLICATA (id 264) | 2026-08-05 | v3 → OBSOLETA |
| `contratto` | **v3** PUBBLICATA (id 43) | 2026-08-05 | v2 → OBSOLETA |
| `off-comm` | **v3** PUBBLICATA (id 265) | 2026-08-05 | v2 → OBSOLETA |

Tutte e tre citano `indirizzi.consegna` e portano il marker
`meta->>'brief'` di questo cantiere.

Il contratto aveva una v3 in BOZZA dal 2026-05-28, e prima di toccarla abbiamo
verificato che fosse **identica alla v2 pubblicata** — stesso md5 su
`html_template` *e* su `css_template`. Era una copia intatta, non il lavoro a
metà di qualcuno: crearne una quarta avrebbe lasciato quella orfana per sempre.
Per questo il contratto pubblica una v3 e non una v4: **è quella bozza, riempita**
(id 43, lo stesso di prima).

`valido_dal = current_date`, quindi l'area vale dai documenti generati da
adesso: i PDF già emessi restano com'erano, come chiede il vostro §6.

**Verifiche dopo l'apply**, tutte sul database e non sulla carta:

| Controllo | Esito |
| --- | --- |
| i tre template che il §6 chiede di non toccare (`test`, `ddt-ven`, `fattura`) | **fermi**: stessa versione pubblicata e stesso `valido_dal` di prima |
| invariante «una sola PUBBLICATA attiva per template» | **0** template la violano |
| le OBSOLETE restano ri-renderizzabili (`attivo`) | **0** disattivate |
| 8 suite pgTAP su `documenti` | **tutte verdi**, zero variazioni prima/dopo |

> ℹ️ I due presidi fail-loud sono stati provati, non solo scritti. Simulando un
> template ritoccato (in una transazione poi annullata) l'ancora non combacia più
> e il migrate si ferma con «ancora trovata 0 volte invece di 1». Senza quel
> controllo una `replace` a vuoto avrebbe pubblicato una versione nuova identica
> alla vecchia: il registro avrebbe detto «fatto» e il PDF sarebbe rimasto senza
> indirizzo. Il secondo presidio è nel `-10`, che pubblica solo bozze che citano
> davvero `indirizzi.consegna` e fallisce se non ne pubblica esattamente tre.

### 9.2 🔴 Il blocco del §3 non era copiabile così com'era

Il vostro snippet stampa `{{ indirizzi.consegna.intestazione }}<br>` protetto
dal solo `{% if indirizzi.consegna %}`. Gli snapshot reali però **non hanno
tutti la stessa forma**:

| Dominio | righe | con `intestazione` valorizzata | chiavi presenti nello snapshot |
| --- | --- | --- | --- |
| `ord-ven` | 14 | **5** | cap, citta, display, intestazione, prov, stato, via |
| `contratto` | 1 | **0** | cap, citta, prov, stato, via *(niente `intestazione`)* |
| `off-comm` | 1 | 1 | display, intestazione, stato, via *(niente cap/citta/prov)* |
| `ddt-ven` | 16 | 4 | + email |

Voi garantite le **chiavi** — l'helper normalizza a `None` — ma non i **valori**.
Con la guardia sul solo slot, **9 ordini su 14 e l'unico contratto** avrebbero
stampato una riga vuota sotto «Luogo di consegna». Abbiamo quindi usato la forma
già in produzione sul `ddt-ven` v3, che guarda ogni campo per conto suo. Il
vostro §4 sull'accesso diretto è rispettato alla lettera: nessun `.get()`, solo
`indirizzi.consegna.via`.

> ℹ️ Il ramo `{% elif ... .display %}` che abbiamo tenuto è **oggi non
> esercitato**: `via` risulta valorizzata su 16 righe su 16 e non esiste un solo
> snapshot con `display` ma senza `via`. Lo teniamo perché è la forma del DDT e
> perché `display` è la versione libera di un indirizzo senza via strutturata,
> ma va saputo: se un giorno serve, va provato a mano.

### 9.3 La risposta al §8: sì, restringete

Avete chiesto se abbia senso esporre quattro slot. Misurato su tutto il
database:

| Dominio | CON | FATT | FORNITURA | RES |
| --- | --- | --- | --- | --- |
| `ddt-ven` | 16 | 0 | 0 | 0 |
| `ord-ven` | 14 | 0 | 0 | 0 |
| `contratto` | 1 | 0 | 0 | 0 |
| `off-comm` | 1 | 0 | 0 | 0 |

**Un solo slot è mai stato popolato: `consegna`, 32 righe su 32.** Perciò i tre
template stampano solo quello, e la risposta alla vostra domanda è sì:
restringete la dichiarazione nei builder. Un contesto che espone quattro slot di
cui tre non sono mai stati scritti da nessuno non è generosità, è superficie che
nessuno può verificare e che invecchia senza che ce ne accorgiamo.

> Correzione al vostro §1: `off-comm` non ha «0 righe» di snapshot, ne ha **1**.
> Cambia poco, ma non è più un dominio a copertura zero.

### 9.4 🔴 La rinomina `test` → `preventivo` non si fa, e non per pigrizia

È **vietata dal database**. Su `documenti.template_documenti` c'è un guard:

```text
trg_template_documenti_a10_lock_columns_upd
  BEFORE UPDATE OF codice_interno
  → script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')
```

Provato davvero, non dedotto leggendo il trigger: l'`UPDATE` solleva
*«Impossibile modificare il valore interno della colonna codice_interno»*. È la
convenzione del progetto — `codice_interno` immutabile, `codice` mutabile —
resa vincolante.

Il vostro §5 è corretto nel merito: abbiamo verificato anche il lato DB e
**nessuna funzione, vista o FK cita il literal `'test'`**, quindi la rinomina
sarebbe innocua *nei fatti*. Ma il lock è una policy generale, non una
dipendenza specifica, e aggirarlo per comodità creerebbe il precedente «il lock
si toglie quando dà fastidio». Decisione di Tid del 2026-08-05: **non si
rinomina**.

Va anche detto che non c'è nulla di sbagliato a video: `codice` e `descrizione`
di quel template dicono già «Preventivo». A dire `test` è solo la chiave
interna, che per costruzione nessuno legge.

Se un giorno la si vuole davvero cambiare, la strada onesta non è disabilitare
il trigger per una `UPDATE`, ma decidere se `codice_interno` dei template sia o
no una chiave di binding: se non lo è, il lock va tolto da quella tabella con un
changeSet che lo dichiara: una volta, per tutti, con la ragione scritta.

### 9.5 Cosa non era nostro

`context_version` non esiste come colonna in nessuna tabella del database: vive
dentro `context_json`, che scrivete voi. Il vostro ⚠️ del §2 è informativo, per
noi non c'era lavoro — e la garanzia che il contesto del DDT resti invariato
byte per byte resta vostra, non l'abbiamo riverificata.

### 9.6 Definizione di «fatto», aggiornata

* [x] `ord-ven`, `contratto`, `off-comm`: versione nuova PUBBLICATA con l'area
      indirizzi, le precedenti a OBSOLETA e ancora ri-renderizzabili —
      **applicato** con `20260805-09` e `-10`, verificato sul database (§9.1);
* [x] i tre blocchi usano l'accesso diretto, **con guardia per campo** e non
      solo sullo slot (§9.2);
* [ ] un ordine con indirizzo di consegna, rigenerato, lo mostra sul PDF —
      **tocca a voi**: il DB non renderizza, e questa è la verifica che chiude
      davvero il cantiere. I 14 ordini con snapshot di consegna sono i soggetti
      su cui provarlo; **9 di quei 14 non hanno `intestazione`** ed è proprio il
      caso in cui il blocco del §3, così com'era, avrebbe stampato una riga
      vuota: conviene rigenerare uno di quelli, non uno dei 5 completi;
* [ ] ~~`template_documenti.codice_interno` del Preventivo = `preventivo`~~
      **non si fa**, §9.4.
