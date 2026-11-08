## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_cliente_ddt`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — la tabella su cui è montato, col CHECK di forma della provenienza
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_ddt_guard_cliente_sorgente](/dbzero/vendite/funzioni/trgfn_ddt_guard_cliente_sorgente) — la stessa regola del cliente sulla bolla
> * [vendite.trgfn_resi_guard_ddt_consegnato](/dbzero/vendite/funzioni/trgfn_resi_guard_ddt_consegnato) — il reso nasce solo da una bolla consegnata
> * [vendite.trgfn_resi_normalize](/dbzero/vendite/funzioni/trgfn_resi_normalize) — chi copia dalla bolla billing account, utility e destinatario
>
> Guide:
>
> * [Gestione DDT](/guide/gestione-ddt) — il reso della merce

---

### 🎯 Scopo Principale

Il guard che tiene il reso legato alla sua bolla: il reso nasce solo da una bolla di vendita, e ha
il cliente di quella bolla, anche quando la bolla non ne ha uno.

---

### Il reso nasce solo da una bolla

Il reso registra la merce che torna da una consegna, e la consegna è la bolla: la sua provenienza
è sempre `DDT_VENDITA`. La forma la tiene il CHECK della tabella (la chiave della bolla in
`sorgente_id`); il **tipo** lo fa valere questo guard, perché un CHECK non legge il catalogo dei
tipi. Un reso che dichiara un altro documento d'origine è `E_RESO_SORGENTE_NON_DDT`.

---

### Il cliente è quello della bolla, vuoto compreso

Il billing account del reso è quello della bolla, **vuoto compreso**: dal reso di una bolla di
conto lavoro, che non ha cliente, nasce un reso senza cliente. Se il cliente non è quello della
bolla: `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`.

Il guard gira quando il reso nasce e quando cambiano il suo billing account o la sua provenienza,
in qualunque stato. Il reso non ha un blocco «fuori bozza» sul cliente: la sua bolla è consegnata,
quindi il cliente della bolla è già bloccato, e questo guard tiene il reso uguale a lei.

---

### 🔒 Una bolla che non si trova

Una bolla d'origine dichiarata e **non trovata**, cioè inesistente o di un'altra azienda, è un
errore: `E_DOC_SORGENTE_NON_TROVATA`. Quando il reso **nasce** parla prima
`trgfn_resi_guard_ddt_consegnato`, che una bolla non trovata la rifiuta come «non consegnata».
Questo guard è l'unico a guardare un reso **spostato** su un'altra bolla.

Non è un doppione del guard unico della provenienza (`script.trgfn_guard_sorgente`): quello
verifica che la bolla esista quando si scrive la provenienza; questo fa valere il tipo, scatta
anche quando cambia il solo billing account, e se non vede la bolla rifiuta invece di non
confrontare.

---

### Codici errore

* `E_RESO_SORGENTE_NON_DDT` — la provenienza del reso non è una bolla di vendita.
* `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE` — il billing account del reso non è quello della bolla.
* `E_DOC_SORGENTE_NON_TROVATA` — la bolla dichiarata non c'è, o non si vede.

---

### Test

* `vendite/test-esecutivi-ba-coppia-v1` — test 21 (reso col cliente di un'altra bolla), 35 (reso
  senza cliente da una bolla senza cliente), 37 (reso spostato su una bolla che non esiste).
* `vendite/test-sorgente-testate-bolle-resi-v1` — test 20 (reso che dichiara l'ordine al posto
  della bolla).

---

### Note di migrazione

* 2026-10-10 — una bolla dichiarata e non trovata diventa un errore; prima il guard lasciava
  passare.
* 2026-11-08 — il guard fa valere anche il tipo: la provenienza del reso è solo la bolla; la bolla
  si cerca per `sorgente_id`.

---

{% include-markdown "signature-core.md" %}
