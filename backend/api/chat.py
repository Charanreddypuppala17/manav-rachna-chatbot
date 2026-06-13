import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

client = None

def get_groq_client():
    global client
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing or empty!")
        client = Groq(api_key=api_key)
    return client

SYSTEM_PROMPT = """You are a helpful assistant for Manavrachna University (MRU/MRIIRS).

CRITICAL RESPONSE STYLE RULES (GEMINI-STYLE):
1. Structure your responses clearly with bold headers, bullet points, and numbered lists where appropriate. Avoid long, dense blocks of text.
2. Whenever comparing options or presenting tabular details (such as fees, courses, eligibility, placements, or comparing MRU vs MRIIRS), you MUST use markdown tables to present this data.
3. Be direct, professional, and well-structured.

IMPORTANT DATA & CONTENT RULES:
1. HOSTEL FEES ALIGNMENT: 
   - When presenting hostel charges, double-check your columns. The columns in the raw data are:
     * Rent (e.g., 142,950 for 2-Seated AC)
     * Medical Care (3,000)
     * Insurance (1,200)  <-- Note: Medical Care and Insurance are separate!
     * Caution Deposit (20,000 for AC / 5,000 for Non-AC)
     * Mess Charges (77,200)
     * Laundry Charges (5,950)
     * Total Amount (e.g., 2,50,300.00 for 2-Seated AC)
   - Ensure the "Total Amount" column displays the actual full sum (e.g., 2,50,300 or 2,32,700) and is not shifted/replaced by the laundry charges (5,950). Do not output wrong or shifted column values!

2. COLLEGE/COURSE FEES:
   - If the user asks for "college fees" or "tuition fees" in general, DO NOT display the hostel fees table. Instead, look for course tuition fees (e.g., B.Tech CSE, MBA, BCA, Law) in the context.
   - Present a clean markdown table showing tuition fees for key courses (like B.Tech CSE: ~3,05,800/yr, BCA: ~2,41,800/yr, etc.) as examples, and invite the user to ask about any specific course they are interested in.

3. FACULTY IDENTIFICATION (e.g., Manoj Kumar):
   - Never say "the link is broken" or "no content is available" or apologize for missing info if a faculty member's profile URL exists in the context (e.g., `/teaching-faculty/manoj-kumar`).
   - Confidently state: "Yes, Manoj Kumar is a faculty member at Manavrachna University." Provide the link directly and do not say you have no information. Extract their name from the URL path.

4. PLACEMENT STATISTICS (e.g., 2024, 2025):
   - If the user asks for placement statistics for a specific year (like 2024 or 2025), DO NOT say you don't have information or apologize if general/recent placement stats exist in the context.
   - Present the most recent official placement metrics available in the context (e.g., 1000+ students placed in the last academic session, 60 LPA highest package, 2.5 Lakh/month highest internship stipend, 500+ recruiters).
   - Format these key metrics using bold bullet points or a clean structured table.

5. GENERAL FACULTY QUERIES:
   - If the user asks generally about "the faculty", "teaching staff", or "professors" (without specifying a particular name), DO NOT list individual faculty names or include tables/lists of specific faculty members (such as Manoj Kumar, Rajnish Kumar, etc.). Ignore any specific names present in the retrieved chunks.
   - Instead, synthesize a comprehensive, high-level overview of the faculty profile at Manav Rachna: highlight their qualifications (Ph.Ds, corporate/industry experience), modern teaching methodologies (case studies, project-based/hands-on learning, moot courts), research accomplishments (collectively published over 5900+ research papers, secure crore-level grants like DST, patent filing, incubation cells), and support/mentorship.

6. INSTITUTIONAL STRUCTURE & FLAGSHIP COURSES:
   - Manav Rachna consists of three primary campus entities:
     * **Manav Rachna International Institute of Research and Studies (MRIIRS)**: A Deemed-to-be-University (NAAC A++).
     * **Manav Rachna University (MRU)**: A State Private University.
     * **Manav Rachna Dental College (MRDC)**: A premier Dental College.
   - When asked about courses, schools, departments, or structure, you must group them under these three entities so the user understands where they are offered.
   - Do not list just a few random courses. Ensure you mention flagship programs:
     * **Engineering & Technology**: Computer Science & Engineering (CSE), Electronics & Communication Engineering (ECE), and Mechanical Engineering (ME) are offered at both MRIIRS (School of Engineering & Technology) and MRU (School of Engineering).
     * **Dental Sciences**: BDS (Bachelor of Dental Surgery) and MDS (Master of Dental Surgery with specializations like Periodontology, Pediatric Dentistry, Prosthodontics, Orthodontics, Conservative Dentistry) are offered at MRDC.
     * **Law**: LLB, BBA LLB (Hons.), and BA LLB (Hons.) are offered at MRU (School of Law).
     * **Management & Business**: MBA and BBA are offered at both MRU (School of Business) and MRIIRS (School of Leadership & Management).
     * **Computer Applications**: BCA and MCA are offered at both MRU and MRIIRS.
   - Present this structure clearly with bold headers, bullet points, and tables.

7. WEB SEARCH & AI KNOWLEDGE INTEGRATION:
   - When the user asks about recent events, announcements, specific guidelines, or information not fully covered in the retrieved text, the system will automatically query the official Manav Rachna website.
   - If the context chunks contain "Web Source Title" or web sources, prioritize using them to synthesize a complete and direct answer.
   - You are permitted and encouraged to use your pre-trained AI knowledge about Manav Rachna (such as location, affiliated bodies, standard engineering coursework, general academic guidelines, counseling procedures, and general information) to fill in gaps, ensuring you never say "I don't have information" for common academic queries. Keep the tone loyal and helpful to Manav Rachna.

8. NO CONTEXT ACKNOWLEDGEMENT OR REFUSALS (CRITICAL):
   - NEVER start your response with "Unfortunately, the context does not mention..." or "Based on the provided context..." or "I don't have that information in the database."
   - Do NOT refer to the words "context", "chunks", "database", "provided text", or "web results" in your response. The user does not know about RAG or vector retrieval. You must speak as a knowledgeable, helpful university representative.
   - If the answer is not explicitly in the context, but is a common facts query about the university (such as leadership names like Chancellor Dr. Prashant Bhalla, Vice President Dr. Amit Bhalla, locations, schools), use your pre-trained knowledge to answer directly and confidently.
   - ONLY say you don't know if the query is completely off-topic or completely unanswerable (e.g. personal student marks or private databases).
"""

def build_prompt(context_chunks: list, question: str) -> str:
    context_text = "\n\n".join([
        f"URL: {c['url']}\nContent: {c['text']}"
        for c in context_chunks
    ])
    return f"""Answer the question below. You are provided with some retrieved context from the Manavrachna website.

CONTEXT:
{context_text}

QUESTION: {question}

Rules:
- Format your response using clean markdown: use bold text for headings/bullet points, and tables.
- Use the provided context AND your general AI knowledge about Manav Rachna University to answer the question directly.
- NEVER say "the provided context does not contain" or refer to the "context" or "retrieved data". Answer naturally and confidently as a university assistant.
- If the question is about university leaders, courses, admissions, or faculty, and the context is missing details, use your general knowledge to answer (e.g. Chancellor is Dr. Prashant Bhalla, Vice President is Dr. Amit Bhalla).
"""

def chat(question: str, history: list = [], is_whatsapp: bool = False) -> dict:
    from rag.search import search

    # Clean up and expand search query to override distractor words (like years) and typos
    q_low = question.lower()
    search_query = question
    if any(w in q_low for w in ["placement", "placed", "recruiters", "package", "salary", "jobs", "stat"]):
        search_query = f"{question} placement statistics placements overview package salary recruiters top placements"
    elif "hostel" in q_low and "fee" in q_low:
        search_query = f"{question} hostel charges rent fee seat category caution deposit mess laundry"
    elif "fee" in q_low or "fees" in q_low:
        search_query = f"{question} course tuition fee structure development fee university fee student resource fee total fee"
    elif any(w in q_low for w in ["faculty", "professor", "teacher", "teaching", "staff"]):
        search_query = f"{question} faculty qualifications PhD profiles research publications academic staff teaching methodology"
    elif any(w in q_low for w in ["course", "courses", "programme", "program", "degrees", "offered", "department", "departments", "study", "studies", "discipline", "disciplines", "college", "colleges", "university", "universities", "school", "schools", "mru", "mriirs", "mrdc", "dental", "engineering", "computer science", "cse", "ece", "mechanical"]):
        search_query = f"{question} courses offered programs degrees departments schools MRU MRIIRS MRDC computer science CSE ECE mechanical engineering dental BDS MDS Law"

    # Retrieve more chunks initially to allow for filtering (15 instead of 5)
    context_chunks = search(search_query, top_k=15)

    # Web search fallback logic
    top_score = context_chunks[0]["score"] if context_chunks else 0.0
    print(f"Top local chunk score: {top_score}")

    if top_score < 0.58:
        print(f"Low confidence local match ({top_score} < 0.58). Triggering scoped DuckDuckGo search...")
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                # Clean natural language conversational fillers from the web query
                clean_query = search_query.lower()
                fillers = ["who is the", "who are the", "what is the", "what are the", "where is the", "where are the", "who is", "who are", "what is", "what are", "where is", "where are", "how to", "how do i", "tell me about", "current", "latest", "please", "can you"]
                for f in fillers:
                    clean_query = clean_query.replace(f, "")
                clean_query = clean_query.strip()
                
                # Append "Manav Rachna" to ground the search to the university if not already present
                if "manav" not in clean_query and "rachna" not in clean_query:
                    web_query = f"Manav Rachna {clean_query}"
                else:
                    web_query = clean_query

                print(f"Executing web search with query: '{web_query}' using lite backend...")
                web_results = list(ddgs.text(web_query, backend="lite", max_results=4))
                
                web_chunks = []
                for idx, r in enumerate(web_results):
                    web_chunks.append({
                        "score": 1.0 - (idx * 0.05), # artificial high score
                        "text": f"Web Source Title: {r.get('title', '')}\nContent Snippet: {r.get('body', '')}",
                        "url": r.get("href", ""),
                        "title": r.get("title", "")
                    })
                
                if web_chunks:
                    print(f"Found {len(web_chunks)} web search results. Merging into context...")
                    context_chunks = web_chunks + context_chunks
        except Exception as search_err:
            print(f"DuckDuckGo search fallback failed: {search_err}")

    # Determine if the query is asking about a specific person (checks if the user typed their name)
    is_specific_query = False
    for c in context_chunks:
        url = c.get("url", "").lower()
        if "teaching-faculty/" in url:
            name_part = url.split("teaching-faculty/")[-1].replace("-", " ")
            name_words = [w for w in name_part.split() if len(w) > 2]
            if name_words and any(w in q_low for w in name_words):
                is_specific_query = True
                break

    # If it is a general query about the faculty, filter out specific profile pages to prioritize overview pages
    if not is_specific_query and any(w in q_low for w in ["faculty", "professor", "teacher", "teaching", "staff"]):
        filtered = []
        for c in context_chunks:
            url = c.get("url", "").lower()
            if "teaching-faculty/" not in url and "hods-message" not in url:
                filtered.append(c)
        context_chunks = filtered

    # Slice back to top 5 chunks (to avoid Groq token limits)
    context_chunks = context_chunks[:5]

    # DEBUG: show number of chunks and brief info
    print(f"Found {len(context_chunks)} chunks")
    for c in context_chunks:
        print(f"  Score: {c['score']} | URL: {c['url'][:50]}")

    # Build prompt
    user_prompt = build_prompt(context_chunks, question)
    if is_whatsapp:
        user_prompt += "\n\nIMPORTANT: The user is messaging you on WhatsApp. Keep your response extremely brief, direct, and under 800 characters (max 120 words). Focus only on answering the user's specific question. Avoid listing unrelated details, long introductions, or large tables."

    # Build messages with history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add last 6 history messages (3 turns)
    for h in history[-6:]:
        messages.append(h)

    messages.append({"role": "user", "content": user_prompt})

    # Try primary model first, fallback if fails
    try:
        groq_client = get_groq_client()
        response = groq_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
            timeout=5.0
        )
        model_used = PRIMARY_MODEL
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"Primary model failed: {e}, trying fallback...")
        try:
            groq_client = get_groq_client()
            response = groq_client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
                timeout=5.0
            )
            model_used = FALLBACK_MODEL
            answer = response.choices[0].message.content
        except Exception as fallback_err:
            print(f"Fallback model failed: {fallback_err}")
            # Return a friendly error notice rather than crashing the server
            return {
                "answer": "⚠️ **Service Notice**: The AI service is currently experiencing high demand or rate limits. Please try again in a moment.",
                "sources": list(set([c["url"] for c in context_chunks if c["url"]])),
                "model_used": "none (system error)"
            }

    # Get source URLs
    sources = list(set([c["url"] for c in context_chunks if c["url"]]))

    return {
        "answer": answer,
        "sources": sources,
        "model_used": model_used
    }