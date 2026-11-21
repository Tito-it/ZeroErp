# Brief BE → DB — l'indirizzo c'è, ma tre PDF su sei non lo stampano

> 🟢 **CHIUSO — 2026-08-16.** L'ultima voce aperta era guardare un PDF, e Tid
> l'ha guardato: anteprima dell'ordine **ORD0018247** (creato lo stesso giorno,
> indirizzo di consegna completo), **indirizzo corretto a video**. Prima di
> quella prova il blocco era già stato renderizzato qui su tutti e 17 i
> documenti con un indirizzo congelato — 17 su 17, zero render falliti, zero
> righe vuote (§10.2) — quindi la conferma visiva chiude una verifica, non un
> dubbio. Dettaglio della chiusura in §10.4.
>
> **I due residui del §10.5 e §10.6 sono chiusi il 2026-08-16 senza scrivere
> codice**, entrambi con decisione di Tid — motivazioni in **§11**:
>
> * §10.5 — **non si restringe.** Gli slot seguono `config.tipi_indirizzi_allowed`,
>   cioè il pannello che l'operatore vede: toglierli reintrodurrebbe il difetto
>   di partenza su una casella invece che su un documento (§11.1);
> * §10.6 — **non si bonifica.** Le 4 righe sono dati di test e le tre strade di
>   scrittura ripuliscono tutte gli spazi dal 2026-07-31: un documento nuovo ha
>   la provincia giusta (§11.2).
>
> ⚠️ **Resta aperto un residuo che né §10.5 né §10.6 nominavano**: la forma unica
> promessa dal §7.2 del brief precedente vale su **4 builder su 6** — preventivo
> e fattura hanno ancora la loro. Il preventivo si allinea (§11.3), la fattura è
> una scelta a sé.

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-05.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** ordini, contratti e offerte **congelano** l'indirizzo del documento e
poi non lo stampano. Il contesto PDF ora glielo passa (fatto, lato BE): mancano
le versioni di template che lo rendano. Più la rinomina del template Preventivo,
che si chiama ancora `test`.
**Nasce da:** vostra risposta del 2026-08-04 al brief
[template Preventivo / chiavi snapshot](brief-db-template-preventivo-indirizzi.md),
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
* [x] un ordine con indirizzo di consegna, rigenerato, lo mostra sul PDF —
      **fatto il 2026-08-16** da Tid, sull'ordine `ORD0018247`: indirizzo
      corretto a video (§10.4). Il render del blocco era già stato provato qui
      su tutti e 17 i documenti con indirizzo congelato (§10.2);
* [ ] ~~`template_documenti.codice_interno` del Preventivo = `preventivo`~~
      **non si fa**, §9.4.

---

## 10. Ricontrollo di chiusura (DB, 2026-08-16)

> Undici giorni dopo l'apply, per rispondere a una domanda semplice: che cosa
> resta davvero aperto. Tutto quanto segue è letto oggi dal database di
> sviluppo, non ricordato dal §9.

### 10.1 Lo stato a DB non si è mosso

| Template | Versione pubblicata | `valido_dal` | Cita `indirizzi.consegna` | Precedente |
| --- | --- | --- | --- | --- |
| `ord-ven` | v4 (id 264) | 2026-08-05 | sì | v3 OBSOLETA, ancora attiva |
| `contratto` | v3 (id 43) | 2026-08-05 | sì | v2 OBSOLETA, ancora attiva |
| `off-comm` | v3 (id 265) | 2026-08-05 | sì | v2 OBSOLETA, ancora attiva |

I tre template che il §6 chiedeva di non toccare (`test`, `ddt-ven`, `fattura`)
sono fermi dove erano: stessa versione pubblicata, stesso `valido_dal`.

### 10.2 Il blocco è stato renderizzato davvero, su tutti i documenti veri

Il §9.6 lasciava la prova del render al BE perché «il DB non renderizza». Vero
per il PDF; **non** per il blocco Jinja, che si può provare da qui. Fatto oggi,
in sola lettura, senza toccare nulla:

* il template è quello **pubblicato a DB** (`html_template` delle versioni 264,
  43, 265), non una copia;
* il contesto è costruito con la funzione **vera del BE**
  (`shape_indirizzi_context`, importata dal sorgente) sugli **snapshot reali**
  letti dalle tabelle `vendite.*_indirizzi`;
* il motore è Jinja con `StrictUndefined`, cioè lo stesso presidio del §4: una
  chiave sbagliata avrebbe fatto fallire il render invece di stampare vuoto.

| Dominio | Documenti con indirizzo | Render riusciti | Righe vuote |
| --- | --- | --- | --- |
| `ord-ven` | 15 | **15** | 0 |
| `contratto` | 1 | **1** | 0 |
| `off-comm` | 1 | **1** | 0 |

Esempi di ciò che esce, presi ai due estremi del §9.2 — l'ordine completo e
quello senza `intestazione`, che era il caso a rischio:

```text
ORD0005174  Luogo di consegna: | Azienda PG Test Natura | PIAZZA PRIMO MAGGIO 77 | 75025 POLICORO (MT) | IT
ORD0000608  Luogo di consegna: | PIAZZA PRIMO MAGGIO, 77/A | 75025 POLICORO (MT) | IT
```

La scelta del §9.2 — guardia **per campo** e non solo sullo slot — regge sui
dati: i 9 ordini senza `intestazione` non stampano nessuna riga vuota, e con lo
snippet del §3 così com'era ne avrebbero stampata una.

### 10.3 Le tre versioni nuove non portano altra superficie

Confrontate riga per riga con la versione che sostituiscono: la differenza è
**solo** il blocco aggiunto, una pura inserzione, e il `css_template` è
identico byte per byte (stesso md5). Non c'è nient'altro di nuovo da provare
oltre a ciò che il §10.2 ha già provato.

### 10.4 L'ultima voce: guardare un PDF — fatta, e il PDF è giusto

Alla misura di stamattina **nessun documento risultava generato in tutto il
database dal 2026-08-03**: le tre versioni nuove — e neppure il Preventivo v3
del brief precedente, né il DDT v3 — avevano prodotto un solo documento
persistito.

⚠️ **E il database non poteva dire se qualcuno avesse già guardato.**
L'anteprima (`anteprima_documento`) renderizza e **non persiste**: niente riga,
niente evento. La misura diceva «nessuno ha *generato*», non «nessuno ha
*visto*» — due cose diverse, e questa distinzione è il motivo per cui la voce è
rimasta aperta undici giorni senza che si potesse dire se lo fosse davvero.

**Esito (2026-08-16).** Tid ha aperto l'anteprima dell'ordine `ORD0018247` e
l'indirizzo è corretto. L'ordine è nato lo stesso giorno, in DRAFT, con uno
snapshot di consegna completo e pulito:

```json
{"intestazione": "Azienda ConTutto", "via": "VIA CAVALIERE ANTONIO OLIVIERI 4",
 "cap": "62014", "citta": "CORRIDONIA", "prov": "MC", "stato": "IT",
 "display": "VIA CAVALIERE ANTONIO OLIVIERI, 4/C"}
```

> ℹ️ **Perché l'anteprima basta come prova, e cosa non prova.** Ripercorre gli
> stessi passi della generazione tranne l'ultimo: risolve la **versione
> pubblicata** (quindi la v4, non un template a mano), costruisce il contesto
> con lo **stesso builder**, e renderizza con lo **stesso motore**. Quello che
> non esercita è la sola persistenza — riga in `documenti_generati`, scrittura
> su storage, evento — che non è materia di questo brief. Coerentemente, in
> `documenti_generati` **non c'è traccia** di questa prova, ed è atteso.

Restano i due soggetti buoni se un giorno serve rifare il giro sui casi
scomodi, che questo ordine non copre: `ORD0000608` (senza `intestazione`, il
caso che il §9.2 ha risolto) e `ORD0000046` (con la provincia riempita a
spazi, §10.6).

### 10.5 Residuo BE — il §9.3 non è stato applicato

I tre context builder dichiarano ancora gli stessi slot del 2026-08-05:
`ord-ven` due (`CON`, `FATT`), `contratto` tre, `off-comm` quattro. I template
ne stampano **uno solo**, `consegna`.

> ⚠️ **E la misura del §9.3 va corretta: non era «tutto il database».** Contava
> le sole quattro tabelle di questo cantiere. Rifatta oggi su tutte e sei:

| Dominio | CON | FATT | RES |
| --- | --- | --- | --- |
| `ddt` | 16 | — | — |
| `ordini` | 15 | — | — |
| `preventivi` | 12 | — | — |
| `contratti` | 1 | — | — |
| `offerte` | 1 | — | — |
| **`fatture`** | 4 | **6** | **2** |

Le righe `FATT` e `RES` delle fatture esistono dal **2026-07-31**, cioè erano
già lì quando il §9.3 ha scritto «un solo slot è mai stato popolato». La frase
era falsa già allora, per un perimetro di misura troppo stretto. Resta vero che
nei **quattro domini di questo brief** l'unico slot mai popolato è `consegna`:
la raccomandazione «restringete» non è sbagliata per loro, ma non poggia più su
«nessuno usa gli altri slot», perché le fatture li usano.

> ✅ **Deciso (Tid, 2026-08-16): non si restringe.** Gli slot seguono la
> whitelist che il pannello FE legge a runtime — toglierli farebbe sparire in
> silenzio un indirizzo che l'operatore può già inserire. Motivazione in §11.1.

### 10.6 Trovato per strada, fuori perimetro: 4 provincie riempite a spazi

Quattro snapshot congelano `prov` con il riempimento a spazi di un
`character(10)` — sul PDF uscirebbe `(AV        )` invece di `(AV)`:

| Tabella | Documento | Congelato il |
| --- | --- | --- |
| `ddt_indirizzi` | ddt 91, 92 | 2026-07-12 |
| `ddt_indirizzi` | ddt 521 | 2026-07-25 |
| `ordini_indirizzi` | ordine 55 (`ORD0000046`) | 2026-07-26 |

Sono **tutti anteriori al 2026-07-31**, quando `fn_snapshot_indirizzo` ha
adottato `NULLIF(btrim(...))` su ogni valore proprio per questo. Non è un
difetto vivo: è dato vecchio, congelato prima del rimedio, e riguarda anche il
DDT che stampa l'indirizzo da luglio. Si corregge a mano con un `UPDATE` di
`btrim` su quattro righe, oppure si lascia — **non è stato toccato**, serve una
decisione di Tid.

> ✅ **Deciso (Tid, 2026-08-16): si lascia.** Motivazione e verifica in §11.2 —
> grazie per l'offerta di preparare l'`UPDATE`, non serve.

---

## 11. Chiusura BE dei due residui (2026-08-16)

> Risposta al §10.5 e al §10.6. Nessuno dei due si chiude scrivendo codice, e in
> un caso la ragione è che il codice **non va** scritto: vale la pena metterla
> per iscritto qui, perché è l'unica difesa contro qualcuno che fra sei mesi
> rilegge il §9.3 e lo applica.

### 11.1 §10.5 — non si restringe, e la ragione non è la pigrizia

Confermato lo stato che avete letto: `ord-ven` dichiara `("CON", "FATT")`,
`contratto` `("CON", "FATT", "FORNITURA")`, `off-comm` tutti e quattro. I
template ne stampano uno, `consegna`.

**Restringere reintrodurrebbe il difetto da cui è nato il cantiere.** Quei
codici non sono un elenco arbitrario: sono il mirror statico di
`config.tipi_indirizzi_allowed` per ambito — la stessa whitelist che il
**pannello FE legge a runtime** (`IndirizziDocumentoRepositoryMixin.list_tipi_indirizzo_ammessi`).
Oggi un operatore apre un ordine e può congelare un indirizzo `FATT`, perché
l'app glielo offre. Con il builder ristretto a `CON` quel dato verrebbe salvato
e poi **lasciato cadere in silenzio** prima della stampa: è alla lettera la
diagnosi del §1 di questo brief — dato raccolto e mai consegnato a valle —
applicata a uno slot invece che a un dominio. Il difetto sarebbe anche più
difficile da vedere del primo, perché riguarderebbe un solo campo.

**La vostra correzione del §10.5 toglie anche la base empirica.** «Un solo slot
mai popolato» era falsa già quando è stata scritta. Quel che resta della misura
— «in questi quattro domini nessuno li ha ancora usati» — è un'osservazione
sull'**anzianità del dato**, non un argomento sulla forma: i quattro domini
hanno gli indirizzi da luglio, le fatture li hanno da fine luglio e usano già
tre slot su quattro.

**Il risparmio sarebbe nullo, il costo no.** Uno slot vuoto è `None` nel
contesto e un `{% if %}` che non scatta nel template. Toglierlo cambia la forma
del contesto → cambia il `context_hash` → tocca il dedup dei documenti già
generati, per zero beneficio. Va anche contro il disegno esplicito del BB:
`INDIRIZZO_SLOT_BY_CODICE` è dichiarata mappa **completa** apposta, con il
commento «se un ambito domani ne ammette uno nuovo, lo slot ha già un nome e
nessuno deve ricordarsi di aggiungerlo qui».

Resta vero e prezioso il vostro allarme di fondo — superficie che nessuno
verifica invecchia. Qui però la superficie non è dichiarata a caso: è verificata
da chi la può verificare davvero, cioè la configurazione.

### 11.2 §10.6 — si lascia, e un documento nuovo è già corretto

Verificate tutte e tre le strade da cui uno snapshot può nascere: **puliscono
tutte**, quindi il difetto non può ricomparire.

| Strada | Ripulisce |
| --- | --- |
| Picker su indirizzo di **ruolo** (`script.fn_snapshot_indirizzo`) | ✅ `NULLIF(btrim(...))` su ogni valore, dal 2026-07-31 |
| Picker su indirizzo di **soggetto** (`fn_snapshot_indirizzo_soggetto`) | ✅ identica alla gemella, stesso fix |
| **Una-tantum** digitato (BE, `_clean_snapshot`) | ✅ `strip()` per valore, con scarto delle stringhe vuote |

Le 4 righe restano sbagliate e l'unico effetto visibile è che ristampando
proprio quei documenti (DDT 91, 92, 521 e `ORD0000046`) esce `(AV        )`.
Sono dati di test, il progetto non è in produzione: si accetta sapendolo.

⚠️ **Non abbiamo aggiunto un `btrim` difensivo nel BE**, che pure sarebbe una
riga in `shape_indirizzi_context`. Maschererebbe la qualità del dato su un
difetto **già chiuso alla sorgente**, e renderebbe invisibile la prossima
colonna `character(n)` che dovesse entrare nello snapshot senza `btrim`. Il
posto giusto per quel presidio è dove già sta.

> ℹ️ Nota per il §10.4: `ORD0000046` resta uno dei due «soggetti buoni» per
> rifare il giro sui casi scomodi, e ora si sa **perché** è scomodo — lo è
> ancora, per scelta.

### 11.3 Il residuo che nessuno dei due paragrafi nominava

Il §7.2 del brief precedente prometteva **una** forma per l'indirizzo, chiamata
da tutti e sei i builder. Oggi la chiamano in quattro:

| Builder | Forma nel contesto |
| --- | --- |
| ordine, contratto, offerta, ddt | `indirizzi.consegna.via` — slot con nome, chiavi fisse ✅ |
| **preventivo** | `indirizzi` è una **lista da scorrere**: `{% for ind in indirizzi %}`, poi `ind.snapshot.via` |
| **fattura** | `cliente.indirizzo` — **stringa già composta**, non i componenti |

Le tre forme che vi preoccupavano esistono ancora, e la promessa è a metà. Le
due ragioni scritte nel codice per non averle mosse **non sono la stessa cosa**:

* il **preventivo** non si è mosso per stabilità del `context_hash` dei
  documenti già generati. Questa ragione **si scioglie**: sono documenti di
  test e non siamo in produzione (decisione di Tid, 2026-08-16). **Si allinea** —
  arriva un brief dedicato, perché serve una versione nuova del template
  Preventivo: la lista diventa slot, non è una rinomina di chiavi. In quella
  riscrittura si chiude anche il `.get()` del §2 **sull'area indirizzi**: il
  Preventivo è l'ultimo dei sei a leggere l'indirizzo in modo che un nome
  sbagliato stampi vuoto invece di far fallire il render;

  > 🔴 **Correzione (2026-08-16, rilievo del DB).** Questa riga diceva che con
  > il Preventivo si chiudeva «l'ultima voce» del §2 e che era «l'unico template
  > rimasto» a leggere con `.get()`. **Falso, e falso in modo pericoloso**:
  > dichiarava chiusa una cosa aperta. Il `.get()` resta su **righe e IVA** in
  > tutti i template — `off-comm` 37, `ord-ven` 29, `contratto` 21, `ddt-ven` 11
  > (misurato il 2026-08-16) — e sul Preventivo stesso ne restano ~20 fuori dal
  > blocco indirizzi. Il §2 si chiude qui **solo per l'area indirizzi**; il
  > resto è un cantiere a sé, con la sua misura, perché lì un nome sbagliato non
  > stampa un indirizzo monco ma una riga d'ordine vuota. Annotato, non
  > pianificato.
* la **fattura** non è un residuo bloccato da dati. Non ha slot da stampare: ha
  **un** indirizzo che conta, quello fiscale, e il template lo rende già
  composto su una riga. Uniformarla significa ridecidere come si compone quella
  riga su un documento fiscale — si può fare ed è più coerente, ma è una scelta
  a sé, non un debito di questo cantiere. Annotata, non pianificata.
