## 📘 Documentazione Concettuale – Tabella `magazzino.eventi_assets`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.assets](/dbzero/magazzino/tabelle/assets)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Il ciclo di vita di un asset**: installazione, rientro, sostituzione, manutenzione.

Un asset è un bene che esce dal magazzino ma **non smette di essere nostro** — un contatore
installato presso un cliente, un apparato in comodato. Da qui la differenza con una vendita:
la merce si sposta, la proprietà no.

---

### ⭐ L'evento e il movimento sono due cose distinte

L'installazione genera un movimento (`ASSET_INSTALL`, segno −1) e **insieme** un evento qui.
Il movimento dice che la quantità è uscita dal magazzino; l'evento dice **che cosa è
successo all'asset** e dove si trova ora.

Il ledger da solo non basterebbe a rispondere a «dove sono i miei apparati e da quando»: la
giacenza cala e la traccia si perde. Le causali `ASSET_INSTALL` / `ASSET_RIENTRO` sono a
impatto `cmp`, quindi l'uscita **movimenta anche il valore**.

⚠️ Nulla garantisce oggi che i due lati siano scritti insieme: non c'è un verbo unico che
crei evento e movimento in una transazione sola. È una delle cose da chiudere prima di
attivare il dominio.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
