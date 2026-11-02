## 📘 Documentazione Concettuale – Tabella `magazzino.trasferimenti_righe`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — la testata
> * [magazzino.lotti](/dbzero/magazzino/tabelle/lotti) — il lotto spostato
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — il pezzo serializzato spostato
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — le posizioni di partenza e di arrivo
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_trasferimento](/dbzero/magazzino/funzioni/fn_posta_trasferimento) — l'operazione che trasforma le righe in movimenti
> * [magazzino.trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata) — le righe seguono lo stato della testata
>
> Guide:
>
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — il meccanismo comune del perimetro

---

### 🎯 Scopo Principale

**Le righe di [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti)**: per
ogni articolo (ed eventualmente lotto o pezzo serializzato) quanto viene spostato (`qta`,
sempre positiva) e, quando servono, l'ubicazione di partenza (`ubicazione_id_da`) e quella di
arrivo (`ubicazione_id_a`). Ogni riga è la **sorgente** della coppia di movimenti di uscita e
di entrata (`TRASFERIMENTO_RIGA`): due righe del registro con la stessa sorgente e due causali.

---

### Lotto e seriale sono chiavi

`lotto_id` ([magazzino.lotti](/dbzero/magazzino/tabelle/lotti)) e `asset_id`
([magazzino.assets](/dbzero/magazzino/tabelle/assets)) sono riferimenti, non testi liberi:
senza, l'operazione non avrebbe niente da passare alla primitiva del registro. Se l'articolo
li pretende (`requires_lotto`, `requires_serial`) è l'operazione a rifiutare una riga senza;
«il lotto è di questo articolo» lo controlla lei, non un CHECK.

Con un pezzo serializzato si sposta **un** pezzo.

---

### Partenza e arrivo non coincidono

Le due ubicazioni di una riga, se ci sono entrambe, sono diverse. Quando la testata sposta
merce dentro lo stesso magazzino le due ubicazioni sono obbligatorie: è la registrazione a
rifiutare una riga che ne manca, perché partenza e arrivo coinciderebbero
(`E_MAG_TRASFERIMENTO_STESSA_POSIZIONE`).

---

### Le righe seguono la testata

Le righe si scrivono con la testata in `DRAFT`; in `CONFIRM` scrive solo l'operazione di
posting; in `POSTED` e `CANCEL` sono congelate (`E_MAG_DOCUMENTO_RIGHE_CONGELATE`).

---

### Chi può vedere e scrivere

Le righe seguono la testata: `rls_trasferimenti_righe_ef_whitelist` risale al trasferimento,
e da lì al magazzino di origine e al suo emittente. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Codici errore

* `E_MAG_DOCUMENTO_RIGHE_CONGELATE`: una riga scritta, cambiata o cancellata con la testata fuori
  da `DRAFT`, salvo l'operazione di posting in `CONFIRM`.
* `E_MAG_TRASFERIMENTO_STESSA_POSIZIONE`: alla registrazione, una riga nello stesso magazzino
  senza le due ubicazioni.

---

### Note di migrazione

* 2026-09-15 — la tabella entra nel primo lotto del magazzino
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.7); `lotto_id` e `asset_id` prendono il posto
  dei due testi liberi `lotto` e `seriale`.
* 2026-09-28 — con il posting del trasferimento arrivano le ubicazioni di partenza e di arrivo
  (`brief-db-magazzino-lotto-3-scarico-da-ddt`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
