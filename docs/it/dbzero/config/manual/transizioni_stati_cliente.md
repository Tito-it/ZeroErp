## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_cliente`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
>
[anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
>
Approfondimento funzioni:
>
[anagrafiche.trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/manual/trgfn_clienti_guard_stato_date)

---
### 🎯 Scopo Principale
(latest review 14-10-26)

Elenca i **passaggi di stato ammessi** per un cliente. Un passaggio che non è qui viene rifiutato
(`E_CLIENTE_STATO_TRANSIZIONE_INVALIDA`).

---

### Il percorso (decisione del 2026-10-14)

| Da | A |
| --- | --- |
| pre-contrattuale | attivo, annullato |
| attivo | richiesta di sospensione, sospeso (fatturabile o no), chiuso, chiuso per morosità, chiuso per switch, annullato |
| richiesta di sospensione | attivo, sospeso (fatturabile o no) |
| sospeso | attivo, l'altro sospeso, chiuso, chiuso per morosità, chiuso per switch |
| chiuso, chiuso per morosità, chiuso per switch | chiuso e fatturato |
| chiuso e fatturato, annullato | nessuno: sono finali |

L'aggregante non è nel percorso: resta a catalogo come promemoria.

---

### Campi chiave

* `stato_da_id` → `stato_a_id`: il passaggio;
* `attivo`: un passaggio spento resta scritto ma viene rifiutato.

---

### Note operative

* Le righe si cambiano dal loro file di dati (`transizioni_stati_cliente.csv`), la cui chiave è la
  coppia di stati.
* La creazione di un cliente non passa da qui: un cliente può nascere in qualunque stato, con le
  date che lo stato pretende.
