## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_pdp`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> • [config.stati_pdp](/dbzero/config/tabelle/stati_pdp)
>
Approfondimento viste:
> • [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Unisce il **punto di prelievo** al suo indirizzo già normalizzato e alla sua utility, in modo
che chi cerca un PdP non debba ricomporre la catena
`pdp → indirizzo_dettaglio → stradario → comune`.

L'indirizzo non è ricostruito qui: arriva per intero da `anagrafiche.vw_indirizzi_dettaglio`,
compresi `indirizzo_normalizzato`, `via_norm` e le due geolocalizzazioni
(`civic_geoloc` del civico, `street_geoloc` della via). La normalizzazione vive in un posto
solo e questa vista la consuma.

---

### Il PdP può non avere un cliente

Il legame verso `anagrafiche.clienti` è un **`LEFT JOIN`**, ed è corretto così: un punto di
prelievo esiste come entità fisica sul territorio **prima** di essere associato a un cliente,
e continua a esistere dopo che il cliente se n'è andato.

Le altre tre relazioni — indirizzo, utility, stato — sono `JOIN` interni: un PdP senza uno di
quelli non compare affatto. In particolare **un PdP il cui `indirizzo_dettaglio_id` non
risolve sparisce dalla vista**, e sparisce in silenzio.

⚠️ La colonna `cliente_id` c'è, ma **nessun dato del cliente** viene esposto: il `LEFT JOIN`
su `clienti` serve solo a non perdere righe. Per l'anagrafica del cliente si passa da
`vw_clienti_lista`.

---

### ⚠️ Non è `security_invoker` — oggi innocuo

La vista **non** dichiara `WITH (security_invoker = on)`: gira con i diritti del proprietario.
Verificato il 2026-08-21: nessuna delle tabelle lette — `pdp`, `clienti`,
`indirizzi_dettaglio` — ha la RLS attiva, quindi la differenza oggi non produce effetti.

⚠️ Resta la rete mancante: se un domani il PdP entrasse nel perimetro emittente, questa vista
continuerebbe a mostrare tutto, senza errori. Vale lo stesso avvertimento di
`vw_fornitori_dettaglio`.

---

### I nomi delle colonne sono prefissati apposta

`indirizzo_attivo`, `indirizzo_storicizza`, `indirizzo_tx_id`, `indirizzo_data_insert`… Il
prefisso non è decorativo: distingue i campi tecnici **dell'indirizzo** da quelli del PdP, che
in una vista piatta finirebbero altrimenti a collidere. Chi legge `attivo` senza prefisso sta
guardando un campo che qui non esiste.

---

### Consumatori

Nessun consumo diretto dal backend: è letta dentro il livello DB. Come per
`vw_clienti_codice_ba`, cambiarne le colonne non rompe un endpoint — rompe le viste e le
funzioni che la compongono, e quelle non falliscono: restituiscono meno righe.

---

{% include-markdown "signature-core.md" %}
