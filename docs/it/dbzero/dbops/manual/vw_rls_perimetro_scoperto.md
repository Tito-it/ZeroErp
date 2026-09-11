## 📘 Documentazione Concettuale – View `dbops.vw_rls_perimetro_scoperto`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.rls_perimetro_debito](/dbzero/dbops/manual/rls_perimetro_debito)
>
Approfondimenti viste:
>
[dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/manual/vw_processi_dominio_senza_difesa)

---
### 🎯 Scopo Principale
(latest review 09-09-2026)

Risponde a una domanda sola:

> **C'è nel database una tabella che dovrebbe mostrare a ciascuna azienda solo
> i propri dati, e non lo fa?**

Ogni riga è una tabella in quella condizione, con accanto **che cosa le manca** e
**se qualcuno se n'era già accorto**.

---

### ⭐ Perché serviva, e non bastava guardare

Perché il difetto non fa rumore. Una tabella che non filtra non dà errori e non
rompe nessuna schermata: **mostra di più**. Non c'è un log da leggere, non c'è
una pagina bianca, non c'è un test che diventa rosso da solo.

⚠️ E una difesa **parziale** è peggio dell'assenza, perché sembra una difesa. È
successo davvero: le note dei documenti erano protette una per una, e si potevano
leggere tutte passando dalla porta accanto — la tabella che le raccoglie tutte.

---

### ⛔ Il perimetro non è un elenco, ed è tutto il punto

La vista non parte da una lista di tabelle da controllare: **se la ricava dai
legami dichiarati nel database**. Se una riga è agganciata a una riga protetta,
anche lei dovrebbe esserlo.

Ne discendono due cose che valgono più della vista stessa:

* una tabella **nuova**, appesa a un documento, compare qui **da sola**, senza
  che nessuno si ricordi di aggiungerla;
* il controllo **si estende**: chiusa una tabella, le sue figlie entrano nel
  perimetro al giro successivo.

⚠️ Perché è scritto così: l'elenco scritto a mano era stato provato, e aveva già
mentito due volte. *Un elenco ha per perimetro ciò che chi lo scriveva aveva in
mente.*

---

### Le tre risposte, e come si leggono

| `stato` | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `DEBITO_DICHIARATO` | qualcuno l'ha già guardata e ha scritto perché resta così | niente, per ora: è un lavoro con un nome |
| `NON_DICHIARATO` | nessuno l'ha guardata | **allarme**: è nata scoperta e non se n'è accorto nessuno |
| `DEBITO_ESTINTO` | la tabella è a posto, ma l'elenco la nomina ancora | togliere la riga dall'elenco: finché resta, fa tacere il controllo su una tabella che potrebbe tornare aperta |

> ⛔ **La regola non è «la vista è vuota».** Oggi non lo è, e non lo sarà per un
> po'. La regola è: **niente fuori da `DEBITO_DICHIARATO`**.

---

### ⚠️ Che cosa questa vista NON dice

Che le regole di filtro siano scritte **bene**. Dice che esistono e che vengono
applicate. Se poi lascino passare le righe giuste lo verificano le prove
funzionali, una per famiglia di documenti.

---

### Esempio d'uso

```sql
-- Le sole righe che chiedono una decisione oggi
SELECT criterio, schema_tabella, nome_tabella, manca, stato
FROM dbops.vw_rls_perimetro_scoperto
WHERE stato <> 'DEBITO_DICHIARATO'
ORDER BY schema_tabella, nome_tabella;

-- Il debito per intero, e da quanto tempo e' li'
SELECT schema_tabella, nome_tabella, data_registrazione, ragione
FROM dbops.vw_rls_perimetro_scoperto
WHERE stato = 'DEBITO_DICHIARATO'
ORDER BY data_registrazione, schema_tabella, nome_tabella;
```

Presidio: `db/pgtap/rls/test-rls-perimetro-scoperto.sql`.
Origine: `docs/it/dev/work-done/brief-db-perimetro-emittente-righe-documento.md` §8 e §10.

---

{% include-markdown "signature-core.md" %}
