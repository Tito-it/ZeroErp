# Brief DB — il documento trattenuto conta e passa lo stesso

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-09. **A chi:** team DB.
> **Seguito di:** [brief-db-documento-trattenuto-da-un-lotto-vivo](brief-db-documento-trattenuto-da-un-lotto-vivo.md).
>
> **In una riga:** il verdetto «trattenuto da un lotto vivo» funziona, ma due
> strade non lo attraversano: la **card** lo conta ancora, e il **giro di massa**
> lo prende ancora. Il secondo ha già prodotto un lotto.

---

## 1. Come è nato

Collaudo a video di Tid, 2026-09-09, su `09/2026`. La card «Da emettere» dice
**4**; l'elenco sotto ne mostra 3 e sbarra `ORD0036005`, trattenuto da
**LTF-0010331**. Premuto **«Fattura»** sulla card, `ORD0036005` è finito in un
lotto nuovo — **LTF-0010332**, poi annullato.

---

## 2. Che cosa abbiamo misurato

| Sorgente | Dice |
| --- | --- |
| `vw_dash_competenza_gruppi_riepilogo` | `n_gruppi 2 · n_attivita 3 · n_gruppi_trattenuti 1` ✅ esclude |
| `vw_dash_competenza_mensile` — la CARD | `n_attivita 4 · valore 300` 🔴 **include** |
| `fn_list_emittibili_lane` | `ORD0036005` **non** fra i `gruppi_coperti` ✅ esclude |
| `LTF-0010332`, il lotto nato dal gesto | perimetro dichiarato **vuoto** (giro di massa) e un **esito** su `ORD0036005` 🔴 |

⭐ **Il verdetto in sé è corretto**: `emissione_blocco_lotto_codice` punta a
`LTF-0010331` — il lotto **vivo** — e non a `LTF-0010332`, che è annullato.

⚠️ E `ORD0036005` risulta adesso `ERRORE` in **due** lotti.

---

## 3. 🔵 Che cosa serve

1. **Che la card conti come la lista.** Il numero su cui l'operatore decide
   comprende lavoro che non può prendere, e le due cifre convivono sulla stessa
   schermata.
2. **Che il giro non prenda ciò che la lane non ha offerto.** L'esclusione oggi
   vale sull'elenco e non su ciò che il giro poi prende davvero: il lotto qui
   sopra è nato dopo che la lane aveva già escluso quel documento.

---

## 4. ⚪ Una domanda, non una richiesta

La colonna «lotto del tentativo» mostra `LTF-0010332` su tutte e tre le righe,
**anche se quel lotto è annullato**. Tid preferirebbe non vederla in quel caso.

⚠️ Ma il tentativo **è avvenuto**, e quella è l'unica traccia a video che spieghi
perché il documento è tornato disponibile. ⛔ Quello che non regge è com'è
adesso: mostrato come se contasse ancora.

⇒ La scelta è di modello, e la lasciamo a voi e a Tid.
