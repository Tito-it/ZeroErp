## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_contabili_righe`** contiene il dettaglio delle
righe importate/gestite nella testata contabile vendite, con stato di lavorazione
e riferimenti di abbinamento (fattura, billing account).

---

### Campi chiave (semantica)

* `contabile_id`: FK alla testata `pagamenti.vendite_contabili`.
* `riferimento_ente`: riferimento esterno del flusso (CRO/TRN/UID operazione).
* `importo`: importo riga (vincolo `<> 0`).
* `fattura_id`: fattura eventualmente abbinata.
* `billing_account_id`: billing account eventualmente abbinato.
* `stato_id`: stato di lavorazione riga.
* `motivo_sospeso`: dettaglio diagnostico in caso di sospensione.
* `fondo_source_id`: l'**atto di fondo fattura** da cui la riga nasce
  (`vendite.fatture_fondi_fattura_source`). `NULL` su ogni riga che non viene da
  un fondo, cioè sulla maggior parte.
* `scadenza_id`: la **rata** a cui questo denaro è imputato
  (`vendite.fatture_scadenze`). ⭐ L'abbinamento vive **qui**, e non in una
  tabella N:N: la riga è già l'unità di allocazione, e chi paga due rate con un
  bonifico solo fa **due righe** — che è anche il modo in cui la banca lo
  racconta.
* `forzata` / `motivo_forzatura`: la riga è stata registrata **fuori dalla
  capienza**, e qualcuno l'ha confermato. Il motivo è facoltativo.

> ⚠️ **`scadenza_id` è facoltativo di proposito**, e non è una dimenticanza: ci
> sono righe che saldano un documento **senza riferirsi a una rata**. La riga del
> fondo fattura è esattamente quella — è un saldo per trasferimento, ha fattura
> sì e rata no. Il guard sui dati dello stato **non la pretende**, ed è scritto
> così da prima che la colonna esistesse: chi lo legge non deve pensare a una
> svista.
>
> ⭐ **`forzata` è il prezzo di una decisione**: che un cliente paghi più del
> dovuto, o paghi due volte, è un **fatto del mondo** e il database non lo
> dichiara impossibile — lo **segnala**, e se qualcuno conferma registra e lascia
> scritto. Senza traccia, una forzatura è un modo di *nascondere* denaro, non di
> registrarlo. L'elenco a valle è
> [vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza).
>
> ⚠️ Da non confondere `motivo_forzatura` con `motivo_sospeso`: il secondo dice
> perché una riga **non** è stata lavorata, il primo perché è stata lavorata **lo
> stesso**.
>
> ⭐ **`fondo_source_id` è nuova del 21-08-2026, e prima era una stringa dentro
> un JSON** (`meta ->> 'fondo_source_id'`). Non era una relazione: nessuna
> integrità, nessun indice, nessuna garanzia che il valore fosse un id
> esistente — e la leggevano già **tre** funzioni. Quando il progetto ci ha
> appeso sopra una macchina a stati (l'atto passa a `ESEGUITO` leggendo questo
> legame) è diventata portante, e un legame portante si scrive come tale.
>
> ⚠️ La FK è **`NO ACTION`** di proposito: cancellare un atto pretende di aver
> prima cancellato le sue righe. È l'ordine che `vendite.fn_reset_fondi_fattura`
> rispetta spezzando il lavoro in più statement — una FK differita avrebbe
> *nascosto* l'ordine invece di dichiararlo.
>
> ℹ️ Da non confondere con `meta ->> 'origine' = 'FONDO_FATTURA'`, che resta:
> quello dice **da quale processo** nasce la riga, questo **a quale atto**
> appartiene.

---

### Regole principali

* La riga appartiene sempre a una testata (`contabile_id` obbligatorio).
* `stato_id` usa il lookup `pagamenti.vendite_contabili_righe_stati`.
* `importo` non puo` essere zero.
* Centro riscossione/ente di provenienza sono definiti in testata, non in riga.
* Uno stato che pretende l'abbinamento vuole **fattura e cliente** valorizzati
  (bandiera `richiede_abbinamento` sul catalogo degli stati).
* Portando la riga in uno stato **registrato**, l'eventuale atto di fondo
  citato da `fondo_source_id` passa a `ESEGUITO` — lo fa un trigger, non il
  chiamante (`trgfn_vendite_contabili_righe_marca_fondo_eseguito`).

---

### Esempio d’uso

```sql
SELECT r.id, r.contabile_id, r.importo, r.stato_id, r.fattura_id
FROM pagamenti.vendite_contabili_righe r
WHERE r.attivo IS TRUE
ORDER BY r.id DESC
LIMIT 50;
```

---

{% include-markdown "signature-core.md" %}
