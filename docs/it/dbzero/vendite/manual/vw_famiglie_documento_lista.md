## 📘 Documentazione Concettuale – Vista `vendite.vw_famiglie_documento_lista`

> 👀 **Vedi anche**
>
> **Approfondimenti tabelle:**
>
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
>
> **Da dove vengono le due capability:**
>
> • [script.fn_check_famiglia_documento_disattivabile](/dbzero/script/manual/fn_check_famiglia_documento_disattivabile)
> • [script.fn_check_famiglia_documento_struttura_modificabile](/dbzero/script/manual/fn_check_famiglia_documento_struttura_modificabile)

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — vista nata il 2026-09-01)*

**La superficie di lettura del catalogo delle famiglie di documento**: le colonne
del catalogo, quanti registri le portano, e per ogni riga se si può spegnere e se
se ne può cambiare la struttura — **col motivo**, quando la risposta è no.

---

### ⛔ Perché il lookup generico non bastava

`dbops.fn_get_lookup_codici` restituisce cinque colonne — id, codice, codice
interno, descrizione, attivo — e non può portare i default della forma né le
colonne che dicono la natura della famiglia.

⚠️ **Non è un suo difetto**: è generico, e va lasciato generico. Serviva una
superficie dedicata.

---

### ⭐ Tre lettori, una sede

1. **L'elenco del CRUD delle famiglie** — ed è anche la `vista_sql` dichiarata a
   catalogo per la lista `vendite.famiglie_documento`. ⭐ Da quel momento il
   database **valida da sé** ogni `campo_sorgente` del catalogo contro le colonne
   vere di questa vista;
2. **il suo export** in CSV/XLSX, che legge le stesse righe con le stesse
   chiavi;
3. ⭐ **la maschera dei registri**, che da qui prende `prefisso_default` e
   `lunghezza_default` per **precompilare la forma** quando si crea un registro,
   e `colonna_serie` / `presidia_data_documento` per sapere quali campi mostrare.

⛔ Il terzo è quello che toglie da backend e frontend i due letterali `'FATTURA'`
paralleli: dal 2026-09-02 **`ammette_regole_fiscali` È la colonna che risponde a
quella domanda** — quali campi il registro ammette — e `presidia_data_documento`
resta accanto a lei per l'altra, il pavimento di sequenza. ⚠️ Due domande diverse
con la stessa risposta di oggi, tenute distinte apposta.

---

### ⚠️ Il nome delle colonne è un contratto

Il componente della lista legge il valore per `campo_sorgente`, e il generatore
dell'export fa esattamente lo stesso.

⇒ Rinominare una colonna qui **non è un dettaglio interno**: rompe le celle a
video e il file esportato insieme — e lo fa **in silenzio**, con una cella vuota
e una colonna vuota che porta ancora la sua intestazione.

---

### Che cosa aggiunge alle colonne del catalogo

| Colonna | Che cos'è |
| --- | --- |
| `tabella_documento` | schema e tabella in una cella sola: chi guarda l'elenco vuole sapere «dove», non due pezzi da unire |
| `gestisce_serie` | derivata: vera quando la colonna della serie è dichiarata. ⭐ Il frontend deve decidere se **offrire** il campo serie, e quella è una domanda sì/no — il nome della colonna resta accanto, perché è quello che il controllo automatico verifica |
| `n_registri` | ⭐ è il predicato che rende immutabile la struttura |
| `n_registri_attivi` | ⭐ è il predicato che blocca lo spegnimento |
| `rimozione_blocco_*`, `can_disattivare` | «posso spegnerla?», col motivo |
| `struttura_blocco_*`, `can_modificare_struttura` | «posso cambiarle le colonne?», col motivo |

⭐ Mostrare i due conteggi fa **capire il rifiuto prima di provarlo**.

⛔ **Due blocchi, due nomi**: su una famiglia con registri sono spenti entrambi,
ma per motivi diversi. Riusare uno per l'altra domanda mostrerebbe la frase
sbagliata senza che niente fallisca.

---

### ⚠️ Note operative

* **`LEFT JOIN LATERAL … ON TRUE`, non `CROSS JOIN`**: la verifica risponde con
  un elenco **vuoto** quando l'azione è ammessa, e un elenco vuoto non produce
  righe. Con un `CROSS JOIN` sparirebbero dall'elenco proprio le famiglie **senza
  problemi**.
* **L'ordine dei motivi è il contratto**: il guard solleva il **primo**, e il
  tooltip deve mostrare quello stesso. Da qui il `LIMIT 1` su un ordinamento
  esplicito.
* **`security_invoker = on`, e va riscritto a ogni revisione**: l'opzione **si
  azzera** a ogni `CREATE OR REPLACE VIEW`, e una revisione che non la ripete
  trasforma la vista in un bypass della RLS, in silenzio. ⚠️ Qui sotto non c'è
  nessuna tabella con RLS, ma la vista si allinea alle sette liste documento
  esistenti: una vista di elenco che si comporta diversamente dalle altre è una
  trappola per chi scriverà l'ottava.
* **Solo lettura**: le scritture passano dalla madre e dagli aggiornamenti sulla
  tabella, dove i guard sono montati. Una vista aggiornabile sarebbe una seconda
  porta senza portiere.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.8.*
