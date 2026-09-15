## 📘 Documentazione Concettuale – Tabella `magazzino.trasferimenti_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — la testata
> • [magazzino.lotti](/dbzero/magazzino/tabelle/lotti), [magazzino.assets](/dbzero/magazzino/tabelle/assets)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Le righe di [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti)**: per
ogni articolo (ed eventualmente lotto o pezzo serializzato) quanto viene spostato (`qta`,
positiva). Ogni riga è la **sorgente** della coppia di movimenti OUT/IN
(`TRASFERIMENTO_RIGA`): due righe del registro con la stessa sorgente e due causali.

### Lotto e seriale sono chiavi

`lotto_id` ([magazzino.lotti](/dbzero/magazzino/tabelle/lotti)) e `asset_id`
([magazzino.assets](/dbzero/magazzino/tabelle/assets)) hanno preso il posto dei due testi
liberi `lotto` e `seriale`: senza, l'operazione non avrebbe niente da passare alla primitiva
del registro. Se l'articolo li pretende (`requires_lotto`, `requires_serial`) è
l'operazione a rifiutare una riga senza; «il lotto è di questo articolo» lo controlla lei,
non un CHECK.

Con un pezzo serializzato si sposta **un** pezzo (`qta = 1`).

### Chi può vedere e scrivere

Le righe seguono la testata: `rls_trasferimenti_righe_ef_whitelist` risale al trasferimento,
e da lì al magazzino di origine e al suo emittente. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
