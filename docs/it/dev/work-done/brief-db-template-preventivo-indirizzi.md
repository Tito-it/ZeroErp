# Brief BE → DB — il template Preventivo legge lo snapshot indirizzo con le chiavi sbagliate

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** nel PDF del preventivo l'area indirizzi stampa **solo intestazione e
CAP**. Via, città e provincia spariscono — non perché manchino, ma perché il
template le cerca con nomi che nessuno produce.
**Trovato da:** Tid, in-app, 2026-08-04 («Azienda PG Test Natura / 75025»).
**Correlati:** [fn_snapshot_indirizzo](/dbzero/script/funzioni/fn_snapshot_indirizzo) ·
[fn_resolve_indirizzo_documento](/dbzero/script/funzioni/fn_resolve_indirizzo_documento) ·
[brief-design-indirizzi-documenti-vendita](../work-done/brief-design-indirizzi-documenti-vendita.md)

---

## 1. Il fatto, misurato

Lo snapshot a DB è **completo e corretto** (preventivo `PRV0000198`, letto oggi):

```json
{"cap": "75025", "via": "PIAZZA PRIMO MAGGIO 77", "prov": "MT",
 "citta": "POLICORO", "stato": "IT", "display": "PIAZZA PRIMO MAGGIO, 77/A",
 "intestazione": "Azienda PG Test Natura"}
```

Il template **Preventivo v2** (`template_documenti_versioni.id = 8`, PUBBLICATA)
lo legge così:

```jinja
{{ s.get("denominazione") or cliente.denominazione or "" }}
{% if s.get("indirizzo") %}<br>{{ s.get("indirizzo") }}{% endif %}
{% if s.get("cap") or s.get("comune") or s.get("provincia") %}
  <br>{{ s.get("cap") or "" }} {{ s.get("comune") or "" }}{% if s.get("provincia") %} ({{ s.get("provincia") }}){% endif %}
{% endif %}
{% if s.get("nazione") %}<br>{{ s.get("nazione") }}{% endif %}
```

| Il template cerca | Lo snapshot contiene | Esito a video |
| --- | --- | --- |
| `denominazione` | `intestazione` | vuoto → ripiega su `cliente.denominazione` |
| `indirizzo` | `via` (+ `display`) | **riga assente** |
| `comune` | `citta` | **vuoto** |
| `provincia` | `prov` | **vuoto** |
| `nazione` | `stato` | **riga assente** |
| `cap` | `cap` | ✅ l'unica che combacia |

Da qui esattamente ciò che si vede: la ragione sociale (dal ripiego) e il CAP.

**Lo snapshot canonico è il vostro**, e lo dichiarate voi nel `COMMENT` di
`fn_snapshot_indirizzo`: «compone lo snapshot canonico (intestazione, via, cap,
citta, prov, stato, display)». Il produttore è a posto: è il template a essere
rimasto sulla shape v1, pre-canonica.

**Non è un problema diffuso.** Ho controllato tutti e sei i template PUBBLICATI:
solo il Preventivo ha questo difetto. Il **DDT v3** rende gli indirizzi con le
chiavi giuste (`intestazione`, `via`/`display`, `cap`, `citta`, `prov`, `stato`)
ed è la forma da cui ho ricopiato il frammento del §3.

## 2. Perché non se n'è accorto nessuno (la parte che vale)

Il template usa `s.get("comune")` invece di `s.comune`. Con l'accesso diretto,
`StrictUndefined` avrebbe fatto **fallire il render** al primo preventivo — un
errore rumoroso il giorno stesso del rilascio. Con `.get()` la chiave mancante
diventa stringa vuota e il PDF esce **plausibile ma monco**: il difetto è
sopravvissuto finché un occhio umano non ha letto un indirizzo senza via.

È lo stesso meccanismo per cui il render della fattura era rotto e lo scoprimmo
solo con lo smoke E2E: un fallimento silenzioso su un documento *fiscale* costa
molto più del render che si pianta.

Da qui una proposta, non una richiesta: nei template, per i campi che **devono**
esserci usare l'accesso diretto (`s.intestazione`) e tenere `.get()` per i soli
campi davvero opzionali. Il costo è un render che si pianta in sviluppo; il
beneficio è che non esce un documento sbagliato.

## 3. Cosa chiediamo

Una **versione nuova** del template Preventivo (la v2 è PUBBLICATA e il vostro
trigger `trgfn_template_documenti_versioni_protect_pubblicata` la protegge
giustamente da UPDATE): v3 BOZZA con il blocco corretto, poi pubblicazione.

Blocco da sostituire — stessa struttura, chiavi canoniche, fallback `via` →
`display` come nel DDT:

```jinja
{% if indirizzi %}
  <section class="section">
    <div class="label">Indirizzi documento</div>
    <div class="box">
      {% for ind in indirizzi %}
        {% set s = ind.get("snapshot") or {} %}
        <div{% if not loop.last %} style="margin-bottom: 8px;"{% endif %}>
          <strong>{{ ind.get("tipo_indirizzo_descrizione") or "Indirizzo" }}</strong><br>
          {{ s.get("intestazione") or cliente.denominazione or "" }}
          {% if s.get("via") %}<br>{{ s.get("via") }}
          {% elif s.get("display") %}<br>{{ s.get("display") }}{% endif %}
          {% if s.get("cap") or s.get("citta") or s.get("prov") %}
            <br>{{ [s.get("cap"), s.get("citta")] | select | join(" ") }}{% if s.get("prov") %} ({{ s.get("prov") }}){% endif %}
          {% endif %}
          {% if s.get("stato") %}<br>{{ s.get("stato") }}{% endif %}
        </div>
      {% endfor %}
    </div>
  </section>
{% endif %}
```

Il resto del template non si tocca.

## 4. Due conseguenze da mettere in conto

1. **I preventivi già stampati non cambiano, ed è corretto.** La ristampa fedele
   (chiusa il 2026-08-03) ri-renderizza con la **versione pinnata**: i PDF emessi
   con la v2 continueranno a mostrare l'indirizzo monco. È il comportamento
   voluto — un documento consegnato non si riscrive a posteriori — ma va saputo:
   la correzione vale dal primo documento generato con la v3.
2. **Il `context_schema` della v3** va riallineato se dichiara le chiavi vecchie:
   non l'ho verificato, è nel vostro perimetro.

## 5. Cosa NON chiediamo

* **Nessuna modifica allo snapshot né alle due `fn_snapshot_indirizzo*`**: sono
  la fonte canonica e sono giuste. Il difetto è a valle.
* **Nessun ritocco agli altri cinque template**: verificati, usano le chiavi
  giuste o non hanno l'area indirizzi.
* **Nessuna bonifica dei PDF già generati** (vedi §4.1).

## 6. Definizione di «fatto»

- [ ] template Preventivo v3 PUBBLICATA con il blocco del §3;
- [ ] un preventivo rigenerato mostra intestazione, via, `CAP città (PR)` e stato;
- [ ] la v2 resta OBSOLETA e ri-renderizzabile: la ristampa fedele di un vecchio
      preventivo continua a produrre il documento com'era.
