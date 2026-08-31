## 📘 Documentazione Concettuale – Vista `vendite.vw_fondi_fattura_da_decidere`

> 👀 **Vedi anche**
>
> **Le due regole che la vista NON riscrive:**
>
> • [vendite.fn_fondo_fattura_proponibile](/dbzero/vendite/funzioni/fn_fondo_fattura_proponibile) — la proposta, la stessa che usa il giro di fatturazione
> • [vendite.fn_check_fondo_fattura_capiente](/dbzero/vendite/funzioni/fn_check_fondo_fattura_capiente) — la capienza, la stessa che usa l'applicazione
>
> **Tabelle:**
>
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — ⚠️ è lei a portare la RLS
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-10

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**I casi di fondo fattura che chiedono una persona.**

Non è un cruscotto e non è una coda di lavoro automatica: è l'elenco delle
situazioni che il database ha deciso di **non** risolvere da sé, perché
risolverle significherebbe muovere denaro senza che nessuno l'abbia deciso.

| `motivo` | Che cosa è successo | Che cosa può fare una persona |
| --- | --- | --- |
| `PROPOSTA_SENZA_ATTO` | la fattura merita un fondo e non ce l'ha | emetterlo, o lasciar perdere |
| `UTILITY_NON_ATTRIBUIBILE` | è nella banda ma **senza utility**: nessun giro la vedrà mai | completare il dato sulla fattura |
| `IMPORTO_NON_CORRISPONDENTE` | il residuo esiste ma **non assomiglia** al documento | capire da dove viene la riga contabile che lo sfonda |
| `NON_PIU_CAPIENTE` | l'atto c'è, ma la sorgente non lo regge più | annullare l'atto, o gestire l'incasso arrivato |

---

### ⭐ La regola di questa vista: presenta, **non sana**

Nessuna riga di questo elenco deve avere un gemello automatico che la corregge da
solo. È il principio che regge tutto il cantiere del fondo: *i fatti si
aggiungono, i saldi si leggono, le decisioni le prende una persona.*

Ed è anche il motivo per cui la vista **non riscrive nessuna regola**: la
proposta la dà `fn_fondo_fattura_proponibile` — la stessa funzione da cui il giro
notturno prende l'importo che scrive — e la capienza `fn_check_fondo_fattura_capiente`,
la stessa che decide se un fondo si applica. Così l'elenco non può raccontare una
cosa diversa da quello che il sistema fa.

---

### ⭐ `IMPORTO_NON_CORRISPONDENTE`: il silenzio reso visibile

Quando il residuo non corrisponde al documento, la generazione **non fa niente**
— ed è corretto: un lotto intero non si ferma per un caso ordinario. Ma «non fare
niente **in silenzio**» è esattamente ciò che questa vista esiste per rendere
visibile.

```text
fattura sorgente:   +8,00
riga contabile:    +40,00     ← qualcuno sta lavorando un incasso che la sfonda
residuo:           −32,00     ← un fondo a CREDITO su un documento a DEBITO
```

Non è «un fondo negativo» (quello è legittimo, è metà della banda): è un fondo
che **racconta un'altra fattura**. Prima di questa vista, nessuno lo sapeva.

---

### 🔴 CONFIGURAZIONE_INCOMPLETA non esiste, ed è una buona notizia

Il piano prevedeva un quinto motivo per le soglie configurate a metà. Dal
2026-08-15 il `CHECK chk_emittenti_fiscali_utilities_soglie_coppia` rende quella
configurazione **non salvabile**: il caso è irraggiungibile.

> Una riga di elenco che non può accadere insegna una cosa falsa a chi la legge —
> e chi la legge la userà per progettarci sopra.

---

### ⚠️ Il vocabolario dei motivi non è presidiato da un `CHECK`

Perché **PostgreSQL non ha vincoli `CHECK` sulle colonne di una vista**
(`WITH CHECK OPTION` governa le scritture su viste aggiornabili: un'altra cosa).

Il vocabolario è chiuso **per costruzione** — quattro letterali nei rami della
`UNION`, nessun dato li produce — e il presidio contro un quinto valore aggiunto
di nascosto è il **pgTAP**, che asserisce l'**insieme** dei motivi distinti e non
la presenza dei quattro. La differenza è tutta lì: un test che verifica «ci sono
i quattro» resta verde anche quando ne compare un quinto.

---

### 🔴 Sicurezza: la reloption non basta

`security_invoker=on` è obbligatorio — `vendite.fatture` ha la RLS operatori,
`fatture_fondi_fattura_source` **no** — e va **ri-specificato a ogni
`CREATE OR REPLACE`**, perché non è visibile in `pg_get_viewdef` e PostgreSQL lo
azzera in silenzio.

Ma il punto delicato è un altro:

> ⚠️ **Il ramo `NON_PIU_CAPIENTE` parte dalla tabella che la RLS non ce l'ha.**
> È protetto dal `JOIN` **INNER** con `vendite.fatture`, non da un filtro proprio.
> Chi un giorno lo trasformasse in `LEFT JOIN`, o lo togliesse perché «i dati
> della fattura non servono in questa colonna», aprirebbe l'elenco ai fondi di
> **tutti** gli emittenti senza accorgersene.

⚠️ Lato backend: va letta con la connessione **dell'utente**, mai con un ruolo di
servizio, altrimenti il perimetro salta comunque.

---

### ⚠️ Due vincoli interni da conoscere prima di modificarla

**1. Il pre-filtro `DEFINITIVA + minimo` è un pezzo di inviluppo scritto in un
secondo posto**, e sta lì perché la vista non ha uno scope mentre
`fn_fondo_fattura_proponibile` è `VOLATILE`: senza, verrebbe chiamata su ogni
fattura del database. **Restringe, non decide** — se un giorno l'inviluppo si
allargasse oltre `minimo`, la vista mostrerebbe meno del vero.

**2. L'ordine dei rami della `UNION` non è libero.** Per non scrivere i tipi a
mano, i rami che non hanno un valore usano `NULL` nudo e prendono il tipo da chi
il valore ce l'ha; PostgreSQL però risolve a coppie, da sinistra, quindi il ramo
che non porta **nessuna** colonna propria (`UTILITY_NON_ATTRIBUIBILE`) deve stare
per ultimo. Chi lo sposta se ne accorge subito: la `CREATE VIEW` fallisce.

---

### Grana e colonne utili

Una riga per **caso**, non per fattura: la stessa sorgente può comparire una sola
volta, perché i quattro rami sono disgiunti per costruzione.

| Colonna | Dove è valorizzata |
| --- | --- |
| `importo_proposto` | solo su `PROPOSTA_SENZA_ATTO` |
| `capienza_attuale` | **sempre** — è il residuo della sorgente adesso |
| `fondo_source_id`, `origine`, `stato_atto`, `importo_atto`, `atto_motivo`, `atto_data` | solo dove un atto esiste (`NON_PIU_CAPIENTE`) |

---

### Esempio d'uso

```sql
-- Quanti casi aperti, per motivo.
SELECT motivo, count(*) AS n
  FROM vendite.vw_fondi_fattura_da_decidere
 GROUP BY motivo
 ORDER BY n DESC;
```

---

{% include-markdown "signature-core.md" %}
