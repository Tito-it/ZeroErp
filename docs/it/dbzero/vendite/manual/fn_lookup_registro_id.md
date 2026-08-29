## 📘 Documentazione Concettuale – Funzione `vendite.fn_lookup_registro_id`

> 👀 **Vedi anche**
>
> [vendite.fn_get_registro_id](/dbzero/vendite/funzioni/fn_get_registro_id) — l'involucro che solleva
> [vendite.fn_resolve_registro_documento](/dbzero/vendite/funzioni/fn_resolve_registro_documento) — la catena completa
> [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/tabelle/tipi_doc_fiscale_registri)
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> [config.fn_get_natura_doc_fiscale_id](/dbzero/config/funzioni/fn_get_natura_doc_fiscale_id)

---

### 🎯 Scopo Principale

**Cercare il sezionale di numerazione, e basta.**

Data una coppia *(tipo documento, natura)* — più, opzionalmente, utility ed
emittente a raffinare — questa funzione dice su quale registro il documento
andrebbe scritto, con quale serie e con quale politica di data.

⛔ **Non solleva mai.** Chi non trova risponde `NULL`.

```sql
-- il caso normale
SELECT * FROM vendite.fn_lookup_registro_id(
    p_tipo_doc_fiscale_id         => 1,
    p_natura_doc_id               => 1,
    p_utility_id                  => 2,
    p_emittente_soggetto_ruolo_id => 72);

-- e il caso che conta: nessun errore, solo NULL
SELECT * FROM vendite.fn_lookup_registro_id(NULL, NULL, NULL, NULL);
```

---

### ⭐ Perché esiste: una previsione non può uccidere la lista che decora

La Dashboard Competenza mostra, **prima** di premere «fattura», su quale
sezionale finirà il documento e che data porterà. Per farlo deve **cercare** il
registro senza che una ricerca a vuoto diventi un errore.

⛔ E il caso a vuoto **è ammesso dal modello, non è teorico**. Il vincolo
`chk_commesse_attivita_tipo_doc_emittibile` pretende il tipo documento **solo**
su una riga *approvata e non ancora emessa*: su un'attività ancora `DA_APPROVARE`
quella colonna **può essere vuota**, ed è uno dei quattro stadi che la lista
mostra.

Se la vista chiamasse l'involucro, con quel vuoto non otterrebbe una colonna
vuota: **l'intera lista risponderebbe con un errore**, e ogni tentativo di
aprirla lascerebbe una riga nel giornale degli errori.

> ⚠️ Una funzione che *cerca* e una che *ferma* sono due mestieri. Tenerli nello
> stesso corpo obbliga chi ha bisogno del primo a subire il secondo.

---

### ⭐ La forma: lettore puro e involucro

Non è un'invenzione di questo cantiere — è la coppia che il progetto usa già per
l'emittente fiscale:

| Ruolo | Sull'emittente | Sul sezionale |
| --- | --- | --- |
| **lettore puro** — torna `NULL` | `script.fn_get_ba_emittente_sr_id` | **questa funzione** |
| **involucro** — trasforma il `NULL` in errore di dominio | `anagrafiche.fn_get_emittente_fiscale_id` | [`fn_get_registro_id`](/dbzero/vendite/funzioni/fn_get_registro_id) |

La regola è scritta **una volta sola**, nel lettore. Chi legge consuma il
lettore, chi scrive consuma l'involucro.

---

### La regola di ricerca

Il registro si sceglie su **due assi**, con una gerarchia di specificità a
quattro livelli:

| Livello | Il registro combacia su… |
| --- | --- |
| 1 | utility **e** emittente |
| 2 | la sola utility |
| 3 | il solo emittente |
| 4 | né l'una né l'altro — il registro «di chiunque» |

⚠️ **La natura invece è un filtro ESATTO, non un ripiego.** Non esiste «il
registro della natura più vicina»: se il mapping per quella natura non c'è, la
risposta è vuota. Ripiegare sulla fattura emetterebbe una nota di credito nel
registro delle fatture, e nessuno se ne accorgerebbe.

ℹ️ Il livello 4 oggi **non è raggiungibile**, ed è voluto: nessun registro ha
l'emittente vuoto. È la condizione che aveva fatto numerare due aziende diverse
sullo stesso sezionale, ed è presidiata da `test-registri-per-emittente-v1`.

---

### Cosa restituisce, e perché quattro colonne

**Sempre una riga**, anche quando non ha trovato niente.

| Colonna | A cosa serve |
| --- | --- |
| `natura_doc_id` | la natura **risolta** — se non è stata passata, il default per chiave naturale (`FATTURA`) |
| `registro_id` | il sezionale, o `NULL` |
| `serie` | l'eventuale override del mapping |
| `politica_data_documento` | *quando* il documento sarà datato: oggi, oppure a fine mese di competenza |

⭐ **La natura esce perché serve all'involucro.** È così che
`fn_get_registro_id` distingue «natura non risolta» da «registro non trovato»
senza rifarsi il calcolo del default per conto proprio — cioè senza una terza
copia della stessa regola.

⭐ **La politica esce perché è gratis.** La ricerca già unisce
`registri_fatturazione`: restituire anche quella colonna non è lavoro in più, è
restituire ciò che si è già letto invece di far rifare al chiamante una lettura
sulla stessa riga.

⚠️ **La serie esce grezza**, non sostituita dal default del registro. `NULL` qui
significa *«vale il default del sezionale»*, e chi numera lo risolve già da sé.
Sostituirlo qui scriverebbe il default dentro la colonna `serie` di documenti già
emessi, dove oggi c'è vuoto.

---

### Note operative

- **`STABLE`**, e onestamente: legge tre tabelle e nient'altro. Serve perché la
  funzione finisce dentro `vw_dash_competenza_attivita`, che è la base di altre
  quattro viste — da `VOLATILE` il pianificatore non potrebbe nemmeno scartarla
  dai consumatori che quelle colonne non le guardano.
- **Nessun controllo sui parametri.** Un tipo documento vuoto non trova e basta:
  il controllo vive nell'involucro, dove il chiamante è uno scrittore e un buco
  di configurazione **deve** fermare.
- Le tre tabelle lette sono **configurazione**: non hanno regole di visibilità
  per riga, e la loro dimensione è quella del dominio (i sezionali di un'azienda,
  la matrice tipo × natura), non cresce con i documenti.

> 📎 Piano e decisioni: `brief-db-registro-e-data-prevista-in-competenza`, DB-0.
