## 📘 Documentazione Concettuale – Trigger function `script.trgfn_componenti_guard_coerenza_bom`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta base contro cui si valida
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — `is_composito` dell'articolo della riga padre
> * [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — una delle tabelle su cui è montata
> * [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti) — il montaggio con una data di validità al posto della data documento
>
> Approfondimento funzioni:
>
> * [script.trgfn_listini_righe_comp_guard_coerenza_bom](/dbzero/script/funzioni/trgfn_listini_righe_comp_guard_coerenza_bom) — il controllo gemello sui componenti dei listini
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori
>
> Guide:
>
> * [Gestione Listini e Pricing](/guide/gestione-listini) — la distinta base e i componenti di un kit (§5.2)

---

### 🎯 Scopo Principale

La trigger function `script.trgfn_componenti_guard_coerenza_bom` garantisce che ogni riga componente
di un documento di vendita corrisponda a una voce legittima e valida della distinta base (BoM)
dell'articolo della riga padre.

Il controllo sta nel database, così vale qualunque sia la strada che scrive la riga: il backend, una
chiamata diretta, un seed.

---

### I quattro controlli

| # | Che cosa verifica | Errore |
| --- | --- | --- |
| 1 | L'articolo della riga padre è composito (`is_composito`); una riga padre che non si trova vale come non composita | `E_DOC_RIGA_NON_COMPOSITO` |
| 2 | `articolo_componente_id` è una voce della BoM dell'articolo padre | `E_DOC_COMPONENTE_NON_BOM` |
| 3 | `componente_id` è l'articolo che quella voce di BoM indica | `E_DOC_COMPONENTE_ID_INCOERENTE` |
| 4 | La voce di BoM è valida alla data di riferimento della testata | `E_DOC_COMPONENTE_BOM_NON_VALIDA` |

Il controllo 3 è difensivo: `componente_id` ripete un'informazione che la voce di BoM già contiene, e
il trigger impedisce che le due dicano cose diverse.

Il controllo 4 si salta quando la testata non ha la data di riferimento valorizzata: gli altri tre
restano attivi.

Tutti i componenti attivi della BoM possono stare in una riga di documento: la funzione non guarda se
il componente è esposto in fattura.

---

### ⭐ Una funzione, cinque montaggi

La funzione non sa su quale documento lavora: i sei argomenti del montaggio le dicono lo schema, la
tabella della riga padre, la colonna che collega il componente alla riga padre, la tabella della
testata, la colonna che collega la riga padre alla testata e la colonna data della testata.

Le colonne `articolo_componente_id` e `componente_id` invece hanno lo stesso nome su ogni tabella
componenti, e la funzione le legge direttamente.

È montata come trigger `BEFORE INSERT OR UPDATE`, riga per riga, nella fase dei guard (`_a10_`), su
cinque tabelle:

| Tabella componenti | Riga padre | Data di riferimento |
| --- | --- | --- |
| `vendite.preventivi_righe_componenti` | `preventivi_righe` | `preventivi.data` |
| `vendite.contratti_righe_componenti` | `contratti_righe` | `contratti.data` |
| `vendite.ordini_righe_componenti` | `ordini_righe` | `ordini.data` |
| `vendite.ddt_righe_componenti` | `ddt_righe` | `ddt.data` |
| `vendite.offerte_commerciali_eccezioni_componenti` | `offerte_commerciali_eccezioni` | `offerte_commerciali.validita_dal` |

Il montaggio non ha `UPDATE OF`: qualunque modifica della riga ripassa dai quattro controlli.

⚠️ `vendite.listini_righe_componenti` ha le stesse colonne ma **non** usa questa funzione: i
componenti di un listino si legano a una versione di listino, non a una testata con una data, e li
controlla `script.trgfn_listini_righe_comp_guard_coerenza_bom`.

---

### Codici errore

* `E_DOC_RIGA_NON_COMPOSITO` — controllo 1.
* `E_DOC_COMPONENTE_NON_BOM` — controllo 2.
* `E_DOC_COMPONENTE_ID_INCOERENTE` — controllo 3.
* `E_DOC_COMPONENTE_BOM_NON_VALIDA` — controllo 4.

---

### Test

* `script/test-componenti-helpers-v1` — i controlli 1, 2 e 3 provocati con un inserimento su
  `vendite.preventivi_righe_componenti`, e il montaggio su quella tabella. ⚠️ Il controllo 4 non ha
  una prova che lo faccia scattare: il punto che lo nomina passa senza eseguire niente.
* `vendite/test-preventivi-righe-componenti-v1` — la funzione è fra i presidi montati su
  `vendite.preventivi_righe_componenti`.

---

### Note di migrazione

* 2026-05-13 — ritirato il controllo che esigeva il componente esposto in fattura
  (`E_DOC_COMPONENTE_NON_ESPOSTO`): col modello unificato della BoM tutti i componenti attivi generano
  righe, qualunque sia il flag di presentazione in fattura.

---

{% include-markdown "signature-core.md" %}
