## 📘 Documentazione Concettuale – Vista `dbops.vw_parameter_fk_surrogate_dangling`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.parameter_fk_surrogate](/dbzero/config/tabelle/parameter_fk_surrogate) — il registro che dice quali parametri puntano a quale catalogo
> * [config.parameters](/dbzero/config/tabelle/parameters) — i valori di default dei parametri
> * [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides) — i valori sovrascritti
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — dove la vista è iscritta
>
> Approfondimento funzioni:
>
> * [script.fn_check_parameter_fk_surrogate](/dbzero/script/funzioni/fn_check_parameter_fk_surrogate) — la verifica che la vista chiama riga per riga
> * [config.trgfn_parameters_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameters_fk_surrogate_dispatch) — il guard che rifiuta un valore inesistente in scrittura
> * [config.trgfn_parameter_overrides_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameter_overrides_fk_surrogate_dispatch) — lo stesso guard sulle sovrascritture
>
> Guide:
>
> * [Configurazione e gestione dei parametri](/guide/configurazione-e-gestione-parametri) — i parametri e i loro valori

---

### 🎯 Scopo Principale

I parametri — valori di default e sovrascritture — il cui valore **non esiste più** nel catalogo a
cui il parametro rimanda. **Deve restare vuota**: ogni riga è un valore da correggere a mano.

---

### ⭐ Perché serve, se c'è il guard

Alcuni parametri contengono il codice di una riga di catalogo (l'utility di default, lo stile e la
lingua delle note, l'aliquota IVA proposta, il fuso orario…): è una chiave esterna «surrogata»,
dichiarata nel registro `config.parameter_fk_surrogate` invece che con un vincolo. I guard sui
parametri rifiutano un valore inesistente quando si **scrive** il parametro; nessuno però guarda la
**cancellazione** della riga di catalogo. Un parametro che puntava a una riga poi cancellata resta
appeso finché qualcuno non lo corregge, e questa vista lo trova.

Il rimedio è una delle due: correggere il parametro verso un valore valido, oppure ricreare la riga
di catalogo cancellata.

---

### Come decide

Per ogni parametro (e per ogni sovrascrittura) a cui si applica un pattern abilitato del registro, la
vista chiede a `script.fn_check_parameter_fk_surrogate` se il valore esiste nel bersaglio. Un valore
vuoto vale come «nessun valore» e passa. La verifica è viva: ogni interrogazione cerca nel catalogo
di oggi.

⚠️ **La vista e la verifica scelgono il pattern in due modi diversi.** La verifica usa un pattern solo,
il più specifico (prima la corrispondenza esatta, poi il pattern più lungo); la vista abbina invece il
parametro a **ogni** pattern che lo copre. Un parametro coperto da due pattern compare due volte, e
`target`, `matched_pattern` e `matched_mode` di una delle due righe nominano un bersaglio che non è
quello verificato. Il bersaglio vero è quello del pattern più specifico.

---

### Il presidio

Nel catalogo dei presidi è di natura `ZERO`, guardata ogni settimana, e a correggerla è
l'amministratore. Non blocca niente: è diagnostica.

---

### Test

* `db/pgtap/dbops/test-vw-parameter-fk-surrogate-dangling-v1.sql` — una sovrascrittura con un valore
  inesistente, inserita a guard spento, compare nella vista come una riga in più.

---

### Note di migrazione

* 2026-05-02 — nasce col registro delle chiavi esterne surrogate sui parametri, come diagnostica del
  caso che il guard non copre: la cancellazione del bersaglio.

---

{% include-markdown "signature-core.md" %}
