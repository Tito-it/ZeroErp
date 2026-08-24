## 📘 Documentazione Concettuale – Tabella `config.tipi_tariffe_ee`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
> • [config.categoria_accisa](/dbzero/config/tabelle/categoria_accisa)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Tipologia di **tariffa del mercato elettrico**. Referenziata da `config.classi_utenze`
(`tipi_tariffa_ee_id`), completa la qualificazione tecnico-commerciale di un'utenza elettrica.

Il suffisso `_ee` dice il perimetro: **energia elettrica**, non gas né idrico. È l'unica
tabella del gruppo utilities che nel nome dichiara la propria utility invece di collegarvisi
con una FK.

---

### ⚠️ Oggi è **vuota**

Misurato il 2026-08-21: **zero righe**, come `config.categoria_accisa`. Predisposizione per il
modello energia, non ancora in esercizio.

---

### `gruppo_tariffa_ee` è il campo che conta

Oltre al `codice` c'è `gruppo_tariffa_ee`, `NOT NULL`: le tariffe del mercato elettrico si
raccolgono in **gruppi** (per potenza impegnata, per fascia oraria, per tipo di utenza), e il
pricing ragiona sul gruppo più spesso che sulla singola tariffa.

⚠️ Il gruppo è una **stringa libera**, non una FK a un vocabolario di gruppi. Finché la
tabella è vuota non produce effetti; quando la si popolerà, nulla impedirà due grafie diverse
dello stesso gruppo — ed è il tipo di divergenza che si scopre quando un raggruppamento
restituisce due righe invece di una.

---

{% include-markdown "signature-core.md" %}
