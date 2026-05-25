jel ima vec online servisa koji nude RAG mozda?

Pogledat ću ovo kao “što već postoji na tržištu” i odvojiti dvije stvari: gotove RAG platforme za korisnike i developer/cloud servise za gradnju vlastitog RAG-a.



Pogledat ću ovo kao “što već postoji na tržištu” i odvojiti dvije stvari: gotove RAG platforme za korisnike i developer/cloud servise za gradnju vlastitog RAG-a.

Thought for 6s

Da, ima ih već dosta. RAG više nije neka egzotika — tržište se već podijelilo u nekoliko kategorija.

1. Gotovi “upload docs and chat” servisi

Ovo su servisi gdje ubaciš dokumente, spojiš izvore tipa Google Drive/Confluence/SharePoint/GitHub i dobiješ enterprise search/chatbot.

Primjeri:

Glean
Vectara
Onyx
Cohere North
Dust
ChatGPT Enterprise / Team s file search / knowledge features
Microsoft Copilot / Foundry IQ / Azure AI Search-based rješenja

Onyx npr. opisuje tržište kao slojeve: turnkey RAG platforme, cloud RAG servisi i infrastruktura/frameworkovi koje sam slažeš.

2. Cloud-managed RAG servisi

Ovo je više za developere i firme koje žele graditi vlastitu aplikaciju, ali bez ručnog slaganja svih komponenti.

Primjeri:

AWS Bedrock Knowledge Bases — spaja foundation modele s internim data sourceovima za RAG.
Azure AI Search / Azure AI Foundry — Microsoft direktno podržava classic i agentic RAG pattern preko Azure AI Searcha.
Google Cloud RAG / Vertex AI / BigQuery + search integrations — Google opisuje RAG kao kombinaciju LLM-a s vanjskim knowledge baseovima i nudi više načina za gradnju na GCP-u.
OpenAI Retrieval / File Search / Vector Stores — OpenAI API ima retrieval preko vector stores, semantic search i file-based workflows.

3. RAG infrastructure servisi

Ovo nisu “gotovi chatbotovi”, nego komponente:

Pinecone
Weaviate
Qdrant Cloud
Elastic
Milvus / Zilliz
Chroma
LlamaIndex Cloud
LangChain / LangSmith
Unstructured.io za parsing dokumenata

Tu sam moraš složiti ingestion, chunking, embeddings, retrieval, reranking, prompt, eval, auth itd.

Za tvoj slučaj — učenje / PoC / firma

Za ozbiljnu firmu bih to gledao ovako:

Najbrži demo: ChatGPT Team/Enterprise, OpenAI File Search, Azure AI Search ili Bedrock Knowledge Bases.

Najbolji enterprise fit ako ste Microsoft-heavy: Azure AI Search + Azure OpenAI / Foundry.

Najbolji cloud-neutral/open-source PoC: Qdrant/Weaviate + LlamaIndex ili LangChain + neki LLM.

Za automotive dokumentaciju i interne manuale: ne bih odmah kupovao turnkey RAG. Prvo bih napravio mali kontrolirani PoC: 20–50 PDF/manual dokumenata, dobar parsing, citati na izvore, evaluacijski set pitanja i mjerenje koliko često halucinira.

Glavna poanta: RAG servis postoji, ali vrijednost nije samo “vector DB + chatbot”. Pravi problem je kvaliteta dokumenata, permissions, citiranje izvora, evaluacija, verzioniranje dokumentacije i sigurnost.



Razdvojit ću odgovor na praktičnu arhitekturu, build-vs-buy odluku i “optimalno za tehničku dokumentaciju”. Pretpostavit ću: on-prem, bez proprietary LLM API-ja, ali open-source modeli/komponente su OK.

Thought for 13s

Da — ne bih gradio cijelu RAG platformu od nule. Za in-house rješenje bih složio platformu od gotovih open-source komponenti, ali bih vlastiti dio gradio oko ingestion pravila, evaluacije, permissions modela, citiranja i UX-a za tehničku dokumentaciju.

Najkraći verdict:

Ne buildati sve sam. Ne uzeti jedan “magic RAG product” i vjerovati mu slijepo. Uzeti gotove komponente i složiti kontrolirani in-house stack.

Preporučena arhitektura

Za tehničku dokumentaciju bih išao ovako:

PDF / HTML / Markdown / Word / code docs
        ↓
document parser / normalizer
        ↓
chunking by structure, not blind fixed-size chunks
        ↓
embeddings + metadata
        ↓
hybrid search: keyword + vector
        ↓
reranking
        ↓
local LLM
        ↓
answer with citations + source snippets
Konkretan stack koji bih ja predložio
PoC / prvi ozbiljan interni demo

UI: Open WebUI ili RAGFlow
LLM serving: Ollama za start, vLLM kasnije za production
Model: Qwen, Llama, Mistral, Gemma — ovisno o hardveru i jezicima
Embeddings: BGE-M3
Vector DB: Qdrant
Orchestration: Haystack ili LlamaIndex
Keyword search: OpenSearch / Elasticsearch / PostgreSQL full-text, ovisno što već imate
Storage: MinIO / filesystem / Git repo / internal doc source
Deployment: Docker Compose za PoC, Kubernetes kasnije

Open WebUI je self-hosted i podržava lokalne model runnere poput Ollama te ima ugrađen RAG engine. To ga čini dobrim za brzi interni demo, ali ne bih na njemu temeljio cijelu enterprise arhitekturu bez dodatne kontrole.

RAGFlow je zanimljiv baš za dokumente jer se fokusira na “deep document understanding”, parsing i citirane odgovore nad kompleksno formatiranim dokumentima. To ga čini dobrim kandidatom za tehničke PDF-ove, manuale i dokumentaciju s tablicama/slikama.

Haystack je bolji ako želiš production-grade, programabilan pipeline gdje imaš jasne komponente za retrieval, routing, generation i custom logiku. To mi je bolji temelj ako firma želi dugoročno razumjeti i kontrolirati sustav.

Za LLM serving: Ollama je super za lokalni start i jednostavno pokretanje open modela, dok je vLLM bolji kandidat za centralni interni API jer nudi OpenAI-compatible server za self-hostane modele.

Za embeddings bih jako ozbiljno gledao BGE-M3, jer podržava multilingual retrieval, dense retrieval, sparse/lexical matching i duže ulaze do 8192 tokena. To je korisno ako imate dokumentaciju na engleskom, njemačkom, možda hrvatskom, plus tehničke termine.

Build vs gotove komponente

Ja bih to podijelio ovako:

Nemoj sam graditi
vector database
embedding model
LLM serving engine
osnovni web chat UI
osnovni parser za PDF/Word/HTML
auth od nule, ako već imate LDAP/AD/OIDC
Trebaš sam kontrolirati / graditi
ingestion pipeline za vaše dokumente
metadata model: document version, product, ECU, software version, standard, release, validity
chunking strategiju
permissions filtering
citation format
evaluation dataset
“answer only from sources” policy
feedback loop: wrong answer → which chunk failed?
document freshness/versioning

To je bitno. RAG nije “ubaci PDF u vector DB”. Za tehničku dokumentaciju, parsing i struktura dokumenta su pola posla.

Optimalno rješenje za tehničku dokumentaciju

Za vaš tip use casea — manuali, automotive docs, tehnička dokumentacija, možda AUTOSAR/Vector/AURIX-style dokumenti — optimalno bih krenuo s ovim:

RAGFlow za brzi document-RAG PoC
+
Qdrant kao vector DB
+
BGE-M3 embeddings
+
local LLM preko Ollama/vLLM
+
mali evaluacijski set pitanja

Ali ako želite dugoročno platformu koju možete širiti i integrirati u firmu:

Haystack custom pipeline
+
Qdrant
+
OpenSearch/Elasticsearch za keyword/hybrid search
+
BGE-M3 embeddings
+
vLLM model serving
+
custom internal UI ili Open WebUI kao frontend

Moja preferenca:

PoC: RAGFlow + Ollama + Qdrant + BGE-M3
Production direction: Haystack + Qdrant/OpenSearch + vLLM + vlastiti ingestion/eval layer

Zašto hybrid search, a ne samo vector search?

Tehnička dokumentacija ima puno stvari gdje semantic search nije dovoljan:

error codes
register names
API function names
AUTOSAR module names
requirement IDs
signal names
exact parameter names
version numbers
acronyms

Tu klasični keyword/BM25 često pobijedi vector search. Zato bih radio hybrid retrieval: keyword + vector + reranker.

Najvažniji dio: evaluacija

Prije nego što itko kaže “ovo radi”, napravio bih 50–100 test pitanja:

pitanje
očekivani dokument
očekivani section/page
idealan odgovor
acceptable answer
forbidden answer
dokument/version iz kojeg mora odgovoriti

Primjeri:

Q: What is the valid range for parameter X?
Expected source: Manual ABC v3.2, section 5.4
Must cite: page/section
Forbidden: answer from v2.8

Bez toga će demo izgledati impresivno, ali nećeš znati je li sustav stvarno pouzdan.

Moj konkretan prijedlog za prvi interni PoC

Ne bih išao odmah široko. Uzeo bih:

20–30 reprezentativnih dokumenata
3 vrste dokumenata: clean PDF, nasty scanned/layout PDF, HTML/Markdown docs
50 pitanja od stvarnih developera/testera
lokalni model, npr. Qwen/Llama klase
BGE-M3 embeddings
Qdrant
RAGFlow za brzi test
paralelno mali Haystack pipeline za usporedbu

Cilj PoC-a ne bi bio “napravili smo chat nad dokumentima”, nego:

Možemo li dobiti citiran, provjerljiv, permission-aware odgovor iz prave verzije dokumentacije?

Finalni izbor

Za tehničku dokumentaciju ja bih preporučio:

Ne build from scratch. Build composed in-house platform.

Prvi korak:

RAGFlow + Qdrant + BGE-M3 + Ollama

Drugi korak, ako PoC pokaže vrijednost:

Haystack-based internal RAG service
+ Qdrant/OpenSearch hybrid retrieval
+ vLLM serving
+ proper eval + permissions + document versioning

To ti daje najbolji balans: brzo pokažeš vrijednost, ali ne zaključaš se u toy demo.



Napravit ću ti ovo kao realan roadmap: prvo mali, ali profesionalan PoC nad jednim javnim dokumentom, zatim skaliranje prema internoj platformi. Za javni dokument predložit ću nešto tehničko i dovoljno “ružno” da test bude stvaran, ne demo-igračka.

Thought for 6s

Da. Krenuo bih ovako: jedan javni tehnički dokument → dobar PoC → interna produkcijska RAG platforma → “svemirski brod” s permissions, eval, verzijama, agentima i integracijama.

Za početni dokument predlažem Infineon AURIX TC3xx User Manual, jer je javno dostupan, tehnički težak, velik, ima tablice, registre, sekcije i realne embedded/automotive pojmove. Infineon ima javnu stranicu s AURIX TC3xx manualima i aplikacijskim bilješkama, uključujući Part 1 i Part 2 user manuale.

0. Što ti moraš osigurati

Za prvi PoC:

Jedan javni dokument
npr. AURIX TC3xx User Manual Part 1 ili neka application note.
Ako želiš lakši start: application note.
Ako želiš realističan test: veliki User Manual.
Jedan Linux stroj
Za početak može laptop/workstation.
Idealno: 32 GB RAM.
GPU nije nužan za embedding/search PoC, ali je koristan za lokalni LLM.
Ako nema GPU-a, možemo prvo raditi retrieval + citati, a generiranje kasnije.
Python okruženje
Python 3.11 ili 3.12.
Git repo.
Docker opcionalno, ali poželjno.
Odgovor na sigurnosno pitanje
Za PoC koristimo javni dokument.
Kasnije za firmu moraš znati: smije li dokumentacija napustiti mrežu? Tko smije vidjeti koji dokument? Kako se verzije dokumenata kontroliraju?
Test pitanja
Minimalno 20.
Bolje 50.
Ne generička pitanja, nego stvarna tehnička pitanja tipa:
“Where is X configured?”
“Which register controls Y?”
“What are the constraints for DMA/cache?”
“Which section explains UCB?”
“What is the valid range/value of parameter Z?”
1. PoC faza — mali, ali dobar

Cilj PoC-a nije “chatbot koji nešto odgovori”.

Cilj je:

Za jedno tehničko pitanje, sustav mora pronaći relevantne dijelove dokumenta, odgovoriti samo iz izvora i dati citate na page/section/chunk.

Step 1 — dokument ingestion

Uzimamo jedan PDF.

Pipeline:

PDF
→ extract text page-by-page
→ preserve page number
→ optionally extract headings
→ save as JSONL

Output:

data/pages.jsonl

Svaki red:

{
  "doc_id": "aurix_tc3xx_part1",
  "page": 123,
  "text": "...",
  "source": "Infineon AURIX TC3xx User Manual Part 1"
}

Bitno: page metadata mora biti očuvan. Bez toga citati ne vrijede puno.

Step 2 — chunking

Ne raditi samo “1000 znakova pa reži”.

Za tehničku dokumentaciju:

page-aware chunking
+ heading-aware ako moguće
+ overlap
+ metadata

Chunk metadata:

{
  "doc_id": "aurix_tc3xx_part1",
  "chunk_id": "aurix_tc3xx_part1_p123_c02",
  "page_start": 123,
  "page_end": 124,
  "section": "if detected",
  "text": "..."
}

Za početak je OK:

800–1200 tokens po chunku
100–150 tokens overlap
Step 3 — embeddings

Za in-house/open-source bih krenuo s:

BAAI/bge-m3

Zašto? Dobar je za multilingual i tehnički retrieval, podržava dense retrieval i duže kontekste. BGE-M3 je dokumentiran kao multilingual embedding model s podrškom za dense, sparse i multi-vector retrieval.

Ako želimo jednostavnije za start:

sentence-transformers + bge-small/en ili bge-base/en

Ali za ozbiljniji PoC:

bge-m3

Output ide u:

Qdrant ili Chroma

Za PoC: Chroma je najbrži.
Za ozbiljnije: Qdrant.

Step 4 — semantic search CLI

Prije chatbota napraviti obični search.

Primjer:

python scripts/search_chunks.py \
  --db vector_db \
  --collection aurix_manual \
  --query "DMA cache coherency"

Output mora pokazati:

score
page_start/page_end
source
text snippet

Ovo je jako važno. Ako search ne radi dobro, chatbot neće magično popraviti stvar.

Step 5 — RAG answer CLI

Tek onda:

python scripts/ask.py \
  --db vector_db \
  --collection aurix_manual \
  --query "What does the manual say about DMA cache coherency?"

Answer format:

Answer:
...

Sources:
[1] AURIX TC3xx User Manual Part 1, pages 123–124
[2] AURIX TC3xx User Manual Part 1, page 127

Pravila:

- answer only from retrieved context
- if not enough information, say so
- always cite pages
- no citation = bad answer
Step 6 — evaluation set

Napravimo file:

eval/questions.yaml

Primjer:

- id: q001
  question: "Where is UCB described?"
  expected_pages: [ ... ]
  expected_terms:
    - "User Configuration Block"
    - "UCB"
  must_cite: true

Zatim:

python scripts/eval_rag.py --questions eval/questions.yaml

Za PoC ne trebamo savršenu metriku. Trebamo barem ručno/semiautomatski vidjeti:

retrieval hit?
citation correct?
answer grounded?
wrong version?
hallucination?
2. PoC arhitektura koju bih sada složio

Za prvi dobar PoC:

Python scripts
+ PyMuPDF / pymupdf4llm for extraction
+ custom chunking
+ sentence-transformers / bge-m3 embeddings
+ Chroma or Qdrant
+ local LLM via Ollama
+ CLI ask/search/eval

Ne bih odmah stavljao veliki UI. CLI je bolji za dokazivanje kvalitete.

Minimalni repo:

rag-poc/
  README.md
  requirements.txt
  data/
    raw/
    pages.jsonl
    chunks.jsonl
  scripts/
    extract_pdf.py
    chunk_pages.py
    embed_chunks.py
    search_chunks.py
    ask.py
    eval_rag.py
  eval/
    questions.yaml
  vector_db/
3. Koliko vremena treba?

Realno:

Dobar PoC nad jednim dokumentom

Ako radimo fokusirano:

1–2 dana za osnovni PoC
3–5 dana za dobar PoC
1–2 tjedna za PoC koji se može pokazati ozbiljnim ljudima u firmi

Razlika je velika.

1 dan PoC znači: “radi search i odgovara”.
1 tjedan PoC znači: “ima citate, evaluaciju, dokumentiran pipeline, reproducibilne komande, poznate limite”.
2 tjedna PoC znači: “možeš prezentirati kao ozbiljan interni prijedlog”.

Moj prijedlog:

Tjedan 1: single-document RAG PoC
Tjedan 2: evaluation + cleanup + demo package
4. Korak-po-korak roadmap do “svemirskog broda”
Faza A — Single-document PoC

Scope:

1 PDF
local embeddings
local vector DB
CLI search
CLI ask
citations
small eval

Deliverable:

README + scripts + reproducible result

Success criteria:

- can ingest document from scratch
- can search relevant chunks
- answers cite pages
- refuses when context is insufficient
- 20–50 eval questions tested
Faza B — Multi-document PoC

Dodamo:

10–50 dokumenata
doc_id
document version
document type
source URL/path
metadata filters

Ovdje počinje prava vrijednost.

Metadata primjer:

{
  "product": "AURIX TC3xx",
  "doc_type": "user_manual",
  "version": "v2.0",
  "language": "en",
  "visibility": "public",
  "source": "..."
}

Search mora moći:

search only in product=AURIX
search only in version=v2.0
search only application notes
Faza C — Hybrid search

Dodamo keyword search.

Zašto? Jer tehnički dokumenti imaju:

register names
error codes
function names
requirement IDs
signal names
AUTOSAR module names
numeric values

Vector search često ne uhvati egzaktne stvari dovoljno dobro.

Stack:

Qdrant vector search
+ OpenSearch/Elasticsearch BM25
+ reranker

Result:

vector candidates + keyword candidates → rerank → top context
Faza D — Local LLM serving

Za PoC može Ollama.

Za platformu:

vLLM
OpenAI-compatible local endpoint
one or more approved open-source models

Modeli koje bih testirao:

Qwen2.5 / Qwen3 family
Llama family
Mistral family

Za tehničku dokumentaciju često nije najbitniji “najpametniji” model, nego:

retrieval quality
context quality
citation discipline
low hallucination
Faza E — UI

Tek kad CLI radi dobro.

Opcije:

Open WebUI kao brzi frontend
vlastiti interni frontend kasnije

UI mora pokazati:

answer
citations
source snippets
document/page
confidence / retrieval score
feedback button

Nikako samo “chat bubble”. Za tehničku dokumentaciju korisnik mora moći provjeriti izvor.

Faza F — Permissions

Ovo je enterprise-critical.

Treba riješiti:

user identity
groups
document ACL
chunk-level filtering
audit log

Bitno pravilo:

Permissions filter mora se dogoditi prije slanja contexta LLM-u.

Ne smije se dogoditi:

retrieval na svim dokumentima → LLM vidi zabranjeni context → UI sakrije citat

To je sigurnosno pogrešno.

Faza G — Versioning

Za tehničku dokumentaciju ovo je ogromno.

Treba znati:

koja verzija dokumenta?
od kada vrijedi?
za koji produkt?
za koju software/hardware verziju?
je li dokument deprecated?

Bez toga RAG može dati točan odgovor iz pogrešne verzije. To je opasno.

Faza H — Evaluation platform

S vremenom treba imati:

golden question set
retrieval metrics
answer quality review
hallucination checks
citation correctness
regression tests

Primjer:

make eval

I onda vidiš:

retrieval hit rate: 82%
citation correctness: 76%
grounded answer: 71%
hallucination: 9%
Faza I — Integracije

Kasnije:

Confluence
SharePoint
Git repos
Jama
Polarion
requirements docs
test reports
PDF manuals
code docs

Ali nemoj to raditi prije nego single-document pipeline radi dobro.

Faza J — “Svemirski brod”

To je već interna AI documentation platforma:

document ingestion service
connectors
metadata catalog
hybrid retrieval
reranking
local LLM gateway
permissions
citations
eval dashboard
feedback loop
admin UI
document freshness checks
API for tools
possibly agents for investigation/report generation

Tu više ne pričamo samo o RAG-u, nego o knowledge platformi.

5. Moj optimalni redoslijed

Ja bih radio ovako:

Step 1: single public PDF
Step 2: extract page-aware text
Step 3: chunk with page metadata
Step 4: embed into Chroma/Qdrant
Step 5: semantic search CLI
Step 6: RAG answer CLI with citations
Step 7: 20–50 eval questions
Step 8: try second parser/chunking strategy
Step 9: add hybrid search
Step 10: local LLM serving via Ollama/vLLM
Step 11: small UI
Step 12: internal document pilot
6. Što bih ja sada uzeo kao prvi dokument

Imamo dvije dobre opcije:

Opcija 1 — veliki realistični manual

Infineon AURIX TC3xx User Manual Part 1

Prednost:

realna automotive/embedded dokumentacija
veliki PDF
tablice, sekcije, registri
dobar stres-test

Mana:

težak za prvi PoC
parsing može biti ružan

Infineon javno navodi AURIX TC3xx user manuale i posebno Part 1/Part 2 dokumente.

Opcija 2 — application note

Npr. neka AURIX application note.

Prednost:

manja
lakša za prvi demo
brže se vidi rezultat

Mana:

nije toliko dobar stres-test kao veliki manual

Infineon ima javnu listu AURIX TC3xx application notes, uključujući teme kao functional safety, DMA, ADC, motor control i druge.

Moj prijedlog:

Krenuti s application note ako želiš brz uspjeh.
Krenuti s User Manual Part 1 ako želiš odmah realan test.

S obzirom na tvoj cilj, ja bih uzeo User Manual Part 1, ali bih scope suzio na 20–50 pitanja i par konkretnih tema, npr.:

UCB
DMA
cache coherency
interrupts
memory map
startup/boot
7. Što radimo sljedeće

Sljedeći konkretan korak bih definirao ovako:

TASK 1:
Create local repo structure and implement PDF extraction script.

Input:
AURIX TC3xx User Manual Part 1 PDF

Output:
data/pages.jsonl with page numbers and text

Nakon toga:

TASK 2:
Chunk pages into data/chunks.jsonl with page_start/page_end metadata.

Onda:

TASK 3:
Embed chunks and implement search CLI.

To je zdrav početak. Bez chata, bez UI-ja, bez “AI magije”. Prvo dokazujemo da možemo pouzdano pronaći prave dijelove dokumenta.




Thought for a second

Od prvotno navedenih gotovih komponenti, za naš PoC sam zapravo zadržao samo dio stacka — i to namjerno.

Koristio bih ove:

Komponenta	Uloga u našem PoC-u	Status
Qdrant	Vector DB za embeddings/chunkove	ozbiljniji PoC / production smjer
Chroma	Jednostavniji lokalni vector DB za prvi PoC	brži start
Ollama	Lokalno pokretanje LLM-a za početak	PoC
vLLM	Lokalni OpenAI-compatible LLM server	kasnije / production smjer
BGE-M3	Embedding model	glavni kandidat
Haystack	Programabilan RAG pipeline	production smjer
OpenSearch / Elasticsearch	Keyword/BM25 dio za hybrid search	faza nakon basic PoC-a
Open WebUI	Brzi frontend	tek kad CLI radi
RAGFlow	Alternativni/document-focused PoC alat	opcija za usporedbu, ne nužno glavni put

Ono što nisam stavio u prvi PoC:

Komponenta	Zašto ne odmah
Weaviate	OK alternativa Qdrantu, ali ne trebamo više vector DB-ova odjednom
Pinecone	Cloud/proprietary-ish managed servis, otpada
LlamaIndex Cloud	Cloud, otpada
LangSmith	Proprietary/cloud observability, otpada
Unstructured.io SaaS	Cloud varijanta otpada; lokalni parsing alati su OK
ChatGPT / Claude / Bedrock / Azure / Google	proprietary/cloud AI, otpada po tvom constraintu
Glean / Vectara / Dust / Cohere North	gotove enterprise/cloud platforme, nisu fit za in-house/no proprietary AI constraint

Moj najčišći PoC stack bi zato bio:

Python scripts
+ PyMuPDF / pymupdf4llm
+ Chroma
+ BGE-M3 or smaller BGE model
+ Ollama
+ local open-source LLM

A ozbiljniji interni stack:

Haystack
+ Qdrant
+ OpenSearch/Elasticsearch
+ BGE-M3
+ vLLM
+ Open WebUI or custom UI

Dakle: nisam predložio da odmah uzmemo RAGFlow/Open WebUI kao “platformu koja sve rješava”. Za prvi kvalitetan PoC bih radije složio mali transparentni pipeline da razumijemo svaki korak: extraction → chunking → embeddings → search → answer → citations → eval.



Da, znam gdje ste stali: PDF extraction, page-aware chunking i Chroma semantic search su već prošli; lokalni model je sljedeća prepreka jer ga nemaš od kuće. Sad je pravo pitanje kvaliteta parsinga, ne još LLM.

Thought for 7s

Da, to je istina: gotovi alati često bolje rade extraction od skripte koju napišemo u par iteracija — pogotovo za layout, tablice, headers/footers, multi-column tekst i slike. Ali to ne znači da trebamo baciti naš pipeline.

Moj prijedlog: nastaviti s našim pipelineom, ali zamijeniti/usporediti extraction layer s boljim parserima. Drugim riječima:

naš RAG pipeline ostaje:
extract → pages/chunks → embeddings → search → RAG answer

ali extraction postaje pluggable:
PyMuPDF raw
PyMuPDF4LLM
Docling
Marker
Unstructured
Što mislim o našoj trenutnoj skripti

Za PoC je sasvim OK što smo napravili. Čak je dobro jer razumijemo:

page metadata
chunking
JSONL format
embedding
search
CLI flow

To je vrijedno. Problem je samo što plain PDF text extraction često nije dovoljno dobar za ozbiljnu tehničku dokumentaciju.

Kod tehničkih manuala najčešće pucaju ove stvari:

tablice se raspadnu
header/footer ulaze u svaki chunk
redoslijed teksta bude kriv
lijevi/desni stupac se pomiješaju
captioni se odvoje od slike/tablice
register layout izgubi strukturu
formule i specijalni znakovi se pokvare
page number ostane, ali section context se izgubi

Za RAG je posebno opasno ovo: extraction može izgledati “OK” na oko, ali retrieval kasnije faila jer su tablice i nazivi parametara loše izvučeni.

Koje alate bih sada testirao
1. PyMuPDF4LLM

Ovo je najbliže našem trenutnom pristupu, ali bolje pripremljeno za RAG. PyMuPDF4LLM radi konverziju u strukturirani Markdown/JSON/TXT, ima layout analysis i ne traži GPU.

Prednost:

lagan
brz
local-only
dobar za prvi upgrade
malo mijenja naš postojeći pipeline

Ja bih ovo prvo probao.

2. Docling

Docling je jako zanimljiv za ozbiljniji document conversion: open-source, lokalno izvršavanje, PDF understanding, layout analysis i table structure recognition. Njegov technical report ga opisuje kao MIT-licensed open-source package za PDF conversion, s modelima za layout analysis i table structure recognition.

Prednost:

bolji kandidat za “serious mode”
dobar za kompleksne PDF-ove
struktura dokumenta, tablice, layout

Ovo bih testirao odmah nakon PyMuPDF4LLM.

3. Marker

Marker eksplicitno cilja PDF/document → Markdown/JSON/chunks/HTML i navodi podršku za tablice, forme, jednadžbe, slike, headers/footers i code blocks.

Prednost:

može dati jako dobar Markdown
dobar za dokumente gdje nam je bitna čitljiva struktura

Ali provjerio bih licencu i corporate usability prije nego ga predložimo firmi.

4. Unstructured open-source

Unstructured partitioning izvlači dokument u elemente poput Title, NarrativeText i ListItem, što je korisno ako želimo element-aware chunking umjesto čistog text dumpa.

Prednost:

dobar koncept elemenata
široka podrška formatima
koristan za pipeline

Mana:

može biti dependency-heavy
nekad je setup gnjavaža
Da li nastaviti s našom skriptom?

Da, ali ne kao “final parser”.

Naša skripta treba postati baseline.

Znači:

parser_baseline = current PyMuPDF extraction
parser_candidate_1 = PyMuPDF4LLM
parser_candidate_2 = Docling
parser_candidate_3 = Marker
parser_candidate_4 = Unstructured

Onda ne raspravljamo filozofski “koji je bolji”, nego izmjerimo.

Sljedeći najbolji korak

Ja bih napravio mali parser benchmark nad istim dokumentom.

Repo struktura bi ostala ista, samo dodamo:

scripts/extract_with_pymupdf.py
scripts/extract_with_pymupdf4llm.py
scripts/extract_with_docling.py
scripts/extract_with_marker.py

data/extracted/pymupdf/pages.jsonl
data/extracted/pymupdf4llm/pages.jsonl
data/extracted/docling/pages.jsonl
data/extracted/marker/pages.jsonl

Zatim za svaki parser pokrenemo isti ostatak pipelinea:

extract
chunk
embed
search

I testiramo istih 20 pitanja.

Kako mjeriti kvalitetu extractiona

Ne bih mjerio samo “lijepo izgleda”.

Mjerio bih:

1. Je li page metadata točan?
2. Je li reading order dobar?
3. Jesu li tablice upotrebljive?
4. Jesu li headers/footers uklonjeni?
5. Jesu li section naslovi očuvani?
6. Jesu li register names / parameter names očuvani?
7. Nalazi li search prave stranice?
8. Daje li RAG bolji citirani odgovor?

Najvažnije: retrieval rezultat je bolja metrika od samog extracted texta.

Može parser izgledati ružnije, ali ako search pronalazi prave chunkove — bolji je za RAG.

Moj konkretan verdict

Ne bih nastavio samo s našom ručno pisanom extraction skriptom kao glavnim putem.

Ali bih definitivno nastavio s projektom.

Najbolji smjer:

zadržati naš pipeline
dodati pluggable parsere
usporediti PyMuPDF4LLM, Docling, Marker, Unstructured
odabrati parser na temelju retrieval/eval rezultata

Za prvi sljedeći korak bih uzeo:

1. PyMuPDF4LLM
2. Docling

Ako ta dva ne daju dovoljno bolje rezultate, tek onda Marker/Unstructured.

Moja procjena: za tehničku dokumentaciju će Docling ili Marker vjerojatno dati bolji structure output od naše skripte, ali PyMuPDF4LLM može biti najbolji tradeoff jer je lagan, local-only i blizu postojećeg pipelinea.



Thought for a second

Ne. Ne želiš za svaki dokument ručno isprobavati parser. To bi brzo postalo kaos.

Bolji pristup je:

1. parser benchmark na malom reprezentativnom setu dokumenata
2. odabereš default parser
3. definiraš fallback parsere za problematične tipove
4. uvedeš quality checks nakon extractiona
5. samo dokumenti koji failaju idu u “review/fallback” tok
Kako to izgleda praktično

Ne testiraš parser na 1000 dokumenata jedan po jedan, nego uzmeš recimo 20–30 reprezentativnih dokumenata:

- veliki PDF manual
- application note
- PDF s puno tablica
- PDF s register layoutima
- HTML dokumentacija
- Word dokument
- skenirani PDF ako postoji
- dokument s dva stupca
- dokument s puno slika/captiona

Na njima usporediš npr.:

current PyMuPDF
PyMuPDF4LLM
Docling
Marker
Unstructured

Onda odabereš strategiju.

Tipična strategija koju bih ja koristio

Primjer:

Default parser:
  PyMuPDF4LLM

Fallback for complex PDFs:
  Docling

Fallback for bad tables/layout:
  Marker or Docling

OCR/scanned documents:
  special OCR pipeline

HTML/Markdown:
  native parser, ne PDF parser

Znači ne pitaš svaki put “koji parser?”, nego imaš pravila.

Još bolje: document classification

Prije parsinga možeš napraviti mali “document sniffing” korak:

PDF ima selectable text? → normal parser
PDF je skeniran? → OCR
PDF ima puno tablica? → Docling/Marker
PDF je HTML? → HTML parser
PDF je Markdown? → Markdown parser

To može biti vrlo jednostavno. Ne treba AI za to.

Primjeri signala:

broj znakova po stranici
broj slika po stranici
ima li embedded text
broj tabličnih struktura
je li reading order čudan
ponavljaju li se header/footer linije
Najvažnije: quality gate

Nakon extractiona svaki dokument dobije “quality score”.

Primjeri checkova:

- premalo teksta po stranici
- puno praznih stranica
- previše ponovljenih header/footer linija
- čudni Unicode znakovi
- tablice potpuno spljoštene
- nema section naslova
- chunkovi prekratki ili predugi

Ako score prođe:

document → chunks → embeddings

Ako ne prođe:

document → fallback parser → review queue
Za PoC bih napravio jednostavno

Ne bih odmah gradio veliki parser-router.

Za sada:

1. Usporedimo 2–3 parsera na jednom teškom dokumentu.
2. Dodamo još 5–10 različitih dokumenata.
3. Odaberemo default.
4. Dodamo fallback samo ako vidimo realnu potrebu.

Moj trenutni kandidat:

Default: PyMuPDF4LLM
Fallback: Docling
Special cases: OCR pipeline za skenirane dokumente
Bitna poanta

Parser ne biraš po dokumentu ručno.

Biraš ga po klasi dokumenta.

technical PDF with selectable text → default parser
complex layout/table-heavy PDF → Docling
scanned PDF → OCR
HTML docs → HTML parser
Markdown/docs repo → Markdown parser

To je skalabilno.

Dakle: ne, nećeš isprobavati sve za svaki dokument. Napraviš benchmark jednom, definiraš parser policy, i onda samo mjeriš quality/failure cases.


