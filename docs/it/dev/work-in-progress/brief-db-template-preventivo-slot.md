# Brief BE → DB — il template Preventivo passa dalla lista agli slot (l'ultimo dei sei)

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-16.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** il context builder del Preventivo ora espone `indirizzi` nella
**forma unica cross-dominio** — slot con nome, chiavi fisse — come ordini, DDT,
contratti e offerte. Serve una versione nuova del template Preventivo che la
legga. Era l'ultimo dominio a slot rimasto fuori.
**Nasce da:** §11.3 di
[brief-db-indirizzi-su-ordini-contratti-offerte.md](../work-done/brief-db-indirizzi-su-ordini-contratti-offerte.md),
chiuso lo stesso giorno. Decisione di Tid del 2026-08-16.
**Correlati:** [brief-db-template-preventivo-indirizzi.md](../work-done/brief-db-template-preventivo-indirizzi.md)
(§2 sul `.get()`, §7.2 sulla forma unica).

> 🔴 **C'è una finestra rotta, ed è voluta.** Fra il merge del BE e la
> pubblicazione della vostra versione nuova, **l'anteprima e la generazione del
> Preventivo falliscono il render**. Non è una svista: vedi §4.

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

1. **Niente `.get()`, mai.** È il presidio del §2 del primo brief, l'unica voce
   di quel cantiere rimasta aperta: il Preventivo è **l'ultimo template** a
   leggere in modo che un nome sbagliato stampi vuoto invece di far fallire il
   render. Questa riscrittura la chiude. Se preferite `display_compatto` per la
   riga geografica, va benissimo — è pensato per questo — purché resti accesso
   diretto.
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

* [ ] template Preventivo **v4 PUBBLICATA** con il blocco del §3, v3 → OBSOLETA
      e ancora ri-renderizzabile;
* [ ] il blocco usa **accesso diretto** su ogni campo, con guardia per campo
      (§2) — chiude anche il §2 del brief di agosto;
* [ ] un preventivo con indirizzo di consegna, rigenerato, lo mostra sul PDF;
* [ ] un preventivo **senza** indirizzi non stampa la sezione (guardia esterna).

## 7. Una domanda per voi

Il Preventivo è l'unico dei quattro domini a slot che ne ammette **quattro** e a
poterne stampare più di uno nello stesso PDF (gli altri tre stampano solo
`consegna`). Le quattro etichette del §3 sono una proposta scritta da chi non
compila preventivi: se sul documento reale «Punto di fornitura» e «Residenza»
non hanno senso accanto agli altri due, ditelo e le togliamo dal template —
resterebbero comunque negli slot del contesto, che seguono la whitelist
dell'ambito e non ciò che il template sceglie di stampare (§11.1).
