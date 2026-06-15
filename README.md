# Manavrachna Assistant — Campus Platform for Manav Rachna University

An intelligent, premium university platform for Manav Rachna University (MRU/MRIIRS). It features a high-performance web crawling pipeline, a custom-built low-memory semantic search engine (RAG) powered by Groq and NumPy, multi-database support (SQLite/PostgreSQL), secure user authentication with Google OAuth integration, and a dedicated WhatsApp integration via Twilio webhook.

Developed by **Charan**. Powered by **Groq + Hugging Face + NumPy + SQLite/PostgreSQL**.

---

## 🚀 Key Features

*   🤖 **Hybrid Semantic RAG Assistant**: Context-aware chatbot powered by Groq (LLaMA-3.3-70B & LLaMA-3.1-8B failover models). It searches official Manav Rachna documents, admissions guidelines, hostels, courses, and faculty directories.
*   ⚡ **Ultra-Lightweight Vector Search**: Employs a custom vector search backend using Hugging Face's serverless Inference API for real-time 384-dimensional query embedding (`all-MiniLM-L6-v2`) and local NumPy similarity computation, keeping runtime RAM footprint to 0MB.
*   🔍 **Smart Web Search Fallback**: Automatically triggers external web search queries scoped to the university domain via DuckDuckGo when local database similarity confidence falls below `0.58`.
*   💬 **WhatsApp Chat Integration**: Accessible directly from WhatsApp via a Twilio webhook integration (`POST /whatsapp`) with automated conciseness formatting and TwiML responses.
*   🔐 **Secure User Authentication**: Custom email/password accounts (with hashed passwords using bcrypt and JWT validation) alongside Google Sign-In (OAuth 2.0) support. Includes a full Guest Mode capability.
*   📦 **Flexible Double-Database Architecture**: Zero-credentials SQLite database (`local_supabase.db`) for immediate local development, with automatic production fallback to PostgreSQL when a `DATABASE_URL` is detected.
*   🕸️ **Custom Async Crawler**: Scalable web crawler built with `crawl4ai` capable of crawling and parsing up to 5,000 pages of the university portal into clean Markdown.

---

## 🛠️ Tech Stack & Architecture

```
                  +----------------------------------------+
                  |          User Browser / PWA            |
                  +-------------------+--------------------+
                                      |
                                      v
                         +------------+------------+
                         |  Next.js 14 / Vercel    |
                         +------------+------------+
                                      |
                                      v
                         +------------+------------+
                         |  FastAPI / Render Cloud |
                         +------+-----------+------+
                                |           |
                                v           v
             +------------------+--+     +--+------------------+
             | NumPy Vectors (RAG) |     | SQLite / PostgreSQL |
             | (vectors.npy/chunks)|     | (local_supabase.db) |
             +---------------------+     +---------------------+
```

*   **Frontend**: Next.js 14 (App Router), React 18, TailwindCSS (Configuration), Vanilla CSS Modules.
*   **Backend**: FastAPI, Uvicorn, Python 3.11.
*   **Vector Retrieval**: Local NumPy cosine similarity lookup (`vectors.npy`) matching metadata in SQLite (`chunks.db`).
*   **Optional Index Database**: Local Qdrant serverless path (`local_qdrant/`) with INT8 scalar quantization to optimize memory during local index rebuilds.
*   **Model API**: Hugging Face Inference API for embedding generation, Groq API (LLaMA 3.3 70B & 8B models) for answering queries.
*   **User/Chat DB**: SQLite (`local_supabase.db`) for local, PostgreSQL (via `psycopg2`) for production deployment.
*   **Integrations**: Twilio API for WhatsApp webhook support.

---

## ⚙️ Local Development Setup

### 1. Prerequisites
*   Node.js (v18+)
*   Python (v3.10+)
*   A Groq Cloud API Key (Get one at [console.groq.com](https://console.groq.com))
*   Hugging Face Token (Get one at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))

---

### 2. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend/` directory with the following variables:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   HF_TOKEN=your_hugging_face_token_here
   GOOGLE_CLIENT_ID=your_google_client_id_here
   # Optional: Set DATABASE_URL to use PostgreSQL in local development
   # DATABASE_URL=postgresql://username:password@localhost:5432/dbname
   ```

5. *(Optional)* Run the web scraper and index build scripts if you want to rebuild the document database:
   ```bash
   # Crawl pages from manavrachna.edu.in
   python crawler/crawl_college.py
   
   # Clean, chunk, and index crawled markdown
   python rag/clean_data.py
   python rag/chunk_data.py
   python rag/build_index.py
   ```
   *Note: If you just want to run RAG search out-of-the-box, the backend automatically extracts and loads the search databases from `rag_data.zip` (containing `vectors.npy` and `chunks.db`) during startup.*

6. Start the FastAPI development server:
   ```bash
   python main.py
   # Or run directly via uvicorn:
   uvicorn main:app --reload --port 8000
   ```
   The API will be available at `http://localhost:8000`.

---

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Configure environmental variables. Create a `.env.local` file in the `frontend/` directory:
   ```env
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id_here
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your web browser.

---

## 📂 Project Structure

```
college-chatbot-v2/
├── backend/
│   ├── api/              # API router endpoints (auth.py, chat.py)
│   ├── crawler/          # Web scraping pipelines (crawl_college.py)
│   ├── data/             # Crawled data and parsed content JSON files
│   ├── db/               # SQLite schemas, user helpers, session tables (database.py)
│   ├── rag/              # RAG search retrieval & index builders (search.py, build_index.py)
│   ├── main.py           # Core entry point (FastAPI server, WhatsApp integration)
│   ├── requirements.txt  # Python package requirements
│   ├── vectors.npy       # Pre-computed NumPy matrix of document vectors
│   └── chunks.db         # SQLite metadata database mapping IDs to text snippets
└── frontend/
    ├── public/           # Static assets, logos, and fonts
    ├── components/       # Custom React widgets (chat.tsx, message.tsx)
    └── app/              # Next.js page routes (login/page.tsx, home/page.tsx, layout.tsx)
```

---

## 🌐 Production Deployment

### 1. Backend (Render / Heroku)
1. Commit and push the repository to GitHub.
2. Link the project to Render or Heroku.
3. Configure the following environment variables:
   *   `GROQ_API_KEY`: *(Your Groq API key)*
   *   `HF_TOKEN`: *(Your Hugging Face API token)*
   *   `DATABASE_URL`: *(Your PostgreSQL database link for production persistence)*
   *   `GOOGLE_CLIENT_ID`: *(Your Google Client ID)*

### 2. Frontend (Vercel)
1. Import the frontend directory on Vercel.
2. In the project settings, add the environment variable:
   *   Key: `NEXT_PUBLIC_API_URL`
   *   Value: `https://your-backend-api-url.onrender.com`
   *   Key: `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
   *   Value: `your_google_client_id_here`
3. Trigger a deploy.
