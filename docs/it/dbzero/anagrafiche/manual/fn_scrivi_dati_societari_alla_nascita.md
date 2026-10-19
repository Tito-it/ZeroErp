## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_scrivi_dati_societari_alla_nascita()`

> 👀 **Vedi anche**
>
> [anagrafiche.dati_societari](/dbzero/anagrafiche/manual/dati_societari) ·
> [fn_crea_soggetto_pg](/dbzero/anagrafiche/manual/fn_crea_soggetto_pg) ·
> [fn_crea_soggetto_pf](/dbzero/anagrafiche/manual/fn_crea_soggetto_pf)

### 🎯 Scopo
(20-10-2026 — brief `brief-db-dati-societari-in-creazione`, changeSet `20261020-01`)

Quando nasce un soggetto, **decide se i suoi dati societari vanno scritti**, e li scrive con il
verbo `fn_scrivi_dati_societari`. La chiamano le due porte di creazione: società ed enti
(`fn_crea_soggetto_pg`) e persone fisiche (`fn_crea_soggetto_pf`). Prima la decisione stava
solo nella prima porta, e la ditta individuale, che passa dalla seconda, perdeva la sezione.
Ora la regola è una sola (regola del 2).

### La regola

* La natura li **pretende** (`dati_societari_policy = REQUIRED`): si scrivono sempre.
* Altrimenti si scrivono se la **sezione c'è**, cioè almeno un campo ha un valore fra forma,
  provincia e numero REA, capitale, canale FE, PEC, codice SDI e data di costituzione. Un testo
  fatto di soli spazi non conta. **Socio unico e liquidazione da soli non contano**: hanno sempre
  un valore, perché se mancano il verbo usa il default dei parametri, e il form li manda anche a
  sezione vuota.
* Una sezione passata a una natura che **non la ammette** (`NONE`, il privato) arriva al verbo, e
  la rifiuta il guard della natura (`E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`). Non viene mai
  scartata in silenzio.

Il BB non aggiunge regole: forma ammessa, REA e capitale dalla forma, canale FE stanno nei trigger
della tabella. Restituisce l'id dei dati societari, oppure `NULL` se non c'era niente da scrivere.

Il soggetto è obbligatorio: se manca, `E_PARAMETRO_INVALIDO`; se non esiste,
`E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` (gli stessi codici del verbo). La funzione è
`SECURITY INVOKER`: la porta di scrittura resta il verbo.

### Test

`db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql`.

---

{% include-markdown "signature-core.md" %}
