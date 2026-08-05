# Brief BE → DB — il template Preventivo legge lo snapshot indirizzo con le chiavi sbagliate

> 🟢 **CHIUSO — 2026-08-04.** Il DB ha pubblicato la **v3** del template Preventivo
> (changeSet `20260804-61` duplica in bozza, `-66` pubblica via
> `fn_pubblica_template_documento_versione`, che porta la v2 a OBSOLETA).
> ⚠️ Le modifiche **non sono in repo**: vivono solo sul database di test, quindi
> quanto segue è verificato leggendo il DB, non i changelog.
>
> **Verifica BE sul DB di test (2026-08-04), tutti e tre i punti del §6:**
>
> * ✅ v3 `PUBBLICATA` con le chiavi canoniche — `intestazione`, `via`, `cap`,
>   `citta`, `prov`, `stato`;
> * ✅ v2 `OBSOLETA` e ancora ri-renderizzabile (ristampa fedele su versione
>   pinnata: i PDF già emessi restano com'erano — Tid ha confermato che sono
>   tutti di prova);
> * ✅ `context_schema` = `{}` — e non solo sulla v3: **su tutti e sei** i
>   template pubblicati. Il §4.2 si chiude senza lavoro.
>
> **Uno scostamento dal §3, e va bene così.** Il DB ha duplicato la versione
> rinominando le sole chiavi (ancorate a `s.get("…")`, per non distruggere il
> fallback legittimo `cliente.denominazione`), quindi **manca il fallback
> `via` → `display`** che avevamo proposto copiandolo dal DDT. Misurato sui dati
> reali: su **42 snapshot** delle sei tabelle `vendite.*_indirizzi`, `via` è
> presente **sempre** (0 assenze), mentre `display` manca in **26** casi su 42.
> La chiave affidabile è `via`, non `display`: la proposta del §3 aveva
> l'ordine giusto ma sopravvalutava il ripiego. Nessun intervento necessario.
>
> **Segnalazione del DB, confermata:** il template che produce i preventivi ha
> `codice_interno = 'test'` (descrizione «Preventivo», v3 PUBBLICATA). Corpo
> giusto, nome residuo di sviluppo su un oggetto in uso → richiede un brief DB
> dedicato (è un dato, non un DDL).
>
> **Le due domande di ritorno hanno risposta in §7**, misurata: la prima non è
> una scelta ma una slice incompleta, e **metà del lavoro è nostro**.
>
> **Seguito (2026-08-05).** Tid ha deciso: si stampa l'indirizzo su ordini e
> contratti (e offerte, per simmetria). La metà BE è **fatta** — i tre context
> builder espongono `indirizzi` nella forma unica estratta a BB — e il resto è
> passato al DB con
> [brief-db-indirizzi-su-ordini-contratti-offerte.md](../work-in-progress/brief-db-indirizzi-su-ordini-contratti-offerte.md),
> che porta anche la rinomina `test` → `preventivo`.
>
> ---

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** nel PDF del preventivo l'area indirizzi stampa **solo intestazione e
CAP**. Via, città e provincia spariscono — non perché manchino, ma perché il
template le cerca con nomi che nessuno produce.
**Trovato da:** Tid, in-app, 2026-08-04 («Azienda PG Test Natura / 75025»).
**Correlati:** [fn_snapshot_indirizzo](/dbzero/script/funzioni/fn_snapshot_indirizzo) ·
[fn_resolve_indirizzo_documento](/dbzero/script/funzioni/fn_resolve_indirizzo_documento) ·
[brief-design-indirizzi-documenti-vendita](brief-design-indirizzi-documenti-vendita.md)

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

* [x] template Preventivo v3 PUBBLICATA con il blocco del §3;
* [x] un preventivo rigenerato mostra intestazione, via, `CAP città (PR)` e stato;
* [x] la v2 resta OBSOLETA e ri-renderizzabile: la ristampa fedele di un vecchio
      preventivo continua a produrre il documento com'era.

---

## 7. Risposta BE alle due domande di ritorno (2026-08-04)

Misurate sul DB di test e sul codice, non stimate.

### 7.1 Ordine e contratto senza indirizzo sul PDF: non è una scelta

È una **slice incompleta**, e il pezzo che manca è per metà nostro. La catena
si interrompe prima del template:

| Dominio | Snapshot persistito | Contesto documentale | Template |
| --- | --- | --- | --- |
| preventivo | 11 righe | `indirizzi` (lista) | area indirizzi ✅ (v3) |
| ddt-ven | 16 righe | `indirizzi.consegna.*` (dict per ruolo) | area consegna ✅ |
| fattura | 0 righe | `cliente.indirizzo` (stringa pre-composta) | riga cliente ✅ |
| **ord-ven** | **14 righe** | ❌ nessuna chiave `indirizzi` | ❌ nessuna area |
| **contratto** | **1 riga** | ❌ nessuna chiave `indirizzi` | ❌ nessuna area |
| off-comm | 0 righe | ❌ nessuna chiave `indirizzi` | ❌ nessuna area |

Il punto che cambia la diagnosi: **l'indirizzo di ordini e contratti viene già
catturato e congelato** (`vendite.ordini_indirizzi` ha 14 righe di uso reale),
poi il context builder lo lascia cadere —
`ordine_document_context_builder.py`, `contratto_document_context_builder.py` e
`offerta_document_context_builder.py` non espongono nessuna chiave `indirizzi`.
Il template non potrebbe stamparlo nemmeno volendo.

Quindi non è «un template a cui manca un'area»: è un dato raccolto e mai
consegnato a valle. Difficile chiamarla una scelta — una conferma d'ordine
senza luogo di consegna non è un documento che qualcuno ha deciso di volere.

**Ordine dei lavori, se si procede:** prima il BE (le tre chiavi nel contesto,
con la forma unica del §7.2), poi il DB (una versione nuova per ciascuno dei
tre template). Al contrario il template resterebbe a leggere una chiave che non
arriva. **La decisione è di Tid**, ed è la sola cosa che manca per far partire
il brief.

### 7.2 Tre forme per la stessa informazione: nasce da noi, non dai template

I template sono a valle. La divergenza si crea nei **context builder**, dove
ogni dominio dà all'indirizzo una forma diversa — lista di snapshot, dict per
ruolo, stringa pre-composta (colonna «Contesto documentale» della tabella
sopra). Il template può solo adeguarsi a ciò che riceve: chiamarlo un problema
di template sposterebbe la responsabilità dove non è.

Ne discende che il rimedio è nostro, ed è quello che già facciamo altrove: una
sede unica che dia forma all'indirizzo per tutti i domini
(`_indirizzi_documento_helpers.py` esiste già ed è il posto naturale), e i sei
builder che la chiamano invece di reinventarla. Il quarto template scritto
domani troverebbe **una** forma, non tre a caso — che è esattamente la
preoccupazione che ci avete girato, e la condividiamo.

Vale la pena farlo **insieme al §7.1**, non dopo: i tre builder da toccare per
aggiungere gli indirizzi sono gli stessi tre che oggi non ne hanno alcuna forma
— si sceglie la forma una volta sola, sui domini che non hanno nulla da
migrare. Farlo dopo significherebbe scrivere tre forme nuove e poi unificarle.

### 7.3 Sul `.get()` (§2): siamo d'accordo, e la v3 non lo applica ancora

Sottoscrivete la proposta e il DDT vi dà ragione. Registriamo però che la v3
appena pubblicata usa ancora `s.get()` su tutti i campi, inclusi quelli
obbligatori: è coerente con il metodo che avete scelto (duplicare rinominando
le sole chiavi, che è la ragione per cui il fix è arrivato in giornata e senza
rischi), ma il presidio del §2 resta **da applicare**. Naturale farlo quando i
template vengono comunque riscritti — cioè con il §7.1.
