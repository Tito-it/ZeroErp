## 📘 Documentazione Concettuale – Tabella `acquisti.ordini_righe_fulfillment`

> 👀 **Vedi anche**
>
> • [acquisti.ordini_righe](/dbzero/acquisti/tabelle/ordini_righe)
> • [acquisti.ddt_righe](/dbzero/acquisti/tabelle/ddt_righe)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Il ponte fra riga d'ordine e riga di DDT**: quanto di ciò che era stato ordinato è stato
effettivamente ricevuto.

Ammette evasioni **parziali e multiple**: una riga d'ordine può essere coperta da più
ricezioni in tempi diversi, e ogni ricezione copre una quota.

⭐ È il ponte a rendere possibile la domanda «che cosa manca ancora?»: il residuo è
l'ordinato meno la somma delle quote di fulfillment. Senza il ponte servirebbe uno stato sulla
riga, che andrebbe mantenuto — e che divergerebbe.

---

### ⚠️ È l'equivalente di `vendite.ordini_righe_fulfillment`

Stessa forma, verso opposto: là misura la merce spedita, qui quella ricevuta. In vendite quel
ponte è protetto da `ON DELETE RESTRICT` — niente cancellazioni, solo storni.

⚠️ Che qui valga la stessa policy **va verificato**, non dedotto dalla somiglianza dei nomi.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
