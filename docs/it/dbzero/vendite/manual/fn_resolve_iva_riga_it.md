## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_iva_riga_it`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — **il guscio: si chiama quello**
> • [vendite.fn_get_tipo_utenza_fornitura](/dbzero/vendite/funzioni/fn_get_tipo_utenza_fornitura)
>
**Approfondimento tabelle:**
>
• [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti)
> • [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)

---
### 🎯 Scopo Principale
(latest review 30-08-2026)

**La regola italiana**, e solo quella. Dice quale trattamento IVA si applica a una
riga di documento e **in che proporzione**.

> ⛔ **Non si chiama direttamente.** Si passa sempre dal guscio
> `vendite.fn_resolve_iva_riga`, che smista per paese. Chiamare questa
> scavalcando il guscio significa scrivere «Italia» dentro il chiamante, che è
> proprio ciò che il guscio esiste per evitare.

---

### Due stadi, e vanno letti in ordine

**Stadio A — quale aliquota compete alla MERCE.**

1. l'**articolo**, se ha un'opinione (`catalogo.articoli.iva_id`);
2. altrimenti l'**uso della fornitura** (`config.tipi_utenze.iva_id`), raggiunto
   attraverso il contratto attivo;
3. altrimenti `origine = 'ASSENTE'`.

> ⚠️ **L'ordine non è invertibile, e il motivo è preciso.** L'articolo può dire
> «non ho un'opinione» — la sua colonna è nullabile, e il vuoto significa
> qualcosa. `config.tipi_utenze` **non sa dirlo**: applicato per primo si
> prenderebbe anche cauzioni, spese e servizi, che con l'uso della fornitura non
> c'entrano niente.

**Stadio B — un TITOLO del cliente che la sostituisce.**

Un titolo è un documento registrato che dà diritto a un trattamento diverso: una
dichiarazione d'intento, un uso industriale, un'agevolazione. Se ne esiste uno
valido **su questa riga**, il suo codice sostituisce quello dello stadio A.

> ⭐ **«Su questa riga», non «su questo cliente».** Un titolo può essere ristretto
> a un articolo, a un gruppo o a un tipo di voce: un'agevolazione limitata a due
> articoli non agevola le altre otto righe della stessa fattura. È la differenza
> fra un titolo e il vecchio «codice IVA del cliente».

---

### Quando i titoli sono più di uno

Vince **il più specifico**: un titolo sul singolo articolo batte uno che vale per
tutto.

> ⛔ **A parità di specificità la funzione SOLLEVA.** Non sceglie il più recente,
> non prende il primo: se due titoli diversi hanno lo stesso diritto di applicarsi
> alla stessa riga, non c'è niente da scegliere — è un difetto della
> registrazione, e va corretto da chi l'ha fatta. Un'ambiguità risolta
> sull'ordine degli identificativi darebbe una fattura diversa a ogni ricalcolo,
> e nessuno saprebbe mai che c'era una scelta da fare.

---

### Il plafond: due domande, scelte da `p_consumo`

Alcuni titoli — la dichiarazione d'intento — hanno un **tetto di importo**. Su un
titolo così la funzione risponde in due modi:

* **anteprima** (`p_consumo = false`, i documenti): **una riga**, quanto vale il
  **primo euro** — il titolo se ha ancora capienza, l'ordinario dello stadio A se è
  esaurito. È ciò che serve a un form quando l'operatore ha appena scelto
  l'articolo, e la spezzatura non si inventa;
* **consumo** (`p_consumo = true`, il giro del plafond in fattura): **due righe
  sempre**, prima il titolo col suo codice e poi l'ordinario dello stadio A,
  `quota` NULL, **senza leggere il residuo**. `p_consumo` è **in coda** alla
  firma (dal 2026-10-04): le chiamate di prima non cambiano.

⛔ **Nessuna delle due prende un importo.** Fino al 2026-10-04 c'era una terza
domanda, la **proiezione** (`p_imponibile` valorizzato): la spezzatura proiettata
sul residuo di adesso. Il suo unico chiamante era il giro del plafond, passato al
consumo; è stata **ritirata** (`20261004-15`, decisione di Tid: orfana → si
ritira). `p_imponibile` resta nella firma, che non si riordina, e **un valore
qualunque solleva** `E_IVA_RESOLVE_NON_INVOCABILE`: un importo accettato e
ignorato farebbe credere al chiamante di aver avuto una spezzatura. La colonna
`quota` resta, ed esce sempre `NULL`.

> ⭐ **Perché il consumo non guarda il residuo** (decisione C di Tid, 2026-10-04,
> `brief-db-bom-flag-quantita-e-kit-in-fattura` §13): il plafond si consuma sul
> **netto** della fattura, e una riga negativa restituisce capienza alle righe
> prima. Una proiezione riga per riga non può saperlo; lo sa
> [fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe),
> che prende il lock e decide la spezzatura. Per la stessa ragione, a residuo zero
> il titolo resta nella risposta: è la madre a dire che non copre più niente.

> ⚠️ **La parte ordinaria può uscire con `origine = 'ASSENTE'`, ed è corretto**: il
> titolo copre una parte, e sul resto nessuno sa dire l'aliquota. Sarà il cancello
> all'emissione a fermarla.

> ⛔ **La funzione NON consuma il plafond.** È sola lettura.

---

### Cosa NON fa, e non è una mancanza

* **non tocca i bundle**: sui componenti di kit l'aliquota è una scelta di
  composizione già presa, e questa funzione lavora sulla riga;
* **non controlla il congelamento** del documento: è contratto del chiamante;
* **non decide la scissione dei pagamenti né l'esigibilità**: dal 2026-10-01 la
  coppia `esigibilita` / `split_payment` esce da
  [script.fn_esigibilita_iva](/dbzero/script/funzioni/fn_esigibilita_iva), la
  regola unica condivisa col trigger di riga della fattura, chiamata **per
  parte** (le due parti di una riga spezzata dal plafond hanno codici, e quindi
  nature, diverse). Entrano il regime dell'emittente (IVA per cassa), scissione
  e partita IVA del soggetto. ⚠️ Senza emittente, fuori dalla scissione,
  l'esigibilità esce `NULL` (regime non noto) e non più `'I'`.

---

### Errori che solleva

| Codice | Quando |
| --- | --- |
| `E_IVA_RESOLVE_NON_INVOCABILE` | parametri mancanti (anche `p_consumo` passato `NULL`), un importo in `p_imponibile` (con qualunque domanda: la proiezione è ritirata), o articolo inesistente — è un **chiamante rotto**, non un errore dell'operatore |
| `E_IVA_TITOLI_AMBIGUI` | due titoli in pari specificità sulla stessa riga |

---

### Esempio d'uso

```sql
-- ⛔ NON così: si scavalca il guscio.
--    SELECT * FROM vendite.fn_resolve_iva_riga_it(...);

-- ✅ Così:
SELECT * FROM vendite.fn_resolve_iva_riga(
  p_articolo_id          => :articolo_id,
  p_data_riferimento     => :data_documento,
  p_soggetto_id          => :soggetto_cliente_id,
  p_emittente_fiscale_id => :emittente_fiscale_id
);
-- il giro del plafond: in più p_consumo => true in fondo.
-- ⛔ p_imponibile non si passa mai: un valore solleva (proiezione ritirata).
```

---

{% include-markdown "signature-core.md" %}
