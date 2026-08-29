## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_iva_riga`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_resolve_iva_riga_it](/dbzero/vendite/funzioni/fn_resolve_iva_riga_it)
> • [vendite.fn_get_tipo_utenza_fornitura](/dbzero/vendite/funzioni/fn_get_tipo_utenza_fornitura)
> • [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)
>
**Approfondimento tabelle:**
>
• [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [config.iva](/dbzero/config/tabelle/iva)

---
### 🎯 Scopo Principale
(latest review 30-08-2026)

**È la sede unica della domanda «quale IVA porta questa riga».**

Prima esistevano due risposte indipendenti — una per la riga di documento, una
per la riga di fattura — e in entrambi i casi si leggeva **solo l'articolo**.
Coincidevano *per costruzione*, perché la fonte era la stessa: il giorno che una
delle due avesse imparato qualcosa che l'altra non sapeva, sarebbero divergute su
documenti già emessi.

Questa funzione è **il guscio**. Non contiene la regola fiscale: guarda il paese
delle due parti e passa la domanda all'implementazione di quel paese. Oggi esiste
solo quella italiana, `fn_resolve_iva_riga_it`.

---

### Perché un guscio, se il paese è uno solo

Perché il costo di aggiungerne un secondo lo decide **la firma**, non la logica.
Con una firma che prende solo `(articolo, data)` funziona benissimo in Italia e
obbliga a toccare **ogni chiamante** il giorno che si aggiunge un paese. Con il
paese dentro la firma, quel giorno nasce una `_xx` accanto e nessun chiamante
cambia.

> ⭐ **E l'`ELSE` solleva.** Se il paese dell'emittente non è implementato, la
> funzione si ferma con un errore di dominio. Il precedente da cui questo
> schema è copiato — il dispatcher nazionale che valida codice fiscale e partita
> IVA — quel ramo **non ce l'ha**: su un paese non previsto passa in silenzio,
> cioè non valida niente e nessuno lo sa. Qui si è scelto il contrario.

---

### Regole principali

* `p_articolo_id` e `p_data_riferimento` sono **obbligatori**.
* ⚠️ **La data è un parametro, mai `CURRENT_DATE`**: è la data di effettuazione
  dell'operazione, e su un documento vecchio deve restare quella di allora.
* `p_paese_emittente`, `p_paese_cliente` e `p_e_cessione_beni` sono **opzionali**:
  se non passati, la funzione li **ricava** da emittente, soggetto e articolo.
  Chi li conosce già li passa e risparmia le letture.
* Lo smistamento guarda il **paese dell'emittente**; in assenza si assume `IT`.
* Un paese non implementato **solleva**, non tace.
* ⛔ **Sola lettura.** Non consuma il plafond di un titolo, non scrive niente:
  la ripartizione che ritorna è una **proiezione** sul residuo di adesso.
* ⛔ **Non controlla se il documento è congelato**: quella è una proprietà del
  documento, ed è responsabilità di chi chiama.

---

### Output — è un **composito**, non un numero

Ritorna **una o più righe**, ciascuna con:

| Campo | Cosa dice |
| --- | --- |
| `quota` | la parte di imponibile coperta da questa riga (`NULL` in anteprima) |
| `iva_id` | il codice IVA da applicare |
| `aliquota` | la percentuale, già risolta per lo stato dell'emittente |
| `natura_codice` | la natura dell'operazione (`N1`…`N7`), quando c'è |
| `is_reverse_charge` | se quella natura è un'inversione contabile |
| `esigibilita` | `I` immediata, `D` differita, `S` scissione |
| `split_payment` | se l'imposta la versa il cliente |
| `riferimento_normativo` | la frase da stampare in fattura |
| `origine` | **chi ha deciso**: `ARTICOLO`, `TIPO_UTENZA`, `TITOLO`, `ASSENTE` |
| `titolo_iva_id` | il titolo che ha sostituito l'aliquota, se ce n'è uno |

> ⭐ **Perché un composito e non l'aliquota.** Chi costruisce una riga fiscale ha
> bisogno di tutte queste cose insieme. Se la funzione tornasse il solo numero,
> il chiamante andrebbe a riprendere natura, esigibilità e riferimento normativo
> per conto suo — cioè **ricostruirebbe la decisione fuori dalla sua sede**, che
> è esattamente il problema che questa funzione esiste per chiudere.

> ⚠️ **`esigibilita` e `split_payment` sono TRASPORTATI, non usati.** La scissione
> dei pagamenti non cambia l'aliquota: cambia **chi versa** l'imposta. Non entra
> nella scelta del codice, ma esce nel composito perché chi costruisce la riga
> vuole un oggetto solo.

> ⚠️ **Quando il soggetto non è noto, quei due campi escono `NULL` — insieme.**
> Non è una dimenticanza: senza il cliente il regime di scissione **non è stato
> determinato**, e rispondere «immediata, non scissa» sarebbe un'**affermazione**
> su un documento che potrebbe andare a una Pubblica Amministrazione. «Non lo so»
> si dice, non si tace.

---

### `origine` è la parte che si legge per prima

Serve a chi guarda una riga e vuole sapere **perché** porta quel codice.
`ASSENTE` non è un errore: in bozza una riga senza IVA è legittima, e sarà il
cancello all'emissione a fermarla.

---

### Esempio d'uso

```sql
-- Anteprima nel form: l'operatore ha appena scelto l'articolo
SELECT * FROM vendite.fn_resolve_iva_riga(
  p_articolo_id      => :articolo_id,
  p_data_riferimento => CURRENT_DATE
);

-- La riga vera, con tutto quello che si sa
SELECT * FROM vendite.fn_resolve_iva_riga(
  p_articolo_id          => :articolo_id,
  p_data_riferimento     => :data_documento,
  p_imponibile           => :imponibile,
  p_billing_account_id   => :billing_account_id,
  p_utility_id           => :utility_id,
  p_soggetto_id          => :soggetto_cliente_id,
  p_emittente_fiscale_id => :emittente_fiscale_id
);
```

> ⚠️ **Il risultato può avere DUE righe**, ed è il caso normale quando il plafond
> di una dichiarazione d'intento finisce a metà riga: la prima parte va al titolo,
> il resto torna all'aliquota ordinaria. Chi consuma deve iterare, non prendere
> `LIMIT 1`. L'ordine è parte del contratto: **prima la quota coperta**.

---

{% include-markdown "signature-core.md" %}
